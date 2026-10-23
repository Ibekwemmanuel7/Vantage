"""Fit a fixed small regression on frozen training data; compare separate cohorts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from vantage.gap_dataset import split_inventory
from vantage.gap_learning import causal_samples, fit_residual, score_samples


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--sequence",type=Path,nargs="+",required=True)
    args=p.parse_args()
    manifest=json.loads(args.manifest.read_text())
    identity={k:v for k,v in manifest.items() if k!="manifest_id"}
    if hashlib.sha256(json.dumps(identity,sort_keys=True,allow_nan=False).encode()).hexdigest()!=manifest["manifest_id"]:
        raise ValueError("Manifest content identity differs")
    verified=split_inventory(manifest["plan"],[s for rows in manifest["splits"].values() for s in rows])
    if not verified["training_data_gate_passed"]:raise ValueError("Training-data gate failed")
    lookup={}
    for sequence in args.sequence:
        digest=hashlib.sha256(sequence.read_bytes()).hexdigest()
        for row in json.loads(sequence.read_text())["observations"]:
            if row["status"]=="processed":lookup[(digest,row["scene_id"])]=(sequence.parent,row)
    samples={}
    isolated_samples={}
    clear_samples={}
    transferred_training_support=0
    for partition,scenes in manifest["splits"].items():
        groups={}
        grids={}
        for scene in scenes:
            directory,row=lookup[(scene["source_sequence_sha256"],scene["scene_id"])]
            path=directory/row["metrics"]["artifact"]
            if hashlib.sha256(path.read_bytes()).hexdigest()!=scene["artifact_sha256"]:
                raise ValueError("Artifact checksum differs")
            if row["location_id"]!=scene["location_id"] or row["acquired_at"]!=scene["acquired_at"]:
                raise ValueError("Scene assignment differs")
            with np.load(path,allow_pickle=False) as artifact:
                grid=(str(artifact["crs"]),tuple(artifact["transform"]),artifact["ndvi"].shape)
                location=scene["location_id"]
                if location in grids and grids[location]!=grid:raise ValueError("Grid differs")
                grids[location]=grid
                ndvi=artifact["ndvi"].copy()
                if int(artifact["valid"].sum())!=scene["valid_pixels"] or not np.array_equal(artifact["valid"],np.isfinite(ndvi)):
                    raise ValueError("Mask and NDVI differ from manifest")
                ndvi[~artifact["valid"]]=np.nan
                groups.setdefault(location,[]).append(dict(acquired_at=scene["acquired_at"],ndvi=ndvi))
        samples[partition]=[sample for series in groups.values()
                            for sample in causal_samples(series,transferred_masks=partition!="train")]
        isolated_samples[partition]=[sample for series in groups.values()
            for sample in causal_samples(series,isolated_gaps=True)]
        clear_samples[partition]=[sample for series in groups.values()
            for sample in causal_samples(series,transferred_masks=False)]
        if partition=="train":
            transferred_training_support=sum(len(sample["target"]) for series in groups.values()
                for sample in causal_samples(series,transferred_masks=True))
    model=fit_residual(samples["train"])
    scores={k:score_samples(v,model) for k,v in samples.items()}
    result=dict(schema_version="gap-protocol-comparison-1",model=model,
        implementation_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                               for name in ["scripts/train_gap_baseline.py","vantage/gap_learning.py"]},
        manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        numpy_version=np.__version__,results=scores,
        isolated_gap_results={k:score_samples(v,model) for k,v in isolated_samples.items()},
        clear_transition_diagnostics={k:score_samples(v,model) for k,v in clear_samples.items()},
        comparison_policy="Same fitted model, grids, masks and seven-day limit; only simulated-history availability differs",
        transferred_mask_training_pixel_date_pairs=transferred_training_support,
        supported_validation_dates=sum(r["predicted_pixels"]>0 for r in scores["validation"]["dates"]),
        promotion_status="blocked_no_supported_validation_predictions" if not scores["validation"]["predicted_pixel_date_pairs"] else "research_only_requires_independent_evaluation",
        training_protocol="Prior clear-pixel transitions, current targets enter history only after sample construction",
        evaluation_protocol="Transferred prior rejection masks, hidden targets never update history",
        operational_infill=False,untouched_final_test=False,
        limitations=["Small correlated whole-box cohorts", "Training on clear transitions differs from simulated evaluation gaps",
                     "Clear-transition training protocol retained across sequence expansion; transferred-mask support reported separately",
                     "Transferred quality masks, not actual-cloud truth",
                     "No uncertainty calibration, crop diagnosis or independent field validation",
                     "Development test already inspected; no final performance claim"])
    target=args.manifest.parent/"protocol-comparison.json"
    target.write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(dict(report=str(target),model=model,
        protocols={name:{k:{a:b for a,b in v.items() if a!="dates"} for k,v in result[name].items()}
                   for name in ["results","isolated_gap_results","clear_transition_diagnostics"]}),indent=2))


if __name__=="__main__":main()
