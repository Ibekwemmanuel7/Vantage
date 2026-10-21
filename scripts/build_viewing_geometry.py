"""Acquisition-specific local viewing geometry; no complete shadow/illumination certification."""

# ruff: noqa: E402
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source  # noqa: F401 -- matching PROJ database
from scripts.build_radar_series import checked_cog
from vantage.archive import fingerprint
from vantage.imagery import atomic_json, sha256_file
from vantage.radar_values import numeric_evidence, paired_change
from vantage.viewing import (
    parse_annotation,
    interpolate_look,
    surface_normals,
    local_geometry,
    ecef,
    ellipsoid_up,
)
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform as warp_coordinates, reproject
import scipy

CLASS_NAMES = [
    "unknown",
    "locally_unflagged",
    "local_range_reversal_risk",
    "back_facing_facet_risk",
    "incidence_guard_risk",
]
ANGLE_BANDS = [
    "nominal_ellipsoid_incidence_degrees",
    "approx_local_incidence_degrees",
    "toward_sensor_surface_slope_degrees",
]


def grid_geometry(grid):
    transform = rasterio.Affine(*grid["transform"][:6])
    if (
        grid["crs"] != "EPSG:32636"
        or transform.b != 0
        or transform.d != 0
        or transform.a <= 0
        or transform.e >= 0
    ):
        raise ValueError("Unrotated metric Uganda study grid required")
    rows, cols = np.indices((grid["height"], grid["width"]))
    x = transform.c + (cols + 0.5) * transform.a
    y = transform.f + (rows + 0.5) * transform.e

    def geographic(px, py):
        longitude, latitude = warp_coordinates(
            grid["crs"], "EPSG:4326", px.ravel().tolist(), py.ravel().tolist()
        )
        return np.array(latitude).reshape(x.shape), np.array(longitude).reshape(x.shape)

    lat, lon = geographic(x, y)
    lat_x, lon_x = geographic(x + 1, y)
    lat_y, lon_y = geographic(x, y + 1)
    position = ecef(lat, lon, 0)
    return dict(
        query=np.stack([x, y], axis=-1),
        up=ellipsoid_up(lat, lon),
        grid_x_delta=ecef(lat_x, lon_x, 0) - position,
        grid_y_delta=ecef(lat_y, lon_y, 0) - position,
    )


def calculate(annotation, record, elevation, grid, basis, plan):
    parsed = parse_annotation(
        annotation, record, plan["annotation_incidence_tolerance_degrees"]
    )
    gx, gy = warp_coordinates(
        "EPSG:4326",
        grid["crs"],
        parsed["longitude"].tolist(),
        parsed["latitude"].tolist(),
    )
    look = interpolate_look(
        np.column_stack([gx, gy]), parsed["look_ecef"], basis["query"]
    )
    transform = rasterio.Affine(*grid["transform"][:6])
    normal, gradient = surface_normals(
        elevation,
        transform.a,
        -transform.e,
        basis["up"],
        basis["grid_x_delta"],
        basis["grid_y_delta"],
    )
    result = local_geometry(
        look,
        normal,
        basis["up"],
        gradient,
        plan["min_local_incidence_degrees"],
        plan["max_local_incidence_degrees"],
    )
    return result, parsed["summary"]


def radar_grid(result, source_grid, target_grid):
    source_transform = rasterio.Affine(*source_grid["transform"][:6])
    target_transform = rasterio.Affine(*target_grid["transform"][:6])
    shape = (target_grid["height"], target_grid["width"])
    bands = []
    for name in ("nominal_incidence", "local_incidence", "toward_sensor_slope"):
        array = np.full(shape, np.nan, dtype="float32")
        reproject(
            result[name],
            array,
            src_transform=source_transform,
            src_crs=source_grid["crs"],
            dst_transform=target_transform,
            dst_crs=target_grid["crs"],
            src_nodata=np.nan,
            dst_nodata=np.nan,
            resampling=Resampling.nearest,
        )
        bands.append(array)
    classes = np.zeros(shape, dtype="uint8")
    reproject(
        result["classes"],
        classes,
        src_transform=source_transform,
        src_crs=source_grid["crs"],
        dst_transform=target_transform,
        dst_crs=target_grid["crs"],
        resampling=Resampling.nearest,
    )
    return np.stack(bands), classes


