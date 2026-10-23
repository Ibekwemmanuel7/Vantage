"""Offline audit of cached recent rasters; never downloads or fills missing pixels."""
import argparse
import hashlib
import json
import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Match the numerical builder's rasterio runtime rather than system PostGIS.
proj = Path(importlib.util.find_spec("rasterio").origin).parent / "proj_data"
if proj.is_dir():
    os.environ["PROJ_DATA"] = str(proj)
    os.environ["PROJ_LIB"] = str(proj)
import numpy as np
from rasterio.transform import from_bounds
from rasterio.warp import transform_bounds
from vantage.imagery import decode_metadata
from vantage.quality_audit import audit_quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text())
    path = args.inventory.parent / "pixels/observations.json"
    observations = json.loads(path.read_text())
    if hashlib.sha256(args.inventory.read_bytes()).hexdigest() != observations["inventory_sha256"]:
        raise ValueError("Inventory differs from pixel run")
    cache = ROOT / "outputs/uganda/cache"
    # Metadata cache filenames include access signatures; use content identity,
    # never expose the original URL or cache filename in the public report.
    metadata = {hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest():p
                for p in cache.glob("*.txt")}
    results = []
    for observation in observations["observations"]:
        result = dict(location_id=observation["location_id"], status="failed")
        try:
            record = next(r for r in inventory["locations"] if r["location_id"] == observation["location_id"])
            archive = args.inventory.parent / (record["location_id"] + ".stac.json")
            if hashlib.sha256(archive.read_bytes()).hexdigest() != record["archive_sha256"]:
                raise ValueError("Catalog checksum differs")
            item = next(i for i in json.loads(archive.read_text())["response"]["features"] if i["id"] == observation["scene_id"])
            bounds = transform_bounds("EPSG:4326", "EPSG:32636", *record["bbox"])
            width = int(np.ceil((bounds[2]-bounds[0])/20))
            height = int(np.ceil((bounds[3]-bounds[1])/20))
            transform = from_bounds(*bounds, width, height)
            arrays = {}
            input_hashes = {}
            for band in ("B04", "B08", "SCL"):
                key = item["assets"][band]["href"]+str(transform)+str(width)+str(height)
                cached = cache / (hashlib.sha256(key.encode()).hexdigest()+".npy")
                arrays[band] = np.load(cached, allow_pickle=False)
                input_hashes[band] = hashlib.sha256(cached.read_bytes()).hexdigest()
            text = metadata[observation["metrics"]["metadata_sha256"]].read_text(encoding="utf-8")
            q, offsets = decode_metadata(text, item["properties"]["s2:processing_baseline"])
            audit = audit_quality({b:arrays[b] for b in ("B04", "B08")}, arrays["SCL"], q, offsets)
            if audit["accepted_pixels"] != observation["metrics"]["valid_pixels"]:
                raise ValueError("Audit disagrees with original observation")
            result.update(status="audited", scene_id=item["id"], audit=audit, input_sha256=input_hashes)
        except Exception as error:
            result["error_type"] = type(error).__name__
        results.append(result)
        print(json.dumps(result), flush=True)
    destination = path.parent / "quality-audit.json"
    destination.write_text(json.dumps(dict(schema_version="quality-audit-1",
        observations_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), results=results), indent=2), encoding="utf-8")
    if any(r["status"] != "audited" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
