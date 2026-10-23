"""Portable historical evidence example; not a partner API or publication service."""
from copy import deepcopy
from datetime import datetime
import hashlib
from html import escape
import json


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Evidence timestamps require a timezone")
    return parsed


def build_bundle(snapshot):
    """Retain source evidence, recomputing freshness at its frozen cutoff."""
    if snapshot["mode"] != "historical_research":
        raise ValueError("Only historical research snapshots are supported")
    evidence = deepcopy(snapshot)
    cutoff = timestamp(evidence["as_of"])
    optical = evidence["optical"]
    for observation in optical["observations"]:
        if timestamp(observation["acquired_at"]) > cutoff:
            raise ValueError("Observation is after the evidence cutoff")
    usable = [timestamp(o["acquired_at"]) for o in optical["observations"]
              if o["coverage_qualified"]]
    latest = max(usable) if usable else None
    if latest is not None and timestamp(optical["latest_usable"]) != latest:
        raise ValueError("Latest usable date disagrees with observations")
    age = (cutoff - latest).total_seconds() / 86400 if latest else None
    state = "missing" if latest is None else (
        "stale" if age > optical["freshness_policy_days"] else "within_research_freshness_window")
    bundle = {
        "schema_version": "vantage-partner-example-1",
        "product": "Vantage",
        "portfolio": "https://github.com/Ibekwemmanuel7/Lillie_US",
        "mode": "historical_research",
        "review_status": "unreviewed_draft",
        "publication_authorized": False,
        "source_snapshot_id": evidence["snapshot_id"],
        "decision_cutoff": evidence["as_of"],
        "quality": {"state": state, "age_at_cutoff_days": age,
                    "freshness_policy_days": optical["freshness_policy_days"],
                    "first_known_available_time": None,
                    "availability_note": "Acquisition time does not establish historical delivery availability"},
        "decision": {"status": "withheld", "field_priorities": [],
                     "reason": "Historical locality evidence has no validated field recommendations"},
        "unavailable_outputs": ["yield_forecast", "production_tonnes", "disease_diagnosis",
                                "nutrient_diagnosis", "irrigation_prescription",
                                "water_allocation", "validated_farmland_change",
                                "household_food_insecurity_assessment"],
        "evidence": evidence,
    }
    encoded = json.dumps(bundle, sort_keys=True, allow_nan=False).encode()
    bundle["bundle_id"] = hashlib.sha256(encoded).hexdigest()
    return bundle


def render_report(bundle):
    """Escape all source strings; report includes no remote or private assets."""
    evidence = bundle["evidence"]
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{:.1%}</td></tr>".format(
            escape(o["acquired_at"]), "Qualified" if o["coverage_qualified"] else "Insufficient",
            o["usable_crop_fraction"])
        for o in evidence["optical"]["observations"])
    limitations = "".join("<li>" + escape(s) + "</li>" for s in evidence["limitations"])
    unavailable = ", ".join(bundle["unavailable_outputs"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vantage historical evidence brief</title>
<body><main><h1>Vantage agricultural evidence brief</h1>
<p>Historical research · Unreviewed draft · Not authorized for publication</p>
<h2>{escape(evidence['name'])}, {escape(evidence['country'])}</h2>
<p>Boundary: {escape(evidence['boundary_status'])}</p>
<p>Frozen evidence cutoff: {escape(bundle['decision_cutoff'])}</p>
<p>Optical quality: <strong>{escape(bundle['quality']['state'])}</strong>.</p>
<p>Freshness is assessed at the historical cutoff, not today. Acquisition dates
do not prove when evidence was available to a decision maker.</p>
<p>Field priorities withheld. This report does not establish crop damage or cause.</p>
<table><caption>Optical observation coverage over the historical crop mask</caption>
<thead><tr><th>Date</th><th>Coverage gate</th><th>Usable fraction</th></tr></thead>
<tbody>{rows}</tbody></table><h2>Limitations</h2><ul>{limitations}</ul>
<h2>Unavailable outputs</h2><p>{escape(unavailable)}</p>
<p>Source lineage and preview checksums are retained in evidence.json.
Raster preview files are not included or claimed as verified by this export.</p>
<p>Bundle: {escape(bundle['bundle_id'])}</p>
<p>Part of <a href="https://github.com/Ibekwemmanuel7/Lillie_US">Lillie US</a>.</p>
</main></body></html>'''