def geometry_summary(classes, angles, crop):
    if (
        classes.shape != crop.shape
        or angles.shape != (3,) + crop.shape
        or crop.dtype.kind != "b"
        or not np.isin(classes, range(5)).all()
    ):
        raise ValueError("Aligned geometry classes, angles and crop mask required")
    total = int(crop.sum())
    counts = {
        name: int(((classes == i) & crop).sum()) for i, name in enumerate(CLASS_NAMES)
    }
    supported = crop & (classes != 0) & np.isfinite(angles).all(axis=0)
    return dict(
        historical_crop_pixels=total,
        counts=counts,
        locally_unflagged_crop_fraction=counts["locally_unflagged"] / total
        if total
        else None,
        nominal_incidence_range_degrees=[
            float(np.min(angles[0][supported])),
            float(np.max(angles[0][supported])),
        ]
        if supported.any()
        else None,
        approximate_local_incidence_range_degrees=[
            float(np.min(angles[1][supported])),
            float(np.max(angles[1][supported])),
        ]
        if supported.any()
        else None,
        local_geometry_checks_applied=True,
        nonlocal_shadow_checked=False,
        terrain_screen_verified=False,
        radar_illumination_confirmed=False,
        agronomic_review_eligible=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    plan = json.loads((ROOT / "configs/kween_2023_viewing.json").read_text())
    pointer = json.loads(
        (ROOT / "outputs/africa/viewing/latest-inputs.json").read_text()
    )
    root = ROOT / "outputs/africa/viewing" / pointer["directory"]
    inputs_path = root / pointer["manifest"]
    inputs = json.loads(inputs_path.read_text())
    if (
        inputs["plan"] != plan
        or inputs["plan_sha256"] != fingerprint(plan)
        or inputs["code_sha256"]
        != sha256_file(ROOT / "scripts/acquire_viewing_annotations.py")
    ):
        raise ValueError("Pinned annotation acquisition inputs differ")
    if sha256_file(root / "frozen-plan.json") != inputs["frozen_plan_sha256"]:
        raise ValueError("Frozen viewing plan differs")
    terrain_info = json.loads((ROOT / "docs/africa/KWEEN_TERRAIN_RUN.json").read_text())
    terrain_root = ROOT / "outputs/africa/terrain" / terrain_info["plan_sha256"][:20]
    terrain_path = terrain_root / (plan["parent_terrain_run_id"] + ".json")
    if (
        terrain_info["run_id"] != plan["parent_terrain_run_id"]
        or sha256_file(terrain_path) != terrain_info["manifest_sha256"]
    ):
        raise ValueError("Pinned terrain run differs")
    terrain = json.loads(terrain_path.read_text())
    grid = terrain["context"]["grid"]
    dgrid = terrain["derivative_grid"]
    asset = terrain_root / terrain["terrain_assets"]["derivatives"]["href"]
    if sha256_file(asset) != terrain["terrain_assets"]["derivatives"]["sha256"]:
        raise ValueError("Pinned DSM differs")
    with rasterio.open(asset) as ds:
        elevation = ds.read(1)
    radar_info = json.loads(
        (ROOT / "docs/africa/KWEEN_RADAR_PIXELS_RUN.json").read_text()
    )
    radar_root = ROOT / "outputs/africa/radar-pixels" / radar_info["plan_sha256"][:20]
    radar_path = radar_root / (plan["parent_radar_run_id"] + ".json")
    if sha256_file(radar_path) != radar_info["manifest_sha256"]:
        raise ValueError("Pinned radar input differs")
    radar = json.loads(radar_path.read_text())
    by_id = {r["item_id"]: r for r in radar["observations"]}
    if radar["context"] != terrain["context"]:
        raise ValueError("Radar and terrain grids/context must match exactly")
    if {r["item_id"] for r in inputs["annotations"]} != set(by_id) or len(
        inputs["annotations"]
    ) != len(by_id):
        raise ValueError("Annotation and radar acquisition cohorts must match exactly")
    for record in inputs["annotations"]:
        original = by_id[record["item_id"]]
        if (
            record["acquired_at"] != original["acquired_at"]
            or record["track_id"] != original["track_id"]
        ):
            raise ValueError("Annotation acquisition time or track differs")
    crop_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    crop_root = ROOT / "outputs/africa/kween" / crop_info["plan_sha256"][:20]
    context = terrain["context"]
    crop_path = crop_root / context["crop_asset"]
    if sha256_file(crop_path) != context["crop_asset_sha256"]:
        raise ValueError("Pinned historical crop mask differs")
    with rasterio.open(crop_path) as ds:
        crop = ds.read(1).astype(bool)
    basis = grid_geometry(dgrid)
    rows = []
    filtered = {}
    native_transform = rasterio.Affine(*dgrid["transform"][:6])
    transform = rasterio.Affine(*grid["transform"][:6])
    for index, record in enumerate(inputs["annotations"]):
        annotation_path = root / record["annotation"]
        if sha256_file(annotation_path) != record["annotation_sha256"]:
            raise ValueError("Annotation checksum differs")
        result, diagnostic = calculate(
            annotation_path.read_text(), record, elevation, dgrid, basis, plan
        )
        angles, classes = radar_grid(result, dgrid, grid)
        native_angles = np.stack(
            [
                result[k]
                for k in ("nominal_incidence", "local_incidence", "toward_sensor_slope")
            ]
        )
        assets = dict(
            native_angles=checked_cog(
                root / f"{index}-native-angles.tif",
                native_angles,
                native_transform,
                ANGLE_BANDS,
            ),
            native_classes=checked_cog(
                root / f"{index}-native-classes.tif",
                result["classes"],
                native_transform,
                ["local_geometry_risk_classes"],
            ),
            radar_angles=checked_cog(
                root / f"{index}-radar-angles.tif", angles, transform, ANGLE_BANDS
            ),
            radar_classes=checked_cog(
                root / f"{index}-radar-classes.tif",
                classes,
                transform,
                ["local_geometry_risk_classes"],
            ),
        )
        original = by_id[record["item_id"]]
        power_path = radar_root / original["assets"]["linear"]["href"]
        if sha256_file(power_path) != original["assets"]["linear"]["sha256"]:
            raise ValueError("Radar intensity differs")
        with rasterio.open(power_path) as ds:
            power = ds.read()
        filtered[record["item_id"]] = np.where(
            (classes == 1)[None, ...], power, np.nan
        ).astype("float32")
        evidence = numeric_evidence(
            filtered[record["item_id"]],
            crop,
            plan["minimum_crop_retained_fraction"],
            plan["minimum_comparable_pixels"],
        )
        rows.append(
            dict(
                item_id=record["item_id"],
                acquired_at=record["acquired_at"],
                track_id=record["track_id"],
                annotation_sha256=record["annotation_sha256"],
                annotation_check=diagnostic,
                assets=assets,
                geometry_summary=geometry_summary(classes, angles, crop),
                numeric_evidence=evidence,
            )
        )
        print(record["acquired_at"], rows[-1]["geometry_summary"]["counts"], flush=True)
    changes = []
    for index, pair in enumerate(radar["changes"]):
        first, second = by_id[pair["earlier_item_id"]], by_id[pair["later_item_id"]]
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
            root / f"local-geometry-pair-{index}-change.tif",
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
    report = dict(
        schema_version="local-viewing-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=inputs["frozen_plan_sha256"],
        inputs_sha256=sha256_file(inputs_path),
        terrain_manifest_sha256=sha256_file(terrain_path),
        radar_manifest_sha256=sha256_file(radar_path),
        context=context,
        derivative_grid=dgrid,
        observations=rows,
        changes=changes,
        geometry_cogs=len(rows) * 4,
        change_cogs=len(changes),
        local_geometry_checks_applied=True,
        nonlocal_shadow_checked=False,
        terrain_screen_verified=False,
        radar_illumination_confirmed=False,
        agronomic_review_eligible=False,
        independent_field_labels=0,
        trained_model=False,
        causal_attribution=False,
        optical_status_unchanged=radar["optical_status_unchanged"],
        software=dict(
            numpy=np.__version__,
            scipy=scipy.__version__,
            rasterio=rasterio.__version__,
            gdal=rasterio.__gdal_version__,
        ),
        code={
            p: sha256_file(ROOT / p)
            for p in (
                "scripts/build_viewing_geometry.py",
                "scripts/acquire_viewing_annotations.py",
                "vantage/viewing.py",
                "vantage/radar_values.py",
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
        summary = {k: v for k, v in report.items() if k not in ("context", "code")}
        summary["manifest_sha256"] = sha256_file(path)
        summary["observations"] = [
            {k: v for k, v in r.items() if k != "assets"} for r in rows
        ]
        atomic_json(ROOT / "docs/africa/KWEEN_VIEWING_RUN.json", summary)
    print(
        "Local geometry run",
        report["run_id"],
        "- no complete illumination certification",
        flush=True,
    )


if __name__ == "__main__":
    main()
