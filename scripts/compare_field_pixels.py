"""Write a private observed field-change report and masked GeoTIFF, offline."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Pair JSON; see docs/integration/FIELD_CHANGE.md")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        from scripts.validate_field_evidence import private_output
        directory = private_output(args.out_dir)
        proj = Path(importlib.util.find_spec("rasterio").origin).parent / "proj_data"
        if proj.is_dir():
            os.environ["PROJ_DATA"] = os.environ["PROJ_LIB"] = str(proj)
        import numpy as np
        import rasterio
        from affine import Affine
        from vantage.field_change import compare_fields
        raw = args.input.read_bytes()
        spec = json.loads(raw.decode("utf-8-sig"))
        boundary_path = args.input.parent / spec["boundaries"]
        boundary_raw = boundary_path.read_bytes()
        collection = json.loads(boundary_raw.decode("utf-8-sig"))
        scenes = []
        hashes = dict(spec=hashlib.sha256(raw).hexdigest(), boundaries=hashlib.sha256(boundary_raw).hexdigest())
        for name in ("before", "after"):
            entry = spec[name]
            path = args.input.parent / entry["pixels"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != entry["sha256"]:
                raise ValueError(f"{name} artifact checksum mismatch")
            with np.load(path, allow_pickle=False) as data:
                scene = {key: data[key].copy() for key in ("ndvi", "valid", "transform")}
                scene["crs"] = str(data["crs"])
            scene.update({key: entry[key] for key in ("acquired_at", "available_at", "source_ref", "recipe_ref")})
            scenes.append(scene)
            hashes[name] = digest
        report, delta, valid = compare_fields(collection, *scenes, cutoff=spec["cutoff"])
        report["input_sha256"] = hashes
        report["software_versions"] = dict(numpy=np.__version__, rasterio=rasterio.__version__)
        directory.mkdir(parents=True, exist_ok=False)
        raster_path = directory / "observed-change.tif"
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(raster_path, "w", driver="GTiff", height=delta.shape[0], width=delta.shape[1],
                               count=1, dtype="float32", crs=scenes[1]["crs"],
                               transform=Affine(*tuple(scenes[1]["transform"])[:6]), nodata=float("nan"), compress="deflate") as dst:
                dst.write(delta, 1)
                dst.write_mask(valid.astype("uint8") * 255)
                dst.set_band_description(1, "Observed NDVI after minus before; not a diagnosis")
                dst.update_tags(before_acquired_at=scenes[0]["acquired_at"], after_acquired_at=scenes[1]["acquired_at"],
                                decision_cutoff=spec["cutoff"], recipe_ref=scenes[1]["recipe_ref"], field_priorities_available="false")
        report["change_raster"] = dict(path=raster_path.name, sha256=hashlib.sha256(raster_path.read_bytes()).hexdigest())
        with (directory / "report.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print(f"Saved {len(report['fields'])} declared field comparisons and observed-change.tif; no field priorities.")
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        parser.exit(2, f"Field comparison failed: {exc}\n")


if __name__ == "__main__":
    main()
