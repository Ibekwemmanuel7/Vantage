"""Explicit intensity/dB contracts; numeric support is not agricultural validity."""

import numpy as np


def decibels(power):
    values = np.asarray(power, dtype="float32")
    valid = np.isfinite(values) & (values > 0)
    result = np.full(values.shape, np.nan, dtype="float32")
    result[valid] = 10 * np.log10(values[valid])
    return result


def numeric_evidence(power, crop, min_fraction=0.6, min_pixels=100):
    if power.shape != (2,) + crop.shape or crop.dtype.kind != "b":
        raise ValueError(
            "Exactly aligned VV/VH linear intensity and Boolean crop mask required"
        )
    if not 0 <= min_fraction <= 1 or min_pixels < 1:
        raise ValueError("Invalid numeric support policy")
    common = np.isfinite(power).all(axis=0) & (power > 0).all(axis=0)
    use = common & crop
    total, count = int(crop.sum()), int(use.sum())
    fraction = count / total if total else None
    qualified = (
        count >= min_pixels and fraction is not None and fraction >= min_fraction
    )
    features = None
    if qualified:
        db = decibels(power)
        features = dict(
            vv_db_median=float(np.median(db[0][use])),
            vh_db_median=float(np.median(db[1][use])),
            vh_minus_vv_db_median=float(np.median((db[1] - db[0])[use])),
        )
    return dict(
        status="numeric_backscatter_only"
        if qualified
        else "insufficient_numeric_support",
        historical_crop_pixels=total,
        numeric_crop_pixels=count,
        numeric_crop_fraction=fraction,
        numeric_support_qualified=qualified,
        features=features,
        terrain_screen_verified=False,
        agronomic_review_eligible=False,
        current_crop_confirmed=False,
        independent_field_labels=0,
    )


def paired_change(
    earlier, later, crop, earlier_track, later_track, min_fraction=0.6, min_pixels=100
):
    if not 0 <= min_fraction <= 1 or min_pixels < 1:
        raise ValueError("Invalid paired numeric support policy")
    if earlier_track != later_track:
        raise ValueError("Cross-track backscatter comparisons are prohibited")
    first, second = decibels(earlier), decibels(later)
    if (
        first.shape != second.shape
        or first.shape != (2,) + crop.shape
        or crop.dtype.kind != "b"
    ):
        raise ValueError("Aligned two-polarization arrays and crop mask required")
    common = np.isfinite(first).all(axis=0) & np.isfinite(second).all(axis=0) & crop
    total, count = int(crop.sum()), int(common.sum())
    fraction = count / total if total else None
    qualified = (
        count >= min_pixels and fraction is not None and fraction >= min_fraction
    )
    delta = np.where(common[None, ...], second - first, np.nan).astype("float32")
    if not qualified:
        delta[:] = np.nan
    return dict(
        delta_db=delta,
        summary=dict(
            status="descriptive_same_track_change" if qualified else "withheld",
            comparable_pixels=count,
            comparable_crop_fraction=fraction,
            vv_median_delta_db=float(np.nanmedian(delta[0])) if qualified else None,
            vh_median_delta_db=float(np.nanmedian(delta[1])) if qualified else None,
            crop_condition_label=None,
            terrain_screen_verified=False,
            causal_attribution=False,
        ),
    )
