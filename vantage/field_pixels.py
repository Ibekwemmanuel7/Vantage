"""Topology-aware field summaries of observed, quality-masked NDVI only."""
import hashlib
import json
import math

import numpy as np
from affine import Affine
from rasterio.crs import CRS
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
from shapely.geometry import box, mapping, shape

from vantage.core import instant


def validate_boundaries(collection):
    if (not isinstance(collection, dict) or collection.get("type") != "FeatureCollection"
            or "crs" in collection or not isinstance(collection.get("features"), list)
            or not 1 <= len(collection["features"]) <= 100):
        raise ValueError("Expected 1-100 WGS84 GeoJSON features, without a custom CRS")
    result, seen = [], set()
    for feature in collection["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("GeoJSON Feature required")
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("Field properties required")
        for key in ("field_id", "boundary_version", "consent_ref", "season_id", "crop"):
            if not isinstance(properties.get(key), str) or not properties[key].strip():
                raise ValueError(f"Nonempty {key} required")
        if properties["field_id"] in seen:
            raise ValueError("Duplicate field ID")
        seen.add(properties["field_id"])
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError("Polygon or MultiPolygon required")
        polygons = [geometry.get("coordinates")] if geometry["type"] == "Polygon" else geometry.get("coordinates")
        if not isinstance(polygons, list) or not polygons:
            raise ValueError("Empty polygon")
        vertex_count = 0
        for polygon in polygons:
            if not isinstance(polygon, list) or not polygon:
                raise ValueError("Empty rings")
            for ring in polygon:
                if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError("Explicitly closed rings required; no automatic repair")
                vertex_count += len(ring)
                for point in ring:
                    if not isinstance(point, (list, tuple)) or len(point) != 2:
                        raise ValueError("Two-dimensional coordinates required")
                    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in point):
                        raise ValueError("Finite numeric coordinates required")
                    if not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90:
                        raise ValueError("Coordinates outside WGS84 bounds")
        if vertex_count > 10000:
            raise ValueError("Field exceeds 10000-vertex processing budget")
        polygon = shape(geometry)
        if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
            raise ValueError("Invalid field topology; repair requires a separately reviewed boundary version")
        west, south, east, north = polygon.bounds
        if east - west > 1 or north - south > 1:
            raise ValueError("Field exceeds one-degree extent budget or crosses the antimeridian")
        digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, allow_nan=False).encode()).hexdigest()
        result.append(dict(properties=properties, geometry=geometry, geometry_sha256=digest))
    return sorted(result, key=lambda r: r["properties"]["field_id"])


def summarize_fields(collection, ndvi, valid, transform, crs, *, acquired_at, available_at,
                     cutoff, source_ref, min_coverage=.7, min_pixels=9, freshness_days=7):
    """Summarize only fields fully covered by a north-up projected raster.

    Rasterio's default polygon burn rule is used, not fractional pixel weighting.
    NDVI and valid must already come from the observed reflectance quality recipe.
    """
    fields = validate_boundaries(collection)
    if (ndvi.ndim != 2 or ndvi.size == 0 or ndvi.size > 4_000_000
            or valid.shape != ndvi.shape or valid.dtype.kind != "b"):
        raise ValueError("Aligned 2D NDVI/boolean mask required; budget is four million pixels")
    if not np.array_equal(valid, np.isfinite(ndvi)) or np.any(np.abs(ndvi[valid]) > 1):
        raise ValueError("Observed NDVI mask must equal finite, bounded NDVI support")
    transform = Affine(*tuple(transform)[:6])
    if (not all(math.isfinite(v) for v in transform) or transform.a <= 0 or transform.e >= 0
            or transform.b != 0 or transform.d != 0):
        raise ValueError("Finite north-up raster transform required")
    crs = CRS.from_user_input(crs)
    if not crs.is_projected or crs.linear_units != "metre":
        raise ValueError("Projected metre grid required")
    if not isinstance(source_ref, str) or not source_ref.strip():
        raise ValueError("Observed source reference required")
    acquired, available, decision = map(instant, (acquired_at, available_at, cutoff))
    if not acquired <= available <= decision:
        raise ValueError("Acquisition and input availability must precede the decision cutoff")
    if (isinstance(min_coverage, bool) or not isinstance(min_coverage, (int, float))
            or not 0 < min_coverage <= 1 or type(min_pixels) is not int or min_pixels < 1
            or isinstance(freshness_days, bool) or not isinstance(freshness_days, (int, float))
            or not math.isfinite(freshness_days) or freshness_days < 0):
        raise ValueError("Invalid declared quality policy")
    age = (decision - acquired).total_seconds() / 86400
    height, width = ndvi.shape
    footprint = box(transform.c, transform.f + height * transform.e,
                    transform.c + width * transform.a, transform.f)
    records = []
    for field in fields:
        projected = shape(transform_geom("EPSG:4326", crs, field["geometry"]))
        if not projected.is_valid or projected.is_empty:
            raise ValueError("Projection produced an invalid field")
        blockers = []
        if not footprint.covers(projected):
            blockers.append("partial_raster_coverage" if footprint.intersects(projected) else "outside_raster")
        mask = geometry_mask([mapping(projected)], out_shape=ndvi.shape, transform=transform,
                             all_touched=False, invert=True)
        selected = int(mask.sum())
        accepted = int((mask & valid).sum())
        fully_covered = not blockers
        coverage = accepted / selected if selected and fully_covered else None
        if selected < min_pixels:
            blockers.append("insufficient_field_pixels")
        if accepted < min_pixels:
            blockers.append("insufficient_accepted_pixels")
        if fully_covered and (coverage is None or coverage < min_coverage):
            blockers.append("insufficient_usable_coverage")
        if age > freshness_days:
            blockers.append("stale_observation")
        # Never report a partial-field median as the field observation.
        values = ndvi[mask & valid] if fully_covered and accepted >= min_pixels else np.array([])
        props = field["properties"]
        records.append({key: props[key] for key in ("field_id", "boundary_version", "season_id", "crop")} |
                       dict(geometry_sha256=field["geometry_sha256"], projected_area_m2=float(projected.area),
                            selected_grid_pixels=selected, accepted_pixels=accepted, usable_fraction=coverage,
                            observed_ndvi_median=float(np.median(values)) if values.size else None,
                            eligible_for_research_comparison=not blockers, blockers=blockers,
                            field_priority_available=False))
    return dict(schema_version="vantage-field-pixels-1", acquired_at=acquired_at, available_at=available_at,
                decision_cutoff=cutoff, age_days=age, source_ref=source_ref, fields=records,
                policy=dict(minimum_coverage=min_coverage, minimum_pixels=min_pixels, freshness_days=freshness_days,
                            pixel_rule="rasterio default all_touched=False; not fractional area weighting"),
                grid=dict(crs=crs.to_string(), transform=list(transform), width=width, height=height),
                independently_verified_fields=0, field_priorities_available=False,
                limitations=["Boundary identity, consent, crop and source declarations require independent review.",
                             "Grid support is not independent sample size; small fields and mixed edge pixels limit interpretation.",
                             "NDVI is observed vegetation context, not diagnosis, yield, irrigation advice or an anomaly score.",
                             "No automatic visit-protocol export or replacement of the existing rectangular prototype."])
