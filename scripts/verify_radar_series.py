"""Verify catalog cohorts, native clip hashes, resampled intensities and dB changes."""

# ruff: noqa: E402
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_radar_series import native_clip
from vantage.archive import fingerprint
from vantage.imagery import sha256_file
from vantage.radar import catalog_candidates, track_coverage
from vantage.radar_values import numeric_evidence, paired_change
import numpy as np
import rasterio


def require(condition, message):
    if not condition:
        raise ValueError(message)


def manifest(base):
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    path = root / pointer["manifest"]
    report = json.loads(path.read_text())
    require(
        fingerprint({k: v for k, v in report.items() if k != "run_id"})[:24]
        == report["run_id"],
        "Run identity differs",
    )
    require(
        fingerprint(report["plan"]) == report["plan_sha256"], "Plan identity differs"
    )
    require(
        sha256_file(root / "frozen-plan.json") == report["frozen_plan_sha256"],
        "Frozen plan hash differs",
    )
    require(
        json.loads((root / "frozen-plan.json").read_text())["plan"] == report["plan"],
        "Frozen choices differ",
    )
    for path_name, expected in report["code"].items():
        require(sha256_file(ROOT / path_name) == expected, "Science code differs")
    return root, path, report


def check_cog(root, asset, expected, transform, descriptions):
    path = root / asset["href"]
    require(sha256_file(path) == asset["sha256"], "COG checksum differs")
    with rasterio.open(path) as ds:
        require(
            ds.crs.to_epsg() == 32636 and ds.transform == transform, "COG grid differs"
        )
        require(list(ds.descriptions) == descriptions, "COG bands differ")
        require(
            ds.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") == "COG",
            "Cloud-optimized layout missing",
        )
        require(
            np.array_equal(
                ds.read(),
                expected if expected.ndim == 3 else expected[None, ...],
                equal_nan=True,
            ),
            "Recomputed COG values differ",
        )


def main():
    catalog_root, catalog_path, catalog = manifest(ROOT / "outputs/africa/radar")
    optical_path = ROOT / "docs/africa/KWEEN_TEMPORAL_RUN.json"
    optical = json.loads(optical_path.read_text())
    for name, key in [
        ("collection.json", "collection_sha256"),
        ("radar-catalog.json", "catalog_sha256"),
        ("anonymous-access.json", "access_probe_sha256"),
    ]:
        require(
            sha256_file(catalog_root / name) == catalog[key],
            "Archived radar source differs",
        )
    require(
        sha256_file(optical_path) == catalog["optical_summary_sha256"],
        "Optical summary differs",
    )
    items = json.loads((catalog_root / "radar-catalog.json").read_text())["response"][
        "features"
    ]
    candidates, excluded = catalog_candidates(items, catalog["plan"])
    require(
        candidates == catalog["candidates"] and excluded == catalog["exclusions"],
        "Catalog cohort differs",
    )
    require(
        track_coverage(
            candidates,
            optical["observations"],
            catalog["plan"]["as_of"],
            catalog["plan"]["max_observation_age_days"],
        )
        == catalog["tracks"],
        "Track timing differs",
    )
    root, path, report = manifest(ROOT / "outputs/africa/radar-pixels")
    require(
        sha256_file(catalog_path) == report["catalog_manifest_sha256"],
        "Pixel cohort catalog differs",
    )
    require(
        [r["item_id"] for r in report["observations"]]
        == [r["item_id"] for r in candidates],
        "Pixel cohort differs",
    )
    parent_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    parent_root = ROOT / "outputs/africa/kween" / parent_info["plan_sha256"][:20]
    context = report["context"]
    require(
        sha256_file(parent_root / context["crop_asset"])
        == context["crop_asset_sha256"],
        "Historical crop mask differs",
    )
    with rasterio.open(parent_root / context["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    grid = context["grid"]
    transform = rasterio.Affine(*grid["transform"][:6])
    plan = report["plan"]
    arrays = {}
    count = 0
    for row, candidate in zip(report["observations"], candidates):
        require(row["status"] == "processed", "Incomplete pixel run")
        require(
            row["track_id"] == candidate["track_id"]
            and row["acquired_at"] == candidate["acquired_at"],
            "Pixel orbit or acquisition differs",
        )
        power, support = [], []
        for band in ("vv", "vh"):
            record = row["recipe"]["lineage"][band]
            require(
                sha256_file(root / "native" / record["cache"]) == record["sha256"],
                "Native clip checksum differs",
            )
            p, s, lineage = native_clip(
                candidate["assets"][band], grid, root / "native", False, None
            )
            require(lineage == record, "Native clip lineage differs")
            power.append(p)
            support.append(s)
        support = np.stack(support)
        require(
            np.nanmin(support) >= 0 and np.nanmax(support) <= 1,
            "Invalid native support fraction",
        )
        power = np.where(
            support >= plan["minimum_native_valid_fraction"], np.stack(power), np.nan
        ).astype("float32")
        common = np.isfinite(power).all(axis=0).astype("uint8")
        require(
            fingerprint(row["recipe"])[:24] == row["artifact_id"],
            "Scene recipe identity differs",
        )
        check_cog(
            root,
            row["assets"]["linear"],
            power,
            transform,
            ["VV_gamma0_linear", "VH_gamma0_linear"],
        )
        check_cog(
            root,
            row["assets"]["native_support"],
            support,
            transform,
            ["VV_native_positive_fraction", "VH_native_positive_fraction"],
        )
        check_cog(
            root,
            row["assets"]["common_valid"],
            common,
            transform,
            ["both_polarizations_numeric_valid"],
        )
        require(
            numeric_evidence(
                power,
                crop,
                plan["minimum_crop_numeric_fraction"],
                plan["minimum_comparable_pixels"],
            )
            == row["evidence"],
            "Radar evidence differs",
        )
        arrays[row["item_id"]] = power
        count += 3
    by_id = {r["item_id"]: r for r in report["observations"]}
    for change in report["changes"]:
        first, second = by_id[change["earlier_item_id"]], by_id[change["later_item_id"]]
        derived = paired_change(
            arrays[first["item_id"]],
            arrays[second["item_id"]],
            crop,
            first["track_id"],
            second["track_id"],
            plan["minimum_crop_numeric_fraction"],
            plan["minimum_comparable_pixels"],
        )
        for key, value in derived["summary"].items():
            require(change[key] == value, "Radar change summary differs")
        check_cog(
            root,
            change["asset"],
            derived["delta_db"],
            transform,
            ["VV_later_minus_earlier_db", "VH_later_minus_earlier_db"],
        )
        count += 1
    require(
        report["optical_status_unchanged"] == optical["summary"]["status"],
        "Radar must not refresh optical evidence",
    )
    require(
        not report["terrain_screen_verified"]
        and not report["agronomic_review_eligible"],
        "Unverified agricultural eligibility",
    )
    require(count == report["radar_cogs"], "Artifact count differs")
    print(
        json.dumps(
            dict(
                catalog_run=catalog["run_id"],
                pixel_run=report["run_id"],
                verified_cogs=count,
                native_clips=len(candidates) * 2,
                usable_agricultural_radar_evidence=False,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
