"""Replayable bounded DSM sightlines for the pinned Kween viewing cohort."""

# ruff: noqa: E402
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source  # noqa: F401
from scripts.build_terrain_screen import elevation_clip
from scripts.build_radar_series import checked_cog
from scripts.build_viewing_geometry import grid_geometry
from vantage.archive import fingerprint
from vantage.imagery import atomic_json, sha256_file
from vantage.viewing import parse_annotation, interpolate_look, unit
from vantage.visibility import sightlines, CLASS_NAMES
import numpy as np
import rasterio
from rasterio.warp import transform as warp_coordinates, reproject
from rasterio.enums import Resampling
import scipy


def pinned(name, directory):
    summary = json.loads((ROOT / f"docs/africa/{name}_RUN.json").read_text())
    root = ROOT / f"outputs/africa/{directory}" / summary["plan_sha256"][:20]
    path = root / (summary["run_id"] + ".json")
    if sha256_file(path) != summary["manifest_sha256"]:
        raise ValueError("Parent manifest differs")
    report = json.loads(path.read_text())
    for path_name, expected in report["code"].items():
        if sha256_file(ROOT / path_name) != expected:
            raise ValueError("Parent science code differs")
    return root, path, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-downloads", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    plan = json.loads((ROOT / "configs/kween_2023_visibility.json").read_text())
    if (
        plan["distance_m"],
        plan["step_m"],
        plan["clearance_guard_m"],
        plan["padding_cells"],
    ) != (5000, 15, 5, 169):
        raise ValueError("Unsupported bounded sightline policy")
    view_root, view_path, view = pinned("KWEEN_VIEWING", "viewing")
    terrain_root, terrain_path, terrain = pinned("KWEEN_TERRAIN", "terrain")
    if view["run_id"] != plan["parent_viewing_run_id"] or view[
        "terrain_manifest_sha256"
    ] != sha256_file(terrain_path):
        raise ValueError("Pinned parent chain differs")
    root = ROOT / "outputs/africa/visibility" / fingerprint(plan)[:20]
    root.mkdir(parents=True, exist_ok=True)
    frozen = root / "frozen-plan.json"
    if not frozen.exists():
        atomic_json(
            frozen,
            dict(
                plan=plan,
                frozen_at=datetime.now(timezone.utc).isoformat(),
                scope="Exploratory bounded approximation fixed before expanded elevation inspection",
            ),
        )
    if json.loads(frozen.read_text())["plan"] != plan:
        raise ValueError("Frozen policy differs")
    grid = view["derivative_grid"]
    transform = rasterio.Affine(*grid["transform"][:6])
    padding = plan["padding_cells"]
    expanded = dict(
        grid,
        width=grid["width"] + 2 * padding,
        height=grid["height"] + 2 * padding,
        transform=list(transform * rasterio.Affine.translation(-padding, -padding)),
    )
    # Reuse the pinned source tile identity; boundless reads preserve unsupported areas.
    catalog = json.loads((terrain_root / "elevation-catalog.json").read_text())
    if (
        sha256_file(terrain_root / "elevation-catalog.json")
        != terrain["catalog_sha256"]
    ):
        raise ValueError("Elevation source catalog differs")
    items = catalog["response"]["features"]
    tile_id = terrain["elevation_item_id"]
    item = next(i for i in items if i["id"] == tile_id)
    elevation, support, lineage = elevation_clip(
        item, expanded, root / "native-elevation.npz", args.allow_downloads
    )
    elevation[(support < 0.999) | ~np.isfinite(support)] = np.nan
    assets = dict(
        elevation=checked_cog(
            root / "expanded-dsm.tif",
            elevation,
            rasterio.Affine(*expanded["transform"][:6]),
            ["DSM_elevation_m"],
        )
    )
    basis = grid_geometry(grid)
    up = basis["up"]
    xaxis = (
        basis["grid_x_delta"]
        - up * np.sum(basis["grid_x_delta"] * up, axis=-1)[..., None]
    )
    yaxis = (
        basis["grid_y_delta"]
        - up * np.sum(basis["grid_y_delta"] * up, axis=-1)[..., None]
    )
    xscale, yscale = np.linalg.norm(xaxis, axis=-1), np.linalg.norm(yaxis, axis=-1)
    inputs_path = view_root / "inputs.json"
    if sha256_file(inputs_path) != view["inputs_sha256"]:
        raise ValueError("Viewing inputs differ")
    inputs = json.loads(inputs_path.read_text())
    crop_summary = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    context = view["context"]
    crop_path = (
        ROOT
        / "outputs/africa/kween"
        / crop_summary["plan_sha256"][:20]
        / context["crop_asset"]
    )
    if sha256_file(crop_path) != context["crop_asset_sha256"]:
        raise ValueError("Historical crop mask differs")
    with rasterio.open(crop_path) as ds:
        crop = ds.read(1).astype(bool)
    target = context["grid"]
    target_transform = rasterio.Affine(*target["transform"][:6])
    rows, cols = np.indices((grid["height"], grid["width"]))
    observations = []
    for index, record in enumerate(inputs["annotations"]):
        annotation = view_root / record["annotation"]
        if sha256_file(annotation) != record["annotation_sha256"]:
            raise ValueError("Annotation differs")
        parsed = parse_annotation(
            annotation.read_text(),
            record,
            view["plan"]["annotation_incidence_tolerance_degrees"],
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
        lx = np.sum(look * unit(xaxis), axis=-1)
        ly = np.sum(look * unit(yaxis), axis=-1)
        horizontal = np.hypot(lx, ly)
        result = sightlines(
            elevation,
            rows + padding,
            cols + padding,
            lx / horizontal / xscale,
            ly / horizontal / yscale,
            np.sum(look * up, axis=-1) / horizontal,
            distance=plan["distance_m"],
            step=plan["step_m"],
            guard=plan["clearance_guard_m"],
        )
        bands = [
            "minimum_sampled_clearance_m",
            "distance_at_minimum_m",
            "supported_sample_fraction",
        ]
        metrics = np.stack(
            [
                result[k]
                for k in ("minimum_clearance", "minimum_distance", "supported_fraction")
            ]
        )
        row_assets = dict(
            metrics=checked_cog(
                root / f"{index}-metrics.tif", metrics, transform, bands
            ),
            classes=checked_cog(
                root / f"{index}-classes.tif",
                result["classes"],
                transform,
                ["bounded_sightline_class"],
            ),
        )
        mapped = np.zeros(crop.shape, dtype="uint8")
        reproject(
            result["classes"],
            mapped,
            src_transform=transform,
            src_crs=grid["crs"],
            dst_transform=target_transform,
            dst_crs=target["crs"],
            resampling=Resampling.nearest,
        )
        row_assets["radar_classes"] = checked_cog(
            root / f"{index}-radar-classes.tif",
            mapped,
            target_transform,
            ["bounded_sightline_class"],
        )
        counts = {
            name: int(np.sum(crop & (mapped == code)))
            for code, name in enumerate(CLASS_NAMES)
        }
        observations.append(
            dict(
                item_id=record["item_id"],
                acquired_at=record["acquired_at"],
                assets=row_assets,
                historical_crop_counts=counts,
                native_counts={
                    name: int(np.sum(result["classes"] == code))
                    for code, name in enumerate(CLASS_NAMES)
                },
                sample_count=result["samples"],
            )
        )
        print(record["acquired_at"], counts, flush=True)
    report = dict(
        schema_version="bounded-visibility-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=sha256_file(frozen),
        parent_manifest_sha256=sha256_file(view_path),
        elevation_catalog_sha256=sha256_file(terrain_root / "elevation-catalog.json"),
        elevation_lineage=lineage,
        expanded_grid=expanded,
        target_grid=grid,
        assets=assets,
        observations=observations,
        historical_crop_pixels=int(crop.sum()),
        bounded_sampled_sightlines_checked=True,
        terrain_screen_verified=False,
        radar_illumination_confirmed=False,
        agronomic_review_eligible=False,
        independent_field_labels=0,
        trained_model=False,
        optical_status_unchanged=view["optical_status_unchanged"],
        software=dict(
            numpy=np.__version__,
            scipy=scipy.__version__,
            rasterio=rasterio.__version__,
            gdal=rasterio.__gdal_version__,
        ),
        code={
            p: sha256_file(ROOT / p)
            for p in (
                "scripts/build_visibility.py",
                "vantage/visibility.py",
                "scripts/build_terrain_screen.py",
                "scripts/build_viewing_geometry.py",
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
        summary = {k: v for k, v in report.items() if k not in ("assets", "code")}
        summary["observations"] = [
            {k: v for k, v in row.items() if k != "assets"} for row in observations
        ]
        summary["manifest_sha256"] = sha256_file(path)
        atomic_json(ROOT / "docs/africa/KWEEN_VISIBILITY_RUN.json", summary)
    print("Bounded sightline run", report["run_id"], flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Network libraries can include signed URLs in exceptions.
        print("Sightline build failed:", type(error).__name__, file=sys.stderr)
        sys.exit(1)
