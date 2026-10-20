"""Reconstruct public Sentinel-2/WorldCover/CHIRPS evidence; never live monitoring.

Requires numpy, rasterio, scipy, requests. Run from repository root.
Source rasters and signed URLs stay in ignored outputs; published JSON has unsigned lineage.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import importlib.util
from pathlib import Path
import sys
import time
from urllib.parse import quote
import xml.etree.ElementTree as ET

# Prefer this rasterio wheel's matching PROJ database over unrelated system GIS installs.
_proj = Path(importlib.util.find_spec("rasterio").origin).parent / "proj_data"
if _proj.is_dir():
    os.environ["PROJ_DATA"] = str(_proj)
    os.environ["PROJ_LIB"] = str(_proj)

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds, transform_geom
from rasterio.features import geometry_mask
from scipy.ndimage import binary_dilation
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vantage.area import assess, export_bundle, units

CACHE = ROOT / "outputs/uganda/cache"
SESSION = requests.Session()


def fetch(url, *, binary=False):
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest() + (".bin" if binary else ".txt"))
    if path.exists():
        return path.read_bytes() if binary else path.read_text(encoding="utf-8")
    for attempt in range(3):
        try:
            r = SESSION.get(url, timeout=90)
            r.raise_for_status()
            if binary:
                path.write_bytes(r.content)
                return r.content
            path.write_text(r.text, encoding="utf-8")
            return r.text
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(1+attempt)


def search(collection, bbox, interval=None):
    params = dict(collections=collection, bbox=",".join(map(str, bbox)), limit=100)
    if interval:
        params["datetime"] = interval
    url = requests.Request("GET", "https://planetarycomputer.microsoft.com/api/stac/v1/search", params=params).prepare().url
    response = json.loads(fetch(url))
    if any(x.get("rel") == "next" for x in response.get("links", [])):
        raise ValueError("Search truncated; narrow the monitoring interval")
    return response["features"]


def signed(href):
    for attempt in range(4):
        r = SESSION.get("https://planetarycomputer.microsoft.com/api/sas/v1/sign", params={"href":href}, timeout=45)
        if r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
            return r.json()["href"]
        time.sleep(2*(attempt+1))
    r.raise_for_status()


def read_asset(item, key, transform, width, height, crs, categorical=False):
    href = item["assets"][key]["href"]
    cache = CACHE / (hashlib.sha256((href+str(transform)+str(width)+str(height)).encode()).hexdigest()+".npy")
    if cache.exists():
        return np.load(cache)
    # GDAL errors may contain signed URLs; the CLI reports only error types.
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY=2,
                      GDAL_HTTP_TIMEOUT=60, CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        with rasterio.open(signed(href)) as src:
            with WarpedVRT(src, crs=crs, transform=transform, width=width, height=height,
                           resampling=Resampling.nearest if categorical else Resampling.average) as vrt:
                array = vrt.read(1)
    np.save(cache, array)
    return array


def reflectance_parameters(item):
    text = fetch(signed(item["assets"]["product-metadata"]["href"]))
    root = ET.fromstring(text)
    elements = list(root.iter())
    quant = next(float(e.text) for e in elements if e.tag.split("}")[-1] == "BOA_QUANTIFICATION_VALUE")
    offsets = {int(e.attrib["band_id"]): float(e.text) for e in elements if e.tag.split("}")[-1] == "BOA_ADD_OFFSET"}
    if float(item["properties"]["s2:processing_baseline"]) >= 4 and not offsets:
        raise ValueError("Missing reflectance offset metadata")
    return quant, offsets.get(3, 0), offsets.get(7, 0), hashlib.sha256(text.encode()).hexdigest()


def build(config):
    if (config["month"], config["window_start_day"], config["window_end_day"], config["rain_pentad"], config["grid"]) != (5, 1, 15, 3, 2):
        raise ValueError("This research adapter supports May 1-15 vegetation and May 11-15 rainfall on a two by two grid only")
    CACHE.mkdir(parents=True, exist_ok=True)
    bbox = config["bbox"]
    bounds = transform_bounds("EPSG:4326", "EPSG:32636", *bbox)
    width, height = int(np.ceil((bounds[2]-bounds[0])/20)), int(np.ceil((bounds[3]-bounds[1])/20))
    transform = from_bounds(*bounds, width, height)
    wc = next(x for x in search("esa-worldcover", bbox) if "2021" in x["id"] and
              x["bbox"][0] <= bbox[0] and x["bbox"][1] <= bbox[1] and x["bbox"][2] >= bbox[2] and x["bbox"][3] >= bbox[3])
    crop_mask = read_asset(wc, "map", transform, width, height, "EPSG:32636", True) == 40
    unit_masks = {u["id"]: crop_mask & geometry_mask([transform_geom("EPSG:4326", "EPSG:32636", u["geometry"])],
                  out_shape=(height,width), transform=transform, invert=True) for u in units(config)}
    lineage = [dict(source="ESA WorldCover 2021 v200", id=wc["id"], href=wc["assets"]["map"]["href"],
                    interpretation="Historical cropland class, not current crop identity", licence="CC-BY-4.0")]
    all_observations, rains, failures = [], [], []
    years = config["reference_years"]+[config["target_year"]]
    for year in years:
        interval = f'{year}-{config["month"]:02}-{config["window_start_day"]:02}T00:00:00Z/{year}-{config["month"]:02}-{config["window_end_day"]:02}T23:59:59Z'
        items = search("sentinel-2-l2a", bbox, interval)
        # Require one tile covering the whole study box; deduplicate datatakes.
        complete = [i for i in items if i["bbox"][0] <= bbox[0] and i["bbox"][1] <= bbox[1]
                    and i["bbox"][2] >= bbox[2] and i["bbox"][3] >= bbox[3]]
        dedup = {}
        for item in sorted(complete, key=lambda i: i["id"]):
            dedup[item["properties"]["datetime"]] = item
        selected = sorted(dedup.values(), key=lambda i: (i["properties"]["eo:cloud_cover"], i["id"]))[:config["max_scenes_per_year"]]
        print(f"{year}: {len(items)} catalog items, {len(selected)} selected datatakes", flush=True)
        for item in selected:
            try:
                q, ro, no, xml_hash = reflectance_parameters(item)
                red = read_asset(item, "B04", transform, width, height, "EPSG:32636").astype(float)
                nir = read_asset(item, "B08", transform, width, height, "EPSG:32636").astype(float)
                scl = read_asset(item, "SCL", transform, width, height, "EPSG:32636", True)
                valid = np.isin(scl, [4, 5]) & ~binary_dilation(~np.isin(scl, [4, 5]), iterations=1)
                valid &= (red > 0) & (nir > 0)
                red, nir = (red+ro)/q, (nir+no)/q
                valid &= (red >= 0) & (nir >= 0) & (red+nir > 0)
                ndvi = np.divide(nir-red, nir+red, out=np.full_like(red, np.nan), where=valid)
                stamp = item["properties"]["datetime"]
                for unit_id, mask in unit_masks.items():
                        values = ndvi[mask]
                        count = int(np.isfinite(values).sum())
                        all_observations.append(dict(unit_id=unit_id, year=year,
                             acquired_at=stamp, source_id=item["id"], ndvi=float(np.nanmedian(values)) if count else None,
                             usable_fraction=count/int(mask.sum()) if mask.any() else 0,
                             valid_pixels=count, cropland_pixels=int(mask.sum())))
                lineage.append(dict(source="Sentinel-2 L2A", id=item["id"], acquired_at=stamp,
                     baseline=item["properties"]["s2:processing_baseline"], quantification=q,
                     red_offset=ro, nir_offset=no, metadata_sha256=xml_hash,
                     masked_ndvi_sha256=hashlib.sha256(ndvi.tobytes()).hexdigest(),
                     assets={k:item["assets"][k]["href"] for k in ["B04", "B08", "SCL", "product-metadata"]},
                     licence="Copernicus Sentinel data terms"))
            except Exception as exc:
                failures.append(dict(source_id=item["id"], error_type=type(exc).__name__))
                print("Scene failed:", item["id"], type(exc).__name__, flush=True)
        rain_url = f'https://data.chc.ucsb.edu/products/CHIRPS/v3.0/pentads/africa/tifs/chirps-v3.0.{year}.{config["month"]:02}.{config["rain_pentad"]}.tif'
        try:
            raw = fetch(rain_url, binary=True)
            with rasterio.io.MemoryFile(raw) as mem, mem.open() as src:
                from rasterio.windows import from_bounds as pixel_window
                window = pixel_window(*bbox, transform=src.transform).round_offsets().round_lengths()
                from rasterio.windows import bounds as window_bounds
                if not np.allclose(window_bounds(window, src.transform), bbox, atol=1e-6, rtol=0):
                    raise ValueError("Monitoring box must align exactly with native CHIRPS cells")
                array = src.read(1, window=window, masked=True)
                # Study box is 0.1 degrees; one 0.05-degree rainfall pixel per review unit.
                if array.shape != (2, 2) or np.ma.getmaskarray(array).any() or (array < 0).any():
                    raise ValueError("Rainfall grid alignment or validity failed")
                for row in range(2):
                    for col in range(2):
                        rains.append(dict(unit_id=f"IG-{row+1}{col+1}", year=year, mm=float(array[row,col]),
                                          start=f"{year}-05-11", end=f"{year}-05-15", source=rain_url))
            lineage.append(dict(source="CHIRPS v3 final pentad", href=rain_url, sha256=hashlib.sha256(raw).hexdigest(),
                                native_resolution_degrees=.05, unit="mm / pentad", licence="Public domain"))
        except Exception as exc:
            failures.append(dict(source_id=rain_url, error_type=type(exc).__name__))
            print("Rainfall failed:", year, type(exc).__name__, flush=True)
    observations = dict(config=config, observations=all_observations, rainfall=rains,
                        lineage=lineage, failures=failures, retrieved_at=datetime.now(timezone.utc).isoformat())
    (ROOT/"outputs/uganda/observations.json").write_text(json.dumps(observations, indent=2, allow_nan=False))
    return assess(observations)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=ROOT/"configs/uganda_iganga.json")
    args = p.parse_args()
    started = time.monotonic()
    result = build(json.loads(args.config.read_text()))
    result["build_seconds"] = round(time.monotonic()-started, 1)
    export_bundle(result, ROOT/"web/data")
    print("Wrote public-data retrospective demo to web/data", flush=True)
