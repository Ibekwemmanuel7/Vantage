"""Acquisition-time freshness and non-interpolated public-event observations."""

from datetime import date, datetime, timezone
import math


def utc_time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone-aware acquisition and cutoff required")
    return result.astimezone(timezone.utc)


def validate_followup(plan, parent_plan):
    """Keep exploratory follow-ups inside the pinned event's historical cutoff."""
    start = date.fromisoformat(plan["start"])
    end = date.fromisoformat(plan["end"])
    cutoff = utc_time(plan["as_of"])
    if start > end or (end - start).days > 62 or cutoff.date() != end:
        raise ValueError("Ordered bounded interval ending at cutoff required")
    if (
        start.year != parent_plan["target_year"]
        or end.year != parent_plan["target_year"]
    ):
        raise ValueError("Follow-up must use the parent target year")
    if cutoff > utc_time(parent_plan["observation_cutoff"]):
        raise ValueError("Follow-up must not cross the parent observation cutoff")
    if (
        type(plan["max_acquisitions"]) is not int
        or not 1 <= plan["max_acquisitions"] <= 12
    ):
        raise ValueError("Integer acquisition budget of one to twelve required")
    timeline_summary([], plan["as_of"], plan["max_observation_age_days"])


def timeline_summary(rows, as_of, max_age_days):
    """Quality does not imply freshness, and neither establishes agronomic validity."""
    cutoff = utc_time(as_of)
    if not math.isfinite(max_age_days) or max_age_days <= 0:
        raise ValueError("Finite positive freshness policy required")
    ordered = sorted(rows, key=lambda row: utc_time(row["acquired_at"]))
    stamps = [utc_time(row["acquired_at"]) for row in ordered]
    if len(set(stamps)) != len(stamps):
        raise ValueError("Duplicate acquisitions cannot inflate temporal coverage")
    if any(stamp > cutoff for stamp in stamps):
        raise ValueError("After-cutoff acquisitions are not historical evidence")
    usable = [
        row
        for row in ordered
        if row["status"] == "processed" and row["coverage_qualified"]
    ]
    latest = usable[-1] if usable else None
    age = (
        (cutoff - utc_time(latest["acquired_at"])).total_seconds() / 86400
        if latest
        else None
    )
    return dict(
        status="no_quality_qualified_observation"
        if latest is None
        else "fresh_research_observation"
        if age <= max_age_days
        else "stale_research_context",
        as_of=as_of,
        max_observation_age_days=max_age_days,
        catalog_acquisitions=len(ordered),
        processed_observations=sum(r["status"] == "processed" for r in ordered),
        coverage_qualified_observations=len(usable),
        latest_acquisition=ordered[-1]["acquired_at"] if ordered else None,
        latest_quality_qualified_acquisition=latest["acquired_at"] if latest else None,
        latest_quality_qualified_age_days=age,
        quality_qualified_gaps_days=[
            (utc_time(b["acquired_at"]) - utc_time(a["acquired_at"])).total_seconds()
            / 86400
            for a, b in zip(usable, usable[1:])
        ],
        agronomic_review_eligible=False,
        independent_field_labels=0,
        interpretation="Acquisition-time research freshness only; no historical data-delivery, crop-stage or field-outcome validation",
    )
