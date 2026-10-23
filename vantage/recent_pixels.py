"""Bounded selection and explicit whole-box observation quality."""
from datetime import datetime


def select_latest(record):
    eligible = [c for c in record["candidates"]
                if c["bbox_covers_study"] and c["baseline_assets_present"]]
    return max(eligible, key=lambda c: (datetime.fromisoformat(
        c["acquired_at"].replace("Z", "+00:00")), c["id"]), default=None)


def select_sequence(record, limit):
    if type(limit) is not int or not 1 <= limit <= 6:
        raise ValueError("Sequence budget must be 1-6 acquisitions per box")
    eligible = [c for c in record["candidates"]
                if c["bbox_covers_study"] and c["baseline_assets_present"]]
    # One deterministic processing version per acquisition; no cloud ranking.
    unique = {}
    for candidate in sorted(eligible, key=lambda c:c["id"]):
        stamp = datetime.fromisoformat(candidate["acquired_at"].replace("Z", "+00:00"))
        unique[stamp] = candidate
    return [unique[stamp] for stamp in sorted(unique, reverse=True)[:limit]]


def summarize_sequence(results):
    summaries = []
    for location in sorted({r["location_id"] for r in results}):
        rows = [r for r in results if r["location_id"] == location]
        processed = [r for r in rows if r["status"] == "processed"]
        qualified = [r for r in processed if r["quality"]["coverage_qualified"]]
        latest = max(qualified, key=lambda r:r["acquired_at"], default=None)
        summaries.append(dict(location_id=location, attempted_scenes=len(rows),
            processed_scenes=len(processed), coverage_qualified_scenes=len(qualified),
            latest_qualified_acquisition=latest["acquired_at"] if latest else None,
            qualified_age_at_cutoff_days=latest["quality"]["age_at_cutoff_days"] if latest else None,
            status=latest["quality"]["state"] if latest else "no_coverage_qualified_observation",
            field_priorities_available=False))
    return summaries


def observation_quality(metrics, acquired_at, cutoff):
    age = (datetime.fromisoformat(cutoff.replace("Z", "+00:00")) -
           datetime.fromisoformat(acquired_at.replace("Z", "+00:00"))).total_seconds()/86400
    if age < 0:
        raise ValueError("Future observation")
    total, valid = metrics["total_pixels"], metrics["valid_pixels"]
    if total <= 0 or not 0 <= valid <= total:
        raise ValueError("Invalid pixel denominator")
    fraction = valid/total
    qualified = fraction >= .70
    return dict(age_at_cutoff_days=age, usable_fraction=fraction,
                coverage_policy_fraction=.70, freshness_policy_days=7,
                coverage_qualified=qualified,
                state="insufficient_coverage" if not qualified else (
                    "stale" if age > 7 else "recent_whole_box_research"),
                field_priorities_available=False,
                interpretation="Whole study box; no current crop mask or confirmed field identity")
