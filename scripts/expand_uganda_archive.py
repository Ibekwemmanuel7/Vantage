"""Archive multi-location, multi-window STAC responses; optionally process real NDVI pixels.

Offline by default. --online permits public catalog and bounded raster reads.
Leaves the existing demo, model dataset and public web files unchanged.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vantage.archive import fingerprint, windows, summarize_window


def process_pixels(item, window, out):
    # Reuse the established physical decoding and rejection contract.
    import build_uganda_demo as source
    import numpy as np
    from rasterio.transform import from_bounds
    from rasterio.warp import transform_bounds
    from vantage.imagery import derive_scene, decode_metadata
    bounds=transform_bounds("EPSG:4326","EPSG:32636",*window["bbox"])
    width=int(np.ceil((bounds[2]-bounds[0])/20)); height=int(np.ceil((bounds[3]-bounds[1])/20))
    transform=from_bounds(*bounds,width,height)
    metadata=source.fetch(source.signed(item["assets"]["product-metadata"]["href"]))
    q,offsets=decode_metadata(metadata,item["properties"]["s2:processing_baseline"])
    raw={band:source.read_asset(item,band,transform,width,height,"EPSG:32636") for band in ("B04","B08")}
    scl=source.read_asset(item,"SCL",transform,width,height,"EPSG:32636",True)
    _,valid,ndvi=derive_scene(raw,scl,q,offsets)
    artifact=out/(fingerprint([item["id"],window["bbox"],"ndvi-v1"])[:24]+".npz")
    if not artifact.exists():
        np.savez_compressed(artifact,ndvi=ndvi,valid=valid,transform=np.array(tuple(transform)),crs="EPSG:32636")
    else:
        with np.load(artifact,allow_pickle=False) as previous:
            if not (np.array_equal(previous["ndvi"],ndvi,equal_nan=True)
                    and np.array_equal(previous["valid"],valid)
                    and np.array_equal(previous["transform"],np.array(tuple(transform)))
                    and str(previous["crs"])=="EPSG:32636"):
                raise ValueError("Archived pixel artifact differs from current recipe; do not overwrite")
    # NPZ is an internal analysis cache, not a COG or a foundation-model tensor.
    return dict(pixel_status="processed",usable_fraction=float(valid.mean()),valid_pixels=int(valid.sum()),
        total_pixels=int(valid.size),ndvi_median=float(np.nanmedian(ndvi)) if valid.any() else None,
        artifact=artifact.name,artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        metadata_sha256=hashlib.sha256(metadata.encode()).hexdigest(),
        spatial_scope="Whole study box, not crop-masked or field-level",
        foundation_input_status="incompatible: only B04/B08 processed; no harmonized six-band HLS input")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",type=Path,default=ROOT/"configs/uganda_archive.json")
    p.add_argument("--out",type=Path,default=ROOT/"outputs/africa/archive")
    p.add_argument("--online",action="store_true")
    p.add_argument("--pixels",type=int,default=0,help="Bounded number of selected scenes (0-18)")
    args=p.parse_args()
    if not 0<=args.pixels<=18:p.error("Pixel budget must be 0-18 scenes")
    if args.pixels and not args.online:p.error("Pixel acquisition requires explicit --online")
    config=json.loads(args.config.read_text())
    plan=list(windows(config))
    directory=args.out/fingerprint(config)[:20]
    directory.mkdir(parents=True,exist_ok=True)
    records=[]; items={}; failures=[]
    for window in plan:
        key=f'{window["location_id"]}-{window["year"]}-{window["month"]:02}'
        path=directory/(key+".stac.json")
        try:
            if not path.exists():
                if not args.online:raise FileNotFoundError("No archived catalog response; use --online")
                url="https://planetarycomputer.microsoft.com/api/stac/v1/search?"+urlencode(dict(
                    collections=config["collection"],bbox=",".join(map(str,window["bbox"])),
                    datetime=window["interval"],limit=100))
                with urlopen(Request(url,headers={"User-Agent":"Vantage-research/0.2"}),timeout=45) as r:
                    response=json.load(r)
                # Fail before caching a truncated search as complete.
                summarize_window(window,response,config)
                archive=dict(retrieved_at=datetime.now(timezone.utc).isoformat(),request_url=url,response=response)
                with path.open("x",encoding="utf-8") as stream:json.dump(archive,stream,allow_nan=False)
            archive=json.loads(path.read_text())
            record=summarize_window(window,archive["response"],config)
            record.update(retrieved_at=archive["retrieved_at"],request_url=archive["request_url"],
                          archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            records.append(record)
            for item in archive["response"]["features"]:items[item["id"]]=item
            print(f'{key}: {record["item_count"]} items',flush=True)
        except Exception as exc:
            failures.append(dict(window=key,error_type=type(exc).__name__))
            print(f"{key}: {type(exc).__name__}",flush=True)
    # Visit every location/window in the latest year before expanding references.
    # This is deliberately a bounded feasibility sample, not a full seasonal cube.
    ordered=sorted(records,key=lambda r:(-r["year"],r["location_id"],r["month"]))
    selected=[r for r in ordered if r["candidate"]][:args.pixels]
    for record in selected:
        candidates=sorted([c for c in record["candidates"] if c["bbox_covers_study"] and c["baseline_assets_present"]],
                          key=lambda c:(c["scene_cloud_cover"] if c["scene_cloud_cover"] is not None else 101,c["id"]))[:3]
        record["pixel_attempts"]=[]
        for candidate in candidates:
            try:
                record.update(process_pixels(items[candidate["id"]],record,directory))
                record["processed_scene_id"]=candidate["id"]
                record["pixel_attempts"].append(dict(scene_id=candidate["id"],status="processed"))
                print(f'pixels {record["location_id"]}/{record["year"]}/{record["month"]}: {record["usable_fraction"]:.3f}',flush=True)
                break
            except Exception as exc:
                record["pixel_attempts"].append(dict(scene_id=candidate["id"],status="failed",
                    error_type=type(exc).__name__,http_status=getattr(exc,"code",None)))
                record.update(pixel_status="failed",pixel_error_type=type(exc).__name__)
                print(f'pixels failed: {type(exc).__name__}',flush=True)
    report=dict(schema_version="uganda-archive-1",plan_id=fingerprint(config)[:20],config=config,
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        windows_requested=len(plan),windows_archived=len(records),catalog_complete=len(records)==len(plan),
        unique_catalog_items=len(items),pixel_scenes_processed=sum(r["pixel_status"]=="processed" for r in records),
        windows=records,failures=failures,independent_field_labels=0,
        scientific_status="Retrospective data feasibility only; no new training, crop classification or field validation")
    report_path=directory/("pixels-report.json" if args.pixels else "inventory-report.json")
    temporary=report_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    temporary.replace(report_path)
    print(f"Report: {report_path}",flush=True)
    if failures or any(r["pixel_status"]=="failed" for r in records):sys.exit(1)


if __name__=="__main__":main()
