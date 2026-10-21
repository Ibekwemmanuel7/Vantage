"""Verify SAFE identities/checksums and reproduce local viewing geometry artifacts."""

# ruff: noqa: E402
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.acquire_viewing_annotations import product_references
from scripts.build_viewing_geometry import (
    calculate,
    grid_geometry,
    radar_grid,
    geometry_summary,
    ANGLE_BANDS,
)
from scripts.verify_radar_series import manifest, require, check_cog
from vantage.imagery import sha256_file
from vantage.radar_values import numeric_evidence, paired_change
import numpy as np
import rasterio


def main():
    root, path, report = manifest(ROOT / "outputs/africa/viewing")
    inputs_path = root / "inputs.json"
    inputs = json.loads(inputs_path.read_text())
    plan = report["plan"]
    require(
        sha256_file(inputs_path) == report["inputs_sha256"],
        "Annotation input manifest differs",
    )
    require(inputs["plan"] == plan, "Annotation choices differ")
    require(
        inputs["code_sha256"]
        == sha256_file(ROOT / "scripts/acquire_viewing_annotations.py"),
        "Acquisition code differs",
    )
    catalog_info = json.loads((ROOT / "docs/africa/KWEEN_RADAR_RUN.json").read_text())
    catalog_root = ROOT / "outputs/africa/radar" / catalog_info["plan_sha256"][:20]
    require(
        sha256_file(catalog_root / "radar-catalog.json")
        == inputs["source_catalog_sha256"],
        "Original RTC catalog differs",
    )
    terrain_info = json.loads((ROOT / "docs/africa/KWEEN_TERRAIN_RUN.json").read_text())
    terrain_root = ROOT / "outputs/africa/terrain" / terrain_info["plan_sha256"][:20]
    terrain_path = terrain_root / (plan["parent_terrain_run_id"] + ".json")
    require(
        sha256_file(terrain_path)
        == report["terrain_manifest_sha256"]
        == terrain_info["manifest_sha256"],
        "Terrain manifest differs",
    )
    terrain = json.loads(terrain_path.read_text())
    grid = terrain["context"]["grid"]
    dgrid = report["derivative_grid"]
    require(
        dgrid == terrain["derivative_grid"] and report["context"] == terrain["context"],
        "Geometry grids/context differ",
    )
    elevation_path = terrain_root / terrain["terrain_assets"]["derivatives"]["href"]
    require(
        sha256_file(elevation_path)
        == terrain["terrain_assets"]["derivatives"]["sha256"],
        "DSM raster differs",
    )
    with rasterio.open(elevation_path) as ds:
        elevation = ds.read(1)
    radar_info = json.loads(
        (ROOT / "docs/africa/KWEEN_RADAR_PIXELS_RUN.json").read_text()
    )
    radar_root = ROOT / "outputs/africa/radar-pixels" / radar_info["plan_sha256"][:20]
    radar_path = radar_root / (plan["parent_radar_run_id"] + ".json")
    require(
        sha256_file(radar_path)
        == report["radar_manifest_sha256"]
        == radar_info["manifest_sha256"],
        "Radar manifest differs",
    )
    radar = json.loads(radar_path.read_text())
    by_id = {r["item_id"]: r for r in radar["observations"]}
    require(
        {r["item_id"] for r in report["observations"]} == set(by_id),
        "Radar cohort differs",
    )
    crop_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    crop_root = ROOT / "outputs/africa/kween" / crop_info["plan_sha256"][:20]
    crop_path = crop_root / report["context"]["crop_asset"]
    require(
        sha256_file(crop_path) == report["context"]["crop_asset_sha256"],
        "Original crop mask differs",
    )
    with rasterio.open(crop_path) as ds:
        crop = ds.read(1).astype(bool)
    basis = grid_geometry(dgrid)
    native_transform = rasterio.Affine(*dgrid["transform"][:6])
    transform = rasterio.Affine(*grid["transform"][:6])
    filtered = {}
    count = 0
    observed = {r["item_id"]: r for r in report["observations"]}
    for record in inputs["annotations"]:
        row = observed[record["item_id"]]
        for name, key in [
            ("source_item", "source_item_sha256"),
            ("manifest", "manifest_sha256"),
            ("annotation", "annotation_sha256"),
        ]:
            require(
                sha256_file(root / record[name]) == record[key],
                "Archived product metadata differs",
            )
        references = product_references(
            (root / record["manifest"]).read_text(), record["manifest_unsigned_href"]
        )
        require(
            record["product_reference"] in references, "SAFE product reference differs"
        )
        raw = (root / record["annotation"]).read_bytes()
        reference = record["product_reference"]
        require(
            len(raw) == reference["size"]
            and hashlib.md5(raw).hexdigest() == reference["md5"],
            "SAFE annotation byte size/MD5 differs",
        )
        result, diagnostic = calculate(
            raw.decode(), record, elevation, dgrid, basis, plan
        )
        require(
            diagnostic == row["annotation_check"],
            "Orbit/annotation angle consistency differs",
        )
        angles, classes = radar_grid(result, dgrid, grid)
        native_angles = np.stack(
            [
                result[k]
                for k in ("nominal_incidence", "local_incidence", "toward_sensor_slope")
            ]
        )
        check_cog(
            root,
            row["assets"]["native_angles"],
            native_angles,
            native_transform,
            ANGLE_BANDS,
        )
        check_cog(
            root,
            row["assets"]["native_classes"],
            result["classes"],
            native_transform,
            ["local_geometry_risk_classes"],
        )
        check_cog(root, row["assets"]["radar_angles"], angles, transform, ANGLE_BANDS)
        check_cog(
            root,
            row["assets"]["radar_classes"],
            classes,
            transform,
            ["local_geometry_risk_classes"],
        )
        require(
            geometry_summary(classes, angles, crop) == row["geometry_summary"],
            "Local geometry counts differ",
        )
        original = by_id[record["item_id"]]
        power_path = radar_root / original["assets"]["linear"]["href"]
        require(
            sha256_file(power_path) == original["assets"]["linear"]["sha256"],
            "Original radar power differs",
        )
        with rasterio.open(power_path) as ds:
            power = ds.read()
        filtered[record["item_id"]] = np.where(
            (classes == 1)[None, ...], power, np.nan
        ).astype("float32")
        require(
            numeric_evidence(
                filtered[record["item_id"]],
                crop,
                plan["minimum_crop_retained_fraction"],
                plan["minimum_comparable_pixels"],
            )
            == row["numeric_evidence"],
            "Local-filter numerical evidence differs",
        )
        count += 4
    for change in report["changes"]:
        first, second = by_id[change["earlier_item_id"]], by_id[change["later_item_id"]]
        derived = paired_change(
            filtered[first["item_id"]],
            filtered[second["item_id"]],
            crop,
            first["track_id"],
            second["track_id"],
            plan["minimum_crop_retained_fraction"],
            plan["minimum_comparable_pixels"],
        )
        for key, value in derived["summary"].items():
            require(change[key] == value, "Local-filter change summary differs")
        check_cog(
            root,
            change["asset"],
            derived["delta_db"],
            transform,
            ["VV_later_minus_earlier_db", "VH_later_minus_earlier_db"],
        )
        count += 1
    require(
        count == report["geometry_cogs"] + report["change_cogs"],
        "Geometry artifact count differs",
    )
    require(
        not report["nonlocal_shadow_checked"]
        and not report["terrain_screen_verified"]
        and not report["agronomic_review_eligible"],
        "Local checks cannot certify complete illumination or agriculture",
    )
    require(
        report["optical_status_unchanged"] == radar["optical_status_unchanged"],
        "Optical status differs",
    )
    print(
        json.dumps(
            dict(
                run_id=report["run_id"],
                verified_annotations=len(inputs["annotations"]),
                verified_cogs=count,
                nonlocal_shadow_checked=False,
                radar_illumination_confirmed=False,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
