"""Process a bounded sequence of latest eligible scenes per Uganda study box."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vantage.recent_pixels import select_sequence, observation_quality, summarize_sequence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--online", action="store_true", help="Permit bounded metadata and raster reads")
    parser.add_argument("--scenes-per-location", type=int, choices=range(1,7), default=1)
    args = parser.parse_args()
    if not args.online:
        parser.error("Pixel acquisition requires explicit --online")
    inventory = json.loads(args.inventory.read_text())
    if inventory["schema_version"] != "recent-inventory-1" or not inventory["catalog_complete"]:
        parser.error("Complete recent inventory required")
    if not 1 <= len(inventory["locations"]) <= 3:
        parser.error("Bounded budget is one to three locations")
    from expand_uganda_archive import process_pixels
    import build_uganda_demo as source
    from vantage.planetary import ContainerSigner
    source.CACHE.mkdir(parents=True, exist_ok=True)
    source.signed = ContainerSigner(source.SESSION)
    directory = args.inventory.parent / "pixels"
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    tasks = [(record, candidate) for record in inventory["locations"]
             for candidate in (select_sequence(record, args.scenes_per_location) or [None])]
    for record, candidate in tasks:
        result = dict(location_id=record["location_id"], status="failed")
        try:
            archive_path = args.inventory.parent / (record["location_id"] + ".stac.json")
            if hashlib.sha256(archive_path.read_bytes()).hexdigest() != record["archive_sha256"]:
                raise ValueError("Catalog archive checksum mismatch")
            if candidate is None:
                result["status"] = "no_eligible_scene"
            else:
                archive = json.loads(archive_path.read_text())
                item = next(i for i in archive["response"]["features"] if i["id"] == candidate["id"])
                if item["properties"]["datetime"] != candidate["acquired_at"]:
                    raise ValueError("Acquisition differs from inventory")
                metrics = process_pixels(item, record, directory)
                result.update(status="processed", scene_id=item["id"],
                              acquired_at=candidate["acquired_at"], metrics=metrics,
                              quality=observation_quality(metrics, candidate["acquired_at"], inventory["decision_cutoff"]))
        except Exception as error:
            # Signed URLs can be present in provider/GDAL exception text.
            result["error_type"] = type(error).__name__
        results.append(result)
        print(f"{result['location_id']}: {result['status']} {result.get('quality', {}).get('state', '')}", flush=True)
    report = dict(schema_version="recent-pixels-1", processed_at=datetime.now(timezone.utc).isoformat(),
                  inventory_sha256=hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
                  decision_cutoff=inventory["decision_cutoff"], observations=results,
                  independent_field_outcomes=0, field_priorities_available=False,
                  selection=f"Latest {args.scenes_per_location} eligible acquisitions per box; no scene-cloud ranking",
                  series_summary=summarize_sequence(results),
                  limitation="Whole-box NDVI research, not crop health diagnosis, field ranking or yield prediction")
    path = directory / ("observations.json" if args.scenes_per_location == 1 else "sequence-observations.json")
    path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Report: {path}", flush=True)
    if any(r["status"] == "failed" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
