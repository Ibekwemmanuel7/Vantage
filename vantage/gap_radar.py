"""Radar catalog plan for one bounded optical sequence; no pixel eligibility."""
from datetime import timedelta
from vantage.event_series import utc_time


def radar_plan(sequence, bbox):
    rows=[r for r in sequence["observations"] if r["status"]=="processed"]
    if not rows or len({r["location_id"] for r in rows})!=1:
        raise ValueError("One nonempty study-location sequence required")
    dates=[utc_time(r["acquired_at"]) for r in rows]
    if max(dates)>utc_time(sequence["decision_cutoff"]):
        raise ValueError("Optical acquisition exceeds cutoff")
    start=min(dates)-timedelta(days=7)
    if (max(dates)-start).days>62:
        raise ValueError("Radar search interval exceeds budget")
    return dict(collection="sentinel-1-rtc",bbox=bbox,start=start.date().isoformat(),
        end=max(dates).date().isoformat(),as_of=max(dates).isoformat(),
        mode="IW",polarizations=["VV","VH"],max_observation_age_days=7)


def optical_matching_rows(sequence):
    # Include clear dates as potential future training pairs, as well as gaps.
    return [dict(acquired_at=r["acquired_at"],status="processed",coverage_qualified=False,
                 original_coverage_qualified=r["quality"]["coverage_qualified"])
            for r in sequence["observations"] if r["status"]=="processed"]
