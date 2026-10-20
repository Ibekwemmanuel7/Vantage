"""Check artifact integrity, raster grids and optional official STAC schemas."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo  # Match the PROJ database to this Rasterio wheel.
from vantage.imagery import sha256_file,stable_hash
import numpy as np
import rasterio


def validate(directory,schemas=False):
    directory=Path(directory)
    manifest=json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
    if stable_hash(manifest["recipe"])[:20]!=manifest["dataset_id"]:raise ValueError("Recipe identifier mismatch")
    if sha256_file(directory/"source-observations.json")!=manifest["recipe"]["source_sha256"]:raise ValueError("Source observations changed")
    if sha256_file(directory/"observations.jsonl")!=manifest["observations_sha256"]:raise ValueError("Observation records changed")
    count=0
    for scene,hashes in manifest["asset_hashes"].items():
        item=json.loads((directory/"stac"/(scene+".json")).read_text())
        if item["properties"]["vantage:dataset_id"]!=manifest["dataset_id"]:raise ValueError("STAC linkage mismatch")
        for kind,digest in hashes.items():
            path=directory/"assets"/(scene+"-"+kind+".tif")
            if sha256_file(path)!=digest:raise ValueError("Raster checksum mismatch")
            with rasterio.open(path) as src:
                if [src.height,src.width]!=manifest["shape"] or list(src.transform)!=manifest["transform"] or src.crs.to_epsg()!=32636:
                    raise ValueError("Raster grid mismatch")
                if src.tags(ns="IMAGE_STRUCTURE").get("LAYOUT")!="COG":raise ValueError("Raster is not cloud optimized")
                if kind=="ndvi":
                    values=src.read(1)
                    if np.any(np.abs(values[np.isfinite(values)])>1):raise ValueError("Invalid NDVI")
                if kind=="quality" and not np.isin(src.read([2,3]),[0,1]).all():raise ValueError("Invalid binary quality masks")
            count+=1
        if schemas:
            import pystac
            pystac.Item.from_file(str(directory/"stac"/(scene+".json"))).validate()
    if schemas:
        import pystac
        pystac.Catalog.from_file(str(directory/"stac/catalog.json")).validate()
    return dict(dataset_id=manifest["dataset_id"],scenes=len(manifest["scene_ids"]),cogs=count,
                checksum_and_grid_checks="passed",official_stac_schemas="passed" if schemas else "not_requested")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path)
    p.add_argument("--schemas",action="store_true",help="May fetch official STAC and extension JSON schemas")
    a=p.parse_args()
    if a.dataset is None:
        latest=json.loads((ROOT/"outputs/ml/datasets/latest.json").read_text())
        a.dataset=ROOT/"outputs/ml/datasets"/latest["path"]
    print(json.dumps(validate(a.dataset,a.schemas)),flush=True)
