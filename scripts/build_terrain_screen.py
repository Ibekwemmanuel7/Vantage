"""Independent DSM slope-risk sensitivity for the pinned Uganda radar research slice."""

# ruff: noqa: E402
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source
from scripts.build_kween_case import archive_search
from scripts.build_radar_series import checked_cog
from vantage.archive import fingerprint
from vantage.imagery import atomic_json, sha256_file
from vantage.planetary import ContainerSigner
from vantage.radar_values import numeric_evidence, paired_change
from vantage.terrain import slope_proxy, classify_proxy, proxy_summary
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds, Window


def elevation_clip(item, grid, path, online):
    if not path.exists():
        if not online:
            raise FileNotFoundError("Native elevation clip not cached")
        transform = rasterio.Affine(*grid["transform"][:6])
        bounds = rasterio.transform.array_bounds(
            grid["height"], grid["width"], transform
        )
        signer = ContainerSigner(source.SESSION)
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            GDAL_HTTP_MAX_RETRY=2,
            GDAL_HTTP_TIMEOUT=60,
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
        ):
            with rasterio.open(signer(item["assets"]["data"]["href"])) as ds:
                if ds.count != 1 or ds.crs is None:
                    raise ValueError("Single-band georeferenced DSM required")
                window = from_bounds(
                    *transform_bounds(grid["crs"], ds.crs, *bounds),
                    transform=ds.transform,
                )
                left, top = (
                    int(np.floor(window.col_off)) - 2,
                    int(np.floor(window.row_off)) - 2,
                )
                right, bottom = (
                    int(np.ceil(window.col_off + window.width)) + 2,
                    int(np.ceil(window.row_off + window.height)) + 2,
                )
                if max(right - left, bottom - top) > 2000:
                    raise ValueError("Elevation window exceeds acquisition budget")
                window = Window(left, top, right - left, bottom - top)
                raw = (
                    ds.read(1, window=window, boundless=True, masked=True)
                    .astype("float32")
                    .filled(np.nan)
                )
                epsg = ds.crs.to_epsg()
                if epsg is None:
                    raise ValueError("Known elevation CRS required")
                np.savez_compressed(
                    path,
                    raw=raw,
                    transform=np.array(list(ds.window_transform(window))),
                    epsg=np.array(epsg),
                )
    with np.load(path, allow_pickle=False) as data:
        raw = data["raw"].copy()
        native_transform = rasterio.Affine(*data["transform"][:6])
        epsg = int(data["epsg"])
    elevation = np.full((grid["height"], grid["width"]), np.nan, dtype="float32")
    support = np.full_like(elevation, np.nan)
    args = dict(
        src_transform=native_transform,
        src_crs=f"EPSG:{epsg}",
        dst_transform=rasterio.Affine(*grid["transform"][:6]),
        dst_crs=grid["crs"],
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    reproject(raw, elevation, src_nodata=np.nan, **args)
    reproject(np.isfinite(raw).astype("float32"), support, **args)
    return (
        elevation,
        support,
        dict(
            cache=path.name,
            sha256=sha256_file(path),
            native_shape=list(raw.shape),
            native_epsg=epsg,
            unsigned_href=item["assets"]["data"]["href"],
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs/kween_2023_terrain.json"
    )
    parser.add_argument("--allow-downloads", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.config.read_text())
    if (
        plan["derivative_crs"] != "EPSG:32636"
        or plan["derivative_resolution_m"] != 30
        or plan["padding_m"] < 120
        or plan["padding_m"] > 300
        or plan["sensitivity_max_slope_degrees"] != [5, 10, 15]
        or plan["primary_max_slope_degrees"] != 10
    ):
        raise ValueError(
            "This fixed version supports the documented 30m derivative policy and thresholds"
        )
    parent_info = json.loads(
        (ROOT / "docs/africa/KWEEN_RADAR_PIXELS_RUN.json").read_text()
    )
    parent_root = ROOT / "outputs/africa/radar-pixels" / parent_info["plan_sha256"][:20]
    parent_path = parent_root / (plan["parent_radar_run_id"] + ".json")
    if (
        parent_info["run_id"] != plan["parent_radar_run_id"]
        or sha256_file(parent_path) != parent_info["manifest_sha256"]
    ):
        raise ValueError("Pinned radar run differs")
    parent = json.loads(parent_path.read_text())
    if (
        parent["plan"]["bbox"] != plan["bbox"]
        or parent["plan"]["area_id"] != plan["area_id"]
    ):
        raise ValueError("Terrain and radar areas must match")
    context = parent["context"]
    grid = context["grid"]
    transform = rasterio.Affine(*grid["transform"][:6])
    crop_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    crop_root = ROOT / "outputs/africa/kween" / crop_info["plan_sha256"][:20]
    if sha256_file(crop_root / context["crop_asset"]) != context["crop_asset_sha256"]:
        raise ValueError("Historical crop mask differs")
    with rasterio.open(crop_root / context["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    root = ROOT / "outputs/africa/terrain" / fingerprint(plan)[:20]
    root.mkdir(parents=True, exist_ok=True)
    frozen = root / "frozen-plan.json"
    if not frozen.exists():
        atomic_json(
            frozen,
            dict(
                plan=plan,
                frozen_at=datetime.now(timezone.utc).isoformat(),
                scope="Fixed before elevation inspection; exploratory slope proxy, not confirmed SAR terrain validity",
            ),
        )
    elif json.loads(frozen.read_text())["plan"] != plan:
        raise ValueError("Frozen terrain plan differs")
    west, south, east, north = rasterio.transform.array_bounds(
        grid["height"], grid["width"], transform
    )
    resolution = plan["derivative_resolution_m"]
    padding = plan["padding_m"]
    left = np.floor((west - padding) / resolution) * resolution
    top = np.ceil((north + padding) / resolution) * resolution
    width = int(np.ceil((east + padding - left) / resolution))
    height = int(np.ceil((top - south + padding) / resolution))
    derivative_transform = rasterio.Affine(resolution, 0, left, 0, -resolution, top)
    derivative_grid = dict(
        width=width,
        height=height,
        crs=plan["derivative_crs"],
        transform=list(derivative_transform),
    )
    query_bbox = list(
        transform_bounds(
            derivative_grid["crs"],
            "EPSG:4326",
            *rasterio.transform.array_bounds(height, width, derivative_transform),
        )
    )
    items, catalog_hash = archive_search(
        root,
        "elevation-catalog",
        plan["elevation_collection"],
        query_bbox,
        None,
        args.allow_downloads,
    )
    candidates = [
        i
        for i in items
        if "data" in i.get("assets", {})
        and i["bbox"][0] <= query_bbox[0]
        and i["bbox"][1] <= query_bbox[1]
        and i["bbox"][2] >= query_bbox[2]
        and i["bbox"][3] >= query_bbox[3]
    ]
    if not candidates:
        raise ValueError(
            "No single full-extent elevation tile; mosaicking is outside this bounded adapter"
        )
    item = sorted(candidates, key=lambda i: i["id"])[0]
    elevation, support, lineage = elevation_clip(
        item, derivative_grid, root / "native-elevation.npz", args.allow_downloads
    )
    elevation[support < plan["native_support_required"]] = np.nan
    slope, maximum = slope_proxy(
        elevation, resolution, resolution, plan["slope_neighborhood_pixels"]
    )
    radar_maximum = np.full(crop.shape, np.nan, dtype="float32")
    reproject(
        maximum,
        radar_maximum,
        src_transform=derivative_transform,
        src_crs=derivative_grid["crs"],
        dst_transform=transform,
        dst_crs=grid["crs"],
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.nearest,
    )
    classes = np.stack(
        [
            classify_proxy(radar_maximum, t)
            for t in plan["sensitivity_max_slope_degrees"]
        ]
    )
    terrain_assets = dict(
        derivatives=checked_cog(
            root / "surface-derivatives.tif",
            np.stack([elevation, slope, maximum]),
            derivative_transform,
            [
                "DSM_elevation_m",
                "surface_slope_degrees",
                "maximum_3x3_surface_slope_degrees",
            ],
        ),
        radar_grid_slope=checked_cog(
            root / "radar-grid-maximum-slope.tif",
            radar_maximum,
            transform,
            ["maximum_3x3_surface_slope_degrees_nearest"],
        ),
        proxy_classes=checked_cog(
            root / "slope-proxy-classes.tif",
            classes,
            transform,
            [
                f"proxy_classes_at_{t}_degrees"
                for t in plan["sensitivity_max_slope_degrees"]
            ],
        ),
    )
    powers = {}
    for row in parent["observations"]:
        if row["status"] != "processed":
            raise ValueError("Complete pinned radar cohort required")
        asset = parent_root / row["assets"]["linear"]["href"]
        if sha256_file(asset) != row["assets"]["linear"]["sha256"]:
            raise ValueError("Parent radar intensity differs")
        with rasterio.open(asset) as ds:
            powers[row["item_id"]] = ds.read()
    rows = {r["item_id"]: r for r in parent["observations"]}
    sensitivity = []
    for index, threshold in enumerate(plan["sensitivity_max_slope_degrees"]):
        proxy = classes[index]
        retained = proxy == 1
        filtered = {
            key: np.where(retained[None, ...], array, np.nan).astype("float32")
            for key, array in powers.items()
        }
        observations = [
            dict(
                item_id=key,
                evidence=numeric_evidence(
                    array,
                    crop,
                    plan["minimum_crop_retained_fraction"],
                    plan["minimum_comparable_pixels"],
                ),
            )
            for key, array in filtered.items()
        ]
        changes = []
        for pair_index, pair in enumerate(parent["changes"]):
            first, second = rows[pair["earlier_item_id"]], rows[pair["later_item_id"]]
            derived = paired_change(
                filtered[first["item_id"]],
                filtered[second["item_id"]],
                crop,
                first["track_id"],
                second["track_id"],
                plan["minimum_crop_retained_fraction"],
                plan["minimum_comparable_pixels"],
            )
            asset = checked_cog(
                root / f"{threshold}-degrees-pair-{pair_index}-change.tif",
                derived["delta_db"],
                transform,
                ["VV_later_minus_earlier_db", "VH_later_minus_earlier_db"],
            )
            changes.append(
                dict(
                    earlier_item_id=first["item_id"],
                    later_item_id=second["item_id"],
                    asset=asset,
                    **derived["summary"],
                )
            )
        sensitivity.append(
            dict(
                threshold_degrees=threshold,
                is_primary=threshold == plan["primary_max_slope_degrees"],
                proxy_summary=proxy_summary(proxy, crop),
                observations=observations,
                changes=changes,
            )
        )
    report = dict(
        schema_version="terrain-proxy-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=sha256_file(frozen),
        parent_manifest_sha256=sha256_file(parent_path),
        context=context,
        derivative_grid=derivative_grid,
        catalog_sha256=catalog_hash,
        elevation_item_id=item["id"],
        elevation_lineage=lineage,
        terrain_assets=terrain_assets,
        sensitivity=sensitivity,
        terrain_cogs=3,
        change_cogs=6,
        terrain_risk_proxy_applied=True,
        terrain_screen_verified=False,
        radar_illumination_confirmed=False,
        agronomic_review_eligible=False,
        independent_field_labels=0,
        trained_model=False,
        causal_attribution=False,
        optical_status_unchanged=parent["optical_status_unchanged"],
        software=dict(
            numpy=np.__version__,
            rasterio=rasterio.__version__,
            gdal=rasterio.__gdal_version__,
        ),
        code={
            p: sha256_file(ROOT / p)
            for p in (
                "scripts/build_terrain_screen.py",
                "vantage/terrain.py",
                "vantage/radar_values.py",
                "scripts/build_radar_series.py",
            )
        },
    )
    report["run_id"] = fingerprint(report)[:24]
    path = root / (report["run_id"] + ".json")
    atomic_json(path, report)
    atomic_json(
        root.parent / "latest.json", dict(directory=root.name, manifest=path.name)
    )
    if args.write_summary:
        summary = {
            k: v
            for k, v in report.items()
            if k not in ("context", "code", "terrain_assets", "elevation_lineage")
        }
        summary["manifest_sha256"] = sha256_file(path)
        atomic_json(ROOT / "docs/africa/KWEEN_TERRAIN_RUN.json", summary)
    print(
        json.dumps(
            dict(
                run_id=report["run_id"],
                elevation_item=item["id"],
                thresholds=[
                    dict(threshold=r["threshold_degrees"], **r["proxy_summary"])
                    for r in sensitivity
                ],
                verified_radar_illumination=False,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
