"""Quality-gated retrospective comparisons, without causal or agronomic labels."""

import warnings
from datetime import datetime, timezone
import numpy as np


def validate_plan(plan):
    """Reject duplicate cohorts and future dates before counting reference years."""
    years = plan["reference_years"]
    if (
        len(years) < 3
        or len(set(years)) != len(years)
        or any(y >= plan["target_year"] for y in years)
    ):
        raise ValueError("At least three unique earlier reference years required")
    for collection in ("areas", "epochs"):
        ids = [r["id"] for r in plan[collection]]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Nonempty unique area and epoch identifiers required")
    cutoff = datetime.fromisoformat(plan["observation_cutoff"].replace("Z", "+00:00"))
    if cutoff.tzinfo is None or cutoff.year != plan["target_year"]:
        raise ValueError("Timezone-aware target-year cutoff required")
    for epoch in plan["epochs"]:
        start = datetime.fromisoformat(
            f"{plan['target_year']}-{epoch['start']}"
        ).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(
            f"{plan['target_year']}-{epoch['end']}T23:59:59+00:00"
        )
        if start > end or end > cutoff:
            raise ValueError("Ordered observation windows at or before cutoff required")


def anomaly_map(
    target,
    references,
    crop,
    min_references=3,
    min_fraction=0.6,
    min_pixels=100,
    drop_trigger=-0.1,
):
    refs = np.asarray(references, dtype="float32")
    if (
        target.ndim != 2
        or crop.shape != target.shape
        or refs.ndim != 3
        or refs.shape[1:] != target.shape
    ):
        raise ValueError("Exact target/reference/crop grids required")
    if (
        min_references < 3
        or not 0 <= min_fraction <= 1
        or min_pixels < 1
        or drop_trigger >= 0
        or not np.isfinite(drop_trigger)
    ):
        raise ValueError("Invalid frozen comparison policy")
    if crop.dtype.kind != "b":
        raise ValueError("Boolean historical crop mask required")
    count = np.isfinite(refs).sum(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        median = np.nanmedian(refs, axis=0)
        minimum = np.nanmin(refs, axis=0)
    comparable = crop & np.isfinite(target) & (count >= min_references)
    total = int(crop.sum())
    n = int(comparable.sum())
    fraction = n / total if total else None
    reasons = []
    if not total:
        reasons.append("no_historical_crop_pixels")
    if n < min_pixels:
        reasons.append("insufficient_comparable_pixels")
    if fraction is not None and fraction < min_fraction:
        reasons.append("insufficient_comparable_crop_coverage")
    delta = np.where(comparable, target - median, np.nan).astype("float32")
    low = comparable & (delta <= drop_trigger) & (target < minimum)
    if reasons:
        delta[:] = np.nan
        low[:] = False
    return dict(
        delta=delta,
        reference_count=count.astype("uint8"),
        low_flag=low,
        summary=dict(
            status="withheld" if reasons else "research_comparison_available",
            reasons=reasons,
            historical_crop_pixels=total,
            comparable_pixels=n,
            comparable_crop_fraction=fraction,
            median_delta=float(np.nanmedian(delta)) if not reasons else None,
            lower_than_reference_fraction=float(low.sum() / n)
            if n and not reasons
            else None,
            independent_labels=0,
            causal_attribution=False,
        ),
    )


def rainfall_comparison(rows, reference_years, target_year, months):
    if not reference_years or len(set(reference_years)) != len(reference_years):
        raise ValueError("Unique nonempty rainfall reference years required")
    if (
        not months
        or len(set(months)) != len(months)
        or any(m not in range(1, 13) for m in months)
    ):
        raise ValueError("Unique valid rainfall months required")
    if target_year in reference_years or any(y >= target_year for y in reference_years):
        raise ValueError("Earlier reference years only")
    expected = {(y, m) for y in reference_years + [target_year] for m in months}
    indexed = {}
    for r in rows:
        key = (r["year"], r["month"])
        if key in indexed or key not in expected:
            raise ValueError("Duplicate or unexpected rainfall month")
        value = r["mean_mm"]
        if not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
            raise ValueError("Valid rainfall required")
        indexed[key] = value
    missing = sorted(expected - set(indexed))
    if missing:
        return dict(
            status="unavailable",
            missing=missing,
            target_total_mm=None,
            ratio_to_reference_median=None,
        )
    totals = {
        str(y): sum(indexed[y, m] for m in months)
        for y in reference_years + [target_year]
    }
    reference = float(np.median([totals[str(y)] for y in reference_years]))
    return dict(
        status="available",
        totals_mm=totals,
        target_total_mm=totals[str(target_year)],
        reference_median_mm=reference,
        ratio_to_reference_median=totals[str(target_year)] / reference
        if reference > 0
        else None,
        reference_years=reference_years,
        interpretation="Short-reference rainfall context, not climatological drought severity or soil moisture",
    )
