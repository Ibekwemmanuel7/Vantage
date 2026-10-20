"""Area-level extension evidence, separate from the Texas cotton eligibility model."""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import html
from pathlib import Path
import statistics

from .core import instant, number


def units(config):
    west, south, east, north = config["bbox"]
    if config["grid"] != 2 or not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Demo requires a valid WGS84 box and a two by two grid")
    result = []
    for row in range(2):
        for col in range(2):
            x, xx = west+col*(east-west)/2, west+(col+1)*(east-west)/2
            y, yy = north-(row+1)*(north-south)/2, north-row*(north-south)/2
            result.append(dict(id=f"IG-{row+1}{col+1}", geometry=dict(type="Polygon", coordinates=[[[x,y],[xx,y],[xx,yy],[x,yy],[x,y]]])))
    return result


def assess(data):
    config = data["config"]
    cutoff = instant(config["as_of"])
    target = config["target_year"]
    years = config["reference_years"]
    if len(years) != len(set(years)) or any(y >= target for y in years):
        raise ValueError("Reference years must be unique and earlier than target")
    if target != cutoff.year or config["mode"] != "retrospective_reconstruction_not_operational_replay":
        raise ValueError("This adapter supports retrospective reconstruction only")
    number(config["min_usable_fraction"], 0, 1)
    number(config["freshness_days"], 0, 60)
    number(config["min_reference_years"], 3, len(years))
    number(config["ndvi_change_trigger"], -1, -.001)
    number(config["rain_ratio_trigger"], .001, .999)
    unit_list = units(config)
    known = {u["id"] for u in unit_list}
    seen_observations, seen_rain = set(), set()
    for o in data["observations"]:
        stamp = instant(o["acquired_at"])
        if o["unit_id"] not in known or stamp.year != o["year"]:
            raise ValueError("Invalid observation linkage")
        key = (o["unit_id"], o["source_id"])
        if key in seen_observations:
            raise ValueError("Duplicate observation")
        seen_observations.add(key)
        number(o["usable_fraction"], 0, 1)
        if o["ndvi"] is not None:
            number(o["ndvi"], -1, 1)
    for r in data["rainfall"]:
        number(r["mm"], 0, 10000)
        if r["unit_id"] not in known or r["start"] > r["end"] or int(r["end"][:4]) != r["year"]:
            raise ValueError("Invalid rainfall linkage")
        key = (r["unit_id"], r["year"])
        if key in seen_rain:
            raise ValueError("Duplicate rainfall year cannot inflate reference evidence")
        seen_rain.add(key)
    for unit in unit_list:
        history, dates, coverage = [], [], []
        for year in years+[target]:
            candidates = [o for o in data["observations"] if o["unit_id"] == unit["id"] and o["year"] == year
                          and instant(o["acquired_at"]) <= cutoff
                          and instant(o["acquired_at"]).month == config["month"]
                          and config["window_start_day"] <= instant(o["acquired_at"]).day <= config["window_end_day"]]
            usable = [o for o in candidates if o["ndvi"] is not None and o["usable_fraction"] >= config["min_usable_fraction"] and o["valid_pixels"] >= 100]
            value = statistics.median(o["ndvi"] for o in usable) if usable else None
            history.append(dict(year=year, ndvi=value, usable_dates=len(usable)))
            if year == target:
                dates = sorted(o["acquired_at"] for o in usable)
                coverage = [o["usable_fraction"] for o in usable]
                unit["observations"] = candidates
        current = history[-1]["ndvi"]
        refs = [h["ndvi"] for h in history[:-1] if h["ndvi"] is not None]
        median = statistics.median(refs) if refs else None
        age = (cutoff-instant(dates[-1])).total_seconds()/86400 if dates else None
        veg_state = "insufficient_coverage" if current is None else "stale" if age > config["freshness_days"] else "insufficient_reference" if len(refs) < config["min_reference_years"] else "usable"
        delta = current-median if veg_state == "usable" else None
        veg_flag = bool(delta is not None and delta <= config["ndvi_change_trigger"] and current < min(refs))
        rain = [r for r in data["rainfall"] if r["unit_id"] == unit["id"] and r["year"] == target and instant(r["end"]+"T23:59:59Z") <= cutoff]
        rain_refs = [r["mm"] for r in data["rainfall"] if r["unit_id"] == unit["id"] and r["year"] in years
                     and any(r["start"][5:] == t["start"][5:] and r["end"][5:] == t["end"][5:] for t in rain)]
        rain_current = rain[0]["mm"] if len(rain) == 1 else None
        rain_med = statistics.median(rain_refs) if rain_refs else None
        rain_age = (cutoff-instant(rain[0]["end"]+"T23:59:59Z")).total_seconds()/86400 if len(rain) == 1 else None
        rain_state = "missing" if rain_current is None else "stale" if rain_age > config["freshness_days"] else "insufficient_reference" if len(rain_refs) < config["min_reference_years"] or rain_med == 0 else "usable"
        rain_ratio = rain_current/rain_med if rain_state == "usable" else None
        rain_flag = bool(rain_ratio is not None and rain_ratio <= config["rain_ratio_trigger"] and rain_current < min(rain_refs))
        reasons = []
        if veg_flag:
            reasons.append(f"NDVI {delta:+.3f} below seasonal median and below every usable reference year.")
        if rain_flag:
            reasons.append(f"Five-day rainfall {rain_current:.1f} mm is {rain_ratio:.1%} of reference median and below every reference year.")
        status = "review" if reasons else "no_unusual_change" if veg_state == rain_state == "usable" else "insufficient_evidence"
        unit.update(status=status, reasons=reasons, vegetation_state=veg_state, rainfall_state=rain_state,
             ndvi=current, ndvi_reference=median, ndvi_delta=delta, reference_year_count=len(refs),
             trajectory=history, observation_dates=dates, age_days=age,
             median_usable_fraction=statistics.median(coverage) if coverage else None,
             rainfall_mm=rain_current, rainfall_reference_mm=rain_med, rainfall_ratio=rain_ratio,
             rainfall_age_days=rain_age, rainfall_start=rain[0]["start"] if rain else None,
             rainfall_end=rain[0]["end"] if rain else None,
             question="Which crops and growth stages are present here, and do field checks confirm unusual canopy development or recent rainfall conditions?",
             unknowns="Current maize locations, planting dates, causes, management, yield effects and field outcomes are unconfirmed.")
    unit_list.sort(key=lambda u: (u["status"] != "review", u["id"]))
    manifest = dict(schema_version="area-evidence-1", producer="Vantage", code_version="0.2.0-area-prototype", config=config, units=unit_list,
                    lineage=data["lineage"], failures=data.get("failures", []), retrieved_at=data["retrieved_at"],
                    limitation="Retrospective public-data reconstruction. No customer results, diagnosis, prescription or independent performance validation. Historical cropland mask is not current maize location.")
    manifest["brief_id"] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    return manifest


