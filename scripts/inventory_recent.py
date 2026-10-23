"""Archive/replay bounded recent Uganda Sentinel-2 catalog searches; no pixels."""
import argparse
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vantage.archive import fingerprint
from vantage.recent_inventory import recent_window, summarize_recent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="Explicit UTC cutoff, e.g. 2026-10-23T00:00:00Z")
    parser.add_argument("--days", type=int, default=21)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--location", choices=["iganga-study", "lira-study", "kasese-study"],
                        help="Restrict acquisition to one existing study box")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/africa/recent")
    args = parser.parse_args()
    cutoff = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
    if cutoff.tzinfo is None or cutoff > datetime.now(timezone.utc):
        parser.error("Cutoff must be timezone-aware and not in the future")
    config = json.loads((ROOT / "configs/uganda_archive.json").read_text())
    plan = [recent_window(config, location, cutoff, args.days) for location in config["locations"]
            if args.location is None or location["id"] == args.location]
    directory = args.out / fingerprint(dict(plan=plan, collection=config["collection"]))[:20]
    directory.mkdir(parents=True, exist_ok=True)
    records, failures = [], []
    for window in plan:
        path = directory / (window["location_id"] + ".stac.json")
        try:
            if path.exists():
                archive = json.loads(path.read_text())
            else:
                if not args.online:
                    raise FileNotFoundError("Archived response missing")
                url = "https://planetarycomputer.microsoft.com/api/stac/v1/search?" + urlencode(dict(
                    collections=config["collection"], bbox=",".join(map(str, window["bbox"])),
                    datetime=window["interval"], limit=100))
                with urlopen(Request(url, headers={"User-Agent": "Vantage-research/0.3"}), timeout=30) as response:
                    data = json.load(response)
                archive = dict(retrieved_at=datetime.now(timezone.utc).isoformat(), request_url=url, response=data)
                summarize_recent(window, data, config, archive["retrieved_at"])
                with path.open("x", encoding="utf-8") as stream:
                    json.dump(archive, stream, allow_nan=False)
            record = summarize_recent(window, archive["response"], config, archive["retrieved_at"])
            record["archive_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            records.append(record)
            print(f"{window['location_id']}: {record['item_count']} catalog items; usable pixels not assessed", flush=True)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append(dict(location_id=window["location_id"], error_type=type(error).__name__))
    report = dict(schema_version="recent-inventory-1", decision_cutoff=args.as_of,
                  catalog_complete=len(records) == len(plan), locations=records, failures=failures,
                  boundary_status=config["boundary_status"], pixel_observations_processed=0,
                  limitation="No confirmed crops, usable pixel coverage, crop condition or field priorities inferred")
    (directory / "inventory.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Report: {directory / 'inventory.json'}", flush=True)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
