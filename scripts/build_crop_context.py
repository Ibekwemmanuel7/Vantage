"""Join frozen six-band observations to historical WorldCover 2021 crop context.

Research evidence only. The original adviser review queue is never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from scripts.prepare_ml_dataset import cached_asset,write_cog
from scripts.prepare_multispectral import validate_scene
from vantage.imagery import atomic_json,sha256_file
from vantage.archive import fingerprint
from vantage.planetary import ContainerSigner
from vantage.crop_context import crop_evidence,landcover_masks
import numpy as np
import rasterio
from rasterio.transform import Affine


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path)
    p.add_argument("--allow-downloads",action="store_true")
    p.add_argument("--out",type=Path,default=ROOT/"outputs/africa/crop-context")
    args=p.parse_args()
    multi=ROOT/"outputs/africa/multispectral"
    manifest=args.dataset or multi/json.loads((multi/"latest.json").read_text())["manifest"]
    data=json.loads(manifest.read_text())
    multi=manifest.parent
    archive=ROOT/data["source_archive"]
    archive_data=json.loads(archive.read_text())
    if sha256_file(archive)!=data["identity"]["archive_sha256"]:raise ValueError("Source archive changed")
    boxes={w["location_id"]:w["bbox"] for w in archive_data["windows"]}
    source.signed=ContainerSigner(source.SESSION)
    args.out.mkdir(parents=True,exist_ok=True)
    contexts={};rows=[];failures=[]
    for location in sorted(data["sequences"]):
        try:
            selected=[r for r in data["scenes"] if r["location_id"]==location]
            grid=selected[0]["grid"];bbox=boxes[location]
            if len({r["grid_id"] for r in selected})!=1:raise ValueError("Location grids disagree")
            catalog_path=args.out/(location+"-worldcover.stac.json")
            if not catalog_path.exists():
                if not args.allow_downloads:raise FileNotFoundError("WorldCover search not archived")
                items=source.search("esa-worldcover",bbox)
                atomic_json(catalog_path,dict(features=items))
            items=json.loads(catalog_path.read_text())["features"]
            w,s,e,n=bbox
            item=next(i for i in sorted(items,key=lambda i:i["id"]) if "2021" in i["id"]
                      and i["bbox"][0]<=w and i["bbox"][1]<=s and i["bbox"][2]>=e and i["bbox"][3]>=n)
            transform=Affine(*grid["transform"][:6])
            classes=cached_asset(item,"map",transform,grid["width"],grid["height"],args.allow_downloads)
            crop,known=landcover_masks(classes)
            recipe=dict(dataset_id=data["dataset_id"],location_id=location,grid=grid,worldcover_id=item["id"],
                source_catalog_sha256=sha256_file(catalog_path),raw_classification_sha256=hashlib.sha256(classes.tobytes()).hexdigest(),
                code={p:sha256_file(ROOT/p) for p in ("vantage/crop_context.py","scripts/build_crop_context.py")},
                policy="2021 class40; categorical nearest-neighbour to analysis grid; min fraction0.6 and valid pixels100; research only")
            context_id=fingerprint(recipe)[:24]
            path=args.out/(context_id+".tif")
            if path.exists():
                with rasterio.open(path) as existing:
                    if not np.array_equal(existing.read(),np.stack([crop,known]).astype('uint8')):
                        raise ValueError("Existing crop-context artifact differs")
            else:write_cog(path,np.stack([crop,known]).astype('uint8'),transform,["historical_cropland_2021","landcover_known"])
            contexts[location]=dict(context_id=context_id,recipe=recipe,asset=path.name,sha256=sha256_file(path),
                source_href=item["assets"]["map"]["href"],licence="CC-BY-4.0",
                attribution="© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium")
            for record in selected:
                validate_scene(record,multi)
                with rasterio.open(multi/record["artifact_id"]/record["assets"]["reflectance"]["href"]) as ds:cube=ds.read()
                evidence=crop_evidence(cube,np.isfinite(cube).all(axis=0),classes)
                rows.append(dict(scene_id=record["scene_id"],location_id=location,acquired_at=record["acquired_at"],
                    artifact_id=record["artifact_id"],whole_box_usable_fraction=record["common_usable_fraction"],**evidence))
            print(f"{location}: {int(crop.sum())} historical crop pixels, {len(selected)} dated observations",flush=True)
        except Exception as exc:
            failures.append(dict(location_id=location,error_type=type(exc).__name__))
            print(f"{location}: {type(exc).__name__}",flush=True)
    report=dict(schema_version="crop-context-1",dataset_id=data["dataset_id"],source_dataset_sha256=sha256_file(manifest),
        dataset_complete=data["complete_for_requested_scenes"],contexts=contexts,observations=sorted(rows,key=lambda r:(r["location_id"],r["acquired_at"])),
        failures=failures,independent_field_labels=0,trained_model=False,foundation_ready=False,
        limitation="Retrospective research; historical land cover is not current crop truth. Dates are observations, not delivery-time proof. No imagery-only diagnosis or irrigation prescription.")
    report["context_run_id"]=fingerprint(report)[:24]
    atomic_json(args.out/(report["context_run_id"]+".json"),report)
    if not failures:
        atomic_json(args.out/"latest.json",dict(manifest=report["context_run_id"]+".json"))
        # Only public geospatial research measurements, no field outcomes or tokens.
        atomic_json(ROOT/"web/data/research-readiness.json",report)
    print(f"Context report {report['context_run_id']}; {len(rows)} observations; {len(failures)} failures",flush=True)
    if failures:sys.exit(1)


if __name__=="__main__":main()
