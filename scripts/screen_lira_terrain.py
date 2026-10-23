"""Independent 30m surface-slope proxy on the Lira radar grid; no illumination claim."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from scripts.build_kween_case import archive_search
from scripts.build_terrain_screen import elevation_clip
from vantage.archive import fingerprint
from vantage.gap_radar_pixels import slope_screen_summary
from vantage.terrain import slope_proxy,classify_proxy
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject,transform_bounds


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online",action="store_true")
    args=parser.parse_args()
    plan=json.loads((ROOT/"configs/lira_gap_terrain.json").read_text())
    if (plan["derivative_resolution_m"],plan["padding_m"],plan["sensitivity_max_slope_degrees"])!=(30,180,[5,10,15]):
        raise ValueError("Fixed metric slope recipe required")
    parent_root=ROOT/"outputs/africa/gap-radar-pixels"/plan["parent_radar_directory"]
    parent_path=parent_root/"report.json"
    parent=json.loads(parent_path.read_text())
    if parent["plan"]!=json.loads((ROOT/"configs/lira_gap_radar_pixels.json").read_text()):
        raise ValueError("Parent radar plan differs")
    grid=parent["grid"]
    if grid["crs"]!="EPSG:32636":raise ValueError("Supported metric grid required")
    transform=rasterio.Affine(*grid["transform"][:6])
    west,south,east,north=rasterio.transform.array_bounds(grid["height"],grid["width"],transform)
    resolution=plan["derivative_resolution_m"]
    padding=plan["padding_m"]
    left=np.floor((west-padding)/resolution)*resolution
    top=np.ceil((north+padding)/resolution)*resolution
    width=int(np.ceil((east+padding-left)/resolution))
    height=int(np.ceil((top-south+padding)/resolution))
    derivative_transform=rasterio.Affine(resolution,0,left,0,-resolution,top)
    derivative_grid=dict(crs=grid["crs"],transform=list(derivative_transform),width=width,height=height)
    bbox=list(transform_bounds(grid["crs"],"EPSG:4326",*rasterio.transform.array_bounds(height,width,derivative_transform)))
    root=ROOT/"outputs/africa/gap-terrain"/fingerprint(plan)[:20]
    root.mkdir(parents=True,exist_ok=True)
    source.CACHE.mkdir(parents=True,exist_ok=True)
    items,catalog_hash=archive_search(root,"elevation-catalog",plan["elevation_collection"],bbox,None,args.online)
    eligible=[i for i in items if "data" in i.get("assets",{}) and i["bbox"][0]<=bbox[0] and i["bbox"][1]<=bbox[1]
              and i["bbox"][2]>=bbox[2] and i["bbox"][3]>=bbox[3]]
    if not eligible:raise ValueError("No full-cover elevation tile; no implicit mosaic")
    item=sorted(eligible,key=lambda i:i["id"])[0]
    elevation,support,lineage=elevation_clip(item,derivative_grid,root/"native-elevation.npz",args.online)
    elevation[support<plan["native_support_required"]]=np.nan
    slope,maximum=slope_proxy(elevation,resolution,resolution)
    radar_maximum=np.full((grid["height"],grid["width"]),np.nan,dtype="float32")
    reproject(maximum,radar_maximum,src_transform=derivative_transform,src_crs=grid["crs"],
              dst_transform=transform,dst_crs=grid["crs"],src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.nearest)
    classes=np.stack([classify_proxy(radar_maximum,t) for t in plan["sensitivity_max_slope_degrees"]])
    asset=root/"slope-proxy.npz"
    if asset.exists():
        with np.load(asset,allow_pickle=False) as previous:
            if not np.array_equal(previous["classes"],classes) or not np.array_equal(previous["maximum_slope"],radar_maximum,equal_nan=True):
                raise ValueError("Slope artifact differs on replay")
    else:np.savez_compressed(asset,classes=classes,maximum_slope=radar_maximum,transform=np.array(grid["transform"]),crs=grid["crs"])
    rows=[]
    for row in parent["observations"]:
        if row["status"]!="processed":raise ValueError("Complete radar cohort required")
        path=parent_root/row["artifact"]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row["artifact_sha256"]:raise ValueError("Radar array differs")
        with np.load(path,allow_pickle=False) as data:
            if str(data["crs"])!=grid["crs"] or data["transform"].tolist()!=grid["transform"]:raise ValueError("Radar grid differs")
            numeric=np.isfinite(data["power"]).all(axis=0)&(data["power"]>0).all(axis=0)
        rows.append(dict(item_id=row["item_id"],sensitivity=[dict(threshold_degrees=t,**slope_screen_summary(c,numeric))
                    for t,c in zip(plan["sensitivity_max_slope_degrees"],classes)]))
    result=dict(schema_version="lira-slope-proxy-1",plan=plan,source_radar_report_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),
        elevation_catalog_sha256=catalog_hash,elevation_item_id=item["id"],
        elevation_lineage={k:v for k,v in lineage.items() if k!="unsigned_href"},grid=grid,derivative_grid=derivative_grid,
        artifact_sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),observations=rows,
        implementation_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ["scripts/screen_lira_terrain.py","scripts/build_terrain_screen.py","vantage/terrain.py","vantage/gap_radar_pixels.py"]},
        radar_illumination_confirmed=False,usable_agricultural_evidence=False,
        limitation="Surface-slope sensitivity only; acquisition geometry, layover/shadow and processor agreement remain unverified")
    (root/"report.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(dict(report=str(root/"report.json"),observations=rows),indent=2))


if __name__=="__main__":main()
