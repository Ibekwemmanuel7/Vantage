"""Bounded acquisition-specific Lira DSM sightlines, never full illumination validity."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from scripts.build_terrain_screen import elevation_clip
from scripts.build_viewing_geometry import grid_geometry
from vantage.archive import fingerprint
from vantage.viewing import parse_annotation,interpolate_look,unit
from vantage.visibility import sightlines,CLASS_NAMES
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform as warp_coordinates,reproject


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online",action="store_true")
    args=parser.parse_args()
    plan=json.loads((ROOT/"configs/lira_gap_visibility.json").read_text())
    if (plan["distance_m"],plan["step_m"],plan["clearance_guard_m"],plan["padding_cells"],plan["max_passes"])!=(5000,15,5,169,2):
        raise ValueError("Fixed bounded visibility policy required")
    view_root=ROOT/"outputs/africa/gap-viewing"/plan["parent_viewing_directory"]
    view_path=view_root/"report.json"
    view=json.loads(view_path.read_text())
    for name,expected in view["code_sha256"].items():
        if digest(ROOT/name)!=expected:raise ValueError("Viewing implementation differs")
    terrain_root=ROOT/"outputs/africa/gap-terrain"/view["plan"]["parent_terrain_directory"]
    terrain_path=terrain_root/"report.json"
    if digest(terrain_path)!=view["source_terrain_report_sha256"]:raise ValueError("Terrain parent differs")
    terrain=json.loads(terrain_path.read_text())
    radar_path=ROOT/"outputs/africa/gap-radar-pixels"/view["plan"]["parent_radar_directory"]/"report.json"
    if digest(radar_path)!=view["source_radar_report_sha256"]:raise ValueError("Radar parent differs")
    radar=json.loads(radar_path.read_text())
    catalog_path=terrain_root/"elevation-catalog.json"
    if digest(catalog_path)!=terrain["elevation_catalog_sha256"]:raise ValueError("Elevation catalog differs")
    item=next(i for i in json.loads(catalog_path.read_text())["response"]["features"] if i["id"]==terrain["elevation_item_id"])
    grid=terrain["derivative_grid"]
    transform=rasterio.Affine(*grid["transform"][:6])
    if transform.a!=30 or transform.e!=-30 or transform.b!=0 or transform.d!=0:
        raise ValueError("Unrotated 30m derivative grid required")
    padding=plan["padding_cells"]
    expanded=dict(grid,width=grid["width"]+2*padding,height=grid["height"]+2*padding,
                  transform=list(transform*rasterio.Affine.translation(-padding,-padding)))
    root=ROOT/"outputs/africa/gap-visibility"/fingerprint(plan)[:20]
    root.mkdir(parents=True,exist_ok=True)
    elevation,support,lineage=elevation_clip(item,expanded,root/"native-elevation.npz",args.online)
    elevation[(support<.999)|~np.isfinite(support)]=np.nan
    basis=grid_geometry(grid)
    up=basis["up"]
    xaxis=basis["grid_x_delta"]-up*np.sum(basis["grid_x_delta"]*up,axis=-1)[...,None]
    yaxis=basis["grid_y_delta"]-up*np.sum(basis["grid_y_delta"]*up,axis=-1)[...,None]
    xscale=np.linalg.norm(xaxis,axis=-1)
    yscale=np.linalg.norm(yaxis,axis=-1)
    rows,cols=np.indices((grid["height"],grid["width"]))
    results=[]
    if len(view["observations"])!=2:raise ValueError("Complete two-pass viewing cohort required")
    for index,record in enumerate(view["observations"]):
        if record["status"]!="processed":raise ValueError("Verified viewing inputs required")
        annotation=view_root/record["annotation"]
        if digest(annotation)!=record["annotation_sha256"]:raise ValueError("Annotation differs")
        parsed=parse_annotation(annotation.read_bytes(),record,view["plan"]["annotation_incidence_tolerance_degrees"])
        gx,gy=warp_coordinates("EPSG:4326",grid["crs"],parsed["longitude"].tolist(),parsed["latitude"].tolist())
        look=interpolate_look(np.column_stack([gx,gy]),parsed["look_ecef"],basis["query"])
        lx=np.sum(look*unit(xaxis),axis=-1)
        ly=np.sum(look*unit(yaxis),axis=-1)
        horizontal=np.hypot(lx,ly)
        result=sightlines(elevation,rows+padding,cols+padding,lx/horizontal/xscale,ly/horizontal/yscale,
            np.sum(look*up,axis=-1)/horizontal,distance=plan["distance_m"],step=plan["step_m"],guard=plan["clearance_guard_m"])
        target=radar["grid"]
        mapped=np.zeros((target["height"],target["width"]),dtype="uint8")
        reproject(result["classes"],mapped,src_transform=transform,src_crs=grid["crs"],
            dst_transform=rasterio.Affine(*target["transform"][:6]),dst_crs=target["crs"],resampling=Resampling.nearest)
        local_path=view_root/record["artifact"]
        if digest(local_path)!=record["artifact_sha256"]:raise ValueError("Local geometry differs")
        with np.load(local_path,allow_pickle=False) as local:
            if local["classes"].shape!=mapped.shape or str(local["crs"])!=target["crs"] or local["transform"].tolist()!=target["transform"]:
                raise ValueError("Local geometry grid differs")
            joint=(mapped==1)&(local["classes"]==1)
        asset=root/f"{index}-visibility.npz"
        arrays=dict(classes=mapped,derivative_classes=result["classes"],minimum_clearance=result["minimum_clearance"],
                    minimum_distance=result["minimum_distance"],supported_fraction=result["supported_fraction"])
        if asset.exists():
            with np.load(asset,allow_pickle=False) as previous:
                if any(not np.array_equal(previous[k],v,equal_nan=True) for k,v in arrays.items()):
                    raise ValueError("Visibility artifact differs")
        else:np.savez_compressed(asset,**arrays)
        row=dict(item_id=record["item_id"],acquired_at=record["acquired_at"],sample_count=result["samples"],
            whole_box_counts={name:int((mapped==code).sum()) for code,name in enumerate(CLASS_NAMES)},
            whole_box_pixels=int(mapped.size),joint_locally_unflagged_and_bounded_clear_pixels=int(joint.sum()),
            artifact=asset.name,artifact_sha256=digest(asset),radar_illumination_confirmed=False)
        results.append(row)
        print(json.dumps(row),flush=True)
    report=dict(schema_version="lira-bounded-visibility-1",plan=plan,observations=results,
        processed_at=datetime.now(timezone.utc).isoformat(),
        source_viewing_report_sha256=digest(view_path),source_terrain_report_sha256=digest(terrain_path),
        source_elevation_catalog_sha256=digest(catalog_path),
        elevation_item_id=item["id"],elevation_lineage={k:v for k,v in lineage.items() if k!="unsigned_href"},
        expanded_grid=expanded,derivative_grid=grid,target_grid=radar["grid"],
        implementation_sha256={name:digest(ROOT/name) for name in
            ["scripts/check_lira_visibility.py","vantage/visibility.py","vantage/viewing.py","scripts/build_viewing_geometry.py","scripts/build_terrain_screen.py"]},
        bounded_nonlocal_visibility_checked=True,radar_illumination_confirmed=False,usable_agricultural_evidence=False,
        limitation="Sampled flat-tangent 5km search only; not full shadow/layover or trusted-processor agreement")
    (root/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(f"Report: {root / 'report.json'}")


if __name__=="__main__":
    try:main()
    except Exception as error:
        # Provider/GDAL exception text can contain signed access URLs.
        print(json.dumps(dict(status="failed_no_visibility_result",error_type=type(error).__name__)),flush=True)
        sys.exit(1)
