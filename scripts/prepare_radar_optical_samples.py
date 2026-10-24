"""Freeze quality-screened research tensors; independent processor gate stays closed."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vantage.archive import fingerprint
from vantage.event_series import utc_time
from vantage.fusion_samples import make_sample,FEATURES,UNITS
from vantage.radar_pairing import causal_pairs
import numpy as np


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path,expected=None):
    if expected and digest(path)!=expected:raise ValueError("Source report differs")
    return json.loads(path.read_text())


def arrays(path,expected):
    if digest(path)!=expected:raise ValueError("Source array differs")
    with np.load(path,allow_pickle=False) as data:return {k:data[k].copy() for k in data.files}


def load_quality(cohort,radar_path,radar):
    if cohort["quality_kind"]=="combined":
        path=ROOT/cohort["quality_report"]
        quality=read_json(path)
        if quality["source_radar_report_sha256"]!=digest(radar_path) or quality["grid"]!=radar["grid"]:
            raise ValueError("Combined quality parent/grid differs")
        slope=arrays(path.parent/"slope-proxy.npz",quality["slope_artifact_sha256"])["classes"][quality["plan"]["slope_thresholds"].index(10)]
        result={}
        for row in quality["observations"]:
            data=arrays(path.parent/row["artifact"],row["artifact_sha256"])
            result[row["item_id"]]=dict(local_angles=data["angles"],local_classes=data["local_classes"],
                visibility_classes=data["visibility_classes"],slope_classes=slope)
        return result,{cohort["quality_report"]:digest(path)}
    if cohort["quality_kind"]!="separate":raise ValueError("Unsupported quality report layout")
    vp=ROOT/cohort["viewing_report"]
    sp=ROOT/cohort["visibility_report"]
    tp=ROOT/cohort["terrain_report"]
    view,sight,terrain=[read_json(p) for p in [vp,sp,tp]]
    if (view["source_radar_report_sha256"]!=digest(radar_path) or sight["source_viewing_report_sha256"]!=digest(vp)
        or view["source_terrain_report_sha256"]!=digest(tp) or terrain["source_radar_report_sha256"]!=digest(radar_path)
        or sight["target_grid"]!=radar["grid"] or terrain["grid"]!=radar["grid"]):
        raise ValueError("Separate quality chain/grid differs")
    slope=arrays(tp.parent/"slope-proxy.npz",terrain["artifact_sha256"])["classes"][terrain["plan"]["sensitivity_max_slope_degrees"].index(10)]
    result={}
    for row in view["observations"]:
        local=arrays(vp.parent/row["artifact"],row["artifact_sha256"])
        ray=next(r for r in sight["observations"] if r["item_id"]==row["item_id"])
        visibility=arrays(sp.parent/ray["artifact"],ray["artifact_sha256"])
        result[row["item_id"]]=dict(local_angles=local["angles"],local_classes=local["classes"],
            visibility_classes=visibility["classes"],slope_classes=slope)
    return result,{name:digest(ROOT/name) for name in [cohort["viewing_report"],cohort["visibility_report"],cohort["terrain_report"]]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=ROOT/"configs/radar_optical_samples.json")
    args=parser.parse_args()
    plan=read_json(args.config)
    if (plan["primary_slope_threshold_degrees"],plan["maximum_radar_age_days"],plan["minimum_native_support"])!=(10,7,.8):
        raise ValueError("Fixed sample quality policy required")
    split=read_json(ROOT/plan["split_plan"])
    source_hashes={plan["split_plan"]:digest(ROOT/plan["split_plan"])}
    for cohort in plan["cohorts"]:
        for key in ["radar_report","quality_report","viewing_report","visibility_report","terrain_report"]:
            if key in cohort:source_hashes[cohort[key]]=digest(ROOT/cohort[key])
        radar=read_json(ROOT/cohort["radar_report"])
        source_hashes[radar["plan"]["optical_sequence"]]=digest(ROOT/radar["plan"]["optical_sequence"])
    code_hashes={p:digest(ROOT/p) for p in ["scripts/prepare_radar_optical_samples.py","vantage/fusion_samples.py","vantage/radar_pairing.py"]}
    dataset_id=fingerprint(dict(plan=plan,sources=source_hashes,code=code_hashes,numpy_version=np.__version__))[:24]
    root=ROOT/"outputs/ml/radar-optical"/dataset_id
    root.mkdir(parents=True,exist_ok=True)
    records=[]
    withheld=[]
    used_scenes={}
    used_locations={}
    for cohort in plan["cohorts"]:
        location,partition=cohort["location_id"],cohort["partition"]
        if partition not in ("train","validation"):raise ValueError("Only frozen research train/validation cohorts supported")
        if location not in split["splits"][partition]["locations"] or (location in used_locations and used_locations[location]!=partition):
            raise ValueError("Location split differs")
        used_locations[location]=partition
        rp=ROOT/cohort["radar_report"]
        radar=read_json(rp)
        if radar["plan"]["track_id"]!=cohort["track_id"] or any(r["status"]!="processed" for r in radar["observations"]):
            raise ValueError("Complete fixed-track radar cohort required")
        op=ROOT/radar["plan"]["optical_sequence"]
        optical=read_json(op,radar["source_sequence_sha256"])
        quality,quality_hashes=load_quality(cohort,rp,radar)
        if not set(r["item_id"] for r in radar["observations"])<=set(quality):raise ValueError("Quality acquisition identity missing")
        observations=[r for r in optical["observations"] if r["status"]=="processed"]
        for pair,row in zip(causal_pairs(observations,radar["observations"]),observations):
            if row["location_id"]!=location or utc_time(row["acquired_at"]).year not in split["splits"][partition]["years"]:
                raise ValueError("Optical location/year split differs")
            for identity in [row["scene_id"],pair["selected_radar_item_id"]]:
                if identity and identity in used_scenes and used_scenes[identity]!=partition:raise ValueError("Source scene leakage across partitions")
                if identity:used_scenes[identity]=partition
            if not pair["within_age_limit"]:
                withheld.append(dict(location_id=location,partition=partition,**pair))
                continue
            selected=next(r for r in radar["observations"] if r["item_id"]==pair["selected_radar_item_id"])
            if utc_time(selected["acquired_at"]).year not in split["splits"][partition]["years"]:
                raise ValueError("Radar source year differs from frozen partition")
            raw=arrays(rp.parent/selected["artifact"],selected["artifact_sha256"])
            target=arrays(op.parent/row["metrics"]["artifact"],row["metrics"]["artifact_sha256"])
            grid=radar["grid"]
            for data in [raw,target]:
                if str(data["crs"])!=grid["crs"] or data["transform"].tolist()!=grid["transform"]:raise ValueError("Sample grid differs")
            sample=make_sample(raw["power"],raw["support"],**quality[selected["item_id"]],
                ndvi=target["ndvi"],optical_valid=target["valid"],radar_age_days=pair["lag_days"])
            sample_id=fingerprint([location,row["scene_id"],selected["item_id"]])[:24]
            path=root/(sample_id+".npz")
            if path.exists():
                with np.load(path,allow_pickle=False) as old:
                    if any(not np.array_equal(old[k],v,equal_nan=True) for k,v in sample.items()):raise ValueError("Sample differs on replay")
            else:np.savez_compressed(path,**sample)
            records.append(dict(sample_id=sample_id,location_id=location,partition=partition,track_id=cohort["track_id"],
                optical_scene_id=row["scene_id"],optical_acquired_at=row["acquired_at"],
                radar_item_id=selected["item_id"],radar_acquired_at=selected["acquired_at"],lag_days=pair["lag_days"],grid=grid,
                feature_pixels=int(sample["feature_valid"].sum()),target_pixels=int(sample["target_valid"].sum()),
                missing_optical_candidate_pixels=int(sample["gap_candidate"].sum()),
                artifact=path.name,artifact_sha256=digest(path),usable_for_model_training=False))
            print(f"{partition} {row['acquired_at']}: {records[-1]['target_pixels']} observed references",flush=True)
    manifest=dict(schema_version="radar-optical-research-samples-1",dataset_id=dataset_id,plan=plan,
        source_hashes=source_hashes,code_hashes=code_hashes,numpy_version=np.__version__,features=FEATURES,units=UNITS,
        samples=records,withheld=withheld,training_eligible=False,model_trained=False,
        blockers=["independent_processor_exports_pending","untouched_final_test_missing","uncertainty_and_transfer_evaluation_pending"],
        limitation="Whole-box research tensors, not crop labels, measured optical values beneath clouds or certified radar illumination")
    destination=root/"manifest.json"
    text=json.dumps(manifest,indent=2,allow_nan=False)
    if destination.exists() and destination.read_text(encoding="utf-8")!=text:raise ValueError("Frozen manifest differs")
    destination.write_text(text,encoding="utf-8")
    print(json.dumps(dict(manifest=str(destination),sample_counts={p:sum(r["partition"]==p for r in records) for p in ["train","validation"]},
        withheld_dates=len(withheld),training_eligible=False),indent=2))


if __name__=="__main__":main()
