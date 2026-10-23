"""Prepare a frozen research split manifest from verified numerical sequences."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from vantage.gap_dataset import split_inventory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence",required=True,type=Path,nargs="+")
    parser.add_argument("--plan",type=Path,default=ROOT/"configs/gap_benchmark_split.json")
    parser.add_argument("--out",type=Path,default=ROOT/"outputs/ml/cloud-gaps")
    args=parser.parse_args()
    scenes=[]
    for sequence in args.sequence:
        report=json.loads(sequence.read_text())
        if report["schema_version"]!="recent-pixels-1":raise ValueError("Unsupported sequence schema")
        for row in report["observations"]:
            if row["status"]!="processed":continue
            path=sequence.parent/row["metrics"]["artifact"]
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            if digest!=row["metrics"]["artifact_sha256"]:raise ValueError("Artifact checksum differs")
            with np.load(path,allow_pickle=False) as artifact:
                valid=artifact["valid"]
                ndvi=artifact["ndvi"]
                if valid.shape!=ndvi.shape or int(valid.sum())!=row["metrics"]["valid_pixels"]:
                    raise ValueError("Mask counts differ")
                if not np.array_equal(valid,np.isfinite(ndvi)):raise ValueError("Mask and NDVI disagree")
            scenes.append(dict(location_id=row["location_id"],scene_id=row["scene_id"],
                acquired_at=row["acquired_at"],artifact_sha256=digest,
                valid_pixels=row["metrics"]["valid_pixels"],
                source_sequence_sha256=hashlib.sha256(sequence.read_bytes()).hexdigest()))
    manifest=split_inventory(json.loads(args.plan.read_text()),scenes)
    directory=args.out/manifest["manifest_id"][:20]
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/"manifest.json"
    text=json.dumps(manifest,indent=2,allow_nan=False)
    if target.exists() and target.read_text(encoding="utf-8")!=text:raise ValueError("Frozen manifest differs")
    target.write_text(text,encoding="utf-8")
    print(json.dumps(dict(manifest=str(target),training_data_gate_passed=manifest["training_data_gate_passed"],
                         split_counts={k:len(v) for k,v in manifest["splits"].items()},blockers=manifest["blockers"]),indent=2))


if __name__=="__main__":main()
