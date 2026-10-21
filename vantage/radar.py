"""Radar catalog feasibility: geometric coverage and orbit-aware temporal matching."""

from datetime import date
import math
from shapely.geometry import box, shape
from vantage.event_series import utc_time


def catalog_candidates(items, plan):
    target = box(*plan["bbox"])
    accepted, excluded = [], []
    for item in items:
        reasons = []
        props = item.get("properties", {})
        try:
            stamp = utc_time(props["datetime"])
            if not date.fromisoformat(
                plan["start"]
            ) <= stamp.date() <= date.fromisoformat(plan["end"]) or stamp > utc_time(
                plan["as_of"]
            ):
                reasons.append("outside_fixed_interval")
        except (KeyError, TypeError, ValueError):
            reasons.append("invalid_acquisition_time")
        try:
            geometry = shape(item["geometry"])
            if (
                not geometry.is_valid
                or geometry.is_empty
                or not geometry.covers(target)
            ):
                reasons.append("footprint_does_not_cover_box")
        except (KeyError, TypeError, ValueError):
            reasons.append("invalid_footprint")
        if props.get("sar:instrument_mode") != plan["mode"]:
            reasons.append("unsupported_instrument_mode")
        if not set(plan["polarizations"]).issubset(
            props.get("sar:polarizations", [])
        ) or not all(
            p.lower() in item.get("assets", {}) for p in plan["polarizations"]
        ):
            reasons.append("missing_dual_polarization")
        platform = props.get("platform")
        relative = props.get("sat:relative_orbit")
        absolute = props.get("sat:absolute_orbit")
        direction = props.get("sat:orbit_state")
        if (
            platform not in ("SENTINEL-1A", "SENTINEL-1B", "SENTINEL-1C")
            or type(relative) is not int
            or not 1 <= relative <= 175
            or type(absolute) is not int
            or absolute < 1
            or direction not in ("ascending", "descending")
        ):
            reasons.append("incomplete_orbit_identity")
        if item.get("collection") != plan["collection"]:
            reasons.append("wrong_collection")
        if reasons:
            excluded.append(dict(item_id=item.get("id"), reasons=reasons))
            continue
        track = f"{platform}-{relative:03}-{direction}-{plan['mode']}-VV-VH"
        accepted.append(
            dict(
                item_id=item["id"],
                acquired_at=props["datetime"],
                platform=platform,
                relative_orbit=relative,
                absolute_orbit=absolute,
                direction=direction,
                track_id=track,
                product=plan["collection"],
                assets={
                    p.lower(): item["assets"][p.lower()]["href"]
                    for p in plan["polarizations"]
                },
            )
        )
    # Adjacent slices or alternate versions from one orbital pass are not independent visits.
    accepted.sort(key=lambda r: (utc_time(r["acquired_at"]), r["item_id"]))
    seen, unique = set(), []
    for row in accepted:
        key = (row["platform"], row["absolute_orbit"])
        if key in seen:
            excluded.append(
                dict(item_id=row["item_id"], reasons=["duplicate_orbital_pass"])
            )
        else:
            seen.add(key)
            unique.append(row)
    return unique, excluded


def track_coverage(candidates, optical_rows, as_of, max_age_days):
    if not math.isfinite(max_age_days) or max_age_days <= 0:
        raise ValueError("Positive research freshness policy required")
    cutoff = utc_time(as_of)
    if any(utc_time(row["acquired_at"]) > cutoff for row in candidates):
        raise ValueError("Future radar catalog acquisitions rejected")
    tracks = {}
    for row in candidates:
        tracks.setdefault(row["track_id"], []).append(row)
    summaries = []
    for track, rows in sorted(tracks.items()):
        rows = sorted(rows, key=lambda r: utc_time(r["acquired_at"]))
        last = rows[-1]
        age = (cutoff - utc_time(last["acquired_at"])).total_seconds() / 86400
        matches = []
        for optical in optical_rows:
            if optical["status"] == "processed" and optical["coverage_qualified"]:
                continue
            when = utc_time(optical["acquired_at"])
            if when > cutoff:
                raise ValueError("Future optical acquisition rejected")
            prior = [r for r in rows if utc_time(r["acquired_at"]) <= when]
            radar = prior[-1] if prior else None
            lag = (
                (when - utc_time(radar["acquired_at"])).total_seconds() / 86400
                if radar
                else None
            )
            matches.append(
                dict(
                    optical_acquired_at=optical["acquired_at"],
                    prior_radar_item_id=radar["item_id"] if radar else None,
                    prior_radar_acquired_at=radar["acquired_at"] if radar else None,
                    lag_days=lag,
                    catalog_match_within_age_window=lag is not None
                    and lag <= max_age_days,
                    measured_radar_coverage=None,
                    usable_radar_evidence=False,
                )
            )
        summaries.append(
            dict(
                track_id=track,
                catalog_passes=len(rows),
                latest_catalog_acquisition=last["acquired_at"],
                latest_catalog_age_days=age,
                catalog_fresh_at_cutoff=age <= max_age_days,
                optical_gap_matches=matches,
                usable_radar_evidence=False,
            )
        )
    return summaries
