"""Prepare credential-free processor requests and causal research-pair diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from scripts.compare_radar_processor import read_export
from vantage.archive import fingerprint
from vantage.radar_benchmark import request_for,compare
from vantage.radar_pairing import causal_pairs
import numpy as np


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_npz(path,expected):
    if digest(path)!=expected:raise ValueError("Source array checksum differs")
    with np.load(path,allow_pickle=False) as data:return {k:data[k].copy() for k in data.files}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exports",type=Path,help="Optional private directory containing 0/ and 1/ exports")
    args=p.parse_args()
    if args.exports is not None and not args.exports.is_dir():raise ValueError("Export directory missing")
    visibility_root=ROOT/"outputs/africa/gap-visibility/727b09efd2cac9dbfae2"
    visibility_path=visibility_root/"report.json"
    visibility=json.loads(visibility_path.read_text())
    view_root=ROOT/"outputs/africa/gap-viewing"/visibility["plan"]["parent_viewing_directory"]
    view_path=view_root/"report.json"
    if digest(view_path)!=visibility["source_viewing_report_sha256"]:raise ValueError("Viewing parent differs")
    view=json.loads(view_path.read_text())
    radar_root=ROOT/"outputs/africa/gap-radar-pixels"/view["plan"]["parent_radar_directory"]
    radar_path=radar_root/"report.json"
    if digest(radar_path)!=view["source_radar_report_sha256"]:raise ValueError("Radar parent differs")
    radar=json.loads(radar_path.read_text())
    sequence_path=ROOT/radar["plan"]["optical_sequence"]
    if digest(sequence_path)!=radar["source_sequence_sha256"]:raise ValueError("Optical sequence differs")
    sequence=json.loads(sequence_path.read_text())
    grid=radar["grid"]
    if visibility["target_grid"]!=grid:raise ValueError("Visibility target grid differs")
    plan=dict(schema_version="lira-processor-comparison-plan-1",source_visibility_sha256=digest(visibility_path),
        provider="CDSE Sentinel Hub",endpoint="https://sh.dataspace.copernicus.eu/process/v1",
        export_bands=["localIncidenceAngle","shadowMask","dataMask"],max_passes=2,
        policy="Exact singleton SAFE scene and grid; descriptive differences only; no automatic eligibility")
    root=ROOT/"outputs/africa/lira-comparison"/fingerprint(plan)[:20]
    root.mkdir(parents=True,exist_ok=True)
    if len(view["observations"])!=2:raise ValueError("Two verified passes required")
    rows=[]
    screens={}
    for index,record in enumerate(view["observations"]):
        grd_path=view_root/record["source_grd"]
        if digest(grd_path)!=record["source_grd_sha256"]:raise ValueError("GRD source identity differs")
        product=json.loads(grd_path.read_text())["assets"]["safe-manifest"]["href"].split("/")[-2]
        request=request_for(grid,product)
        request_path=root/f"{index}-request.json"
        if request_path.exists() and json.loads(request_path.read_text())!=request:raise ValueError("Frozen request differs")
        request_path.write_text(json.dumps(request,indent=2),encoding="utf-8")
        local=checked_npz(view_root/record["artifact"],record["artifact_sha256"])
        sight=next(r for r in visibility["observations"] if r["item_id"]==record["item_id"])
        ray=checked_npz(visibility_root/sight["artifact"],sight["artifact_sha256"])
        raw=next(r for r in radar["observations"] if r["item_id"]==record["item_id"])
        values=checked_npz(radar_root/raw["artifact"],raw["artifact_sha256"])
        screens[record["item_id"]]=(local["classes"]==1)&(ray["classes"]==1)&np.isfinite(values["power"]).all(axis=0)&(values["power"]>0).all(axis=0)
        row=dict(index=index,item_id=record["item_id"],safe_product=product,
            request_sha256=digest(request_path),status="awaiting_provider_export",metrics=None)
        if args.exports is not None and (args.exports/str(index)).exists():
            provider,lineage=read_export(args.exports/str(index),request,grid,product)
            row.update(status="export_compared",provider_lineage=lineage,
                metrics=compare(local["angles"][1],local["classes"],ray["classes"],provider,np.ones(local["classes"].shape,dtype=bool)))
        rows.append(row)
    optical=[r for r in sequence["observations"] if r["status"]=="processed"]
    pairings=causal_pairs(optical,radar["observations"])
    for pair,row in zip(pairings,optical):
        target=checked_npz(sequence_path.parent/row["metrics"]["artifact"],row["metrics"]["artifact_sha256"])
        selected=pair["selected_radar_item_id"]
        screen=screens[selected] if selected else np.zeros(target["valid"].shape,dtype=bool)
        if screen.shape!=target["valid"].shape or str(target["crs"])!=grid["crs"] or target["transform"].tolist()!=grid["transform"]:
            raise ValueError("Optical/radar pairing grids differ")
        pair.update(numeric_locally_unflagged_bounded_clear_pixels=int(screen.sum()),
            clear_optical_target_pixels=int((screen&target["valid"]).sum()),
            missing_optical_pixels_with_research_radar=int((screen&~target["valid"]).sum()),
            independent_processor_status=("descriptive_comparison_available" if selected and any(
                r["item_id"]==selected and r["status"]=="export_compared" for r in rows) else "pending_external_exports"),
            source_delivery_availability="unknown")
    report=dict(schema_version="lira-comparison-and-pairing-1",plan=plan,requests=rows,pairs=pairings,
        exported_acquisitions_evaluated=sum(r["status"]=="export_compared" for r in rows),
        radar_assisted_model_trained=False,usable_agricultural_evidence=False,
        source_radar_report_sha256=digest(radar_path),source_viewing_report_sha256=digest(view_path),
        source_visibility_report_sha256=digest(visibility_path),source_optical_sequence_sha256=digest(sequence_path),
        code_sha256={name:digest(ROOT/name) for name in ["scripts/prepare_lira_radar_comparison.py","vantage/radar_pairing.py","vantage/radar_benchmark.py"]},
        limitation="Research pair counts only; no external processor results implied, source delivery latency and field validity unknown")
    output=root/"report.json"
    if output.exists() and json.loads(output.read_text())["exported_acquisitions_evaluated"]>report["exported_acquisitions_evaluated"]:
        raise ValueError("Refusing to replace a comparison with fewer provider exports")
    output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(dict(report=str(root/"report.json"),exports_evaluated=report["exported_acquisitions_evaluated"],pairs=pairings),indent=2))


if __name__=="__main__":main()
