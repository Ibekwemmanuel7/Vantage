"""Archive Sentinel-1 RTC availability at optical sequence times; no fusion."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vantage.archive import fingerprint
from vantage.gap_radar import radar_plan,optical_matching_rows
from vantage.radar import catalog_candidates,track_coverage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence",type=Path,nargs="+",required=True)
    parser.add_argument("--online",action="store_true")
    args=parser.parse_args()
    if len(args.sequence)>5:parser.error("At most five sequence windows")
    outputs=[]
    failures=[]
    for path in args.sequence:
        try:
            sequence=json.loads(path.read_text())
            inventory_path=path.parent.parent/"inventory.json"
            if hashlib.sha256(inventory_path.read_bytes()).hexdigest()!=sequence["inventory_sha256"]:
                raise ValueError("Optical inventory checksum differs")
            inventory=json.loads(inventory_path.read_text())
            if len(inventory["locations"])!=1:raise ValueError("Use single-location sequence windows")
            location=inventory["locations"][0]
            if any(r["location_id"]!=location["location_id"] for r in sequence["observations"]):
                raise ValueError("Sequence location differs")
            plan=radar_plan(sequence,location["bbox"])
            root=ROOT/"outputs/africa/gap-radar"/fingerprint(plan)[:20]
            root.mkdir(parents=True,exist_ok=True)
            archive=root/"catalog.json"
            if not archive.exists():
                if not args.online:raise FileNotFoundError("Radar catalog archive missing")
                url="https://planetarycomputer.microsoft.com/api/stac/v1/search?"+urlencode(dict(
                    collections=plan["collection"],bbox=",".join(map(str,plan["bbox"])),
                    datetime=plan["start"]+"T00:00:00Z/"+plan["as_of"],limit=100))
                with urlopen(Request(url,headers={"User-Agent":"Vantage-research/0.4"}),timeout=30) as response:
                    data=json.load(response)
                if any(link.get("rel")=="next" for link in data.get("links",[])):
                    raise ValueError("Truncated radar search")
                archive.write_text(json.dumps(dict(retrieved_at=datetime.now(timezone.utc).isoformat(),
                    request_url=url,response=data),allow_nan=False),encoding="utf-8")
            data=json.loads(archive.read_text())
            response=data["response"]
            if len(response["features"])>100 or any(l.get("rel")=="next" for l in response.get("links",[])):
                raise ValueError("Radar catalog budget exceeded")
            candidates,excluded=catalog_candidates(response["features"],plan)
            matching=optical_matching_rows(sequence)
            tracks=track_coverage(candidates,matching,plan["as_of"],7)
            matched_dates={m["optical_acquired_at"] for t in tracks for m in t["optical_gap_matches"]
                           if m["catalog_match_within_age_window"]}
            gaps=[r for r in matching if not r["original_coverage_qualified"]]
            report=dict(schema_version="gap-radar-catalog-1",location_id=location["location_id"],plan=plan,
                implementation_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                    for name in ["scripts/inventory_gap_radar.py","vantage/gap_radar.py","vantage/radar.py"]},
                source_sequence_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                catalog_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),retrieved_at=data["retrieved_at"],
                raw_items=len(response["features"]),eligible_passes=len(candidates),
                candidates=[{k:v for k,v in c.items() if k!="assets"} for c in candidates],exclusions=excluded,
                tracks=tracks,optical_dates=len(matching),matched_optical_dates=len(matched_dates),
                optical_coverage_gap_dates=len(gaps),matched_coverage_gap_dates=sum(r["acquired_at"] in matched_dates for r in gaps),
                radar_pixels_processed=0,usable_radar_evidence=False,
                limitation="Geometric catalog/time matches only; no measured coverage, terrain validation, crop signal or optical reconstruction")
            (root/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
            summary={k:report[k] for k in ["location_id","raw_items","eligible_passes","optical_dates","matched_optical_dates","optical_coverage_gap_dates","matched_coverage_gap_dates"]}
            summary["report"]=str(root/"report.json")
            outputs.append(summary)
            print(json.dumps(summary),flush=True)
        except Exception as error:
            failures.append(dict(sequence=str(path),error_type=type(error).__name__))
    print(json.dumps(dict(completed=len(outputs),failures=failures)),flush=True)
    if failures:sys.exit(1)


if __name__=="__main__":main()
