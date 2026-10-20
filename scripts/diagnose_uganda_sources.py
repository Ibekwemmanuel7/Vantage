"""Public access diagnostics without logging tokens or signed links."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online",action="store_true",required=True)
    args=parser.parse_args()
    archive=ROOT/"outputs/africa/archive/d9c82747f42377f8ec84"
    report=json.loads((archive/"pixels-report.json").read_text())
    window=next(w for w in report["windows"] if w["location_id"]=="kasese-study" and w["year"]==2024 and w["month"]==5)
    response=json.loads((archive/"kasese-study-2024-05.stac.json").read_text())["response"]
    item=next(i for i in response["features"] if i["id"]==window["processed_scene_id"])
    href=item["assets"]["B02"]["href"]
    parsed=urlparse(href);account=parsed.hostname.split(".")[0];container=parsed.path.strip("/").split("/")[0]
    result=dict(scene_id=item["id"],asset="B02",storage_account=account,container=container)
    with requests.Session() as session:
        signed=session.get("https://planetarycomputer.microsoft.com/api/sas/v1/sign",params={"href":href},timeout=30)
        result["sign_endpoint_status"]=signed.status_code
        token=session.get(f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{account}/{container}",timeout=30)
        result["container_token_status"]=token.status_code
        if token.status_code==200:
            # Signed credentials remain in memory only. Read one byte to verify access.
            check=session.get(href+"?"+token.json()["token"],headers={"Range":"bytes=0-0"},timeout=30,stream=True)
            result["asset_range_status"]=check.status_code
            check.close()
    path=ROOT/"outputs/africa/source-diagnostics.json"
    path.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
