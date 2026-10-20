"""Georeferenced imagery derivatives and dataset features. No inferred crop causes."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from scipy.ndimage import binary_dilation

BAND_IDS = {"B02": 1, "B03": 2, "B04": 3, "B08": 7}
FEATURES = ["ndvi_median", "ndvi_iqr", "red_median", "nir_median", "rainfall_mm"]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_metadata(text, baseline):
    root = ET.fromstring(text)
    elements = list(root.iter())
    q = next(float(e.text) for e in elements if e.tag.split("}")[-1] == "BOA_QUANTIFICATION_VALUE")
    if not np.isfinite(q) or q <= 0:
        raise ValueError("Invalid reflectance quantification")
    offsets = {int(e.attrib["band_id"]): float(e.text) for e in elements if e.tag.split("}")[-1] == "BOA_ADD_OFFSET"}
    if float(baseline) >= 4 and not set(BAND_IDS.values()) <= offsets.keys():
        raise ValueError("Missing band-specific reflectance offsets")
    return q, {band: offsets.get(index, 0.) for band, index in BAND_IDS.items()}


def derive_scene(raw, scl, quantification, offsets):
    """Decode physical reflectance, keep no-data distinct, buffer rejected SCL by 20 m."""
    if not {"B04", "B08"} <= raw.keys() or scl.ndim != 2:
        raise ValueError("Red/NIR and a two-dimensional SCL grid are required")
    shape = scl.shape
    if any(array.shape != shape for array in raw.values()):
        raise ValueError("All bands and masks must share the exact grid")
    if not np.isfinite(quantification) or quantification <= 0:
        raise ValueError("Invalid reflectance quantification")
    reflectance = {band: (array.astype(np.float32)+offsets[band])/quantification for band, array in raw.items()}
    accepted = np.isin(scl, [4, 5])
    valid = accepted & ~binary_dilation(~accepted, iterations=1)
    for band in ("B04", "B08"):
        valid &= (raw[band] > 0) & np.isfinite(reflectance[band]) & (reflectance[band] >= 0)
    red, nir = reflectance["B04"], reflectance["B08"]
    valid &= red+nir > 0
    ndvi = np.divide(nir-red, nir+red, out=np.full(shape, np.nan, dtype=np.float32), where=valid)
    valid &= np.isfinite(ndvi) & (np.abs(ndvi) <= 1)
    ndvi[~valid] = np.nan
    return reflectance, valid, ndvi


def zone_features(reflectance, ndvi, mask):
    values = ndvi[mask]
    finite = np.isfinite(values)
    count = int(finite.sum())
    total = int(mask.sum())
    result = dict(valid_pixels=count, cropland_pixels=total,
                  usable_fraction=count/total if total else 0,
                  ndvi_median=None, ndvi_iqr=None, red_median=None, nir_median=None)
    if count:
        accepted = mask & np.isfinite(ndvi)
        result.update(ndvi_median=float(np.median(values[finite])),
                      ndvi_iqr=float(np.percentile(values[finite],75)-np.percentile(values[finite],25)),
                      red_median=float(np.median(reflectance["B04"][accepted])),
                      nir_median=float(np.median(reflectance["B08"][accepted])))
    return result


def rgba_rgb(reflectance, valid):
    if not {"B02", "B03", "B04"} <= reflectance.keys():
        return None
    image = np.stack([reflectance[b] for b in ("B04", "B03", "B02")], axis=-1)
    # Fixed stretch shared by every acquisition, independent of target-year values.
    rgb = (np.clip(image/.30, 0, 1)**(1/2.2)*255).astype(np.uint8)
    return np.concatenate([rgb, (valid*255).astype(np.uint8)[...,None]], axis=-1)


def rgba_ndvi(ndvi):
    stops = np.array([-.2, 0, .2, .4, .6, .8, 1.])
    colors = np.array([[133,96,76],[181,140,105],[221,202,160],[205,217,155],[124,170,99],[43,111,69],[15,65,45]])
    values = np.nan_to_num(ndvi, nan=0)
    rgb = np.stack([np.interp(values,stops,colors[:,i]) for i in range(3)],axis=-1).astype(np.uint8)
    return np.concatenate([rgb,(np.isfinite(ndvi)*255).astype(np.uint8)[...,None]],axis=-1)


def stable_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def atomic_text(path,text):
    """Publish a complete local artifact with one same-filesystem replacement."""
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=path.parent,delete=False,suffix=".tmp") as stream:
        temporary=Path(stream.name)
        stream.write(text)
    os.replace(temporary,path)


def atomic_json(path,value):
    atomic_text(path,json.dumps(value,indent=2,allow_nan=False))
