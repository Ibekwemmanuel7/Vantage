"""Bounded, sampled terrain sightlines. Passing never certifies illumination."""

import numpy as np
from scipy.ndimage import map_coordinates

CLASS_NAMES = [
    "unknown",
    "clear_within_tested_distance",
    "obstruction_risk",
    "clearance_guard",
]


def sightlines(
    elevation,
    origin_rows,
    origin_cols,
    dx,
    dy,
    rise,
    resolution=30.0,
    distance=5000.0,
    step=15.0,
    guard=5.0,
):
    """Sample a bilinear DSM toward the sensor in physical metres.

    dx/dy are projected metres per horizontal physical metre (dy northward).
    rise is vertical metres per horizontal metre. Flat tangent approximation;
    omits curvature/refraction and geoid variation. Samples start at `step`.
    Missing any required sample prevents a clear result. An observed obstruction
    takes precedence over missing support elsewhere. Guard is engineering policy,
    not a calibrated elevation uncertainty. No extrapolation or hole filling.
    """
    elevation = np.asarray(elevation, dtype=float)
    arrays = np.broadcast_arrays(
        *[np.asarray(a, dtype=float) for a in (origin_rows, origin_cols, dx, dy, rise)]
    )
    rows, cols, dx, dy, rise = arrays
    if (
        elevation.ndim != 2
        or min(elevation.shape) < 2
        or not all(np.isfinite(v) for v in (resolution, distance, step, guard))
        or resolution <= 0
        or distance < step
        or step <= 0
        or guard < 0
    ):
        raise ValueError("Finite positive grid and bounded sampling policy required")

    finite = np.isfinite(elevation).astype(float)
    filled = np.nan_to_num(elevation, nan=0, posinf=0, neginf=0)

    def sample(r, c):
        # Sampling the finite mask too prevents interpolation across missing heights.
        coords = np.stack([r.ravel(), c.ravel()])
        valid = map_coordinates(
            finite, coords, order=1, mode="constant", cval=0, prefilter=False
        )
        z = map_coordinates(
            filled, coords, order=1, mode="constant", cval=0, prefilter=False
        )
        return np.where(valid >= 1 - 1e-12, z, np.nan).reshape(rows.shape)

    base = sample(rows, cols)
    initial = (
        np.isfinite(base)
        & np.isfinite(dx)
        & np.isfinite(dy)
        & np.isfinite(rise)
        & (rise > 0)
        & ((dx * dx + dy * dy) > 0)
    )
    missing = ~initial
    minimum = np.full(rows.shape, np.inf)
    minimum_distance = np.full(rows.shape, np.nan)
    supported = np.zeros(rows.shape, dtype=np.int32)
    distances = np.unique(np.append(np.arange(step, distance, step), distance))
    for d in distances:
        z = sample(rows - dy * d / resolution, cols + dx * d / resolution)
        good = initial & np.isfinite(z)
        clearance = base + d * rise - z
        update = good & (clearance < minimum)
        minimum[update] = clearance[update]
        minimum_distance[update] = d
        supported += good
        missing |= ~good
    classes = np.zeros(rows.shape, dtype="uint8")
    classes[initial & ~missing & (minimum > guard)] = 1
    classes[initial & ~missing & (minimum >= -guard) & (minimum <= guard)] = 3
    classes[initial & (minimum < -guard)] = 2
    minimum[~np.isfinite(minimum)] = np.nan
    return dict(
        classes=classes,
        minimum_clearance=minimum.astype("float32"),
        minimum_distance=minimum_distance.astype("float32"),
        supported_fraction=(supported / len(distances)).astype("float32"),
        samples=len(distances),
    )
