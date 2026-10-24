"""Offline checked ASAP regional context for study boxes or declared private fields."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zones", type=Path, required=True, help="Pinned cached Uganda WFS GeoJSON")
    parser.add_argument("--calendar-archive", type=Path, required=True)
    parser.add_argument("--source-config", type=Path, default=ROOT / "configs/uganda_regional_zones.json")
    parser.add_argument("--calendar-config", type=Path, default=ROOT / "configs/uganda_regional_calendar.json")
    parser.add_argument("--year", type=int, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--fields", type=Path)
    modes.add_argument("--study-config", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        from scripts.validate_field_evidence import private_output
        output = private_output(args.out)
        proj = Path(importlib.util.find_spec("rasterio").origin).parent / "proj_data"
        if proj.is_dir(): os.environ["PROJ_DATA"] = os.environ["PROJ_LIB"] = str(proj)
        from shapely.geometry import box, mapping
        from vantage.field_pixels import validate_boundaries
        from vantage.regional_calendar import read_uganda_archive, regional_windows
        from vantage.regional_zones import read_zone_response, validate_zones, resolve_zone
        config_raw = args.source_config.read_bytes()
        config = json.loads(config_raw)
        if config["schema_version"] != "vantage-regional-zone-source-1": raise ValueError("Unsupported zone source")
        if args.zones.stat().st_size > 4_000_000 or args.calendar_archive.stat().st_size > 2_000_000:
            raise ValueError("Source input budget exceeded")
        zone_raw, calendar_raw = args.zones.read_bytes(), args.calendar_archive.read_bytes()
        if hashlib.sha256(zone_raw).hexdigest() != config["response_sha256"]: raise ValueError("Zone source hash mismatch")
        calendar_config = json.loads(args.calendar_config.read_text())
        if calendar_config["schema_version"] != "vantage-regional-calendar-source-1": raise ValueError("Unsupported calendar source")
        if hashlib.sha256(calendar_raw).hexdigest() != calendar_config["archive_sha256"]: raise ValueError("Calendar archive hash mismatch")
        rows = read_uganda_archive(calendar_raw)
        if len(rows) != calendar_config["expected_uganda_rows"]: raise ValueError("Calendar row count mismatch")
        zones = validate_zones(read_zone_response(zone_raw), rows)
        if len(zones) != config["expected_zone_count"]: raise ValueError("Zone snapshot count mismatch")
        # Validate the anchor year even when every spatial match is unresolved.
        regional_windows(rows[0], args.year)
        units_path = args.fields or args.study_config
        units_raw = units_path.read_bytes()
        data = json.loads(units_raw.decode("utf-8-sig"))
        if args.fields:
            units = [dict(unit_id=f["properties"]["field_id"], geometry=f["geometry"],
                          boundary_version=f["properties"]["boundary_version"]) for f in validate_boundaries(data)]
        else:
            if data.get("schema_version") != "uganda-archive-plan-1" or not 1 <= len(data["locations"]) <= 3:
                raise ValueError("Bounded existing study-box plan required")
            units = []
            for location in data["locations"]:
                if not isinstance(location["id"], str) or not location["id"].strip(): raise ValueError("Study unit ID required")
                w,s,e,n = location["bbox"]
                if not all(isinstance(v, (int,float)) and not isinstance(v,bool) for v in (w,s,e,n)) or not w<e or not s<n:
                    raise ValueError("Ordered study bbox required")
                units.append(dict(unit_id=location["id"], geometry=mapping(box(w,s,e,n))))
            if len({u["unit_id"] for u in units}) != len(units): raise ValueError("Unique study units required")
        records = []
        for unit in units:
            match = resolve_zone(unit["geometry"], zones, rows, border_guard_m=config["border_guard_m"])
            contexts = [regional_windows(r, args.year) for r in rows if r["asap1_id"] == match["asap1_id"]]
            records.append(dict(unit_id=unit["unit_id"], scope="declared_field" if args.fields else "analyst_study_box_not_farm",
                                boundary_version=unit.get("boundary_version"), match=match, regional_calendars=contexts))
        result = dict(schema_version="vantage-regional-context-join-1", created_at=datetime.now(timezone.utc).isoformat(),
                      zone_source=config, calendar_source=calendar_config, source_id_coverage="All calendar zone IDs present; not proof of unchanged historical geometries",
                      source_sha256=dict(zones=hashlib.sha256(zone_raw).hexdigest(), calendars=hashlib.sha256(calendar_raw).hexdigest(),
                                         units=hashlib.sha256(units_raw).hexdigest(), config=hashlib.sha256(config_raw).hexdigest()),
                      implementation_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                          ("vantage/regional_zones.py", "vantage/regional_calendar.py", "vantage/field_pixels.py", "scripts/join_regional_context.py")},
                      units=records, field_calendars_confirmed=0, field_priorities_available=False,
                      limitation="Provisional broad-scale context only. No centroid assignment, cross-zone majority vote, field confirmation or imported provider crop-warning outcome.")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
        print([(r["unit_id"], r["match"]["status"], r["match"]["zone_label"]) for r in records])
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f"Regional join failed: {exc}\n")


if __name__ == "__main__": main()
