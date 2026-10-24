"""Import a pinned cached JRC Uganda calendar archive as regional context, offline."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vantage.regional_calendar import read_uganda_archive, regional_windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/uganda_regional_calendar.json")
    parser.add_argument("--year", type=int, required=True, help="Planting anchor year, not observed event dates")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = args.out.resolve()
        if not output.is_relative_to((ROOT / "outputs").resolve()):
            raise ValueError("Calendar context output must stay beneath outputs")
        if args.archive.stat().st_size > 2_000_000:
            raise ValueError("Calendar archive exceeds two MB budget")
        config_raw, archive = args.config.read_bytes(), args.archive.read_bytes()
        config = json.loads(config_raw.decode("utf-8-sig"))
        if config["schema_version"] != "vantage-regional-calendar-source-1":
            raise ValueError("Unsupported calendar source contract")
        if hashlib.sha256(archive).hexdigest() != config["archive_sha256"]:
            raise ValueError("Source archive checksum differs from pinned reference")
        rows = read_uganda_archive(archive)
        if len(rows) != config["expected_uganda_rows"] or len({r["asap1_id"] for r in rows}) != config["expected_zone_ids"]:
            raise ValueError("Source row/zone counts differ from reviewed snapshot")
        contexts = [regional_windows(r, args.year) for r in rows]
        result = dict(schema_version="vantage-regional-calendars-1", created_at=datetime.now(timezone.utc).isoformat(),
                      source=config, config_sha256=hashlib.sha256(config_raw).hexdigest(),
                      implementation_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                          for name in ("vantage/regional_calendar.py", "scripts/import_regional_calendars.py")},
                      row_count=len(contexts), zone_count=len({r["asap1_id"] for r in rows}), contexts=contexts,
                      field_calendars_confirmed=0, field_priorities_available=False,
                      limitations=["ASAP zone geometry must be version-matched before any field/district spatial join; no geography is inferred from names.",
                                   "The chosen anchor year instantiates recurring source windows, not actual planting/harvest observations.",
                                   "Source observed in October 2026; historical operational availability is not established.",
                                   "No current farmer consent, confirmed crop identity, training label or agronomic recommendation is created."])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print(f"Imported {len(contexts)} Uganda regional contexts in {result['zone_count']} zones; zero field calendars confirmed.")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f"Calendar import failed: {exc}\n")


if __name__ == "__main__":
    main()
