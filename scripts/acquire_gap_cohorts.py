"""Replay the fixed historical cohort acquisition plan; online reads are explicit."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vantage.archive import fingerprint
from vantage.recent_inventory import recent_window


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online",action="store_true",help="Execute catalog and raster acquisition; otherwise print plan")
    parser.add_argument("--plan",type=Path,default=ROOT/"configs/gap_acquisition.json")
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text())
    config=json.loads((ROOT/"configs/uganda_archive.json").read_text())
    for cohort in plan["cohorts"]:
        location=next(l for l in config["locations"] if l["id"]==cohort["location_id"])
        window=recent_window(config,location,datetime.fromisoformat(cohort["as_of"].replace("Z","+00:00")),cohort["days"])
        key=fingerprint(dict(plan=[window],collection=config["collection"]))[:20]
        inventory=ROOT/"outputs/africa/recent"/key/"inventory.json"
        commands=[
            [sys.executable,str(ROOT/"scripts/inventory_recent.py"),"--as-of",cohort["as_of"],"--days",str(cohort["days"]),"--location",cohort["location_id"],"--online"],
            [sys.executable,str(ROOT/"scripts/process_recent_pixels.py"),"--inventory",str(inventory),"--scenes-per-location",str(cohort["scenes_per_location"]),"--online"]]
        for command in commands:
            if args.online:subprocess.run(command,cwd=ROOT,check=True)
            else:print(subprocess.list2cmdline(command))


if __name__=="__main__":main()
