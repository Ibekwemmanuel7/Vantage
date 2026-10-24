"""Reusable fixed-cohort terrain, source-annotation and bounded visibility workflow."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from scripts.build_kween_case import archive_search
from scripts.build_terrain_screen import elevation_clip
from scripts.check_lira_viewing import fetch_cached
from scripts.acquire_viewing_annotations import product_references
from scripts.build_viewing_geometry import grid_geometry,calculate,radar_grid,geometry_summary
from vantage.archive import fingerprint
from vantage.gap_radar_pixels import slope_screen_summary
from vantage.planetary import ContainerSigner
from vantage.safe_annotations import verify_annotation
from vantage.terrain import slope_proxy,classify_proxy
from vantage.viewing import parse_annotation,interpolate_look,unit
from vantage.visibility import sightlines,CLASS_NAMES
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject,transform_bounds,transform as warp_coordinates


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_plan(plan):
    if (plan["derivative_resolution_m"],plan["padding_m"],plan["slope_thresholds"],
        plan["distance_m"],plan["step_m"],plan["clearance_guard_m"],plan["visibility_padding_cells"])!=(30,180,[5,10,15],5000,15,5,169):
        raise ValueError("Fixed derivative/sightline policy required")
    if type(plan["max_passes"]) is not int or not 1<=plan["max_passes"]<=3:
        raise ValueError("At most three fixed-track passes required")


def save_arrays(path,**arrays):
    if path.exists():
        with np.load(path,allow_pickle=False) as old:
            if any(not np.array_equal(old[k],v,equal_nan=True) for k,v in arrays.items()):
                raise ValueError("Derived quality arrays differ on replay")
    else:np.savez_compressed(path,**arrays)


def annotation_bytes(index,item,root,online,signer):
    links=[l["href"] for l in item["links"] if l.get("rel")=="derived_from"]
    if len(links)!=1 or not links[0].startswith("https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-grd/items/"):
        raise ValueError("Authoritative GRD source required")
    grd_path=root/f"{index}-grd.json"
    grd=json.loads(fetch_cached(grd_path,links[0],online))
    manifest_path=root/f"{index}-manifest.xml"
    href=grd["assets"]["safe-manifest"]["href"]
    raw_manifest=fetch_cached(manifest_path,href,online,signer)
    refs=[r for r in product_references(raw_manifest.decode(),href)
          if "vv" in urlparse(r["href"]).path.rsplit("/",1)[-1].lower()]
    if len(refs)!=1:raise ValueError("One SAFE-referenced VV product annotation required")
    reference=refs[0]
    path=root/f"{index}-annotation.xml"
    if not path.exists():
        if not online:raise FileNotFoundError("Source annotation not cached")
        response=source.SESSION.get(signer(reference["href"]),timeout=45)
        if response.status_code==404:
            mapped=grd["assets"]["vv"]["href"].replace("/measurement/","/annotation/").rsplit(".",1)[0]+".xml"
            response=source.SESSION.get(signer(mapped),timeout=45)
        response.raise_for_status()
        verify_annotation(response.content,reference)
        path.write_bytes(response.content)
    raw=path.read_bytes()
    return raw,dict(source_grd=grd_path.name,source_grd_sha256=digest(grd_path),
        manifest=manifest_path.name,manifest_sha256=digest(manifest_path),annotation=path.name,
        annotation_sha256=verify_annotation(raw,reference),reference_md5=reference["md5"],reference_size=reference["size"])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True,type=Path)
    parser.add_argument("--online",action="store_true")
    args=parser.parse_args()
    plan=json.loads(args.config.read_text())
    validate_plan(plan)
    parent_root=ROOT/"outputs/africa/gap-radar-pixels"/plan["parent_radar_directory"]
    parent_path=parent_root/"report.json"
    parent=json.loads(parent_path.read_text())
    records=parent["observations"]
    if not 1<=len(records)<=plan["max_passes"] or any(r["status"]!="processed" or r["track_id"]!=plan["track_id"] for r in records):
        raise ValueError("Complete pinned fixed-track numerical cohort required")
    grid=parent["grid"]
    if grid["crs"]!="EPSG:32636":raise ValueError("Supported metric grid required")
    transform=rasterio.Affine(*grid["transform"][:6])
    west,south,east,north=rasterio.transform.array_bounds(grid["height"],grid["width"],transform)
    left=np.floor((west-plan["padding_m"])/30)*30
    top=np.ceil((north+plan["padding_m"])/30)*30
    width=int(np.ceil((east+plan["padding_m"]-left)/30))
    height=int(np.ceil((top-south+plan["padding_m"])/30))
    dt=rasterio.Affine(30,0,left,0,-30,top)
    derivative=dict(crs=grid["crs"],transform=list(dt),width=width,height=height)
    bbox=list(transform_bounds(grid["crs"],"EPSG:4326",*rasterio.transform.array_bounds(height,width,dt)))
    root=ROOT/"outputs/africa/gap-quality"/fingerprint(plan)[:20]
    root.mkdir(parents=True,exist_ok=True)
    source.CACHE.mkdir(parents=True,exist_ok=True)
    items,elevation_catalog_hash=archive_search(root,"elevation-catalog",plan["elevation_collection"],bbox,None,args.online)
    tiles=[i for i in items if "data" in i.get("assets",{}) and i["bbox"][0]<=bbox[0] and i["bbox"][1]<=bbox[1]
           and i["bbox"][2]>=bbox[2] and i["bbox"][3]>=bbox[3]]
    if not tiles:raise ValueError("No single full-cover elevation tile")
    tile=sorted(tiles,key=lambda i:i["id"])[0]
    elevation,support,terrain_lineage=elevation_clip(tile,derivative,root/"native-elevation.npz",args.online)
    elevation[(support<plan["native_support_required"])|~np.isfinite(support)]=np.nan
    _,maximum=slope_proxy(elevation,30,30)
    mapped_maximum=np.full((grid["height"],grid["width"]),np.nan,dtype="float32")
    reproject(maximum,mapped_maximum,src_transform=dt,src_crs=grid["crs"],dst_transform=transform,
              dst_crs=grid["crs"],src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.nearest)
    slope_classes=np.stack([classify_proxy(mapped_maximum,t) for t in plan["slope_thresholds"]])
    save_arrays(root/"slope-proxy.npz",classes=slope_classes,maximum=mapped_maximum)
    print("Independent slope proxy processed",flush=True)
    basis=grid_geometry(derivative)
    up=basis["up"]
    xaxis=basis["grid_x_delta"]-up*np.sum(basis["grid_x_delta"]*up,axis=-1)[...,None]
    yaxis=basis["grid_y_delta"]-up*np.sum(basis["grid_y_delta"]*up,axis=-1)[...,None]
    padding=plan["visibility_padding_cells"]
    expanded=dict(derivative,width=width+2*padding,height=height+2*padding,
                  transform=list(dt*rasterio.Affine.translation(-padding,-padding)))
    broad,bsupport,expanded_lineage=elevation_clip(tile,expanded,root/"expanded-elevation.npz",args.online)
    broad[(bsupport<plan["native_support_required"])|~np.isfinite(bsupport)]=np.nan
    rr,cc=np.indices((height,width))
    catalog_path=ROOT/"outputs/africa/gap-radar"/parent["plan"]["catalog_directory"]/"catalog.json"
    if digest(catalog_path)!=parent["source_catalog_sha256"]:raise ValueError("Radar catalog differs")
    by_id={i["id"]:i for i in json.loads(catalog_path.read_text())["response"]["features"]}
    signer=ContainerSigner(source.SESSION)
    results=[]
    for index,record in enumerate(records):
        raw,lineage=annotation_bytes(index,by_id[record["item_id"]],root,args.online,signer)
        local,annotation_summary=calculate(raw,record,elevation,derivative,basis,plan)
        angles,classes=radar_grid(local,derivative,grid)
        summary=geometry_summary(classes,angles,np.ones(classes.shape,dtype=bool))
        summary["whole_box_pixels"]=summary.pop("historical_crop_pixels")
        summary["locally_unflagged_whole_box_fraction"]=summary.pop("locally_unflagged_crop_fraction")
        parsed=parse_annotation(raw,record,plan["annotation_incidence_tolerance_degrees"])
        gx,gy=warp_coordinates("EPSG:4326",grid["crs"],parsed["longitude"].tolist(),parsed["latitude"].tolist())
        look=interpolate_look(np.column_stack([gx,gy]),parsed["look_ecef"],basis["query"])
        lx=np.sum(look*unit(xaxis),axis=-1)
        ly=np.sum(look*unit(yaxis),axis=-1)
        horizontal=np.hypot(lx,ly)
        ray=sightlines(broad,rr+padding,cc+padding,lx/horizontal/np.linalg.norm(xaxis,axis=-1),
            ly/horizontal/np.linalg.norm(yaxis,axis=-1),np.sum(look*up,axis=-1)/horizontal,
            distance=plan["distance_m"],step=plan["step_m"],guard=plan["clearance_guard_m"])
        mapped=np.zeros(classes.shape,dtype="uint8")
        reproject(ray["classes"],mapped,src_transform=dt,src_crs=grid["crs"],dst_transform=transform,
                  dst_crs=grid["crs"],resampling=Resampling.nearest)
        radar_path=parent_root/record["artifact"]
        if digest(radar_path)!=record["artifact_sha256"]:raise ValueError("Radar values differ")
        with np.load(radar_path,allow_pickle=False) as data:
            if str(data["crs"])!=grid["crs"] or data["transform"].tolist()!=grid["transform"]:raise ValueError("Radar grid differs")
            numeric=np.isfinite(data["power"]).all(axis=0)&(data["power"]>0).all(axis=0)
        artifact=root/f"{index}-quality.npz"
        save_arrays(artifact,local_classes=classes,angles=angles,visibility_classes=mapped,
                    minimum_clearance=ray["minimum_clearance"],supported_fraction=ray["supported_fraction"])
        row=dict(item_id=record["item_id"],acquired_at=record["acquired_at"],track_id=record["track_id"],
            lineage=lineage,annotation_geometry=annotation_summary,local_geometry=summary,
            slope_sensitivity=[dict(threshold_degrees=t,**slope_screen_summary(c,numeric)) for t,c in zip(plan["slope_thresholds"],slope_classes)],
            bounded_visibility_counts={name:int((mapped==code).sum()) for code,name in enumerate(CLASS_NAMES)},
            joint_numeric_locally_unflagged_bounded_clear_pixels=int((numeric&(classes==1)&(mapped==1)).sum()),
            artifact=artifact.name,artifact_sha256=digest(artifact),usable_for_model_training=False)
        results.append(row)
        print(json.dumps(dict(item_id=row["item_id"],local_counts=summary["counts"],visibility=row["bounded_visibility_counts"])),flush=True)
    report=dict(schema_version="gap-radar-quality-1",plan=plan,grid=grid,derivative_grid=derivative,
        processed_at=datetime.now(timezone.utc).isoformat(),observations=results,
        source_radar_report_sha256=digest(parent_path),elevation_item_id=tile["id"],elevation_catalog_sha256=elevation_catalog_hash,
        terrain_lineage={k:v for k,v in terrain_lineage.items() if k!="unsigned_href"},
        expanded_terrain_lineage={k:v for k,v in expanded_lineage.items() if k!="unsigned_href"},
        slope_artifact_sha256=digest(root/"slope-proxy.npz"),
        code_sha256={name:digest(ROOT/name) for name in ["scripts/check_gap_radar_quality.py","scripts/build_terrain_screen.py",
            "scripts/build_viewing_geometry.py","scripts/check_lira_viewing.py","scripts/acquire_viewing_annotations.py",
            "vantage/viewing.py","vantage/visibility.py","vantage/terrain.py","vantage/safe_annotations.py","vantage/gap_radar_pixels.py"]},
        independent_processor_status="awaiting_exports",radar_illumination_confirmed=False,usable_for_model_training=False,
        limitation="Local/finite-range terrain checks only; independent processor, source delivery, crop and field validity unverified")
    (root/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(f"Report: {root / 'report.json'}")


if __name__=="__main__":
    try:main()
    except Exception as error:
        print(json.dumps(dict(status="failed_no_complete_quality_result",error_type=type(error).__name__)),flush=True)
        sys.exit(1)
