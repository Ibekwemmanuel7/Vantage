"""Surface-slope risk proxies, never a substitute for radar viewing geometry."""

import math
import numpy as np
from scipy.ndimage import binary_erosion, maximum_filter


def slope_proxy(elevation, x_spacing_m, y_spacing_m, neighborhood=3):
    """Metric finite differences, requiring complete neighborhoods around derivatives."""
    z = np.asarray(elevation, dtype="float64")
    if z.ndim != 2 or min(z.shape) < 5:
        raise ValueError("At least a five-by-five elevation grid required")
    if not all(math.isfinite(v) and v > 0 for v in (x_spacing_m, y_spacing_m)):
        raise ValueError("Finite positive metric grid spacing required")
    if neighborhood != 3:
        raise ValueError("This version implements a fixed three-by-three neighborhood")
    valid = binary_erosion(np.isfinite(z), structure=np.ones((3, 3)), border_value=0)
    dz_dy, dz_dx = np.gradient(z, y_spacing_m, x_spacing_m)
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
    slope[~valid] = np.nan
    supported = binary_erosion(
        np.isfinite(slope), structure=np.ones((3, 3)), border_value=0
    )
    maximum = maximum_filter(
        np.where(np.isfinite(slope), slope, -np.inf),
        size=3,
        mode="constant",
        cval=np.inf,
    )
    maximum[~supported] = np.nan
    return slope.astype("float32"), maximum.astype("float32")


def classify_proxy(maximum_slope, threshold_degrees):
    """0 unknown; 1 lower-slope proxy; 2 elevated-slope proxy. No confirmed SAR validity."""
    if not math.isfinite(threshold_degrees) or not 0 < threshold_degrees < 90:
        raise ValueError("Slope threshold must be finite and between zero and ninety")
    values = np.asarray(maximum_slope)
    if (
        np.isinf(values).any()
        or (values[np.isfinite(values)] < 0).any()
        or (values[np.isfinite(values)] > 90).any()
    ):
        raise ValueError("Valid slopes or explicit NaN support required")
    return np.where(
        np.isfinite(values), np.where(values <= threshold_degrees, 1, 2), 0
    ).astype("uint8")


def proxy_summary(classes, crop):
    if (
        classes.shape != crop.shape
        or crop.dtype.kind != "b"
        or not np.isin(classes, [0, 1, 2]).all()
    ):
        raise ValueError(
            "Aligned three-class proxy and Boolean historical crop mask required"
        )
    total = int(crop.sum())
    counts = {
        name: int(((classes == value) & crop).sum())
        for value, name in [(0, "unknown"), (1, "lower_slope"), (2, "elevated_slope")]
    }
    return dict(
        historical_crop_pixels=total,
        counts=counts,
        retained_crop_fraction=counts["lower_slope"] / total if total else None,
        terrain_risk_proxy_applied=True,
        terrain_screen_verified=False,
        radar_illumination_confirmed=False,
        agronomic_review_eligible=False,
    )
