"""Paired observed NDVI changes on exactly aligned grids; no cause inference."""
import math

import numpy as np
from affine import Affine
from rasterio.crs import CRS
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom

from vantage.core import instant
from vantage.field_pixels import summarize_fields, validate_boundaries


def compare_fields(collection, before, after, *, cutoff, min_coverage=.7, min_pixels=9,
                   freshness_days=7, max_pair_days=21, change_threshold=.1):
    """Return report, masked float32 difference and union-of-eligible-fields mask.

    The same boundary collection defines both dates. Individual date medians
    are never subtracted: statistics use per-pixel after-minus-before changes.
    """
    for value, name in ((max_pair_days, "pair interval"), (change_threshold, "change threshold")):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Positive finite {name} required")
    for scene in (before, after):
        for key in ("source_ref", "recipe_ref"):
            if not isinstance(scene.get(key), str) or not scene[key].strip():
                raise ValueError(f"Nonempty {key} required")
    if before["recipe_ref"] != after["recipe_ref"]:
        raise ValueError("Both dates require the same declared observed optical processing recipe")
    if before["source_ref"] == after["source_ref"]:
        raise ValueError("Distinct source observations required")
    interval = (instant(after["acquired_at"]) - instant(before["acquired_at"])).total_seconds() / 86400
    if interval <= 0:
        raise ValueError("Strictly increasing acquisition dates required")
    if (before["ndvi"].shape != after["ndvi"].shape
            or not np.array_equal(np.asarray(before["transform"]), np.asarray(after["transform"]))
            or CRS.from_user_input(before["crs"]) != CRS.from_user_input(after["crs"])):
        raise ValueError("Exact grid alignment required; no implicit resampling")
    summaries = []
    for scene, age_limit in ((before, freshness_days + max_pair_days), (after, freshness_days)):
        summaries.append(summarize_fields(collection, scene["ndvi"], scene["valid"], scene["transform"], scene["crs"],
            acquired_at=scene["acquired_at"], available_at=scene["available_at"], cutoff=cutoff,
            source_ref=scene["source_ref"], min_coverage=min_coverage, min_pixels=min_pixels, freshness_days=age_limit))
    transform = Affine(*tuple(after["transform"])[:6])
    common = before["valid"] & after["valid"]
    difference = np.full(after["ndvi"].shape, np.nan, dtype="float64")
    difference[common] = after["ndvi"][common].astype("float64") - before["ndvi"][common].astype("float64")
    map_valid = np.zeros(common.shape, dtype=bool)
    records = []
    for boundary, previous, current in zip(validate_boundaries(collection), summaries[0]["fields"], summaries[1]["fields"]):
        mask = geometry_mask([transform_geom("EPSG:4326", after["crs"], boundary["geometry"])],
                             out_shape=common.shape, transform=transform, invert=True, all_touched=False)
        paired = mask & common
        count = int(paired.sum())
        total = current["selected_grid_pixels"]
        fraction = count / total if total and current["usable_fraction"] is not None else None
        blockers = ["before_" + b for b in previous["blockers"]] + ["after_" + b for b in current["blockers"]]
        if interval > max_pair_days:
            blockers.append("pair_interval_exceeds_policy")
        if count < min_pixels:
            blockers.append("insufficient_common_pixels")
        if fraction is None or fraction < min_coverage:
            blockers.append("insufficient_common_coverage")
        eligible = not blockers
        values = difference[paired] if eligible else np.array([])
        if eligible:
            map_valid |= paired
        records.append(dict(field_id=current["field_id"], boundary_version=current["boundary_version"],
                            geometry_sha256=current["geometry_sha256"], season_id=current["season_id"], crop=current["crop"],
                            selected_grid_pixels=total, common_valid_pixels=count, common_usable_fraction=fraction,
                            eligible_for_research_comparison=eligible, blockers=blockers,
                            median_paired_ndvi_change=float(np.median(values)) if values.size else None,
                            mean_paired_ndvi_change=float(np.mean(values, dtype="float64")) if values.size else None,
                            declining_pixel_count=int((values < -change_threshold).sum()) if eligible else None,
                            increasing_pixel_count=int((values > change_threshold).sum()) if eligible else None,
                            field_priority_available=False))
    difference[~map_valid] = np.nan
    report = dict(schema_version="vantage-field-change-1", decision_cutoff=cutoff, pair_interval_days=interval,
                  recipe_ref=after["recipe_ref"], before=summaries[0], after=summaries[1], fields=records,
                  policy=dict(minimum_common_coverage=min_coverage, minimum_common_pixels=min_pixels,
                              latest_freshness_days=freshness_days, maximum_pair_days=max_pair_days,
                              exploratory_absolute_change_threshold=change_threshold),
                  field_priorities_available=False, independently_verified_field_outcomes=0,
                  limitations=["After minus before on common observed pixels only; negative values mean lower NDVI, not a diagnosed cause.",
                               "Both dates use one declared boundary version, crop and season; these declarations require review.",
                               "The map covers the union of eligible field pixels. Missing/withheld pixels are nodata, never zero change.",
                               "Thresholds are engineering defaults, not agronomic anomaly thresholds, calibrated confidence or management advice.",
                               "No operational rank, training label, cloud infill, yield estimate or dashboard integration is supplied."])
    return report, difference.astype("float32"), map_valid
