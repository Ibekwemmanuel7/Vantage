"""Publish a dated customer-workspace snapshot and local, real-pixel previews."""

# ruff: noqa: E402
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source  # noqa: F401
from vantage.imagery import atomic_json, sha256_file
from vantage.archive import fingerprint
import numpy as np
import rasterio
from PIL import Image


def snapshot(temporal, radar, visibility, benchmark, sources):
    summary = temporal["summary"]
    if (
        summary["as_of"] != temporal["plan"]["as_of"]
        or summary["independent_field_labels"] != 0
        or summary["agronomic_review_eligible"] is not False
    ):
        raise ValueError(
            "This research-only workspace requires its documented unvalidated cohort"
        )
    return dict(
        schema_version="scouting-workspace-1",
        case_id="kween-2023",
        name="Ngenge locality",
        district="Kween",
        country="Uganda",
        bbox=temporal["plan"]["bbox"],
        as_of=summary["as_of"],
        mode="historical_research",
        boundary_status="Analyst-selected locality box, not verified fields",
        field_recommendations_available=False,
        independent_field_outcomes=0,
        optical=dict(
            status=summary["status"],
            latest_acquisition=summary["latest_acquisition"],
            latest_usable=summary["latest_quality_qualified_acquisition"],
            age_at_cutoff_days=summary["latest_quality_qualified_age_days"],
            freshness_policy_days=summary["max_observation_age_days"],
            observations=[
                dict(
                    acquired_at=r["acquired_at"],
                    coverage_qualified=r["coverage_qualified"],
                    usable_crop_fraction=(r["observation"] or {}).get(
                        "crop_usable_fraction"
                    ),
                )
                for r in temporal["observations"]
            ],
        ),
        radar=dict(
            acquisitions=len(radar["observations"]),
            dates=[r["acquired_at"] for r in radar["observations"]],
            bounded_sightlines_checked=visibility["bounded_sampled_sightlines_checked"],
            illumination_confirmed=visibility["radar_illumination_confirmed"],
        ),
        benchmark=dict(
            status=benchmark["status"],
            evaluated_acquisitions=benchmark["exported_acquisitions_evaluated"],
            compared_acquisitions=benchmark["exported_acquisitions_compared"],
            metrics_available=benchmark["metrics_available"],
        ),
        sources=sources,
        limitations=[
            "Crop identity and planting dates are unconfirmed",
            "No independent field outcomes",
            "An observed vegetation change does not establish its cause",
            "Imported fields are not analyzed automatically",
        ],
    )


def main():
    names = [
        "KWEEN_TEMPORAL",
        "KWEEN_RADAR_PIXELS",
        "KWEEN_VISIBILITY",
        "KWEEN_PROCESSOR_BENCHMARK",
    ]
    reports, sources = [], []
    for name in names:
        path = ROOT / "docs/africa" / (name + "_RUN.json")
        reports.append(json.loads(path.read_text()))
        sources.append(
            dict(
                document=name + "_RUN.json",
                run_id=reports[-1]["run_id"],
                sha256=sha256_file(path),
            )
        )
    temporal, radar, visibility, benchmark = reports
    data = snapshot(*reports, sources)
    parent_root = (
        ROOT / "outputs/africa/event-series" / fingerprint(temporal["plan"])[:20]
    )
    manifest_path = parent_root / (temporal["run_id"] + ".json")
    if sha256_file(manifest_path) != temporal["manifest_sha256"]:
        raise ValueError("Pinned optical manifest differs")
    manifest = json.loads(manifest_path.read_text())
    selected = next(
        r
        for r in manifest["observations"]
        if r["acquired_at"] == data["optical"]["latest_usable"]
    )
    scene = next(r for r in manifest["scenes"] if r["scene_id"] == selected["scene_id"])
    output = ROOT / "outputs/africa/dashboard"
    output.mkdir(parents=True, exist_ok=True)
    reflectance = (
        parent_root
        / "scenes"
        / scene["artifact_id"]
        / scene["assets"]["reflectance"]["href"]
    )
    if sha256_file(reflectance) != scene["assets"]["reflectance"]["sha256"]:
        raise ValueError("Preview reflectance differs")
    with rasterio.open(reflectance) as ds:
        rgb = ds.read([3, 2, 1])
    valid = np.all(np.isfinite(rgb), axis=0)
    color = (np.power(np.clip(np.nan_to_num(rgb) / 0.3, 0, 1), 1 / 2.2) * 255).astype(
        "uint8"
    )
    rgba = np.concatenate(
        [np.moveaxis(color, 0, -1), (valid.astype("uint8") * 255)[..., None]], axis=-1
    )
    Image.fromarray(rgba).save(output / "kween-rgb.png")
    anomaly = parent_root / selected["comparison"]["asset"]
    if sha256_file(anomaly) != selected["comparison"]["sha256"]:
        raise ValueError("Preview anomaly differs")
    with rasterio.open(anomaly) as ds:
        delta = ds.read(1)
    # Fixed display-only scale, orange below reference / blue above. NaNs remain transparent.
    low, mid, high = (
        np.array([179, 85, 38]),
        np.array([244, 242, 226]),
        np.array([33, 115, 157]),
    )
    weight = np.clip(np.nan_to_num(delta) / 0.3, -1, 1)[..., None]
    rgb = np.where(
        weight < 0, mid + (-weight) * (low - mid), mid + weight * (high - mid)
    ).astype("uint8")
    rgba = np.concatenate(
        [rgb, (np.isfinite(delta).astype("uint8") * 255)[..., None]], axis=-1
    )
    Image.fromarray(rgba).save(output / "kween-change.png")
    data["preview"] = dict(
        acquired_at=selected["acquired_at"],
        scene_id=scene["scene_id"],
        reference_years=selected["comparison"]["reference_years"],
        grid=scene["grid"],
        rgb_scale="0–0.30 reflectance; gamma 2.2, display only",
        change_scale=[-0.3, 0.3],
        assets={
            layer: dict(sha256=sha256_file(output / f"kween-{layer}.png"))
            for layer in ("rgb", "change")
        },
    )
    data["snapshot_id"] = fingerprint(data)[:24]
    atomic_json(ROOT / "web/data/scouting.json", data)
    print(
        "Dashboard snapshot",
        data["snapshot_id"],
        "- historical; zero field recommendations",
    )


if __name__ == "__main__":
    main()
