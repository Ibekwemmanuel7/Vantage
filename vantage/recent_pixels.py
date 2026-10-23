"""Bounded selection and explicit whole-box observation quality."""
from datetime import datetime


def select_latest(record):
    eligible = [c for c in record["candidates"]
                if c["bbox_covers_study"] and c["baseline_assets_present"]]
    return max(eligible, key=lambda c: (datetime.fromisoformat(
        c["acquired_at"].replace("Z", "+00:00")), c["id"]), default=None)


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
