"""Inspect numerical radar/optical training references without declaring eligibility."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vantage.radar_pairing import causal_pairs
import numpy as np


def checked(path,digest):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError("Artifact checksum differs")
    with np.load(path,allow_pickle=False) as data:return {k:data[k].copy() for k in data.files}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radar-report",type=Path,required=True)
    args=parser.parse_args()
    radar=json.loads(args.radar_report.read_text())
    if not radar["observations"] or any(r["status"]!="processed" for r in radar["observations"]):
        raise ValueError("Complete numerical radar cohort required")
    path=ROOT/radar["plan"]["optical_sequence"]
    if hashlib.sha256(path.read_bytes()).hexdigest()!=radar["source_sequence_sha256"]:
        raise ValueError("Optical sequence differs")
    optical=[r for r in json.loads(path.read_text())["observations"] if r["status"]=="processed"]
    pairs=causal_pairs(optical,radar["observations"])
    grid=radar["grid"]
    masks={}
    for row in radar["observations"]:
        data=checked(args.radar_report.parent/row["artifact"],row["artifact_sha256"])
        if str(data["crs"])!=grid["crs"] or data["transform"].tolist()!=grid["transform"]:
            raise ValueError("Radar grid differs")
        masks[row["item_id"]]=np.isfinite(data["power"]).all(axis=0)&(data["power"]>0).all(axis=0)&(
            data["support"]>=radar["plan"]["minimum_native_valid_fraction"]).all(axis=0)
    for pair,row in zip(pairs,optical):
        data=checked(path.parent/row["metrics"]["artifact"],row["metrics"]["artifact_sha256"])
        if str(data["crs"])!=grid["crs"] or data["transform"].tolist()!=grid["transform"]:
            raise ValueError("Optical grid differs")
        if data["valid"].dtype.kind!="b" or not np.array_equal(data["valid"],np.isfinite(data["ndvi"])):
            raise ValueError("Optical quality mask differs")
        selected=pair["selected_radar_item_id"]
        mask=masks[selected] if selected else np.zeros(data["valid"].shape,dtype=bool)
        if mask.shape!=data["valid"].shape:raise ValueError("Array shape differs")
        pair.update(numeric_radar_pixels=int(mask.sum()),
            clear_optical_reference_pixels=int((mask&data["valid"]).sum()),
            missing_optical_pixels_with_numeric_radar=int((mask&~data["valid"]).sum()),
            terrain_screen_verified=False,independent_processor_status="not_evaluated")
    report=dict(schema_version="radar-training-pair-diagnostics-1",pairs=pairs,
        source_radar_report_sha256=hashlib.sha256(args.radar_report.read_bytes()).hexdigest(),
        source_optical_sequence_sha256=radar["source_sequence_sha256"],
        code_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                    ["scripts/summarize_radar_training_pairs.py","vantage/radar_pairing.py"]},
        usable_for_model_training=False,model_trained=False,
        historical_delivery_time_verified=False,
        optical_processing_note="Some archived 2023 acquisition IDs identify 2024 processing versions; not contemporaneous operational evidence",
        limitation="Whole-box numerical feasibility only; source track differs from Lira and requires its own terrain/geometry/processor checks")
    destination=args.radar_report.parent/"training-pair-diagnostics.json"
    destination.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(dict(report=str(destination),pairs=pairs),indent=2))


if __name__=="__main__":main()
