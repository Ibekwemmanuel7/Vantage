"""Rebuild the public study-only calendar snapshot from pinned public sources."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build(zones_raw, calendar_raw):
    proj = Path(importlib.util.find_spec('rasterio').origin).parent / 'proj_data'
    os.environ['PROJ_DATA'] = os.environ['PROJ_LIB'] = str(proj)
    from shapely.geometry import box, mapping
    from vantage.regional_calendar import read_uganda_archive, regional_windows
    from vantage.regional_zones import read_zone_response, validate_zones, resolve_zone
    zone_config = json.loads((ROOT/'configs/uganda_regional_zones.json').read_text())
    calendar_config = json.loads((ROOT/'configs/uganda_regional_calendar.json').read_text())
    for raw, expected in ((zones_raw, zone_config['response_sha256']),
                          (calendar_raw, calendar_config['archive_sha256'])):
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Pinned public source hash mismatch')
    rows = read_uganda_archive(calendar_raw)
    zones = validate_zones(read_zone_response(zones_raw), rows)
    # Fixed public analyst boxes only. Never read private field/join packets.
    studies = [('Iganga', [33.40, .65, 33.50, .75]),
               ('Lira', [32.85, 2.20, 32.95, 2.30]),
               ('Kasese', [30.05, .15, 30.15, .25])]
    units = []
    for label, bounds in studies:
        match = resolve_zone(mapping(box(*bounds)), zones, rows, border_guard_m=1000)
        if match['status'] != 'regional_zone_context':
            raise ValueError('Public study zone unresolved')
        units.append(dict(label=label, bbox=bounds, zone_label=match['zone_label'],
                          zone_id=match['asap1_id'], calendars=[regional_windows(r, 2024)
                          for r in rows if r['asap1_id'] == match['asap1_id']]))
    return dict(schema_version='vantage-public-regional-context-1', anchor_year=2024,
                source_observed_on=calendar_config['source_observed_on'],
                field_priorities_available=False, field_calendars_confirmed=0,
                sources=[zone_config, calendar_config], units=units)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zones', type=Path, required=True)
    parser.add_argument('--calendar-archive', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.zones.read_bytes(), args.calendar_archive.read_bytes())
    (ROOT/'web/data/regional-context.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
