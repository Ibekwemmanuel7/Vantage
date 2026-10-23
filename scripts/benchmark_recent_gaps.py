"""Evaluate causal persistence on the bounded recent numerical sequence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from vantage.gap_baseline import evaluate_persistence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence",type=Path,required=True)
    args=parser.parse_args()
    report=json.loads(args.sequence.read_text())
    results=[]
    for location in sorted({r["location_id"] for r in report["observations"]}):
        series=[]
        grid=None
        for row in report["observations"]:
            if row["location_id"]!=location or row["status"]!="processed":continue
            path=args.sequence.parent/row["metrics"]["artifact"]
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row["metrics"]["artifact_sha256"]:
                raise ValueError("Artifact checksum differs")
            with np.load(path,allow_pickle=False) as artifact:
                current=(str(artifact["crs"]),tuple(artifact["transform"]),artifact["ndvi"].shape)
                if grid is not None and grid!=current:raise ValueError("Grids differ")
                grid=current
                ndvi=artifact["ndvi"].copy()
                ndvi[~artifact["valid"]]=np.nan
                series.append(dict(acquired_at=row["acquired_at"],ndvi=ndvi))
        results.append(dict(location_id=location,dates=evaluate_persistence(series)))
    output=dict(schema_version="gap-persistence-benchmark-1",locations=results,
        source_sequence_sha256=hashlib.sha256(args.sequence.read_bytes()).hexdigest(),
        model_trained=False,operational_infill=False,
        limitation="No actual-cloud ground truth, spatial-season holdout or independent field validation")
    path=args.sequence.parent/"gap-baseline.json"
    path.write_text(json.dumps(output,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(output,indent=2))


if __name__=="__main__":main()
