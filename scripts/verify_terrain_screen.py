"""Recompute elevation derivatives, terrain proxy classes and all sensitivity maps."""

# ruff: noqa: E402
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_terrain_screen import elevation_clip
from scripts.verify_radar_series import manifest, require, check_cog
from vantage.imagery import sha256_file
from vantage.terrain import slope_proxy, classify_proxy, proxy_summary
from vantage.radar_values import numeric_evidence, paired_change
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject


def main():
    root, path, report = manifest(ROOT / "outputs/africa/terrain")
    plan = report["plan"]
    grid = report["context"]["grid"]
    dgrid = report["derivative_grid"]
    transform = rasterio.Affine(*grid["transform"][:6])
    dtransform = rasterio.Affine(*dgrid["transform"][:6])
    require(
        sha256_file(root / "elevation-catalog.json") == report["catalog_sha256"],
        "Elevation catalog differs",
    )
    items = json.loads((root / "elevation-catalog.json").read_text())["response"][
        "features"
    ]
    item = next(i for i in items if i["id"] == report["elevation_item_id"])
    require(
        sha256_file(root / report["elevation_lineage"]["cache"])
        == report["elevation_lineage"]["sha256"],
        "Native elevation clip differs",
    )
    elevation, support, lineage = elevation_clip(
        item, dgrid, root / report["elevation_lineage"]["cache"], False
    )
    require(
        lineage == report["elevation_lineage"], "Native elevation provenance differs"
    )
    elevation[support < plan["native_support_required"]] = np.nan
    slope, maximum = slope_proxy(
        elevation,
        plan["derivative_resolution_m"],
        plan["derivative_resolution_m"],
        plan["slope_neighborhood_pixels"],
    )
    check_cog(
        root,
        report["terrain_assets"]["derivatives"],
        np.stack([elevation, slope, maximum]),
        dtransform,
        [
            "DSM_elevation_m",
            "surface_slope_degrees",
            "maximum_3x3_surface_slope_degrees",
        ],
    )
    radar_maximum = np.full((grid["height"], grid["width"]), np.nan, dtype="float32")
    reproject(
        maximum,
        radar_maximum,
        src_transform=dtransform,
        src_crs=dgrid["crs"],
        dst_transform=transform,
        dst_crs=grid["crs"],
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.nearest,
    )
    check_cog(
        root,
        report["terrain_assets"]["radar_grid_slope"],
        radar_maximum,
        transform,
        ["maximum_3x3_surface_slope_degrees_nearest"],
    )
    classes = np.stack(
        [
            classify_proxy(radar_maximum, t)
            for t in plan["sensitivity_max_slope_degrees"]
        ]
    )
    check_cog(
        root,
        report["terrain_assets"]["proxy_classes"],
        classes,
        transform,
        [
            f"proxy_classes_at_{t}_degrees"
            for t in plan["sensitivity_max_slope_degrees"]
        ],
    )
    parent_info = json.loads(
        (ROOT / "docs/africa/KWEEN_RADAR_PIXELS_RUN.json").read_text()
    )
    parent_root = ROOT / "outputs/africa/radar-pixels" / parent_info["plan_sha256"][:20]
    parent_path = parent_root / (plan["parent_radar_run_id"] + ".json")
    require(
        sha256_file(parent_path)
        == report["parent_manifest_sha256"]
        == parent_info["manifest_sha256"],
        "Parent radar manifest differs",
    )
    parent = json.loads(parent_path.read_text())
    require(report["context"] == parent["context"], "Parent crop context differs")
    crop_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    crop_root = ROOT / "outputs/africa/kween" / crop_info["plan_sha256"][:20]
    require(
        sha256_file(crop_root / report["context"]["crop_asset"])
        == report["context"]["crop_asset_sha256"],
        "Crop mask differs",
    )
    with rasterio.open(crop_root / report["context"]["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    raw = {}
    rows = {r["item_id"]: r for r in parent["observations"]}
    for key, row in rows.items():
        path = parent_root / row["assets"]["linear"]["href"]
        require(
            sha256_file(path) == row["assets"]["linear"]["sha256"],
            "Raw radar COG differs",
        )
        with rasterio.open(path) as ds:
            raw[key] = ds.read()
    count = 3
    require(
        [r["threshold_degrees"] for r in report["sensitivity"]]
        == plan["sensitivity_max_slope_degrees"],
        "Fixed sensitivity thresholds differ",
    )
    for index, result in enumerate(report["sensitivity"]):
        require(
            result["proxy_summary"] == proxy_summary(classes[index], crop),
            "Proxy counts differ",
        )
        filtered = {
            key: np.where((classes[index] == 1)[None, ...], array, np.nan).astype(
                "float32"
            )
            for key, array in raw.items()
        }
        for observation in result["observations"]:
            evidence = numeric_evidence(
                filtered[observation["item_id"]],
                crop,
                plan["minimum_crop_retained_fraction"],
                plan["minimum_comparable_pixels"],
            )
            require(
                evidence == observation["evidence"], "Filtered radar evidence differs"
            )
        for change in result["changes"]:
            first, second = (
                rows[change["earlier_item_id"]],
                rows[change["later_item_id"]],
            )
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
                require(change[key] == value, "Filtered change summary differs")
            check_cog(
                root,
                change["asset"],
                derived["delta_db"],
                transform,
                ["VV_later_minus_earlier_db", "VH_later_minus_earlier_db"],
            )
            count += 1
    require(
        count == report["terrain_cogs"] + report["change_cogs"],
        "Terrain artifact count differs",
    )
    require(
        report["optical_status_unchanged"] == parent["optical_status_unchanged"],
        "Optical state differs",
    )
    require(
        not report["terrain_screen_verified"]
        and not report["radar_illumination_confirmed"]
        and not report["agronomic_review_eligible"],
        "Proxy must not certify viewing geometry or agriculture",
    )
    print(
        json.dumps(
            dict(
                run_id=report["run_id"],
                verified_cogs=count,
                terrain_risk_proxy_applied=True,
                radar_illumination_confirmed=False,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
