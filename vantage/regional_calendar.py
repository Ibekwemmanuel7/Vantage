"""Regional calendar priors; never independently confirmed field calendars."""
import calendar
import csv
from datetime import date
import io
import zipfile


MARKERS = ("sos_s", "sos_e", "eos_s", "eos_e")
COLUMNS = {"asap0_id", "name0_shr", "asap1_id", "name1_shr", "crop_name", *MARKERS}


def read_uganda_archive(raw):
    if len(raw) > 2_000_000:
        raise ValueError("Calendar ZIP exceeds two MB budget")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        matches = [m for m in archive.infolist() if m.filename == "crop_calendar_gaul1.csv"]
        if len(matches) != 1 or matches[0].file_size > 2_000_000:
            raise ValueError("One bounded crop_calendar_gaul1.csv member required")
        text = archive.read(matches[0]).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames or set(reader.fieldnames) != COLUMNS or len(reader.fieldnames) != len(COLUMNS):
        raise ValueError("Unexpected source calendar columns")
    rows = []
    seen = set()
    for index, row in enumerate(reader):
        if index >= 10000 or None in row or any(v is None for v in row.values()):
            raise ValueError("Malformed or oversized calendar table")
        if row["name0_shr"].strip().casefold() != "uganda":
            continue
        if row["asap0_id"] != "209" or not row["asap1_id"].isdigit():
            raise ValueError("Unexpected Uganda administrative identifiers")
        if not row["name1_shr"].strip() or not row["crop_name"].strip():
            raise ValueError("Missing zone or crop label")
        key = (row["asap1_id"], row["crop_name"])
        if key in seen:
            raise ValueError("Duplicate regional crop/season row")
        seen.add(key)
        for marker in MARKERS:
            if not row[marker].isdigit() or not 1 <= int(row[marker]) <= 36:
                raise ValueError("Calendar dekads must be integers 1-36")
        rows.append(dict(row, source_markers={m: int(row[m]) for m in MARKERS}))
    if not rows:
        raise ValueError("No Uganda calendar rows")
    return sorted(rows, key=lambda r: (int(r["asap1_id"]), r["crop_name"]))


def _dekad_date(anchor_year, absolute_dekad, *, end=False):
    year = anchor_year + (absolute_dekad - 1) // 36
    local = (absolute_dekad - 1) % 36
    month, third = local // 3 + 1, local % 3
    day = (10, 20, calendar.monthrange(year, month)[1])[third] if end else (1, 11, 21)[third]
    return date(year, month, day).isoformat()


def regional_windows(row, planting_year):
    if type(planting_year) is not int or not 1900 <= planting_year <= 2099:
        raise ValueError("Planting anchor year must be an integer 1900-2099")
    markers = row["source_markers"]
    absolute = []
    for key in MARKERS:
        value = markers[key]
        if type(value) is not int or not 1 <= value <= 36:
            raise ValueError("Invalid dekad marker")
        while absolute and value < absolute[-1]:
            value += 36
        absolute.append(value)
    if absolute[-1] - absolute[0] >= 36:
        raise ValueError("Calendar spans a full year or multiple wraps; manual review required")
    phases = {}
    for name, start, end in (("planting", 0, 1), ("growing", 1, 2), ("harvesting", 2, 3)):
        phases[name] = dict(start=_dekad_date(planting_year, absolute[start]),
                            end=_dekad_date(planting_year, absolute[end], end=True))
    return dict(asap0_id=row["asap0_id"], asap1_id=row["asap1_id"], zone_label=row["name1_shr"],
                crop_season_label=row["crop_name"], source_dekads=dict(markers), planting_anchor_year=planting_year,
                crosses_calendar_year=absolute[-1] > 36, windows=phases,
                confirmation_kind="regional_prior", field_calendar_confirmed=False, crop_identity_confirmed=False,
                field_priorities_available=False,
                interpretation="Recurring regional context anchored to a chosen year, not observed field dates or a forecast. Boundary dekads overlap across phase windows.")


def select_context(rows, zone_id, crop_season_label, planting_year):
    matches = [r for r in rows if r["asap1_id"] == zone_id and r["crop_name"] == crop_season_label]
    if len(matches) != 1:
        return dict(status="unavailable", reason="no_unique_exact_zone_and_crop_season_match",
                    field_calendar_confirmed=False, field_priorities_available=False)
    return dict(status="regional_context_only", **regional_windows(matches[0], planting_year))
