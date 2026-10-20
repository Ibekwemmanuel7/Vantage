"""Physical six-band Sentinel-2 measurements and explicit temporal missingness."""
from datetime import datetime
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.ndimage import binary_dilation

BANDS = ("B02", "B03", "B04", "B8A", "B11", "B12")
BAND_IDS = dict(zip(BANDS, (1, 2, 3, 8, 11, 12)))


def metadata_parameters(text, baseline):
    elements = list(ET.fromstring(text).iter())
    q = next(float(e.text) for e in elements if e.tag.split("}")[-1] == "BOA_QUANTIFICATION_VALUE")
    if not np.isfinite(q) or q <= 0:
        raise ValueError("Invalid reflectance quantification")
    offsets = {int(e.attrib["band_id"]): float(e.text) for e in elements
               if e.tag.split("}")[-1] == "BOA_ADD_OFFSET"}
    if float(baseline) >= 4 and not set(BAND_IDS.values()) <= offsets.keys():
        raise ValueError("Missing six-band reflectance offsets")
    values = {b: offsets.get(i, 0.) for b, i in BAND_IDS.items()}
    if not all(np.isfinite(v) for v in values.values()):
        raise ValueError("Non-finite reflectance offset")
    return q, values


def decode_cube(raw, scl, quantification, offsets):
    """Return C,H,W reflectance, per-band validity and all-band validity.

    Negative physical values are withheld by this conservative analysis policy,
    not clipped into observations. Reflectance above one is retained.
    """
    if set(raw) != set(BANDS) or scl.ndim != 2 or any(raw[b].shape != scl.shape for b in BANDS):
        raise ValueError("Exactly six declared bands and a shared two-dimensional SCL grid required")
    if not np.isfinite(quantification) or quantification <= 0 or not all(np.isfinite(offsets[b]) for b in BANDS):
        raise ValueError("Finite physical reflectance parameters required")
    accepted = np.isin(scl, [4, 5])
    accepted &= ~binary_dilation(~accepted, iterations=1)
    values = np.stack([(raw[b].astype(np.float32) + offsets[b]) / quantification for b in BANDS])
    band_valid = np.stack([raw[b] > 0 for b in BANDS]) & np.isfinite(values) & (values >= 0) & accepted[None]
    values[~band_valid] = np.nan
    return values, band_valid, band_valid.all(axis=0)


def spectral_features(cube, common_valid):
    if cube.shape[0] != 6 or cube.shape[1:] != common_valid.shape:
        raise ValueError("Feature grid mismatch")
    result = {b + "_median": float(np.median(cube[i][common_valid])) if common_valid.any() else None
              for i, b in enumerate(BANDS)}
    for name, a, b in (("ndvi_b8a", 3, 2), ("ndmi_b8a_b11", 3, 4)):
        denominator = cube[a] + cube[b]
        good = common_valid & (denominator > 0)
        values = (cube[a][good] - cube[b][good]) / denominator[good]
        result[name + "_median"] = float(np.median(values)) if values.size else None
    return result


def stamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Explicit observation timezone required")
    return parsed


def temporal_index(records, as_of=None):
    """Observed frames only, ordered by acquisition; never fabricate dates."""
    if len({r["scene_id"] for r in records}) != len(records):
        raise ValueError("Duplicate temporal scene")
    if len({r["grid_id"] for r in records}) > 1:
        raise ValueError("Temporal frames must share an exact grid")
    cutoff = stamp(as_of) if as_of else None
    ordered = sorted((r for r in records if cutoff is None or stamp(r["acquired_at"]) <= cutoff),
                     key=lambda r: (stamp(r["acquired_at"]), r["scene_id"]))
    if len({stamp(r["acquired_at"]) for r in ordered}) != len(ordered):
        raise ValueError("Duplicate acquisition time; resolve processing/tile duplicates first")
    return [dict(scene_id=r["scene_id"], acquired_at=r["acquired_at"],
                 gap_days=None if i == 0 else (stamp(r["acquired_at"]) - stamp(ordered[i-1]["acquired_at"])).total_seconds()/86400,
                 common_usable_fraction=r["common_usable_fraction"], artifact_id=r["artifact_id"])
            for i, r in enumerate(ordered)]


def load_sequence(manifest, root, location_id, as_of=None):
    """Load T,C,H,W physical measurements and masks; no normalization/imputation.

    Acquisition cutoff is not a claim of historical publication-time availability.
    Empty sequences fail explicitly. Source arrays are not model-ready HLS data.
    """
    import importlib.util
    import os
    # The Windows host also has PostGIS. Its PROJ database is incompatible
    # with this rasterio wheel; use the wheel's matching database, as builders do.
    proj = Path(importlib.util.find_spec("rasterio").origin).parent / "proj_data"
    if proj.is_dir():
        os.environ["PROJ_DATA"] = str(proj)
        os.environ["PROJ_LIB"] = str(proj)
    import rasterio
    from .imagery import sha256_file
    if isinstance(manifest, (str, Path)):
        manifest = json.loads(Path(manifest).read_text())
    root = Path(root).resolve()
    records = [r for r in manifest["scenes"] if r["location_id"] == location_id]
    index = temporal_index(records, as_of)
    if not index:
        raise ValueError("No observed frames at requested location/cutoff")
    by_id = {r["scene_id"]: r for r in records}
    cubes=[]; masks=[]
    for frame in index:
        record=by_id[frame["scene_id"]]
        arrays={}
        for name in ("reflectance", "band_valid"):
            asset=record["assets"][name]
            path=(root/record["artifact_id"]/asset["href"]).resolve()
            if not path.is_relative_to(root) or sha256_file(path)!=asset["sha256"]:
                raise ValueError("Untrusted path or changed sequence artifact")
            with rasterio.open(path) as ds:
                if list(ds.transform)!=record["grid"]["transform"] or ds.crs.to_string()!=record["grid"]["crs"]:
                    raise ValueError("Sequence grid differs from manifest")
                if name=="reflectance" and list(ds.descriptions)!=list(BANDS):
                    raise ValueError("Sequence band order mismatch")
                arrays[name]=ds.read()
        valid=arrays["band_valid"].astype(bool)
        if not np.array_equal(np.isfinite(arrays["reflectance"]),valid):
            raise ValueError("Sequence validity mismatch")
        cubes.append(arrays["reflectance"]);masks.append(valid)
    return dict(reflectance=np.stack(cubes),band_valid=np.stack(masks),
                common_valid=np.stack(masks).all(axis=1),frames=index,bands=list(BANDS),
                grid=by_id[index[0]["scene_id"]]["grid"],foundation_ready=False)
