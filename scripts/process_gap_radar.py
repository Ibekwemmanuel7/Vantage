"""Bounded two-pass Lira RTC sample on the exact optical grid; no fusion."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from scripts.build_radar_series import native_clip
from vantage.archive import fingerprint
from vantage.gap_radar_pixels import validate_asset,whole_box_summary
from vantage.planetary import ContainerSigner
from vantage.radar_values import paired_change
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online",action="store_true")
    args=parser.parse_args()
    plan=json.loads((ROOT/"configs/lira_gap_radar_pixels.json").read_text())
    catalog_root=ROOT/"outputs/africa/gap-radar"/plan["catalog_directory"]
    catalog_path=catalog_root/"catalog.json"
    if hashlib.sha256(catalog_path.read_bytes()).hexdigest()!=plan["catalog_sha256"]:
        raise ValueError("Pinned radar catalog differs")
    report=json.loads((catalog_root/"report.json").read_text())
    if report["catalog_sha256"]!=plan["catalog_sha256"]:raise ValueError("Report catalog identity differs")
    sequence_path=ROOT/plan["optical_sequence"]
    if hashlib.sha256(sequence_path.read_bytes()).hexdigest()!=report["source_sequence_sha256"]:
        raise ValueError("Optical sequence differs")
    sequence=json.loads(sequence_path.read_text())
    reference=next(r for r in sequence["observations"] if r["status"]=="processed")
    optical_path=sequence_path.parent/reference["metrics"]["artifact"]
    if hashlib.sha256(optical_path.read_bytes()).hexdigest()!=reference["metrics"]["artifact_sha256"]:
        raise ValueError("Optical grid artifact differs")
    with np.load(optical_path,allow_pickle=False) as optical:
        grid=dict(crs=str(optical["crs"]),transform=optical["transform"].tolist(),
                  height=optical["ndvi"].shape[0],width=optical["ndvi"].shape[1])
    candidates=[r for r in report["candidates"] if r["track_id"]==plan["track_id"]]
    if not 1<=len(candidates)<=plan["max_passes"] or plan["max_passes"]>2:
        raise ValueError("Fixed two-pass budget required")
    root=ROOT/"outputs/africa/gap-radar-pixels"/fingerprint(plan)[:20]
    root.mkdir(parents=True,exist_ok=True)
    native=root/"native"
    native.mkdir(exist_ok=True)
    items={i["id"]:i for i in json.loads(catalog_path.read_text())["response"]["features"]}
    signer=ContainerSigner(source.SESSION)
    rows=[]
    powers=[]
    for candidate in sorted(candidates,key=lambda r:r["acquired_at"]):
        row=dict(candidate,status="failed")
        try:
            item=items[candidate["item_id"]]
            power,support,lineage=[],[],{}
            for band in ("vv","vh"):
                validate_asset(item["assets"][band])
                p,s,record=native_clip(item["assets"][band]["href"],grid,native,args.online,signer)
                power.append(p)
                support.append(s)
                lineage[band]={k:v for k,v in record.items() if k!="unsigned_href"}
            power=np.stack(power)
            support=np.stack(support)
            filtered=np.where(support>=plan["minimum_native_valid_fraction"],power,np.nan)
            destination=root/(fingerprint(candidate["item_id"])[:20]+".npz")
            if destination.exists():
                with np.load(destination,allow_pickle=False) as old:
                    if not np.array_equal(old["power"],filtered,equal_nan=True) or not np.array_equal(old["support"],support,equal_nan=True):
                        raise ValueError("Derived radar artifact differs")
            else:
                np.savez_compressed(destination,power=filtered,support=support,
                    transform=np.array(grid["transform"]),crs=grid["crs"])
            row.update(status="processed",summary=whole_box_summary(power,support,plan["minimum_native_valid_fraction"]),
                       native_lineage=lineage,artifact=destination.name,
                       artifact_sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
            powers.append((candidate,filtered))
        except Exception as error:
            row["error_type"]=type(error).__name__
        rows.append(row)
        print(json.dumps(row),flush=True)
    change=None
    if len(powers)==2:
        first,last=powers
        paired=paired_change(first[1],last[1],np.ones((grid["height"],grid["width"]),dtype=bool),first[0]["track_id"],last[0]["track_id"])
        change=paired["summary"]
        change["comparable_whole_box_fraction"]=change.pop("comparable_crop_fraction")
        change["spatial_scope"]="Whole box, not confirmed crop area"
    result=dict(schema_version="gap-radar-pixels-1",plan=plan,grid=grid,observations=rows,same_track_change=change,
                processed_at=datetime.now(timezone.utc).isoformat(),
                source_catalog_sha256=plan["catalog_sha256"],
                source_sequence_sha256=report["source_sequence_sha256"],
                optical_grid_artifact_sha256=reference["metrics"]["artifact_sha256"],
                code_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                             ["scripts/process_gap_radar.py","scripts/build_radar_series.py","vantage/gap_radar_pixels.py","vantage/radar_values.py"]},
                units="Provider RTC gamma0 linear intensity; 10*log10 after linear-domain averaging",
                radar_terrain_screen_verified=False,usable_agricultural_evidence=False,optical_values_imputed=False)
    path=root/"report.json"
    path.write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    print(f"Report: {path}")
    if any(r["status"]!="processed" for r in rows):sys.exit(1)


if __name__=="__main__":main()
