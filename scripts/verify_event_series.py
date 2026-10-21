"""Recompute temporal evidence and anomaly maps from the saved public inputs."""

# ruff: noqa: E402
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_kween_case import scene_ndvi
from scripts.prepare_multispectral import validate_scene
from scripts.prepare_ml_dataset import cached_asset
from vantage.archive import fingerprint
from vantage.crop_context import crop_evidence
from vantage.event_series import timeline_summary, utc_time, validate_followup
from vantage.seasonal import slot_candidates
from vantage.historical import anomaly_map
from vantage.imagery import sha256_file
import numpy as np
import rasterio


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    base = ROOT / "outputs/africa/event-series"
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    report = json.loads((root / pointer["manifest"]).read_text())
    plan = report["plan"]
    require(
        fingerprint({k: v for k, v in report.items() if k != "run_id"})[:24]
        == report["run_id"],
        "Run identity differs",
    )
    require(fingerprint(plan) == report["plan_sha256"], "Plan identity differs")
    require(
        sha256_file(root / "frozen-plan.json") == report["frozen_plan_sha256"],
        "Frozen plan differs",
    )
    require(
        sha256_file(root / "sentinel-2.json") == report["catalog_sha256"],
        "Archived catalog differs",
    )
    require(
        json.loads((root / "frozen-plan.json").read_text())["plan"] == plan,
        "Frozen choices differ",
    )
    items = json.loads((root / "sentinel-2.json").read_text())["response"]["features"]
    candidates = sorted(
        slot_candidates(plan, items, plan["bbox"]),
        key=lambda i: (i["properties"]["datetime"], i["id"]),
    )
    require(
        [i["id"] for i in candidates]
        == [r["scene_id"] for r in report["observations"]],
        "Eligible catalog acquisitions were dropped or added",
    )
    for path, expected in report["code"].items():
        require(sha256_file(ROOT / path) == expected, "Science code differs")
    parent_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    parent_root = ROOT / "outputs/africa/kween" / parent_info["plan_sha256"][:20]
    parent_path = parent_root / (plan["parent_run_id"] + ".json")
    require(
        sha256_file(parent_path)
        == report["parent_manifest_sha256"]
        == parent_info["manifest_sha256"],
        "Parent manifest differs",
    )
    parent = json.loads(parent_path.read_text())
    validate_followup(plan, parent["plan"])
    context = report["context"]
    require(
        context == parent["contexts"][plan["area_id"]],
        "Historical crop context differs",
    )
    require(
        sha256_file(parent_root / context["crop_asset"])
        == context["crop_asset_sha256"],
        "Crop mask differs",
    )
    with rasterio.open(parent_root / context["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    wc_catalog = json.loads(
        (parent_root / (plan["area_id"] + "-worldcover.json")).read_text()
    )
    wc = next(
        i
        for i in wc_catalog["response"]["features"]
        if i["id"] == context["worldcover_id"]
    )
    grid = context["grid"]
    classes = cached_asset(
        wc,
        "map",
        rasterio.Affine(*grid["transform"][:6]),
        grid["width"],
        grid["height"],
        False,
    )
    refs = [
        r
        for r in parent["observations"]
        if r["area_id"] == plan["area_id"]
        and r["epoch"] == plan["comparison_epoch"]
        and r["year"] in parent["plan"]["reference_years"]
        and r["evidence"]
        and r["evidence"]["evidence_status"] == "sufficient_coverage_for_research"
    ]
    for ref in refs:
        validate_scene(ref["scene"], parent_root / "scenes")
    references = [scene_ndvi(ref["scene"], parent_root / "scenes")[2] for ref in refs]
    policy = parent["plan"]["quality_policy"]
    scenes = {s["artifact_id"]: s for s in report["scenes"]}
    maps = 0
    for row in report["observations"]:
        age = (
            utc_time(plan["as_of"]) - utc_time(row["acquired_at"])
        ).total_seconds() / 86400
        require(age == row["age_at_cutoff_days"], "Observation age differs")
        require(
            row["within_freshness_window"] == (age <= plan["max_observation_age_days"]),
            "Freshness flag differs",
        )
        if row["status"] != "processed":
            continue
        scene = scenes[row["artifact_id"]]
        validate_scene(scene, root / "scenes")
        require(
            scene["acquired_at"] == row["acquired_at"],
            "Observation date differs from raster date",
        )
        cube, common, ndvi = scene_ndvi(scene, root / "scenes")
        evidence = crop_evidence(
            cube,
            common,
            classes,
            policy["min_crop_usable_fraction"],
            policy["min_valid_pixels"],
        )
        require(evidence == row["observation"], "Crop measurements differ")
        require(
            row["coverage_qualified"]
            == (evidence["evidence_status"] == "sufficient_coverage_for_research"),
            "Coverage gate differs",
        )
        comparison = row["comparison"]
        if "asset" not in comparison:
            continue
        path = root / comparison["asset"]
        require(sha256_file(path) == comparison["sha256"], "Anomaly checksum differs")
        derived = anomaly_map(
            ndvi,
            references,
            crop,
            policy["min_reference_years"],
            policy["min_crop_usable_fraction"],
            policy["min_valid_pixels"],
            policy["ndvi_drop_trigger"],
        )
        expected = np.stack(
            [
                derived["delta"],
                np.where(crop, derived["reference_count"], np.nan),
                np.where(np.isfinite(derived["delta"]), derived["low_flag"], np.nan),
            ]
        ).astype("float32")
        with rasterio.open(path) as ds:
            require(
                np.array_equal(ds.read(), expected, equal_nan=True),
                "Anomaly pixels differ",
            )
            require(
                ds.crs.to_epsg() == 32636 and list(ds.transform) == grid["transform"],
                "Anomaly grid differs",
            )
        for key, value in derived["summary"].items():
            require(comparison[key] == value, "Anomaly summary differs")
        maps += 1
    require(
        timeline_summary(
            report["observations"], plan["as_of"], plan["max_observation_age_days"]
        )
        == report["summary"],
        "Timeline summary differs",
    )
    print(
        json.dumps(
            dict(
                run_id=report["run_id"],
                scene_cogs=len(scenes) * 3,
                reproduced_anomaly_cogs=maps,
                summary=report["summary"],
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
