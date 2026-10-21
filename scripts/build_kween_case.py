"""Frozen public-event reconstruction: six-band COGs, crop masks, anomaly maps and native rainfall."""
# ruff: noqa: E402

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source
from scripts.prepare_ml_dataset import cached_asset, write_cog
from scripts.prepare_multispectral import make_scene, validate_scene
from vantage.archive import fingerprint
from vantage.imagery import atomic_json, sha256_file
from vantage.planetary import ContainerSigner
from vantage.seasonal import slot_candidates
from vantage.crop_context import crop_evidence, landcover_masks
from vantage.historical import anomaly_map, rainfall_comparison, validate_plan
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds as pixel_window, bounds as window_bounds


def archive_search(root, name, collection, bbox, interval, online):
    path = root / (name + ".json")
    if not path.exists():
        if not online:
            raise FileNotFoundError("Catalog not archived")
        params = dict(collections=collection, bbox=",".join(map(str, bbox)), limit=100)
        if interval:
            params["datetime"] = interval
        url = "https://planetarycomputer.microsoft.com/api/stac/v1/search?" + urlencode(
            params
        )
        response = json.loads(source.fetch(url))
        if any(link.get("rel") == "next" for link in response.get("links", [])):
            raise ValueError("Truncated catalog")
        atomic_json(
            path,
            dict(
                request_url=url,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                response=response,
            ),
        )
    data = json.loads(path.read_text())
    if any(link.get("rel") == "next" for link in data["response"].get("links", [])):
        raise ValueError("Truncated archive")
    return data["response"]["features"], sha256_file(path)


