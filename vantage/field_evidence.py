"""Validate private intake records without admitting training or evaluation labels."""
from datetime import datetime, timezone
import math


def _instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed


def _positive(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def validate_intake(payload, *, now=None):
    """Return metadata-only checks; declarations are not independent verification."""
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
        raise ValueError("Expected schema_version 1.0")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("records must be an array")
    now = now or datetime.now(timezone.utc)
    results, seen = [], set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} must be an object")
        blockers = []
        # IDs and references remain in the private input, not the validation report.
        for key in ("record_id", "field_id", "boundary_ref", "boundary_version",
                    "season_id", "crop", "source_ref", "observer_ref"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                blockers.append(f"missing_{key}")
        identifier = record.get("record_id")
        if isinstance(identifier, str):
            if identifier in seen:
                blockers.append("duplicate_record_id")
            seen.add(identifier)
        kind = record.get("record_type")
        if kind not in {"scouting", "planting", "harvest"}:
            blockers.append("unsupported_record_type")
        source = record.get("source_kind")
        if source not in {"field_observation", "farm_record", "public_report", "draft"}:
            blockers.append("unsupported_source_kind")
        if source in {"public_report", "draft"}:
            blockers.append("lead_only_requires_field_follow_up")
        if record.get("permission_status") != "approved":
            blockers.append("permission_not_approved")
        dates = {}
        for key in ("observed_at", "received_at", "reviewed_at"):
            try:
                dates[key] = _instant(record[key])
                if dates[key] > now:
                    blockers.append(f"future_{key}")
            except (KeyError, ValueError, TypeError, AttributeError):
                blockers.append(f"invalid_{key}")
        for earlier, later in (("observed_at", "received_at"), ("received_at", "reviewed_at")):
            if earlier in dates and later in dates and dates[earlier] > dates[later]:
                blockers.append(f"{later}_before_{earlier}")
        reviewer = record.get("reviewer_ref")
        if not isinstance(reviewer, str) or not reviewer.strip():
            blockers.append("missing_reviewer_ref")
        elif reviewer == record.get("observer_ref"):
            blockers.append("reviewer_matches_observer")
        if kind == "scouting" and record.get("finding") not in {"useful_finding", "no_useful_finding", "uncertain"}:
            blockers.append("missing_or_invalid_finding")
        if kind == "scouting" and record.get("finding") == "uncertain":
            blockers.append("finding_requires_adjudication")
        measured_yield = None
        if kind == "harvest":
            harvest = record.get("harvest")
            harvest = harvest if isinstance(harvest, dict) else {}
            for key in ("mass", "area"):
                if not _positive(harvest.get(key)):
                    blockers.append(f"invalid_harvest_{key}")
            if harvest.get("mass_unit") not in {"kg", "t"}:
                blockers.append("unsupported_mass_unit")
            if harvest.get("area_unit") not in {"ha", "m2"}:
                blockers.append("unsupported_area_unit")
            for key in ("measurement_ref", "measurement_method", "moisture_basis"):
                if not isinstance(harvest.get(key), str) or not harvest[key].strip():
                    blockers.append(f"missing_{key}")
            if harvest.get("extent") not in {"partial", "whole_field"}:
                blockers.append("missing_harvest_extent")
            if not any(b in blockers for b in ("invalid_harvest_mass", "invalid_harvest_area", "unsupported_mass_unit", "unsupported_area_unit", "missing_moisture_basis")):
                tonnes = harvest["mass"] / (1000 if harvest["mass_unit"] == "kg" else 1)
                hectares = harvest["area"] / (10000 if harvest["area_unit"] == "m2" else 1)
                measured_yield = tonnes / hectares if hectares > 0 else float("inf")
                if not math.isfinite(measured_yield):
                    measured_yield = None
                    blockers.append("nonfinite_derived_yield")
        results.append({"record_index": index, "ready_for_manual_review": not blockers,
                        "blockers": blockers, "measured_yield_t_per_ha": measured_yield,
                        "training_eligible": False, "evaluation_eligible": False})
    return {"schema_version": "1.0", "validated_at": now.isoformat(),
            "record_count": len(records), "ready_for_manual_review_count": sum(r["ready_for_manual_review"] for r in results),
            "independently_verified_outcomes": 0, "records": results,
            "warnings": (["No records supplied"] if not records else []) +
            ["Checks validate declarations only; no automatic label admission or independent verification.",
             "Measured yield describes the submitted harvested area and moisture basis; no field extrapolation."]}
