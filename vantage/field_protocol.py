"""Freeze declared research visits and reconcile intake; never admit labels."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math

from vantage.evaluation import sampling_plan
from vantage.field_evidence import _instant, validate_intake


UNIT_TEXT = ("unit_id", "field_id", "boundary_ref", "boundary_version", "season_id",
             "crop", "spatial_group", "source_run_ref", "acquired_at", "available_at", "status")
UNIT_KEYS = set(UNIT_TEXT) | {"model_score", "baseline_score"}
PROTOCOL_KEYS = {"cohort_id", "prediction_frozen_at", "rubric_ref", "held_out_protocol_ref",
                 "capacity", "seed", "units"}
LINK_KEYS = ("field_id", "boundary_ref", "boundary_version", "season_id", "crop")


def _text(row, keys):
    for key in keys:
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f"Nonempty {key} required")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def freeze_protocol(spec, *, now=None):
    """Validate declared availability, then freeze a stratified visit sample.

    A local hash detects changed content; it does not establish historical custody.
    Input is deliberately allowlisted to exclude outcomes and free-text findings.
    """
    now = now or datetime.now(timezone.utc)
    if not isinstance(spec, dict) or set(spec) != PROTOCOL_KEYS:
        raise ValueError("Protocol keys must match the documented outcome-free contract")
    _text(spec, ("cohort_id", "prediction_frozen_at", "rubric_ref", "held_out_protocol_ref"))
    frozen = _instant(spec["prediction_frozen_at"])
    if frozen > now:
        raise ValueError("Prediction freeze cannot be in the future")
    if type(spec["seed"]) is not int:
        raise ValueError("Seed must be an integer")
    units = spec["units"]
    if not isinstance(units, list) or not units:
        raise ValueError("Nonempty declared cohort required; no live units are invented")
    for unit in units:
        if not isinstance(unit, dict) or set(unit) != UNIT_KEYS:
            raise ValueError("Unit keys must match the documented outcome-free contract")
        _text(unit, UNIT_TEXT)
        if not (_instant(unit["acquired_at"]) <= _instant(unit["available_at"]) <= frozen):
            raise ValueError("Inputs must be acquired and available before prediction freeze")
        if unit["status"] == "unavailable":
            if unit["model_score"] is not None or unit["baseline_score"] is not None:
                raise ValueError("Unavailable units must have null scores")
        else:
            for key in ("model_score", "baseline_score"):
                value = unit[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("Available units require finite model and baseline scores")
    normalized = deepcopy(spec)
    normalized["units"] = sorted(normalized["units"], key=lambda unit: unit["unit_id"])
    plan = sampling_plan(normalized["units"], spec["capacity"], spec["seed"])
    if not plan["selected"]:
        raise ValueError("No eligible visits; retain unavailable units in the evidence review")
    return {"schema_version": "vantage-field-protocol-1", "protocol_sha256": _digest(normalized),
            "spec": normalized, "sampling_plan": plan,
            "created_at": now.isoformat(), "training_eligible": False,
            "complete_cohort_evaluator_compatible": False,
            "limitations": ["Declarations do not prove historical availability, training exclusion or source authenticity.",
                            "The stratified sample requires a separate design-based analysis; do not pass it to the complete-cohort evaluator.",
                            "Local hashes are not a trusted timestamp or an access-controlled registry."]}


def verify_protocol(protocol, *, now=None):
    if not isinstance(protocol, dict) or protocol.get("schema_version") != "vantage-field-protocol-1":
        raise ValueError("Unsupported frozen protocol")
    rebuilt = freeze_protocol(protocol.get("spec"), now=now)
    if (protocol.get("protocol_sha256") != rebuilt["protocol_sha256"]
            or protocol.get("sampling_plan") != rebuilt["sampling_plan"]):
        raise ValueError("Frozen protocol hash or sampling plan mismatch")
    return rebuilt


def collection_form(protocol, *, now=None):
    """Return only field linkage and empty intake fields; no scores/strata."""
    verified = verify_protocol(protocol, now=now)
    units = {u["unit_id"]: u for u in verified["spec"]["units"]}
    records = []
    for selected in verified["sampling_plan"]["selected"]:
        unit = units[selected["unit_id"]]
        record = {key: unit[key] for key in LINK_KEYS}
        record.update(unit_id=unit["unit_id"], record_id=None, record_type="scouting",
                      source_kind="field_observation", permission_status=None, source_ref=None,
                      observer_ref=None, reviewer_ref=None, observed_at=None, received_at=None,
                      reviewed_at=None, finding=None)
        records.append(record)
    # Randomization is reproducible in the private protocol; form order is neutral by ID.
    return {"schema_version": "1.0", "cohort_id": verified["spec"]["cohort_id"],
            "protocol_sha256": verified["protocol_sha256"],
            "rubric_ref": verified["spec"]["rubric_ref"],
            "records": sorted(records, key=lambda r: r["unit_id"])}


def reconcile_intake(protocol, intake, *, now=None):
    """Keep every selected unit, including missing/conflicted/ineligible visits."""
    now = now or datetime.now(timezone.utc)
    verified = verify_protocol(protocol, now=now)
    checks = validate_intake(intake, now=now)
    if (intake.get("cohort_id") != verified["spec"]["cohort_id"]
            or intake.get("protocol_sha256") != verified["protocol_sha256"]
            or intake.get("rubric_ref") != verified["spec"]["rubric_ref"]):
        raise ValueError("Intake must name the frozen cohort, protocol hash and finding rubric")
    selected = {s["unit_id"] for s in verified["sampling_plan"]["selected"]}
    units = {u["unit_id"]: u for u in verified["spec"]["units"]}
    frozen = _instant(verified["spec"]["prediction_frozen_at"])
    counts = Counter(r.get("unit_id") for r in intake["records"] if isinstance(r.get("unit_id"), str))
    linked = {}
    rejected = []
    for record, check in zip(intake["records"], checks["records"]):
        unit_id = record.get("unit_id")
        if not isinstance(unit_id, str) or unit_id not in selected:
            rejected.append({"record_index": check["record_index"], "blockers": ["unit_not_in_selected_plan"]})
            continue
        blockers = list(check["blockers"])
        if counts[unit_id] != 1:
            blockers.append("multiple_records_for_selected_unit")
        if record.get("record_type") != "scouting":
            blockers.append("scouting_record_required")
        for key in LINK_KEYS:
            if record.get(key) != units[unit_id][key]:
                blockers.append(f"frozen_{key}_mismatch")
        if "invalid_observed_at" not in blockers and _instant(record["observed_at"]) <= frozen:
            blockers.append("visit_must_follow_prediction_freeze")
        linked.setdefault(unit_id, []).append({"record_index": check["record_index"], "blockers": blockers})
    visits = []
    for unit_id in sorted(selected):
        records = linked.get(unit_id, [])
        state = "missing" if not records else ("ready_for_adjudication" if len(records) == 1 and not records[0]["blockers"] else "withheld")
        visits.append({"unit_id": unit_id, "state": state, "records": records})
    return {"schema_version": "vantage-field-reconciliation-1", "validated_at": now.isoformat(),
            "protocol_sha256": verified["protocol_sha256"], "selected_count": len(selected),
            "state_counts": {state: sum(v["state"] == state for v in visits)
                             for state in ("missing", "withheld", "ready_for_adjudication")},
            "visits": visits, "rejected_records": rejected,
            "training_eligible": False, "evaluation_eligible": False,
            "independently_verified_outcomes": 0,
            "limitation": "Readiness checks declarations only; missing visits are not negatives. No labels or performance estimates are produced."}