def geojson(result):
    return dict(type="FeatureCollection", features=[dict(type="Feature", id=u["id"], geometry=u["geometry"],
                properties={k:v for k,v in u.items() if k not in ("geometry", "observations", "trajectory")}) for u in result["units"]])


def csv_text(result):
    stream = io.StringIO(newline="")
    keys = ["id", "status", "vegetation_state", "rainfall_state", "ndvi", "ndvi_reference", "ndvi_delta", "reference_year_count", "age_days", "median_usable_fraction", "rainfall_mm", "rainfall_reference_mm", "question"]
    writer = csv.DictWriter(stream, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(result["units"])
    return stream.getvalue()


def export_bundle(result, destination):
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=True)
    (path/"uganda.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    (path/"uganda.geojson").write_text(json.dumps(geojson(result), indent=2, allow_nan=False), encoding="utf-8")
    (path/"uganda.csv").write_text(csv_text(result), encoding="utf-8")
    (path/"weekly-brief.html").write_text(printable(result), encoding="utf-8")


def printable(result):
    esc = html.escape
    articles = []
    for u in result["units"]:
        def fmt(value):
            return "unavailable" if value is None else f"{value:.3f}"
        articles.append(f'<article><h2>{esc(u["id"])} · {esc(u["status"].replace("_", " "))}</h2>'
          f'<p>{esc(" ".join(u["reasons"]) or "No screening flag. Check evidence states before interpretation.")}</p>'
          f'<p>Vegetation: {esc(u["vegetation_state"])}; NDVI {fmt(u["ndvi"])}; reference {fmt(u["ndvi_reference"])}; usable reference years {u["reference_year_count"]}. '
          f'Rainfall: {esc(u["rainfall_state"])}; {fmt(u["rainfall_mm"])} mm; reference {fmt(u["rainfall_reference_mm"])} mm.</p>'
          f'<p>Accepted vegetation dates: {esc(", ".join(u["observation_dates"]) or "none")}. Latest age: {fmt(u["age_days"])} days. '
          f'Rainfall interval: {esc(str(u["rainfall_start"]))} to {esc(str(u["rainfall_end"]))}.</p>'
          f'<p><strong>Field question:</strong> {esc(u["question"])}</p><p>{esc(u["unknowns"])}</p></article>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
      '<title>Vantage weekly evidence brief</title><style>body{font:14px/1.5 system-ui;max-width:900px;padding:20px;margin:auto;color:#203d31}h1,h2{font-family:Georgia,serif}h2{font-size:20px}article{border-top:1px solid #bbb;padding:10px 0;break-inside:avoid}p{margin:8px 0}@media print{body{font-size:10pt;padding:0}a{color:inherit}}</style>'
      '<h1>Vantage · Weekly agricultural evidence brief</h1>'
      f'<p><strong>Retrospective reconstruction · {esc(result["config"]["title"])} · cutoff {esc(result["config"]["as_of"])}</strong></p>'
      f'<p>Brief {esc(result["brief_id"])}. {esc(result["config"]["boundary_status"])}</p>'
      '<p>Four area-level review units, approximately 5.5 km per side; not individual farms. Sentinel-2 L2A vegetation: May 1–15, 2024. CHIRPS v3 final rainfall: May 11–15, 2024. Reference: matching windows in 2020–2023, at least three usable years. Historical WorldCover 2021 cropland mask; no confirmed current maize mapping.</p>'
      '<p>Development rules: NDVI at least 0.10 below reference median and below every usable reference year; rainfall at most 70% of reference median and below every reference year. No calibrated risk or confidence estimate. Vegetation needs 60% usable coverage, 100 valid pixels and age at most 14 days.</p>'
      +''.join(articles)+f'<p>{esc(result["limitation"])}</p>'
      '<p>No IDEA affiliation, approval or engagement is implied. Satellite anomalies do not diagnose causes or justify treatments.</p>'
      '<p>Sources: Copernicus Sentinel-2 via Microsoft Planetary Computer; ESA WorldCover 2021 v200 (CC BY 4.0); UCSB Climate Hazards Center CHIRPS v3 (public domain). Full source IDs, dates, quality and provenance: <a href="uganda.json">evidence JSON</a>. <a href="uganda.csv">CSV</a> · <a href="uganda.geojson">GeoJSON</a>.</p>'
      '<p>Independent product within <a href="https://github.com/Ibekwemmanuel7/Lillie_US">Lillie US</a>. Expert and field interpretation still required.</p></html>')
