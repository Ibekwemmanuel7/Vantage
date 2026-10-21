"""Verify local case provenance/COGs and optionally publish a compact run record."""
# ruff: noqa: E402

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_kween_case import scene_ndvi
from scripts.prepare_multispectral import validate_scene
from scripts import build_uganda_demo as source
from vantage.archive import fingerprint
from vantage.historical import anomaly_map
from vantage.imagery import atomic_json, sha256_file
import numpy as np
import rasterio


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    base = ROOT / "outputs/africa/kween"
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    path = root / pointer["manifest"]
    report = json.loads(path.read_text())
    unsigned = {k: v for k, v in report.items() if k != "run_id"}
    require(fingerprint(unsigned)[:24] == report["run_id"], "Run identity differs")
    require(fingerprint(report["plan"]) == report["plan_sha256"], "Plan differs")
    for name, expected in report["code"].items():
        require(sha256_file(ROOT / name) == expected, "Science code differs: " + name)
    for name, key in [
        ("frozen-plan.json", "frozen_plan_sha256"),
        ("ngenge-osm.json", "geography_sha256"),
    ]:
        require(sha256_file(root / name) == report[key], "Archived provenance differs")
    for name, expected in report["catalog_hashes"].items():
        require(sha256_file(root / (name + ".json")) == expected, "Catalog differs")
    for rain in report["rain_sources"]:
        cache = source.CACHE / (
            hashlib.sha256(rain["url"].encode()).hexdigest() + ".bin"
        )
        require(sha256_file(cache) == rain["sha256"], "Rainfall source differs")
    scenes = []
    for record in report["observations"]:
        if record["scene"]:
            validate_scene(record["scene"], root / "scenes")
            scenes.append(record["scene"])
            if record["year"] == report["plan"]["target_year"]:
                require(
                    record["scene"]["acquired_at"]
                    <= report["plan"]["observation_cutoff"],
                    "Target after cutoff",
                )
    for context in report["contexts"].values():
        require(
            sha256_file(root / context["crop_asset"]) == context["crop_asset_sha256"],
            "Crop mask differs",
        )
    policy = report["plan"]["quality_policy"]
    maps = 0
    for comparison in report["comparisons"]:
        if "asset" not in comparison:
            continue
        asset = root / comparison["asset"]
        require(sha256_file(asset) == comparison["sha256"], "Anomaly map differs")
        context = report["contexts"][comparison["area_id"]]
        with rasterio.open(root / context["crop_asset"]) as ds:
            crop = ds.read(1).astype(bool)
        rows = [
            r
            for r in report["observations"]
            if r["area_id"] == comparison["area_id"]
            and r["epoch"] == comparison["epoch"]
        ]
        target = next(r for r in rows if r["year"] == report["plan"]["target_year"])
        refs = [r for r in rows if r["year"] in comparison["reference_years"]]
        derived = anomaly_map(
            scene_ndvi(target["scene"], root / "scenes")[2],
            [scene_ndvi(r["scene"], root / "scenes")[2] for r in refs],
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
        with rasterio.open(asset) as ds:
            require(
                np.array_equal(ds.read(), expected, equal_nan=True),
                "Derived map cannot be reproduced",
            )
            require(
                ds.crs.to_epsg() == 32636
                and list(ds.transform) == context["grid"]["transform"],
                "Map grid differs",
            )
        for key, value in derived["summary"].items():
            require(comparison[key] == value, "Derived summary differs: " + key)
        maps += 1
    summary = dict(
        schema_version="kween-run-1",
        run_id=report["run_id"],
        manifest_sha256=sha256_file(path),
        plan_sha256=report["plan_sha256"],
        frozen_plan_sha256=report["frozen_plan_sha256"],
        frozen_at=json.loads((root / "frozen-plan.json").read_text())["frozen_at"],
        source_url=report["plan"]["source_url"],
        geography_source=report["plan"]["geography_source"],
        requested_observations=len(report["observations"]),
        processed_observations=len(scenes),
        coverage_qualified_observations=sum(
            r["evidence"] is not None
            and r["evidence"]["evidence_status"] == "sufficient_coverage_for_research"
            for r in report["observations"]
        ),
        validated_scene_cogs=len(scenes) * 3,
        validated_anomaly_cogs=maps,
        available_comparisons=sum(
            c["status"] == "research_comparison_available"
            for c in report["comparisons"]
        ),
        comparisons=report["comparisons"],
        rainfall={k: v["summary"] for k, v in report["rainfall"].items()},
        observations=[
            dict(
                area_id=r["area_id"],
                year=r["year"],
                epoch=r["epoch"],
                status=r["status"],
                acquired_at=r["scene"]["acquired_at"] if r["scene"] else None,
                crop_usable_fraction=r["evidence"]["crop_usable_fraction"]
                if r["evidence"]
                else None,
            )
            for r in report["observations"]
        ],
        independent_field_labels=0,
        trained_model=False,
        causal_attribution=False,
        operational_replay=False,
        limitations=report["plan"]["limitations"],
    )
    if args.write_summary:
        atomic_json(ROOT / "docs/africa/KWEEN_RUN.json", summary)
    print(
        json.dumps(
            {
                k: v
                for k, v in summary.items()
                if k not in ("observations", "comparisons", "rainfall", "limitations")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
