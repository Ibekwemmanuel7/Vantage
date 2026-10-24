"""Exact finite-cohort ranking bounds conditional on declared adjudications.

No imputation, sampling estimator, confidence interval or model-label export.
"""
from collections import Counter
from datetime import datetime, timezone

from vantage.field_evidence import _instant
from vantage.field_protocol import reconcile_intake, verify_protocol


def compare_scouting_bounds(protocol, intake, adjudications, *, now=None):
    """Bound precision and paired difference while unresolved outcomes stay unknown.

    A confirmed declaration must link to a single ready scouting record and
    name a distinct outcome adjudicator. The tool cannot authenticate people,
    permission, field evidence, blinding or actual independence.
    """
    now = now or datetime.now(timezone.utc)
    verified = verify_protocol(protocol, now=now)
    reconciliation = reconcile_intake(protocol, intake, now=now)
    spec = verified["spec"]
    if not isinstance(adjudications, dict) or adjudications.get("schema_version") != "vantage-adjudication-1":
        raise ValueError("Expected vantage-adjudication-1 document")
    for key, expected in (("cohort_id", spec["cohort_id"]),
                          ("protocol_sha256", verified["protocol_sha256"]),
                          ("rubric_ref", spec["rubric_ref"])):
        if adjudications.get(key) != expected:
            raise ValueError(f"Adjudication {key} does not match the frozen protocol")
    declarations = adjudications.get("records")
    if not isinstance(declarations, list) or any(not isinstance(r, dict) for r in declarations):
        raise ValueError("Adjudication records must be an array of objects")
    counts = Counter(r.get("unit_id") for r in declarations if isinstance(r.get("unit_id"), str))
    visits = {v["unit_id"]: v for v in reconciliation["visits"]}
    outcomes, checks = {}, []
    for index, declaration in enumerate(declarations):
        blockers = []
        unit_id = declaration.get("unit_id")
        visit = visits.get(unit_id) if isinstance(unit_id, str) else None
        if visit is None:
            blockers.append("unit_not_in_selected_plan")
        elif counts[unit_id] != 1:
            blockers.append("duplicate_unit_adjudication")
        if visit is not None and visit["state"] != "ready_for_adjudication":
            blockers.append("visit_not_ready_for_adjudication")
        for key in ("record_id", "adjudicator_ref", "reference_ref"):
            if not isinstance(declaration.get(key), str) or not declaration[key].strip():
                blockers.append(f"missing_{key}")
        if declaration.get("decision") != "confirmed":
            blockers.append("adjudication_not_confirmed")
        if declaration.get("independence_confirmed") is not True:
            blockers.append("independence_not_declared")
        if declaration.get("outcome") not in ("useful_finding", "no_useful_finding"):
            blockers.append("binary_outcome_required")
        reviewed = None
        try:
            reviewed = _instant(declaration["adjudicated_at"])
            if reviewed > now:
                blockers.append("future_adjudication")
        except (KeyError, ValueError, TypeError, AttributeError):
            blockers.append("invalid_adjudicated_at")
        if visit is not None and visit["state"] == "ready_for_adjudication":
            record = intake["records"][visit["records"][0]["record_index"]]
            if declaration.get("record_id") != record["record_id"]:
                blockers.append("record_id_mismatch")
            if declaration.get("outcome") != record["finding"]:
                blockers.append("outcome_disagrees_with_intake")
            if declaration.get("adjudicator_ref") in (record["observer_ref"], record["reviewer_ref"]):
                blockers.append("adjudicator_matches_visit_personnel")
            if reviewed is not None and reviewed < _instant(record["reviewed_at"]):
                blockers.append("adjudication_precedes_intake_review")
        checks.append({"adjudication_index": index, "used_as_declared_outcome": not blockers,
                       "blockers": blockers})
        if not blockers:
            outcomes[unit_id] = int(declaration["outcome"] == "useful_finding")

    eligible = [u for u in spec["units"] if u["status"] != "unavailable"]
    k = min(spec["capacity"], len(eligible))
    ranked = {}
    summaries = {}
    for name, key in (("model", "model_score"), ("baseline", "baseline_score")):
        ids = [u["unit_id"] for u in sorted(eligible, key=lambda u: (-u[key], u["unit_id"]))[:k]]
        ranked[name] = set(ids)
        known = sum(outcomes[u] for u in ids if u in outcomes)
        unknown = sum(u not in outcomes for u in ids)
        summaries[name] = {"ranked_unit_ids": ids, "declared_known_positive_count": known,
                           "unresolved_count": unknown, "precision_bounds": [known / k, (known + unknown) / k]}
    model_only = ranked["model"] - ranked["baseline"]
    baseline_only = ranked["baseline"] - ranked["model"]
    known_difference = (sum(outcomes[u] for u in model_only if u in outcomes)
                        - sum(outcomes[u] for u in baseline_only if u in outcomes))
    difference_bounds = [(known_difference - sum(u not in outcomes for u in baseline_only)) / k,
                         (known_difference + sum(u not in outcomes for u in model_only)) / k]
    return {"schema_version": "vantage-scouting-bounds-1", "computed_at": now.isoformat(),
            "cohort_id": spec["cohort_id"], "protocol_sha256": verified["protocol_sha256"],
            "available_cohort_size": len(eligible), "unavailable_cohort_size": len(spec["units"]) - len(eligible),
            "capacity": k, "requested_capacity": spec["capacity"],
            "visit_state_counts": reconciliation["state_counts"],
            "rejected_intake_record_count": len(reconciliation["rejected_records"]),
            "adjudication_checks": checks, "declared_outcomes_used": len(outcomes),
            "model": summaries["model"], "baseline": summaries["baseline"],
            "shared_top_capacity_units": len(ranked["model"] & ranked["baseline"]),
            "paired_precision_difference_bounds": difference_bounds,
            "confidence_interval": None, "training_eligible": False, "evaluation_label_exported": False,
            "independently_authenticated_outcomes": 0,
            "limitations": ["Exact identification bounds conditional on declared outcomes and frozen ranks; not confidence intervals or estimated performance.",
                            "Every unresolved binary outcome may be zero or one. Shared ranked units cancel in the paired difference.",
                            "Adjudication identity, independence and source truth are not authenticated by this local tool.",
                            "Unavailable units are excluded from both rankings, not assessed healthy. No conclusions about their outcomes.",
                            "No training labels, sampling-weighted estimator, causal impact or model promotion is produced."]}
