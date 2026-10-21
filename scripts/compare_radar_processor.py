"""Prepare exact provider requests; compare independently exported rasters offline."""

# ruff: noqa: E402
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source  # noqa: F401
from scripts.build_visibility import pinned
from vantage.archive import fingerprint
from vantage.imagery import atomic_json, sha256_file
from vantage.radar_benchmark import compare, request_for, scene_identity
import numpy as np
import rasterio


def read_checked(root, asset):
    path = root / asset["href"]
    if sha256_file(path) != asset["sha256"]:
        raise ValueError("Parent raster checksum differs")
    with rasterio.open(path) as ds:
        return ds.read()


def read_export(directory, request, grid, product):
    """Exact local export contract; caller-selected directory never goes into Git."""
    submitted = directory / "request.json"
    if json.loads(submitted.read_text()) != request:
        raise ValueError("Submitted provider request differs from frozen request")
    metadata = directory / "userdata.json"
    identity = scene_identity(json.loads(metadata.read_text()), product)
    path = directory / "default.tif"
    with rasterio.open(path) as ds:
        if (
            ds.crs != rasterio.crs.CRS.from_string(grid["crs"])
            or ds.transform != rasterio.Affine(*grid["transform"][:6])
            or ds.count != 3
            or ds.width != grid["width"]
            or ds.height != grid["height"]
        ):
            raise ValueError(
                "Provider raster must exactly match requested grid and three-band order"
            )
        data = ds.read()
        if np.any((data[2] == 1) & ~np.all(ds.read_masks() > 0, axis=0)):
            raise ValueError("Provider raster masks conflict with dataMask")
    return data, dict(
        **identity,
        request_sha256=sha256_file(submitted),
        userdata_sha256=sha256_file(metadata),
        raster_sha256=sha256_file(path),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exports", type=Path, help="Local directory with 0/, 1/, 2/ provider exports"
    )
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    if args.exports is not None and not args.exports.is_dir():
        raise ValueError("Provider export directory does not exist")
    plan = json.loads(
        (ROOT / "configs/kween_2023_processor_benchmark.json").read_text()
    )
    sight_root, sight_path, sight = pinned("KWEEN_VISIBILITY", "visibility")
    view_root, view_path, view = pinned("KWEEN_VIEWING", "viewing")
    if (
        sight["run_id"] != plan["parent_visibility_run_id"]
        or view["run_id"] != plan["parent_viewing_run_id"]
        or sight["parent_manifest_sha256"] != sha256_file(view_path)
    ):
        raise ValueError("Comparison parent chain differs")
    root = ROOT / "outputs/africa/processor-benchmark" / fingerprint(plan)[:20]
    root.mkdir(parents=True, exist_ok=True)
    frozen = root / "frozen-plan.json"
    if not frozen.exists():
        atomic_json(
            frozen,
            dict(
                plan=plan,
                frozen_at=datetime.now(timezone.utc).isoformat(),
                scope="Fixed before any provider comparison outputs; Kween parent results already known",
            ),
        )
    if json.loads(frozen.read_text())["plan"] != plan:
        raise ValueError("Frozen comparison policy differs")
    inputs_path = view_root / "inputs.json"
    if sha256_file(inputs_path) != view["inputs_sha256"]:
        raise ValueError("Viewing inputs differ")
    inputs = json.loads(inputs_path.read_text())
    grid = view["context"]["grid"]
    original = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    crop_path = (
        ROOT
        / "outputs/africa/kween"
        / original["plan_sha256"][:20]
        / view["context"]["crop_asset"]
    )
    if sha256_file(crop_path) != view["context"]["crop_asset_sha256"]:
        raise ValueError("Historical crop mask differs")
    with rasterio.open(crop_path) as ds:
        crop = ds.read(1).astype(bool)
    by_view = {r["item_id"]: r for r in view["observations"]}
    by_sight = {r["item_id"]: r for r in sight["observations"]}
    if set(by_view) != set(by_sight) or {
        r["item_id"] for r in inputs["annotations"]
    } != set(by_view):
        raise ValueError("Parent acquisition cohorts differ")
    rows = []
    for index, record in enumerate(inputs["annotations"]):
        product = record["manifest_unsigned_href"].split("/")[-2]
        request = request_for(grid, product)
        request_path = root / f"{index}-request.json"
        if request_path.exists() and json.loads(request_path.read_text()) != request:
            raise ValueError("Prepared request differs")
        atomic_json(request_path, request)
        row = dict(
            index=index,
            item_id=record["item_id"],
            safe_product=product,
            acquired_at=record["acquired_at"],
            request_sha256=sha256_file(request_path),
            status="awaiting_provider_export",
            metrics=None,
        )
        export = None if args.exports is None else args.exports / str(index)
        if export is not None and export.exists():
            provider, lineage = read_export(export, request, grid, product)
            local = by_view[record["item_id"]]
            local_angles = read_checked(view_root, local["assets"]["radar_angles"])[1]
            local_classes = read_checked(view_root, local["assets"]["radar_classes"])[0]
            sight_classes = read_checked(
                sight_root, by_sight[record["item_id"]]["assets"]["radar_classes"]
            )[0]
            row.update(
                status="export_compared",
                provider_lineage=lineage,
                metrics=dict(
                    full_locality=compare(
                        local_angles,
                        local_classes,
                        sight_classes,
                        provider,
                        np.ones(crop.shape, dtype=bool),
                    ),
                    historical_crop_mask=compare(
                        local_angles, local_classes, sight_classes, provider, crop
                    ),
                ),
            )
        rows.append(row)
    evaluated = sum(r["status"] == "export_compared" for r in rows)
    compared = sum(
        r["metrics"] is not None
        and r["metrics"]["full_locality"]["status"] == "compared"
        for r in rows
    )
    latest = root.parent / "latest.json"
    if latest.exists():
        previous = json.loads(latest.read_text())
        old = json.loads(
            (root.parent / previous["directory"] / previous["manifest"]).read_text()
        )
        if old.get("exported_acquisitions_evaluated", 0) > evaluated:
            raise ValueError(
                "Refusing to replace a comparison with fewer provider exports"
            )
    report = dict(
        schema_version="processor-benchmark-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=sha256_file(frozen),
        parent_visibility_manifest_sha256=sha256_file(sight_path),
        parent_viewing_manifest_sha256=sha256_file(view_path),
        grid=grid,
        observations=rows,
        exported_acquisitions_compared=compared,
        exported_acquisitions_evaluated=evaluated,
        status="awaiting_provider_exports"
        if not evaluated
        else "no_comparable_provider_data"
        if not compared
        else "partial_comparison"
        if evaluated < len(rows)
        else "exploratory_comparison_complete",
        metrics_available=bool(compared),
        external_processor_live_tested=False,
        exact_provider_dem_realization_verified=False,
        independent_field_labels=0,
        agricultural_accuracy_measured=False,
        terrain_screen_verified=False,
        radar_illumination_confirmed=False,
        optical_status_unchanged=sight["optical_status_unchanged"],
        remaining_dependencies=[
            "Authenticated provider exports with actual scene inventory and service version",
            "Exact DEM realization/processing differences and difficult-terrain challenge cases",
            "Independent field outcomes, field boundaries and confirmed calendars",
        ],
        code={
            p: sha256_file(ROOT / p)
            for p in (
                "scripts/compare_radar_processor.py",
                "vantage/radar_benchmark.py",
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
        summary = {k: v for k, v in report.items() if k != "code"}
        summary["manifest_sha256"] = sha256_file(path)
        atomic_json(ROOT / "docs/africa/KWEEN_PROCESSOR_BENCHMARK_RUN.json", summary)
    print(
        report["status"],
        "-",
        compared,
        "provider acquisitions compared;",
        len(rows),
        "requests prepared",
    )
    print(root)


if __name__ == "__main__":
    main()
