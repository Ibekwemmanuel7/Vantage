"""Small, deterministic evidence pipeline; imported values are not imagery diagnoses."""
from datetime import datetime, timezone
import math
import statistics

VERSION = "0.1.0"


def instant(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamps require timezone")
    return dt.astimezone(timezone.utc)


def number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("invalid numeric value")


def ring(geometry):
    # Deliberately bounded import contract: simple axis-aligned rectangles only.
    # Real field polygons require a topology-aware GIS adapter before import.
    if geometry.get("type") != "Polygon" or len(geometry.get("coordinates", [])) != 1:
        raise ValueError("prototype requires rectangular Polygon without holes")
    points = geometry["coordinates"][0]
    if len(points) != 5 or points[0] != points[-1]:
        raise ValueError("closed rectangle required")
    for x, y in points:
        number(x, -180, 180)
        number(y, -90, 90)
    xs, ys = sorted(set(p[0] for p in points)), sorted(set(p[1] for p in points))
    if len(xs) != 2 or len(ys) != 2 or len(set(map(tuple, points[:4]))) != 4:
        raise ValueError("nondegenerate rectangle required")
    for a, b in zip(points, points[1:]):
        if (a[0] == b[0]) == (a[1] == b[1]):
            raise ValueError("rectangle edges must not cross")
    return xs[0], ys[0], xs[1], ys[1]


def validate(data):
    if data["schema_version"] != "1" or not data["tenant_id"]:
        raise ValueError("schema 1 and tenant required")
    fields, zones, observation_ids = {}, {}, set()
    for f in data["fields"]:
        if f["id"] in fields or not f["boundary_version"] or not f["consent_ref"]:
            raise ValueError("duplicate field or missing boundary/consent reference")
        instant(f["planting_at"])
        fields[f["id"]] = f
        ring(f["geometry"])
    for z in data["zones"]:
        if z["id"] in zones:
            raise ValueError("duplicate zone")
        parent = fields[z["field_id"]]
        a, b, c, d = ring(parent["geometry"])
        x, y, xx, yy = ring(z["geometry"])
        if not (a <= x < xx <= c and b <= y < yy <= d):
            raise ValueError("zone outside field")
        zones[z["id"]] = z
    for o in data["observations"]:
        z = zones[o["zone_id"]]
        if o["id"] in observation_ids or o["boundary_version"] != fields[z["field_id"]]["boundary_version"]:
            raise ValueError("duplicate observation or boundary mismatch")
        observation_ids.add(o["id"])
        number(o["ndvi"], -1, 1)
        number(o["usable_fraction"], 0, 1)
        if instant(o["processed_at"]) < instant(o["acquired_at"]) or not o["source_id"]:
            raise ValueError("invalid provenance")
    return fields, zones


def brief(data, as_of, freshness_days=5, min_coverage=0.8, threshold=0.1):
    fields, zones = validate(data)
    now = instant(as_of)
    number(freshness_days, 0, 30)
    number(min_coverage, 0, 1)
    number(threshold, 0.001, 2)
    rows = []
    for zid, z in zones.items():
        f = fields[z["field_id"]]
        eligible = (f["county"] in ("Hale", "Floyd") and f["state"] == "TX"
                    and f["crop"] == "upland_cotton" and f["irrigation"] == "centre_pivot"
                    and f["records_confirmed"] is True and f["stage_eligible"] is True
                    and f["due_for_scouting"] is True and instant(f["planting_at"]) <= now)
        obs = sorted((o for o in data["observations"] if o["zone_id"] == zid
                      and instant(o["acquired_at"]) <= now and instant(o["processed_at"]) <= now),
                     key=lambda o: (instant(o["acquired_at"]), o["id"]))
        usable = [o for o in obs if o["usable_fraction"] >= min_coverage]
        latest = usable[-1] if usable else None
        age = (now - instant(latest["acquired_at"])).total_seconds()/86400 if latest else None
        status = "ineligible" if not eligible else "missing" if not obs else "low_quality" if not latest else "stale" if age > freshness_days else "insufficient_history"
        previous = next((o for o in reversed(usable[:-1]) if 0 < (instant(latest["acquired_at"]) - instant(o["acquired_at"])).total_seconds()/86400 <= 30), None) if latest else None
        delta = latest["ndvi"] - previous["ndvi"] if previous else None
        rows.append(dict(zone_id=zid, field_id=z["field_id"], status=status,
                         latest=latest, latest_seen=obs[-1] if obs else None,
                         previous=previous, age_days=age, delta=delta,
                         geometry=z["geometry"], management_context=f["management_context"], score=None))
    # Compare changes only across zones with exactly the same acquisition pair.
    for row in rows:
        if row["status"] != "insufficient_history" or row["previous"] is None:
            continue
        peers = [r["delta"] for r in rows if r["field_id"] == row["field_id"] and r["previous"]
                 and r["status"] == "insufficient_history"
                 and r["latest"]["acquired_at"] == row["latest"]["acquired_at"]
                 and r["previous"]["acquired_at"] == row["previous"]["acquired_at"]]
        if len(peers) >= 3:
            row["peer_median_delta"] = statistics.median(peers)
            row["score"] = max(0, row["peer_median_delta"] - row["delta"])
    for row in rows:
        if row["score"] is not None:
            row["status"] = "inspect" if row["score"] >= threshold else "no_relative_flag"
        row["explanation"] = "Relative NDVI change deficit versus same-field median; inspect to establish meaning." if row["score"] is not None else "Evidence gate failed; continue routine scouting."
    rows.sort(key=lambda r: (r["status"] != "inspect", -(r["score"] or 0), r["field_id"], r["zone_id"]))
    return dict(schema_version="1", producer="Vantage", code_version=VERSION, tenant_id=data["tenant_id"],
                as_of=as_of, processed_at=datetime.now(timezone.utc).isoformat(),
                policy=dict(freshness_days=freshness_days, min_coverage=min_coverage, threshold=threshold, max_pair_gap_days=30, min_peer_zones=3),
                limitations="Experimental scouting evidence. No diagnosis or irrigation prescription. No flag is not a healthy assessment. Common field-wide changes may be missed. Synthetic demo is not validation.",
                fields=list(fields.values()), zones=rows)