def scene_ndvi(record, root):
    with rasterio.open(
        root / record["artifact_id"] / record["assets"]["reflectance"]["href"]
    ) as ds:
        cube = ds.read()
    common = np.isfinite(cube).all(axis=0)
    valid = common & (cube[3] + cube[2] > 0)
    ndvi = np.divide(
        cube[3] - cube[2],
        cube[3] + cube[2],
        out=np.full(cube.shape[1:], np.nan, dtype="float32"),
        where=valid,
    )
    return cube, common, ndvi


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=ROOT / "configs/kween_2023_case.json")
    p.add_argument("--allow-downloads", action="store_true")
    args = p.parse_args()
    plan = json.loads(args.config.read_text())
    validate_plan(plan)
    root = ROOT / "outputs/africa/kween" / fingerprint(plan)[:20]
    root.mkdir(parents=True, exist_ok=True)
    frozen = root / "frozen-plan.json"
    if not frozen.exists():
        atomic_json(
            frozen,
            dict(
                plan=plan,
                frozen_at=datetime.now(timezone.utc).isoformat(),
                purpose="Analysis choices fixed before this run; not blinded event selection or registered study",
            ),
        )
    elif json.loads(frozen.read_text())["plan"] != plan:
        raise ValueError("Frozen plan changed")
    geography = root / "ngenge-osm.json"
    if not geography.exists():
        if not args.allow_downloads:
            raise FileNotFoundError("Geography anchor not archived")
        atomic_json(geography, json.loads(source.fetch(plan["geography_source"])))
    point = json.loads(geography.read_text())["elements"][0]
    if (
        abs(point["lon"] - plan["geography_expected_point"][0]) > 0.01
        or abs(point["lat"] - plan["geography_expected_point"][1]) > 0.01
    ):
        raise ValueError(
            "Place anchor differs; revise and refreeze plan before processing"
        )
    source.signed = ContainerSigner(source.SESSION)
    scenes_root = root / "scenes"
    scenes_root.mkdir(exist_ok=True)
    metadata = {}
    for path in source.CACHE.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        if "BOA_QUANTIFICATION_VALUE" in text:
            metadata[hashlib.sha256(text.encode()).hexdigest()] = text
    index_path = root / "metadata-index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    records = []
    contexts = {}
    catalog_hashes = {}
    diagnostics = []
    policy = plan["quality_policy"]
    for area in plan["areas"]:
        bbox = area["bbox"]
        bounds = transform_bounds("EPSG:4326", "EPSG:32636", *bbox)
        width = int(np.ceil((bounds[2] - bounds[0]) / 20))
        height = int(np.ceil((bounds[3] - bounds[1]) / 20))
        transform = from_bounds(*bounds, width, height)
        wc_items, h = archive_search(
            root,
            area["id"] + "-worldcover",
            "esa-worldcover",
            bbox,
            None,
            args.allow_downloads,
        )
        catalog_hashes[area["id"] + "-worldcover"] = h
        w, s, e, n = bbox
        wc = next(
            i
            for i in sorted(wc_items, key=lambda i: i["id"])
            if "2021" in i["id"]
            and i["bbox"][0] <= w
            and i["bbox"][1] <= s
            and i["bbox"][2] >= e
            and i["bbox"][3] >= n
        )
        classes = cached_asset(
            wc, "map", transform, width, height, args.allow_downloads
        )
        crop, known = landcover_masks(classes)
        mask_path = root / (area["id"] + "-crop.tif")
        if mask_path.exists():
            with rasterio.open(mask_path) as ds:
                if not np.array_equal(
                    ds.read(), np.stack([crop, known]).astype("uint8")
                ):
                    raise ValueError("Historical mask changed")
        else:
            write_cog(
                mask_path,
                np.stack([crop, known]).astype("uint8"),
                transform,
                ["historical_cropland_2021", "landcover_known"],
            )
        contexts[area["id"]] = dict(
            worldcover_id=wc["id"],
            source_href=wc["assets"]["map"]["href"],
            raw_sha256=hashlib.sha256(classes.tobytes()).hexdigest(),
            crop_asset=mask_path.name,
            crop_asset_sha256=sha256_file(mask_path),
            crop_pixels=int(crop.sum()),
            grid=dict(
                width=width, height=height, transform=list(transform), crs="EPSG:32636"
            ),
        )
        for year in plan["reference_years"] + [plan["target_year"]]:
            for epoch in plan["epochs"]:
                start = f"{year}-{epoch['start']}"
                end = f"{year}-{epoch['end']}"
                name = f"{area['id']}-{year}-{epoch['id']}"
                entry = dict(
                    area_id=area["id"],
                    year=year,
                    epoch=epoch["id"],
                    status="unavailable",
                    attempts=[],
                    scene=None,
                    evidence=None,
                )
                try:
                    items, h = archive_search(
                        root,
                        name,
                        "sentinel-2-l2a",
                        bbox,
                        start + "T00:00:00Z/" + end + "T23:59:59Z",
                        args.allow_downloads,
                    )
                    catalog_hashes[name] = h
                    candidates = slot_candidates(
                        dict(start=start, end=end), items, bbox
                    )
                    entry["candidate_count"] = len(candidates)
                    for item in candidates[:3]:
                        try:
                            sid = item["id"]
                            xml = metadata.get(index.get(sid))
                            if xml is None:
                                if not args.allow_downloads:
                                    raise FileNotFoundError(
                                        "Product metadata not cached"
                                    )
                                xml = source.fetch(
                                    source.signed(
                                        item["assets"]["product-metadata"]["href"]
                                    )
                                )
                                digest = hashlib.sha256(xml.encode()).hexdigest()
                                metadata[digest] = xml
                                index[sid] = digest
                                atomic_json(index_path, index)
                            scene = make_scene(
                                dict(location_id=area["id"], bbox=bbox),
                                item,
                                xml,
                                scenes_root,
                                args.allow_downloads,
                            )
                            validate_scene(scene, scenes_root)
                            if (
                                year == plan["target_year"]
                                and scene["acquired_at"] > plan["observation_cutoff"]
                            ):
                                raise ValueError("After-cutoff observation")
                            cube, common, _ = scene_ndvi(scene, scenes_root)
                            evidence = crop_evidence(
                                cube,
                                common,
                                classes,
                                policy["min_crop_usable_fraction"],
                                policy["min_valid_pixels"],
                            )
                            entry.update(
                                status="processed", scene=scene, evidence=evidence
                            )
                            entry["attempts"].append(
                                dict(scene_id=sid, status="processed")
                            )
                            break
                        except Exception as exc:
                            entry["attempts"].append(
                                dict(scene_id=item["id"], status="failed")
                            )
                            diagnostics.append(
                                dict(
                                    slot=name,
                                    scene_id=item["id"],
                                    error_type=type(exc).__name__,
                                )
                            )
                except Exception as exc:
                    diagnostics.append(dict(slot=name, error_type=type(exc).__name__))
                records.append(entry)
                atomic_json(
                    root / "progress.json",
                    dict(
                        completed=len(records),
                        requested=len(plan["areas"])
                        * (len(plan["reference_years"]) + 1)
                        * len(plan["epochs"]),
                        records=records,
                    ),
                )
                print(f"{name}: {entry['status']}", flush=True)
    # Derive comparisons only after the frozen cohort acquisition is complete.
    comparisons = []
    for area in plan["areas"]:
        context = contexts[area["id"]]
        grid = context["grid"]
        transform = rasterio.Affine(*grid["transform"][:6])
        with rasterio.open(root / context["crop_asset"]) as ds:
            crop = ds.read(1).astype(bool)
        for epoch in plan["epochs"]:
            matching = [
                r
                for r in records
                if r["area_id"] == area["id"] and r["epoch"] == epoch["id"]
            ]
            target = next(r for r in matching if r["year"] == plan["target_year"])
            refs = [
                r
                for r in matching
                if r["year"] in plan["reference_years"]
                and r["evidence"]
                and r["evidence"]["evidence_status"]
                == "sufficient_coverage_for_research"
            ]
            result = dict(
                area_id=area["id"],
                epoch=epoch["id"],
                reference_years=[r["year"] for r in refs],
                target_acquired_at=target["scene"]["acquired_at"]
                if target["scene"]
                else None,
                status="withheld",
            )
            if (
                target["evidence"]
                and target["evidence"]["evidence_status"]
                == "sufficient_coverage_for_research"
                and len(refs) >= policy["min_reference_years"]
            ):
                _, _, target_ndvi = scene_ndvi(target["scene"], scenes_root)
                reference_ndvi = [scene_ndvi(r["scene"], scenes_root)[2] for r in refs]
                derived = anomaly_map(
                    target_ndvi,
                    reference_ndvi,
                    crop,
                    policy["min_reference_years"],
                    policy["min_crop_usable_fraction"],
                    policy["min_valid_pixels"],
                    policy["ndvi_drop_trigger"],
                )
                result.update(derived["summary"])
                identity = fingerprint(
                    dict(
                        target=target["scene"]["artifact_id"],
                        refs=[r["scene"]["artifact_id"] for r in refs],
                        mask=context["crop_asset_sha256"],
                        policy=policy,
                        code=sha256_file(ROOT / "vantage/historical.py"),
                    )
                )[:24]
                path = root / (identity + "-anomaly.tif")
                arrays = np.stack(
                    [
                        derived["delta"],
                        np.where(crop, derived["reference_count"], np.nan).astype(
                            "float32"
                        ),
                        np.where(
                            np.isfinite(derived["delta"]), derived["low_flag"], np.nan
                        ).astype("float32"),
                    ]
                )
                if path.exists():
                    with rasterio.open(path) as ds:
                        if not np.array_equal(ds.read(), arrays, equal_nan=True):
                            raise ValueError("Anomaly artifact differs")
                else:
                    write_cog(
                        path,
                        arrays,
                        transform,
                        [
                            "NDVI_B8A_minus_short_reference_median",
                            "eligible_reference_count",
                            "lower_than_all_references_and_drop_trigger",
                        ],
                    )
                result.update(asset=path.name, sha256=sha256_file(path))
            else:
                result["reasons"] = [
                    "Target coverage or three eligible reference years unavailable"
                ]
            comparisons.append(result)
    # Monthly rainfall is native 0.05-degree context, never resampled into field evidence.
    rain_by_area = {a["id"]: [] for a in plan["areas"]}
    rain_sources = []
    for year in plan["reference_years"] + [plan["target_year"]]:
        for month in plan["rainfall"]["months"]:
            url = f"https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/africa/tifs/chirps-v3.0.{year}.{month:02}.tif"
            cache = source.CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".bin")
            try:
                if not cache.exists() and not args.allow_downloads:
                    raise FileNotFoundError("Rainfall not cached")
                raw = source.fetch(url, binary=True)
                with rasterio.io.MemoryFile(raw) as mem, mem.open() as ds:
                    for area in plan["areas"]:
                        window = (
                            pixel_window(*area["bbox"], transform=ds.transform)
                            .round_offsets()
                            .round_lengths()
                        )
                        if not np.allclose(
                            window_bounds(window, ds.transform),
                            area["bbox"],
                            atol=1e-6,
                            rtol=0,
                        ):
                            raise ValueError("Rainfall native grid mismatch")
                        values = ds.read(1, window=window, masked=True)
                        if (
                            values.shape != (2, 2)
                            or np.ma.getmaskarray(values).any()
                            or not np.isfinite(values).all()
                            or (values < 0).any()
                        ):
                            raise ValueError("Invalid native rainfall cells")
                        rain_by_area[area["id"]].append(
                            dict(
                                year=year,
                                month=month,
                                mean_mm=float(values.mean()),
                                native_cells=values.tolist(),
                            )
                        )
                rain_sources.append(
                    dict(url=url, sha256=hashlib.sha256(raw).hexdigest())
                )
                print(f"Rainfall {year}/{month}: processed", flush=True)
            except Exception as exc:
                diagnostics.append(dict(rainfall=url, error_type=type(exc).__name__))
    report = dict(
        schema_version="kween-case-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=sha256_file(frozen),
        geography_sha256=sha256_file(geography),
        catalog_hashes=catalog_hashes,
        contexts=contexts,
        observations=records,
        comparisons=comparisons,
        rainfall={
            k: dict(
                observations=v,
                summary=rainfall_comparison(
                    v,
                    plan["reference_years"],
                    plan["target_year"],
                    plan["rainfall"]["months"],
                ),
            )
            for k, v in rain_by_area.items()
        },
        rain_sources=rain_sources,
        code={
            p: sha256_file(ROOT / p)
            for p in ("scripts/build_kween_case.py", "vantage/historical.py")
        },
        independent_field_labels=0,
        trained_model=False,
        causal_attribution=False,
        operational_replay=False,
    )
    report["run_id"] = fingerprint(report)[:24]
    atomic_json(root / (report["run_id"] + ".json"), report)
    atomic_json(
        root / "diagnostics.json",
        dict(run_id=report["run_id"], diagnostics=diagnostics),
    )
    atomic_json(
        ROOT / "outputs/africa/kween/latest.json",
        dict(directory=root.name, manifest=report["run_id"] + ".json"),
    )
    print(
        f"Case run {report['run_id']}: {sum(r['status'] == 'processed' for r in records)}/{len(records)} observations",
        flush=True,
    )
    if any(r["status"] != "processed" for r in records) or any(
        v["summary"]["status"] != "available" for v in report["rainfall"].values()
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
