"""Archive public radar metadata and test anonymous access without storing tokens."""

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
from vantage.archive import fingerprint
from vantage.event_series import utc_time
from vantage.imagery import atomic_json, sha256_file
from vantage.radar import catalog_candidates, track_coverage
import shapely


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs/kween_2023_radar.json"
    )
    parser.add_argument("--allow-downloads", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.config.read_text())
    optical_path = ROOT / "docs/africa/KWEEN_TEMPORAL_RUN.json"
    optical = json.loads(optical_path.read_text())
    if (
        plan["parent_run_id"] != optical["run_id"]
        or plan["bbox"] != optical["plan"]["bbox"]
        or plan["as_of"] != optical["plan"]["as_of"]
        or plan["collection"] != "sentinel-1-rtc"
    ):
        raise ValueError("Fixed optical event and supported collection required")
    if not plan["start"] <= plan["end"] or plan["end"] != plan["as_of"][:10]:
        raise ValueError("Ordered interval ending at cutoff required")
    utc_time(plan["as_of"])
    root = ROOT / "outputs/africa/radar" / fingerprint(plan)[:20]
    root.mkdir(parents=True, exist_ok=True)
    frozen = root / "frozen-plan.json"
    if not frozen.exists():
        atomic_json(
            frozen,
            dict(
                plan=plan,
                frozen_at=datetime.now(timezone.utc).isoformat(),
                scope="Exploratory catalog/access feasibility, no radar pixels",
            ),
        )
    elif json.loads(frozen.read_text())["plan"] != plan:
        raise ValueError("Frozen radar plan differs")
    collection_path = root / "collection.json"
    collection_url = (
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections/"
        + plan["collection"]
    )
    if not collection_path.exists():
        if not args.allow_downloads:
            raise FileNotFoundError("Collection metadata not cached")
        atomic_json(collection_path, json.loads(source.fetch(collection_url)))
    collection = json.loads(collection_path.read_text())
    items, catalog_hash = archive_search(
        root,
        "radar-catalog",
        plan["collection"],
        plan["bbox"],
        plan["start"] + "T00:00:00Z/" + plan["end"] + "T23:59:59Z",
        args.allow_downloads,
    )
    if len(items) > plan["max_catalog_items"]:
        raise ValueError("Catalog budget exceeded")
    candidates, excluded = catalog_candidates(items, plan)
    groups = track_coverage(
        candidates,
        optical["observations"],
        plan["as_of"],
        plan["max_observation_age_days"],
    )
    access_path = root / "anonymous-access.json"
    if not access_path.exists():
        if not args.allow_downloads:
            raise FileNotFoundError("Anonymous access probe not archived")
        account = collection.get("msft:storage_account")
        container = collection.get("msft:container")
        # Only the documented RTC token route is probed. No credential discovery or SDK key use.
        if account != "sentinel1euwestrtc" or container != "sentinel1-grd-rtc":
            raise ValueError("Unexpected storage route; inspect metadata before access")
        endpoint = (
            "https://planetarycomputer.microsoft.com/api/sas/v1/token/"
            + account
            + "/"
            + container
        )
        try:
            # Dedicated request with no subscription-key header or user credentials.
            response = source.SESSION.get(endpoint, timeout=45)
            if response.status_code in (401, 403):
                status = "authentication_required"
            elif response.status_code == 200:
                status = (
                    "anonymous_token_available"
                    if isinstance(response.json().get("token"), str)
                    else "unexpected_response"
                )
            else:
                status = "access_probe_failed"
            probe = dict(
                endpoint=endpoint,
                observed_at=datetime.now(timezone.utc).isoformat(),
                http_status=response.status_code,
                status=status,
                token_persisted=False,
                radar_pixels_downloaded=False,
            )
        except Exception as exc:
            probe = dict(
                endpoint=endpoint,
                observed_at=datetime.now(timezone.utc).isoformat(),
                status="access_probe_failed",
                error_type=type(exc).__name__,
                token_persisted=False,
                radar_pixels_downloaded=False,
            )
        atomic_json(access_path, probe)
    probe = json.loads(access_path.read_text())
    report = dict(
        schema_version="radar-feasibility-1",
        plan=plan,
        plan_sha256=fingerprint(plan),
        frozen_plan_sha256=sha256_file(frozen),
        optical_summary_sha256=sha256_file(optical_path),
        collection_sha256=sha256_file(collection_path),
        catalog_sha256=catalog_hash,
        access_probe_sha256=sha256_file(access_path),
        access=probe,
        collection_requires_account=collection.get("msft:requires_account"),
        raw_catalog_items=len(items),
        distinct_eligible_passes=len(candidates),
        candidates=candidates,
        exclusions=excluded,
        tracks=groups,
        radar_cogs=0,
        measured_radar_coverage=None,
        usable_radar_evidence=False,
        optical_status_unchanged=optical["summary"]["status"],
        trained_model=False,
        independent_field_labels=0,
        causal_attribution=False,
        operational_replay=False,
        software=dict(shapely=shapely.__version__),
        code={
            p: sha256_file(ROOT / p)
            for p in (
                "scripts/inspect_radar_coverage.py",
                "vantage/radar.py",
                "vantage/event_series.py",
                "scripts/build_kween_case.py",
            )
        },
    )
    report["run_id"] = fingerprint(report)[:24]
    atomic_json(root / (report["run_id"] + ".json"), report)
    atomic_json(
        root.parent / "latest.json",
        dict(directory=root.name, manifest=report["run_id"] + ".json"),
    )
    if args.write_summary:
        summary = dict(report)
        summary["manifest_sha256"] = sha256_file(root / (report["run_id"] + ".json"))
        # Public summaries retain item identifiers but do not distribute raster access URLs.
        summary["candidates"] = [
            {k: v for k, v in r.items() if k != "assets"} for r in candidates
        ]
        atomic_json(ROOT / "docs/africa/KWEEN_RADAR_RUN.json", summary)
    print(
        json.dumps(
            dict(
                run_id=report["run_id"],
                raw_catalog_items=len(items),
                distinct_eligible_passes=len(candidates),
                tracks=len(groups),
                access=probe,
                radar_cogs=0,
                usable_radar_evidence=False,
            ),
            indent=2,
        )
    )
    if probe["status"] in ("access_probe_failed", "unexpected_response"):
        sys.exit(1)


if __name__ == "__main__":
    main()
