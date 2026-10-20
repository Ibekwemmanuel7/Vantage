"""Archive a bounded STAC inventory, not an anomaly analysis or validation.

Run from the repository: python experiments/inventory.py --out outputs/plainview-inventory.json
No pixels are downloaded. Scene cloud cover is not field usable coverage.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode


def inventory(case):
    payload = dict(collections=[case["collection"]], bbox=case["aoi_bbox_wgs84"],
                   datetime=case["pre_window"].split("/")[0]+"/"+case["post_window"].split("/")[1], limit=1000)
    # STAC GET uses comma-delimited collections and bbox rather than JSON arrays.
    url = case["catalog"]+"?"+urlencode(dict(collections=case["collection"],
          bbox=",".join(map(str, case["aoi_bbox_wgs84"])), datetime=payload["datetime"], limit=1000))
    request = Request(url, headers={"User-Agent": "Vantage-research/0.1"})
    with urlopen(request, timeout=60) as response:
        raw = response.read()
    result = json.loads(raw)
    features = result["features"]
    summary = [dict(id=f["id"], acquired_at=f["properties"].get("datetime"),
                    scene_cloud_cover=f["properties"].get("eo:cloud_cover"),
                    required_assets_present=all(a in f["assets"] for a in case["required_assets"])) for f in features]
    return dict(case_id=case["case_id"], retrieved_at=datetime.now(timezone.utc).isoformat(),
                request_url=url, raw_sha256=hashlib.sha256(raw).hexdigest(),
                complete=not any(link.get("rel") == "next" for link in result.get("links", [])),
                status="catalog_inventory_only_not_pixel_analysis", summary=summary, stac_response=result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=Path(__file__).with_name("plainview_hail_2023.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(json.loads(args.case.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"items": len(result["summary"]), "complete": result["complete"], "status": result["status"]}))
