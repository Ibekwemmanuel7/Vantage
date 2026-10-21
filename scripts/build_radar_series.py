"""Bounded RTC linear-intensity cutouts and descriptive same-track changes."""

# ruff: noqa: E402
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source
from scripts.prepare_ml_dataset import write_cog
from vantage.archive import fingerprint
from vantage.event_series import utc_time
from vantage.imagery import atomic_json, sha256_file
from vantage.planetary import ContainerSigner
from vantage.radar_values import numeric_evidence, paired_change
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds, Window


def native_clip(href, grid, cache_root, online, signer):
    """Read a bounded native window, retaining no signed URL in provenance."""
    identity = fingerprint(dict(href=href, grid=grid, native_margin_pixels=2))[:24]
    path = cache_root / (identity + ".npz")
    if not path.exists():
        if not online:
            raise FileNotFoundError("Native radar clip not cached")
        transform = rasterio.Affine(*grid["transform"][:6])
        bounds = rasterio.transform.array_bounds(
            grid["height"], grid["width"], transform
        )
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            GDAL_HTTP_MAX_RETRY=2,
            GDAL_HTTP_TIMEOUT=60,
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
        ):
            with rasterio.open(signer(href)) as ds:
                if ds.count != 1 or ds.nodata != -32768 or ds.crs is None:
                    raise ValueError("Unexpected RTC raster contract")
                native_bounds = transform_bounds(grid["crs"], ds.crs, *bounds)
                window = from_bounds(*native_bounds, transform=ds.transform)
                left, top = (
                    int(np.floor(window.col_off)) - 2,
                    int(np.floor(window.row_off)) - 2,
                )
                right, bottom = (
                    int(np.ceil(window.col_off + window.width)) + 2,
                    int(np.ceil(window.row_off + window.height)) + 2,
                )
                if right - left > 2500 or bottom - top > 2500:
                    raise ValueError("Native radar read exceeds bounded window")
                window = Window(left, top, right - left, bottom - top)
                raw = (
                    ds.read(1, window=window, boundless=True, masked=True)
                    .astype("float32")
                    .filled(np.nan)
                )
                np.savez_compressed(
                    path,
                    raw=raw,
                    transform=np.array(list(ds.window_transform(window))),
                    epsg=np.array(ds.crs.to_epsg()),
                )
    with np.load(path, allow_pickle=False) as cache:
        raw = cache["raw"].copy()
        native_transform = rasterio.Affine(*cache["transform"][:6])
        epsg = int(cache["epsg"])
    valid = np.isfinite(raw) & (raw > 0)
    power = np.full((grid["height"], grid["width"]), np.nan, dtype="float32")
    support = np.full_like(power, np.nan)
    shared = dict(
        src_transform=native_transform,
        src_crs=f"EPSG:{epsg}",
        dst_transform=rasterio.Affine(*grid["transform"][:6]),
        dst_crs=grid["crs"],
        dst_nodata=np.nan,
        resampling=Resampling.average,
    )
    # Average positive linear intensity, never dB. Preserve partial native support separately.
    reproject(
        np.where(valid, raw, np.nan).astype("float32"),
        power,
        src_nodata=np.nan,
        **shared,
    )
    reproject(valid.astype("float32"), support, **shared)
    return (
        power,
        support,
        dict(
            cache=path.name,
            sha256=sha256_file(path),
            unsigned_href=href,
            native_shape=list(raw.shape),
            native_epsg=epsg,
        ),
    )


