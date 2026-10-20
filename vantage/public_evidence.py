"""Adjudicate public-source references without turning web claims into labels."""
from datetime import date
from urllib.parse import urlparse


def assess_reference(record):
    blockers=[]
    parsed=urlparse(record.get("source_url",""))
    if parsed.scheme!="https" or not parsed.hostname:blockers.append("traceable_https_source_required")
    if record.get("review_state")!="original_reference_verified":blockers.append("original_reference_not_verified")
    if record.get("spatial_precision")!="field_boundary" or record.get("spatial_match_verified") is not True or not record.get("verified_geometry_ref"):
        blockers.append("no_verified_field_spatial_match")
    if record.get("observation_time_precision")!="day":blockers.append("observation_date_not_precise")
    try:
        observed=date.fromisoformat(record["observed_at"])
        published=date.fromisoformat(record["published_at"])
        if observed>published:raise ValueError()
    except (KeyError,TypeError,ValueError):blockers.append("dated_observation_not_verified")
    if record.get("crop_identity_confirmed") is not True:blockers.append("crop_identity_not_verified")
    if record.get("independence")!="independent_field_observation":blockers.append("independence_unverified_or_shared_model_inputs")
    if record.get("target")!="useful_scouting_finding" or record.get("outcome") not in ("useful_finding","no_useful_finding"):
        blockers.append("not_a_verified_scouting_outcome")
    if record.get("sampling_method") not in ("flagged","presampled_unflagged","routine"):
        blockers.append("sampling_design_unknown")
    if record.get("reuse_permission")!="approved":blockers.append("reuse_review_incomplete")
    if not record.get("source_group") or not record.get("verification_ref"):
        blockers.append("origin_or_independent_verification_reference_missing")
    return dict(evidence_id=record.get("evidence_id"),admissible_supervised_reference=not blockers,
        evidence_use=record.get("evidence_use","discovery_lead_only"),blockers=blockers,
        limitation="Checks audit declarations, not truth. Syndicated copies are not independent evidence. No automatic conversion to training labels.")


def assess_registry(records):
    if len({r["evidence_id"] for r in records})!=len(records):raise ValueError("Duplicate evidence identifiers")
    assessments=[assess_reference(r) for r in records]
    return dict(schema_version="public-evidence-assessment-1",records=len(records),
        distinct_origin_groups=len({r.get("source_group") for r in records}),
        admissible_supervised_references=sum(a["admissible_supervised_reference"] for a in assessments),
        assessments=assessments,trained_model=False)
