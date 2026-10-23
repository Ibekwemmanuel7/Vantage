"""Explain the existing numerical rejection recipe without relaxing it."""
import numpy as np
from scipy.ndimage import binary_dilation
from vantage.imagery import derive_scene


def audit_quality(raw, scl, quantification, offsets):
    reflectance, valid, ndvi = derive_scene(raw, scl, quantification, offsets)
    classes, counts = np.unique(scl, return_counts=True)
    accepted = np.isin(scl, [4, 5])
    buffered = accepted & ~binary_dilation(~accepted, iterations=1)
    remaining = buffered.copy()
    reasons = {"scl_class_rejected": int((~accepted).sum()),
               "scl_buffer_rejected": int((accepted & ~buffered).sum())}
    gates = {
        "source_red_or_nir_nodata": (raw["B04"] > 0) & (raw["B08"] > 0),
        "invalid_physical_reflectance": np.isfinite(reflectance["B04"]) & np.isfinite(reflectance["B08"]) &
            (reflectance["B04"] >= 0) & (reflectance["B08"] >= 0),
        "nonpositive_red_plus_nir": reflectance["B04"] + reflectance["B08"] > 0,
        "invalid_ndvi": valid,
    }
    for name, gate in gates.items():
        reasons[name] = int((remaining & ~gate).sum())
        remaining &= gate
    if not np.array_equal(remaining, valid):
        raise ValueError("Diagnostic gates differ from production recipe")
    return dict(total_pixels=int(scl.size), accepted_pixels=int(valid.sum()),
                scl_histogram={str(int(c)):int(n) for c,n in zip(classes, counts)},
                ordered_exclusive_rejections=reasons,
                accounting_complete=sum(reasons.values())+int(valid.sum()) == scl.size,
                interpretation="SCL categories and numerical gates, not independently verified cloud or crop labels")