def checked_cog(path, arrays, transform, descriptions):
    if path.exists():
        with rasterio.open(path) as ds:
            if not np.array_equal(
                ds.read(),
                arrays if arrays.ndim == 3 else arrays[None, ...],
                equal_nan=True,
            ):
                raise ValueError("Existing radar COG differs")
    else:
        write_cog(path, arrays, transform, descriptions)
    with rasterio.open(path) as ds:
        if (
            ds.crs.to_epsg() != 32636
            or ds.transform != transform
            or list(ds.descriptions) != descriptions
        ):
            raise ValueError("Radar artifact grid or band descriptions differ")
    return dict(href=path.name, sha256=sha256_file(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs/kween_2023_radar_pixels.json"
    )
    parser.add_argument("--allow-downloads", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.config.read_text())
    info = json.loads((ROOT / "docs/africa/KWEEN_RADAR_RUN.json").read_text())
    catalog_root = ROOT / "outputs/africa/radar" / info["plan_sha256"][:20]
    catalog_path = catalog_root / (info["run_id"] + ".json")
    if sha256_file(catalog_path) != info["manifest_sha256"]:
        raise ValueError("Pinned catalog manifest differs")
    catalog = json.loads(catalog_path.read_text())
    optical = json.loads((ROOT / "docs/africa/KWEEN_TEMPORAL_RUN.json").read_text())
    if (
        plan["parent_optical_run_id"] != optical["run_id"]
        or plan["bbox"] != catalog["plan"]["bbox"]
        or plan["as_of"] != catalog["plan"]["as_of"]
        or len(catalog["candidates"]) > plan["max_passes"]
    ):
        raise ValueError("Pinned bounded event cohort required")
    if (
        not 0 < plan["minimum_native_valid_fraction"] <= 1
        or not 1 <= plan["max_passes"] <= 3
    ):
        raise ValueError("Invalid fixed pixel support policy")
    parent_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    parent_root = ROOT / "outputs/africa/kween" / parent_info["plan_sha256"][:20]
    parent_path = parent_root / (parent_info["run_id"] + ".json")
    if sha256_file(parent_path) != parent_info["manifest_sha256"]:
        raise ValueError("Original crop context manifest differs")
    parent = json.loads(parent_path.read_text())
    parent_area = next(a for a in parent["plan"]["areas"] if a["id"] == plan["area_id"])
    if (
        parent_area["bbox"] != plan["bbox"]
        or catalog["plan"]["parent_run_id"] != optical["run_id"]
    ):
        raise ValueError(
            "Radar cohort and crop-context area must match the pinned optical case"
        )
    context = parent["contexts"][plan["area_id"]]
    if sha256_file(parent_root / context["crop_asset"]) != context["crop_asset_sha256"]:
        raise ValueError("Historical crop mask differs")
    with rasterio.open(parent_root / context["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    grid = context["grid"]
    transform = rasterio.Affine(*grid["transform"][:6])
    root = ROOT / "outputs/africa/radar-pixels" / fingerprint(plan)[:20]
    root.mkdir(parents=True, exist_ok=True)
    cache_root = root / "native"
    cache_root.mkdir(exist_ok=True)
    frozen = root / "frozen-plan.json"
    if not frozen.exists():
        atomic_json(
            frozen,
            dict(
                plan=plan,
                frozen_at=datetime.now(timezone.utc).isoformat(),
                interpretation="Fixed before radar pixel inspection; exploratory numerical contract only",
            ),
        )
    elif json.loads(frozen.read_text())["plan"] != plan:
        raise ValueError("Frozen radar pixel plan differs")
    signer = ContainerSigner(source.SESSION)
    rows, diagnostics, powers = [], [], {}
    for item in catalog["candidates"]:
        row = {k: v for k, v in item.items() if k != "assets"}
        row["status"] = "processing_failed"
        try:
            if utc_time(item["acquired_at"]) > utc_time(plan["as_of"]):
                raise ValueError("After-cutoff radar acquisition")
            power, support, lineage = [], [], {}
            for band in ("vv", "vh"):
                p, s, record = native_clip(
                    item["assets"][band], grid, cache_root, args.allow_downloads, signer
                )
                power.append(p)
                support.append(s)
                lineage[band] = record
            support = np.stack(support)
            power = np.where(
                support >= plan["minimum_native_valid_fraction"],
                np.stack(power),
                np.nan,
            ).astype("float32")
            common = np.isfinite(power).all(axis=0).astype("uint8")
            recipe = dict(
                software=dict(
                    numpy=np.__version__,
                    rasterio=rasterio.__version__,
                    gdal=rasterio.__gdal_version__,
                ),
                item_id=item["item_id"],
                track_id=item["track_id"],
                grid=grid,
                lineage=lineage,
                support_policy=plan["minimum_native_valid_fraction"],
                code={
                    p: sha256_file(ROOT / p)
                    for p in (
                        "scripts/build_radar_series.py",
                        "vantage/radar_values.py",
                    )
                },
            )
            identity = fingerprint(recipe)[:24]
            assets = dict(
                linear=checked_cog(
                    root / (identity + "-linear.tif"),
                    power,
                    transform,
                    ["VV_gamma0_linear", "VH_gamma0_linear"],
                ),
                native_support=checked_cog(
                    root / (identity + "-support.tif"),
                    support,
                    transform,
                    ["VV_native_positive_fraction", "VH_native_positive_fraction"],
                ),
                common_valid=checked_cog(
                    root / (identity + "-common.tif"),
                    common,
                    transform,
                    ["both_polarizations_numeric_valid"],
                ),
            )
            evidence = numeric_evidence(
                power,
                crop,
                plan["minimum_crop_numeric_fraction"],
                plan["minimum_comparable_pixels"],
            )
            row.update(
                status="processed",
                artifact_id=identity,
                recipe=recipe,
                assets=assets,
                evidence=evidence,
            )
            powers[item["item_id"]] = power
        except Exception as exc:
            diagnostics.append(
                dict(item_id=item["item_id"], error_type=type(exc).__name__)
            )
        rows.append(row)
        atomic_json(
            root / "progress.json",
            dict(
                processed=len(rows),
                requested=len(catalog["candidates"]),
                observations=rows,
            ),
        )
        print(f"{item['acquired_at']}: {row['status']}", flush=True)
    changes = []
    tracks = sorted({r["track_id"] for r in rows})
    for track in tracks:
        ordered = sorted(
            [r for r in rows if r["track_id"] == track],
            key=lambda r: utc_time(r["acquired_at"]),
        )
        for first, second in zip(ordered, ordered[1:]):
            result = dict(
                track_id=track,
                earlier_item_id=first["item_id"],
                later_item_id=second["item_id"],
                status="withheld",
            )
            if first["status"] == second["status"] == "processed":
                derived = paired_change(
                    powers[first["item_id"]],
                    powers[second["item_id"]],
                    crop,
                    track,
                    track,
                    plan["minimum_crop_numeric_fraction"],
                    plan["minimum_comparable_pixels"],
                )
                result.update(derived["summary"])
                identity = fingerprint(
                    dict(
                        first=first["artifact_id"],
                        second=second["artifact_id"],
                        plan=plan,
                    )
                )[:24]
                result["asset"] = checked_cog(
                    root / (identity + "-change.tif"),
                    derived["delta_db"],
                    transform,
                    ["VV_later_minus_earlier_db", "VH_later_minus_earlier_db"],
                )
            changes.append(result)
    report = dict(
        software=dict(
            numpy=np.__version__,
            rasterio=rasterio.__version__,
            gdal=rasterio.__gdal_version__,
        ),
        schema_version="radar-pixels-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=sha256_file(frozen),
        catalog_manifest_sha256=sha256_file(catalog_path),
        context=context,
        observations=rows,
        changes=changes,
        source_collection="sentinel-1-rtc",
        radar_cogs=sum(len(r.get("assets", {})) for r in rows)
        + sum("asset" in c for c in changes),
        terrain_screen_verified=False,
        agronomic_review_eligible=False,
        independent_field_labels=0,
        trained_model=False,
        causal_attribution=False,
        operational_replay=False,
        optical_status_unchanged=optical["summary"]["status"],
        code={
            p: sha256_file(ROOT / p)
            for p in (
                "scripts/build_radar_series.py",
                "vantage/radar_values.py",
                "scripts/prepare_ml_dataset.py",
            )
        },
    )
    report["run_id"] = fingerprint(report)[:24]
    atomic_json(root / (report["run_id"] + ".json"), report)
    atomic_json(
        root / "diagnostics.json",
        dict(run_id=report["run_id"], diagnostics=diagnostics),
    )
    atomic_json(
        root.parent / "latest.json",
        dict(directory=root.name, manifest=report["run_id"] + ".json"),
    )
    if args.write_summary:
        summary = {
            k: v
            for k, v in report.items()
            if k not in ("observations", "context", "code")
        }
        summary["manifest_sha256"] = sha256_file(root / (report["run_id"] + ".json"))
        summary["observations"] = [
            {k: v for k, v in row.items() if k not in ("assets", "recipe")}
            for row in rows
        ]
        atomic_json(ROOT / "docs/africa/KWEEN_RADAR_PIXELS_RUN.json", summary)
    print(
        f"Radar pixel run {report['run_id']}: {sum(r['status'] == 'processed' for r in rows)}/{len(rows)} processed; agricultural validity unconfirmed",
        flush=True,
    )
    if any(r["status"] != "processed" for r in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
