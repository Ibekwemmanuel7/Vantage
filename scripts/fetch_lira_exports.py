"""Dry-run by default. --execute may consume CDSE processing quota for two requests."""
import argparse
from datetime import datetime,timezone
from getpass import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.compare_radar_processor import read_export
from vantage.cdse_exports import access_token,process_export,ExportError
from vantage.radar_benchmark import request_for
import requests


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    root=ROOT/"outputs/africa/lira-comparison/0dbeacd5e45ecbf430b7"
    report=json.loads((root/"report.json").read_text())
    radar_path=ROOT/"outputs/africa/gap-radar-pixels/b9e3ac527f496525a5d7/report.json"
    if hashlib.sha256(radar_path.read_bytes()).hexdigest()!=report["source_radar_report_sha256"]:
        raise ExportError("Source radar report differs")
    grid=json.loads(radar_path.read_text())["grid"]
    rows=report["requests"]
    if len(rows)!=2 or {r["index"] for r in rows}!={0,1}:raise ExportError("Exactly two fixed requests required")
    out=ROOT/"outputs/private-lira-provider-exports"
    jobs=[]
    for row in rows:
        path=root/f"{row['index']}-request.json"
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row["request_sha256"]:raise ExportError("Prepared request differs")
        request=json.loads(path.read_text())
        if request!=request_for(grid,row["safe_product"]):raise ExportError("Request differs from exact-scene builder")
        destination=out/str(row["index"])
        if destination.exists():
            read_export(destination,request,grid,row["safe_product"])
            print(f"{row['index']}: existing export verified; no processing request")
        else:jobs.append((row,request,destination))
    if not args.execute:
        print(json.dumps(dict(status="dry_run_no_network",pending_requests=len(jobs),
            output=str(out),next_step="Set explicit VANTAGE_CDSE_CLIENT_ID and run with --execute; secret is prompted securely")))
        return
    if not jobs:return
    client_id=os.environ.get("VANTAGE_CDSE_CLIENT_ID","")
    if not client_id:raise ExportError("Set VANTAGE_CDSE_CLIENT_ID explicitly before execution")
    secret=getpass("CDSE OAuth client secret (not saved): ")
    with requests.Session() as session:
        token=access_token(session,client_id,secret)
        secret=None
        out.mkdir(parents=True,exist_ok=True)
        for row,request,destination in jobs:
            files=process_export(session,token,request)
            with tempfile.TemporaryDirectory(prefix="staging-",dir=out) as temporary:
                stage=Path(temporary)/"export"
                stage.mkdir()
                (stage/"request.json").write_text(json.dumps(request,indent=2),encoding="utf-8")
                for name,raw in files.items():(stage/name).write_bytes(raw)
                _,lineage=read_export(stage,request,grid,row["safe_product"])
                (stage/"receipt.json").write_text(json.dumps(dict(index=row["index"],lineage=lineage,
                    verified_at=datetime.now(timezone.utc).isoformat()),indent=2),encoding="utf-8")
                stage.rename(destination)
            print(f"{row['index']}: exact-scene/grid export verified and stored locally")
    print("Run scripts/prepare_lira_radar_comparison.py --exports outputs/private-lira-provider-exports")


if __name__=="__main__":
    try:main()
    except Exception as error:
        print(json.dumps(dict(status="failed_no_verified_export",error_type=type(error).__name__)))
        sys.exit(1)
