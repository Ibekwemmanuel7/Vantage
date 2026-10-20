"""Bounded Uganda catalog planning; catalog cloud estimates are not pixel quality."""
import calendar
import hashlib
import json
import math


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def windows(config):
    locations=config["locations"]
    if not locations or len({x["id"] for x in locations}) != len(locations):
        raise ValueError("Unique study location IDs required")
    if len(set(config["years"])) != len(config["years"]) or len(set(config["months"])) != len(config["months"]):
        raise ValueError("Duplicate years or months")
    for location in locations:
        w,s,e,n=location["bbox"]
        if not all(math.isfinite(x) for x in (w,s,e,n)) or not (29<=w<e<=35.1 and -1.6<=s<n<=4.3):
            raise ValueError("Study box outside bounded Uganda research envelope")
        if e-w>.2 or n-s>.2:
            raise ValueError("Study box exceeds bounded pixel budget")
        for year in sorted(config["years"]):
            if type(year) is not int or not 2017<=year<=2025:
                raise ValueError("Use completed supported historical years")
            for month in sorted(config["months"]):
                last=calendar.monthrange(year,month)[1]
                yield dict(location_id=location["id"], bbox=location["bbox"],year=year,month=month,
                    interval=f"{year}-{month:02}-01T00:00:00Z/{year}-{month:02}-{last:02}T23:59:59Z")


def summarize_window(window, response, config):
    if any(link.get("rel")=="next" for link in response.get("links",[])):
        raise ValueError("Truncated search: narrow interval before processing")
    seen=set(); candidates=[]
    w,s,e,n=window["bbox"]
    for item in response["features"]:
        if item["id"] in seen:
            raise ValueError("Duplicate catalog item")
        seen.add(item["id"])
        a,b,c,d=item["bbox"][:4]
        assets=item["assets"]
        cloud=item["properties"].get("eo:cloud_cover")
        candidates.append(dict(id=item["id"], acquired_at=item["properties"]["datetime"],
            scene_cloud_cover=cloud,
            bbox_covers_study=a<=w and b<=s and c>=e and d>=n,
            baseline_assets_present=all(k in assets for k in config["required_baseline_assets"]),
            multispectral_assets_present=all(k in assets for k in config["candidate_multispectral_assets"])))
    eligible=[x for x in candidates if x["bbox_covers_study"] and x["baseline_assets_present"]]
    selected=min(eligible,key=lambda x:(x["scene_cloud_cover"] if x["scene_cloud_cover"] is not None else 101,x["id"])) if eligible else None
    return dict(**window, item_count=len(candidates), acquisition_dates=sorted({x["acquired_at"][:10] for x in candidates}),
        candidate=selected, candidates=candidates, response_sha256=fingerprint(response),
        pixel_status="not_processed", usable_fraction=None,
        limitation="Lowest scene-cloud candidate is a processing choice, not crop coverage or a representative sample. Bounding boxes do not prove valid pixels.")
