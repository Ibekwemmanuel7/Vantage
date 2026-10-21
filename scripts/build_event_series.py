"""Acquire every eligible observation in a bounded, frozen Kween follow-up window."""

# ruff: noqa: E402
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source
from scripts.build_kween_case import archive_search, scene_ndvi
from scripts.prepare_ml_dataset import cached_asset, write_cog
from scripts.prepare_multispectral import make_scene, validate_scene
from vantage.archive import fingerprint
from vantage.crop_context import crop_evidence
from vantage.event_series import timeline_summary, utc_time, validate_followup
from vantage.historical import anomaly_map
from vantage.imagery import atomic_json, sha256_file
from vantage.planetary import ContainerSigner
from vantage.seasonal import slot_candidates
import numpy as np
import rasterio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs/kween_2023_followup.json"
    )
    parser.add_argument("--allow-downloads", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.config.read_text())
    if not 1 <= plan["max_acquisitions"] <= 12:
        raise ValueError("At most twelve acquisitions per research run")
    if not plan["start"] <= plan["end"] or plan["end"] != plan["as_of"][:10]:
        raise ValueError("Ordered interval ending at cutoff required")
    # Pin the inspected parent manifest, not a floating latest dataset.
    expected = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    parent_root = ROOT / "outputs/africa/kween" / expected["plan_sha256"][:20]
    parent_path = parent_root / (plan["parent_run_id"] + ".json")
    if (
        plan["parent_run_id"] != expected["run_id"]
        or sha256_file(parent_path) != expected["manifest_sha256"]
    ):
        raise ValueError("Pinned parent run differs")
    parent = json.loads(parent_path.read_text())
    validate_followup(plan, parent["plan"])
    area = next(a for a in parent["plan"]["areas"] if a["id"] == plan["area_id"])
    if area["bbox"] != plan["bbox"]:
        raise ValueError("Follow-up must use the exact parent grid")
    context = parent["contexts"][area["id"]]
    if sha256_file(parent_root / context["crop_asset"]) != context["crop_asset_sha256"]:
        raise ValueError("Parent historical crop mask differs")
    grid = context["grid"]
    transform = rasterio.Affine(*grid["transform"][:6])
    catalog = json.loads((parent_root / (area["id"] + "-worldcover.json")).read_text())
    wc = next(
        i
        for i in catalog["response"]["features"]
        if i["id"] == context["worldcover_id"]
    )
    classes = cached_asset(wc, "map", transform, grid["width"], grid["height"], False)
    if hashlib.sha256(classes.tobytes()).hexdigest() != context["raw_sha256"]:
        raise ValueError("Raw historical land cover differs")
    with rasterio.open(parent_root / context["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    root = ROOT / "outputs/africa/event-series" / fingerprint(plan)[:20]
    root.mkdir(parents=True, exist_ok=True)
    frozen = root / "frozen-plan.json"
    if not frozen.exists():
        atomic_json(
            frozen,
            dict(
                plan=plan,
                frozen_at=datetime.now(timezone.utc).isoformat(),
                interpretation="Choices fixed before new follow-up acquisition; exploratory, not blinded",
            ),
        )
    elif json.loads(frozen.read_text())["plan"] != plan:
        raise ValueError("Frozen follow-up plan differs")
    items, catalog_hash = archive_search(
        root,
        "sentinel-2",
        "sentinel-2-l2a",
        area["bbox"],
        plan["start"] + "T00:00:00Z/" + plan["end"] + "T23:59:59Z",
        args.allow_downloads,
    )
    candidates = sorted(
        slot_candidates(plan, items, area["bbox"]),
        key=lambda i: (i["properties"]["datetime"], i["id"]),
    )
    if len(candidates) > plan["max_acquisitions"]:
        raise ValueError(
            "Catalog exceeds fixed acquisition budget; no silent truncation"
        )
    source.signed = ContainerSigner(source.SESSION)
    index_path = root / "metadata-index.json"
    index = json.loads(
        (
            index_path if index_path.exists() else parent_root / "metadata-index.json"
        ).read_text()
    )
    metadata = {}
    for path in source.CACHE.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        if "BOA_QUANTIFICATION_VALUE" in text:
            metadata[hashlib.sha256(text.encode()).hexdigest()] = text
    scenes_root = root / "scenes"
    scenes_root.mkdir(exist_ok=True)
    policy = parent["plan"]["quality_policy"]
    epoch = next(
        e for e in parent["plan"]["epochs"] if e["id"] == plan["comparison_epoch"]
    )
    refs = [
        r
        for r in parent["observations"]
        if r["area_id"] == area["id"]
        and r["epoch"] == epoch["id"]
        and r["year"] in parent["plan"]["reference_years"]
        and r["evidence"]
        and r["evidence"]["evidence_status"] == "sufficient_coverage_for_research"
    ]
    if len({r["year"] for r in refs}) != len(refs):
        raise ValueError("Duplicate reference years")
    for ref in refs:
        validate_scene(ref["scene"], parent_root / "scenes")
    reference_ndvi = [scene_ndvi(r["scene"], parent_root / "scenes")[2] for r in refs]
    rows, scenes, diagnostics = [], [], []
    for item in candidates:
        stamp = item["properties"]["datetime"]
        age = (utc_time(plan["as_of"]) - utc_time(stamp)).total_seconds() / 86400
        if age < 0:
            raise ValueError("Acquisition after cutoff")
        row = dict(
            scene_id=item["id"],
            acquired_at=stamp,
            age_at_cutoff_days=age,
            within_freshness_window=age <= plan["max_observation_age_days"],
            status="acquisition_failed",
            coverage_qualified=False,
            observation=None,
            comparison=None,
        )
        try:
            xml = metadata.get(index.get(item["id"]))
            if xml is None:
                if not args.allow_downloads:
                    raise FileNotFoundError("Product metadata not cached")
                xml = source.fetch(
                    source.signed(item["assets"]["product-metadata"]["href"])
                )
                digest = hashlib.sha256(xml.encode()).hexdigest()
                metadata[digest] = xml
                index[item["id"]] = digest
                atomic_json(index_path, index)
            scene = make_scene(
                dict(location_id=area["id"], bbox=area["bbox"]),
                item,
                xml,
                scenes_root,
                args.allow_downloads,
            )
            validate_scene(scene, scenes_root)
            cube, common, ndvi = scene_ndvi(scene, scenes_root)
            evidence = crop_evidence(
                cube,
                common,
                classes,
                policy["min_crop_usable_fraction"],
                policy["min_valid_pixels"],
            )
            qualified = (
                evidence["evidence_status"] == "sufficient_coverage_for_research"
            )
            row.update(
                status="processed",
                coverage_qualified=qualified,
                observation=evidence,
                artifact_id=scene["artifact_id"],
            )
            scenes.append(scene)
            in_epoch = epoch["start"] <= stamp[5:10] <= epoch["end"]
            if in_epoch and qualified and len(refs) >= policy["min_reference_years"]:
                derived = anomaly_map(
                    ndvi,
                    reference_ndvi,
                    crop,
                    policy["min_reference_years"],
                    policy["min_crop_usable_fraction"],
                    policy["min_valid_pixels"],
                    policy["ndvi_drop_trigger"],
                )
                identity = fingerprint(
                    dict(
                        target=scene["artifact_id"],
                        references=[r["scene"]["artifact_id"] for r in refs],
                        policy=policy,
                        crop=context["crop_asset_sha256"],
                        code=sha256_file(ROOT / "vantage/historical.py"),
                    )
                )[:24]
                asset = root / (identity + "-anomaly.tif")
                arrays = np.stack(
                    [
                        derived["delta"],
                        np.where(crop, derived["reference_count"], np.nan),
                        np.where(
                            np.isfinite(derived["delta"]), derived["low_flag"], np.nan
                        ),
                    ]
                ).astype("float32")
                if asset.exists():
                    with rasterio.open(asset) as ds:
                        if not np.array_equal(ds.read(), arrays, equal_nan=True):
                            raise ValueError("Derived artifact differs")
                else:
                    write_cog(
                        asset,
                        arrays,
                        transform,
                        [
                            "NDVI_B8A_minus_short_reference_median",
                            "eligible_reference_count",
                            "lower_than_all_references_and_drop_trigger",
                        ],
                    )
                row["comparison"] = dict(
                    **derived["summary"],
                    asset=asset.name,
                    sha256=sha256_file(asset),
                    reference_years=[r["year"] for r in refs],
                    within_freshness_window=row["within_freshness_window"],
                )
            else:
                row["comparison"] = dict(
                    status="withheld",
                    reasons=["outside_reference_calendar_window"]
                    if not in_epoch
                    else ["insufficient_target_or_reference_coverage"],
                )
        except Exception as exc:
            # A derivation failure must not masquerade as a completed observation.
            row["status"] = "processing_failed"
            row["coverage_qualified"] = False
            diagnostics.append(dict(scene_id=item["id"], error_type=type(exc).__name__))
        rows.append(row)
        atomic_json(
            root / "progress.json",
            dict(completed=len(rows), requested=len(candidates), observations=rows),
        )
        print(
            f"{stamp}: {row['status']}; coverage qualified={row['coverage_qualified']}",
            flush=True,
        )
    summary = timeline_summary(rows, plan["as_of"], plan["max_observation_age_days"])
    report = dict(
        schema_version="event-series-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=sha256_file(frozen),
        parent_manifest_sha256=sha256_file(parent_path),
        catalog_sha256=catalog_hash,
        raw_catalog_items=len(items),
        observations=rows,
        scenes=scenes,
        summary=summary,
        context=context,
        independent_field_labels=0,
        trained_model=False,
        causal_attribution=False,
        operational_replay=False,
        code={
            p: sha256_file(ROOT / p)
            for p in (
                "scripts/build_event_series.py",
                "vantage/event_series.py",
                "scripts/build_kween_case.py",
                "vantage/historical.py",
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
        atomic_json(
            ROOT / "docs/africa/KWEEN_TEMPORAL_RUN.json",
            dict(
                run_id=report["run_id"],
                manifest_sha256=sha256_file(root / (report["run_id"] + ".json")),
                plan=plan,
                frozen_plan_sha256=report["frozen_plan_sha256"],
                summary=summary,
                observations=rows,
                scene_cogs=len(scenes) * 3,
                anomaly_cogs=sum(
                    r["comparison"] is not None and "asset" in r["comparison"]
                    for r in rows
                ),
            ),
        )
    print(f"Temporal run {report['run_id']}: {summary['status']}", flush=True)
    if any(r["status"] != "processed" for r in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
