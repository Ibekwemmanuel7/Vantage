"""Conservative provisional joins to broad-scale ASAP monitoring zones."""
import math
import json
from rasterio.warp import transform_geom
from shapely.geometry import shape, mapping


def read_zone_response(raw):
    if len(raw) > 4_000_000:
        raise ValueError("Zone response exceeds four MB budget")
    data = json.loads(raw.decode("utf-8-sig"))
    features = data.get("features")
    if (data.get("type") != "FeatureCollection" or not isinstance(features, list) or not 1 <= len(features) <= 100
            or data.get("numberMatched") != len(features) or data.get("numberReturned") != len(features)):
        raise ValueError("Complete bounded WFS response required; pagination/truncation cannot be ignored")
    if data.get("crs", {}).get("properties", {}).get("name") not in ("urn:ogc:def:crs:EPSG::4326", "EPSG:4326"):
        raise ValueError("Explicit WGS84 source CRS required")
    result = []
    for feature in features:
        props = feature["properties"]
        if props.get("asap0_id") != 209 or str(props.get("asap0_name", "")).strip().casefold() != "uganda":
            raise ValueError("Response includes non-Uganda units")
        if type(props.get("asap1_id")) is not int:
            raise ValueError("Integer ASAP zone identifier required")
        result.append(dict(type="Feature", geometry=feature["geometry"], properties=dict(
            asap0_id="209", asap1_id=str(props["asap1_id"]), zone_label=props["asap1_name"])))
    # Discard provider crop-warning values: they are not our field outcomes.
    return dict(type="FeatureCollection", features=result)


def validate_zones(collection, calendar_rows):
    if collection.get("type") != "FeatureCollection" or not collection.get("features"):
        raise ValueError("Nonempty zone FeatureCollection required")
    zones = []
    ids = set()
    for feature in collection["features"]:
        properties = feature["properties"]
        zone_id = properties["asap1_id"]
        if not isinstance(zone_id, str) or not zone_id or zone_id in ids:
            raise ValueError("Unique string source zone IDs required")
        ids.add(zone_id)
        if properties.get("asap0_id") != "209" or not isinstance(properties.get("zone_label"), str):
            raise ValueError("Uganda source identifiers and zone label required")
        geometry = shape(feature["geometry"])
        if geometry.geom_type not in ("Polygon", "MultiPolygon") or geometry.is_empty or not geometry.is_valid:
            raise ValueError("Invalid source zone geometry; no silent repair")
        if not (-180 <= geometry.bounds[0] < geometry.bounds[2] <= 180 and -90 <= geometry.bounds[1] < geometry.bounds[3] <= 90):
            raise ValueError("Source zones require WGS84 coordinates")
        zones.append(dict(asap1_id=zone_id, zone_label=properties["zone_label"], geometry=geometry))
    required = {r["asap1_id"] for r in calendar_rows}
    if not required.issubset(ids):
        raise ValueError("Calendar IDs absent from the zone snapshot; incompatible sources")
    return sorted(zones, key=lambda z: z["asap1_id"])


def resolve_zone(geometry, zones, calendar_rows, *, border_guard_m=1000):
    if (isinstance(border_guard_m, bool) or not isinstance(border_guard_m, (int, float))
            or not math.isfinite(border_guard_m) or not 0 <= border_guard_m <= 10000):
        raise ValueError("Border guard must be 0-10000 metres")
    unit = shape(geometry)
    if unit.geom_type not in ("Polygon", "MultiPolygon") or unit.is_empty or not unit.is_valid:
        raise ValueError("Valid polygon unit required")
    if not (-180 <= unit.bounds[0] < unit.bounds[2] <= 180 and -90 <= unit.bounds[1] < unit.bounds[3] <= 90):
        raise ValueError("WGS84 unit coordinates required")
    result = dict(status="unresolved", asap1_id=None, zone_label=None, border_guard_m=border_guard_m,
                  border_distance_m=None, available_crop_seasons=[], field_calendar_confirmed=False,
                  field_priorities_available=False, limitation="Simplified regional context only; border guard is an engineering policy, not certified positional accuracy.")
    intersecting = [z for z in zones if z["geometry"].intersects(unit)]
    containing = [z for z in intersecting if z["geometry"].covers(unit)]
    if not intersecting:
        return dict(result, reason="outside_supplied_zone_coverage")
    if len(containing) != 1:
        return dict(result, reason="crosses_zones_or_no_unique_full_containment")
    chosen = containing[0]
    if any(z is not chosen and z["geometry"].intersection(unit).area > 0 for z in intersecting):
        return dict(result, reason="overlapping_zone_geometry")
    # Uganda-only regional catalogue: metre-based UTM 36N for a guard calculation,
    # not area-weighted membership or a precision boundary survey.
    projected_unit = shape(transform_geom("EPSG:4326", "EPSG:32636", mapping(unit)))
    projected_zone = shape(transform_geom("EPSG:4326", "EPSG:32636", mapping(chosen["geometry"])))
    if not projected_unit.is_valid or not projected_zone.is_valid:
        return dict(result, reason="projection_geometry_invalid")
    distance = projected_zone.boundary.distance(projected_unit)
    if not math.isfinite(distance):
        return dict(result, reason="unknown_border_distance")
    result["border_distance_m"] = distance
    if distance <= border_guard_m:
        return dict(result, reason="near_simplified_zone_boundary")
    labels = sorted({r["crop_name"] for r in calendar_rows if r["asap1_id"] == chosen["asap1_id"]})
    return dict(result, status="regional_zone_context" if labels else "zone_without_calendar_context",
                reason=None if labels else "no_calendar_for_source_zone", asap1_id=chosen["asap1_id"],
                zone_label=chosen["zone_label"], available_crop_seasons=labels)
