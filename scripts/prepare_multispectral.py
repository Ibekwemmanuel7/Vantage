"""Prepare actual six-band COG measurements from the frozen Uganda pixel archive.

Offline by default. No screenshots, labels, training, HLS harmonization or public
desk mutation. --allow-downloads permits missing public band cutouts only.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source
from scripts.prepare_ml_dataset import cached_asset, write_cog
from vantage.imagery import atomic_json, sha256_file
from vantage.archive import fingerprint
from vantage.multispectral import BANDS, metadata_parameters, decode_cube, spectral_features, temporal_index
from vantage.planetary import ContainerSigner
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import transform_bounds


def make_scene(window, item, metadata, destination, allow_downloads):
    bounds = transform_bounds("EPSG:4326", "EPSG:32636", *window["bbox"])
    width = int(np.ceil((bounds[2]-bounds[0])/20)); height = int(np.ceil((bounds[3]-bounds[1])/20))
    transform = from_bounds(*bounds, width, height)
    q, offsets = metadata_parameters(metadata, item["properties"]["s2:processing_baseline"])
    raw = {b: cached_asset(item, b, transform, width, height, allow_downloads) for b in BANDS}
    scl = cached_asset(item, "SCL", transform, width, height, allow_downloads)
    grid = dict(crs="EPSG:32636", transform=list(transform), width=width, height=height)
    recipe = dict(version="six-band-sentinel2-v1", scene_id=item["id"], bands=list(BANDS),
        source_collection=item.get("collection"), grid=grid, quantification=q, offsets=offsets,
        metadata_sha256=hashlib.sha256(metadata.encode()).hexdigest(),
        raw_hashes={b: fingerprint(dict(shape=list(a.shape), dtype=str(a.dtype), sha256=hashlib.sha256(a.tobytes()).hexdigest()))
                    for b, a in {**raw,"SCL":scl}.items()},
        code_hashes={p: sha256_file(ROOT/p) for p in ("vantage/multispectral.py", "vantage/planetary.py", "scripts/prepare_multispectral.py", "scripts/prepare_ml_dataset.py", "scripts/build_uganda_demo.py")},
        versions={p: importlib.metadata.version(p) for p in ("numpy","rasterio","scipy")},
        policy="SCL4/5; one analysis pixel rejection buffer; positive raw DN; finite nonnegative reflectance; no clipping above one; no filling")
    artifact_id = fingerprint(recipe)[:24]
    directory = destination / artifact_id
    manifest_path = directory/"manifest.json"
    if manifest_path.exists():
        result = json.loads(manifest_path.read_text())
        if fingerprint(result["recipe"])[:24] != artifact_id:
            raise ValueError("Scene recipe identity mismatch")
        for key, asset in result["assets"].items():
            if sha256_file(directory/asset["href"]) != asset["sha256"]:
                raise ValueError("Previously versioned artifact checksum mismatch: " + key)
        return result
    if directory.exists():
        raise ValueError("Incomplete artifact directory; inspect before retrying")
    directory.mkdir(parents=True)
    cube, band_valid, common = decode_cube(raw, scl, q, offsets)
    arrays = dict(reflectance=(cube,list(BANDS)), band_valid=(band_valid.astype("uint8"),[b+"_valid" for b in BANDS]),
                  common_valid=(common.astype("uint8"),["all_six_bands_valid"]))
    assets = {}
    for key,(array,names) in arrays.items():
        path=directory/(key+".tif")
        write_cog(path,array,transform,names)
        assets[key]=dict(href=path.name,sha256=sha256_file(path),bands=names)
    result = dict(schema_version="multispectral-scene-1",artifact_id=artifact_id,recipe=recipe,
        scene_id=item["id"],acquired_at=item["properties"]["datetime"],location_id=window["location_id"],
        grid_id=fingerprint(grid)[:20],grid=grid,assets=assets,common_usable_fraction=float(common.mean()),
        band_usable_fractions={b:float(band_valid[i].mean()) for i,b in enumerate(BANDS)},
        features=spectral_features(cube,common),product_family="Sentinel-2 L2A (not HLS)",
        foundation_ready=False,foundation_blockers=["Not HLS harmonized data","No pinned checkpoint/preprocessing adapter","No independent field outcomes"],
        scope="Whole analyst-selected box; crop and season eligibility unconfirmed",
        source_assets={b:item["assets"][b]["href"] for b in (*BANDS,"SCL","product-metadata")})
    atomic_json(manifest_path,result)
    return result


def validate_scene(record, root):
    directory=root/record["artifact_id"]
    expected=(record["grid"]["height"],record["grid"]["width"])
    for name,asset in record["assets"].items():
        path=directory/asset["href"]
        if sha256_file(path)!=asset["sha256"]:raise ValueError("Artifact checksum mismatch")
        with rasterio.open(path) as ds:
            if (ds.height,ds.width)!=expected or list(ds.transform)!=record["grid"]["transform"] or ds.crs.to_epsg()!=32636:
                raise ValueError("Artifact grid mismatch")
            if ds.tags(ns="IMAGE_STRUCTURE").get("LAYOUT")!="COG":raise ValueError("COG layout required")
            if list(ds.descriptions)!=asset["bands"]:raise ValueError("Band order mismatch")
    with rasterio.open(directory/record["assets"]["reflectance"]["href"]) as ds:
        cube=ds.read()
        if not np.isnan(ds.nodata):raise ValueError("Reflectance nodata must be NaN")
    with rasterio.open(directory/record["assets"]["band_valid"]["href"]) as ds:valid=ds.read().astype(bool)
    with rasterio.open(directory/record["assets"]["common_valid"]["href"]) as ds:common=ds.read(1).astype(bool)
    if not np.array_equal(np.isfinite(cube),valid) or not np.array_equal(common,valid.all(axis=0)):
        raise ValueError("Finite reflectance and masks disagree")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,default=ROOT/"outputs/africa/archive/d9c82747f42377f8ec84/pixels-report.json")
    p.add_argument("--out",type=Path,default=ROOT/"outputs/africa/multispectral")
    p.add_argument("--allow-downloads",action="store_true")
    p.add_argument("--publish-partial",action="store_true",help="Explicitly select a nonempty incomplete dataset as latest; status stays incomplete")
    p.add_argument("--limit",type=int,default=18)
    args=p.parse_args()
    if not 1<=args.limit<=18:p.error("Limit must be 1-18 scenes")
    # Applies only to this builder; the original reconstruction policy is intact.
    # Native public asset URLs remain the same; signing credentials are transient.
    source.signed=ContainerSigner(source.SESSION)
    report=json.loads(args.archive.read_text())
    metadata={}
    for path in source.CACHE.glob("*.txt"):
        text=path.read_text(encoding="utf-8")
        if "BOA_QUANTIFICATION_VALUE" in text:metadata[hashlib.sha256(text.encode()).hexdigest()]=text
    scenes=[];failures=[]
    selected=sorted((w for w in report["windows"] if w["pixel_status"]=="processed"),
                    key=lambda w:(-w["year"],w["location_id"],w["month"]))[:args.limit]
    args.out.mkdir(parents=True,exist_ok=True)
    for window in selected:
        sid=window["processed_scene_id"]
        try:
            path=args.archive.parent/f'{window["location_id"]}-{window["year"]}-{window["month"]:02}.stac.json'
            if sha256_file(path)!=window["archive_sha256"]:raise ValueError("Archived catalog checksum mismatch")
            data=json.loads(path.read_text())["response"]
            item=next(i for i in data["features"] if i["id"]==sid)
            result=make_scene(window,item,metadata[window["metadata_sha256"]],args.out,args.allow_downloads)
            validate_scene(result,args.out)
            scenes.append(result)
            print(f'{window["location_id"]} {window["year"]}/{window["month"]}: six-band usable {result["common_usable_fraction"]:.3f}',flush=True)
        except Exception as exc:
            failures.append(dict(scene_id=sid,location_id=window["location_id"],error_type=type(exc).__name__))
            print(f'{sid}: {type(exc).__name__}',flush=True)
    identity=dict(archive_sha256=sha256_file(args.archive),artifact_ids=sorted(r["artifact_id"] for r in scenes),
                  requested_scene_ids=sorted(w["processed_scene_id"] for w in selected),
                  unavailable_scene_ids=sorted(f["scene_id"] for f in failures))
    dataset_id=fingerprint(identity)[:24]
    sequences={location:temporal_index([r for r in scenes if r["location_id"]==location])
               for location in sorted({r["location_id"] for r in scenes})}
    dataset=dict(schema_version="multispectral-dataset-1",dataset_id=dataset_id,identity=identity,
        complete_for_requested_scenes=not failures and len(scenes)==len(selected),
        bands=list(BANDS),units="physical surface reflectance (unitless)",scenes=scenes,sequences=sequences,
        independent_field_labels=0,trained_model=False,foundation_ready=False,
        temporal_scope="Sparse observed acquisitions across years; not a dense crop-season series",
        source_archive=str(args.archive.relative_to(ROOT)) if args.archive.is_relative_to(ROOT) else args.archive.name)
    path=args.out/(dataset_id+".json")
    if path.exists() and json.loads(path.read_text())!=dataset:raise ValueError("Dataset identity collision")
    atomic_json(path,dataset)
    # Execution diagnostics do not change scientific dataset identity between
    # online HTTP failures and offline cache misses for the same absent scenes.
    attempt=dict(dataset_id=dataset_id,allow_downloads=args.allow_downloads,failures=failures)
    atomic_json(args.out/"attempts"/(fingerprint(attempt)[:24]+".json"),attempt)
    if scenes and (not failures or args.publish_partial):
        atomic_json(args.out/"latest.json",dict(dataset_id=dataset_id,manifest=path.name,
                    complete_for_requested_scenes=not failures,scene_count=len(scenes)))
    print(f"Validated {len(scenes)} scenes / {len(scenes)*3} COGs; failures {len(failures)}; dataset {dataset_id}",flush=True)
    if failures:sys.exit(1)


if __name__=="__main__":main()
