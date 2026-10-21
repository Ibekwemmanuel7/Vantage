"""Annotation-derived viewing vectors and approximate local facet geometry risks."""

from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET
import numpy as np
from scipy.interpolate import CubicHermiteSpline, LinearNDInterpolator
from scipy.ndimage import binary_erosion


def annotation_time(value):
    # Sentinel product annotation times are UTC, even when serialized without Z.
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (
        parsed.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None
        else parsed.astimezone(timezone.utc)
    )


def unit(vectors):
    values = np.asarray(vectors, dtype="float64")
    norm = np.linalg.norm(values, axis=-1, keepdims=True)
    return np.divide(
        values,
        norm,
        out=np.full_like(values, np.nan),
        where=np.isfinite(norm) & (norm > 0),
    )


def ecef(latitude, longitude, height):
    lat, lon = np.radians(latitude), np.radians(longitude)
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    radius = a / np.sqrt(1 - e2 * np.sin(lat) ** 2)
    return np.stack(
        [
            (radius + height) * np.cos(lat) * np.cos(lon),
            (radius + height) * np.cos(lat) * np.sin(lon),
            (radius * (1 - e2) + height) * np.sin(lat),
        ],
        axis=-1,
    )


def ellipsoid_up(latitude, longitude):
    lat, lon = np.radians(latitude), np.radians(longitude)
    return np.stack(
        [np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=-1
    )


def orbit_positions(times, positions, velocities, query):
    times, positions, velocities, query = [
        np.asarray(a, dtype="float64") for a in (times, positions, velocities, query)
    ]
    if (
        times.ndim != 1
        or len(times) < 4
        or positions.shape != (len(times), 3)
        or velocities.shape != positions.shape
        or not all(np.isfinite(a).all() for a in (times, positions, velocities, query))
        or (np.diff(times) <= 0).any()
    ):
        raise ValueError(
            "Finite strictly increasing orbit states and velocities required"
        )
    if np.min(query) < times[0] or np.max(query) > times[-1]:
        raise ValueError("Orbit extrapolation prohibited")
    return CubicHermiteSpline(times, positions, velocities, axis=0, extrapolate=False)(
        query
    )


def parse_annotation(text, record, tolerance):
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("Finite positive annotation-consistency tolerance required")
    root = ET.fromstring(text)
    if root.tag != "product":
        raise ValueError("Product annotation XML required")
    header = root.find("adsHeader")
    match = re.match(
        r"^(S1[ABC])_IW_GRDH_1SDV_\d{8}T\d{6}_\d{8}T\d{6}_(\d{6})_", record["item_id"]
    )
    if header is None or not match:
        raise ValueError("Supported source product identity required")
    if any(
        header.findtext(key) != value
        for key, value in [
            ("missionId", match[1]),
            ("productType", "GRD"),
            ("polarisation", "VV"),
            ("mode", "IW"),
        ]
    ):
        raise ValueError("Annotation identity or mode/polarization mismatch")
    if int(header.findtext("absoluteOrbitNumber")) != int(match[2]):
        raise ValueError("Annotation orbit mismatch")
    acquired = annotation_time(record["acquired_at"])
    if (
        not annotation_time(header.findtext("startTime"))
        <= acquired
        <= annotation_time(header.findtext("stopTime"))
    ):
        raise ValueError("Annotation acquisition mismatch")
    states = root.findall(".//orbit")
    if len(states) < 4:
        raise ValueError("At least four orbit states required")
    if any(s.findtext("frame") != "Earth Fixed" for s in states):
        raise ValueError("Earth-fixed orbit states required")
    epoch = annotation_time(states[0].findtext("time"))
    times = [
        (annotation_time(s.findtext("time")) - epoch).total_seconds() for s in states
    ]
    positions = [
        [float(s.findtext("position/" + c)) for c in ("x", "y", "z")] for s in states
    ]
    velocities = [
        [float(s.findtext("velocity/" + c)) for c in ("x", "y", "z")] for s in states
    ]
    points = root.findall(".//geolocationGridPoint")
    if len(points) < 4:
        raise ValueError("Geolocation grid support required")
    latitude = np.array([float(p.findtext("latitude")) for p in points])
    longitude = np.array([float(p.findtext("longitude")) for p in points])
    height = np.array([float(p.findtext("height")) for p in points])
    incidence = np.array([float(p.findtext("incidenceAngle")) for p in points])
    when = [
        (annotation_time(p.findtext("azimuthTime")) - epoch).total_seconds()
        for p in points
    ]
    if (
        not all(np.isfinite(a).all() for a in (latitude, longitude, height, incidence))
        or (np.abs(latitude) > 90).any()
        or (np.abs(longitude) > 180).any()
        or (incidence <= 0).any()
        or (incidence >= 90).any()
    ):
        raise ValueError("Invalid annotated coordinates or angles")
    satellite = orbit_positions(times, positions, velocities, when)
    look = unit(satellite - ecef(latitude, longitude, height))
    computed = np.degrees(
        np.arccos(
            np.clip(np.sum(look * ellipsoid_up(latitude, longitude), axis=-1), -1, 1)
        )
    )
    residual = np.abs(computed - incidence)
    if not np.isfinite(residual).all() or residual.max() > tolerance:
        raise ValueError("Orbit-derived incidence disagrees with annotation")
    return dict(
        latitude=latitude,
        longitude=longitude,
        look_ecef=look,
        summary=dict(
            geolocation_points=len(points),
            orbit_states=len(states),
            incidence_residual_max_degrees=float(residual.max()),
            source_incidence_min_degrees=float(incidence.min()),
            source_incidence_max_degrees=float(incidence.max()),
            reference_frame="Earth Fixed",
            annotation_polarization="VV",
            orbit_extrapolated=False,
        ),
    )


def interpolate_look(points_xy, vectors, query_xy):
    points, vectors, query = [
        np.asarray(a, dtype="float64") for a in (points_xy, vectors, query_xy)
    ]
    if (
        points.ndim != 2
        or points.shape[1] != 2
        or vectors.shape != (len(points), 3)
        or query.shape[-1] != 2
    ):
        raise ValueError("Aligned coordinates and three-component vectors required")
    if not np.isfinite(points).all() or not np.isfinite(vectors).all():
        raise ValueError("Finite annotation support required")
    return unit(LinearNDInterpolator(points, vectors, fill_value=np.nan)(query))


def surface_normals(elevation, spacing_x, spacing_y, up, grid_x_delta, grid_y_delta):
    """Map orthometric DSM gradients to approximate ECEF normals using physical grid axes."""
    z = np.asarray(elevation, dtype="float64")
    if (
        z.ndim != 2
        or min(z.shape) < 3
        or not np.isfinite([spacing_x, spacing_y]).all()
        or spacing_x <= 0
        or spacing_y <= 0
    ):
        raise ValueError("Metric surface grid required")
    if any(np.shape(v) != z.shape + (3,) for v in (up, grid_x_delta, grid_y_delta)):
        raise ValueError("Aligned Earth-fixed grid bases required")
    x_tangent = grid_x_delta - up * np.sum(grid_x_delta * up, axis=-1, keepdims=True)
    y_tangent = grid_y_delta - up * np.sum(grid_y_delta * up, axis=-1, keepdims=True)
    x_scale = np.linalg.norm(x_tangent, axis=-1)
    y_scale = np.linalg.norm(y_tangent, axis=-1)
    if (
        not np.isfinite([x_scale, y_scale]).all()
        or (x_scale <= 0).any()
        or (y_scale <= 0).any()
    ):
        raise ValueError("Finite nonzero physical grid axes required")
    down, east = np.gradient(z, spacing_y, spacing_x)
    gradient = (east / x_scale)[..., None] * unit(x_tangent) + (-down / y_scale)[
        ..., None
    ] * unit(y_tangent)
    normal = unit(up - gradient)
    supported = binary_erosion(
        np.isfinite(z), structure=np.ones((3, 3)), border_value=0
    )
    normal[~supported] = np.nan
    gradient[~supported] = np.nan
    return normal, gradient


def local_geometry(look, normal, up, gradient, min_incidence=5, max_incidence=85):
    if not 0 < min_incidence < max_incidence < 90:
        raise ValueError("Explicit finite local-incidence guards required")
    if (
        any(np.shape(v) != np.shape(look) for v in (normal, up, gradient))
        or np.shape(look)[-1] != 3
    ):
        raise ValueError("Aligned viewing vectors, normals and gradients required")
    finite = (
        np.isfinite(look).all(axis=-1)
        & np.isfinite(normal).all(axis=-1)
        & np.isfinite(gradient).all(axis=-1)
        & np.isfinite(up).all(axis=-1)
    )
    for vectors in (look, normal, up):
        lengths = np.linalg.norm(vectors, axis=-1)
        if not np.allclose(lengths[finite], 1, atol=1e-6, rtol=0):
            raise ValueError("Unit viewing, normal and up vectors required")
    nominal_cos = np.sum(look * up, axis=-1)
    local_cos = np.sum(look * normal, axis=-1)
    nominal = np.arccos(np.clip(nominal_cos, -1, 1))
    local = np.degrees(np.arccos(np.clip(local_cos, -1, 1)))
    finite &= (nominal > 0) & (nominal < np.pi / 2)
    horizontal = unit(look - up * nominal_cos[..., None])
    toward_sensor_gradient = np.sum(gradient * horizontal, axis=-1)
    reversal = finite & (toward_sensor_gradient <= -np.tan(nominal))
    back_facing = finite & (local_cos <= 0)
    guard = finite & ((local < min_incidence) | (local > max_incidence))
    classes = np.zeros(finite.shape, dtype="uint8")
    classes[finite] = 1
    classes[guard] = 4
    classes[reversal] = 2
    classes[back_facing] = 3
    nominal_degrees = np.where(finite, np.degrees(nominal), np.nan).astype("float32")
    local = np.where(finite, local, np.nan).astype("float32")
    return dict(
        nominal_incidence=nominal_degrees,
        local_incidence=local,
        classes=classes,
        toward_sensor_slope=np.where(
            finite, np.degrees(np.arctan(toward_sensor_gradient)), np.nan
        ).astype("float32"),
    )
