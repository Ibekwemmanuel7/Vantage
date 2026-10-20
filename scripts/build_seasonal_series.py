"""Bounded multi-month six-band research series, with explicit missing temporal slots."""
import argparse
import calendar
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from scripts.prepare_multispectral import make_scene,validate_scene
from scripts.prepare_ml_dataset import cached_asset
from vantage.archive import fingerprint
from vantage.imagery import atomic_json,sha256_file
from vantage.planetary import ContainerSigner
from vantage.seasonal import dekad_slots,slot_candidates,calendar_readiness
from vantage.crop_context import crop_evidence
from vantage.multispectral import temporal_index
import numpy as np
import rasterio
from rasterio.transform import Affine


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",type=Path,default=ROOT/"configs/uganda_seasonal.json")
    p.add_argument("--allow-downloads",action="store_true")
    p.add_argument("--calendars",type=Path,help="Private independent calendar JSON array; never copied to web")
    p.add_argument("--out",type=Path,default=ROOT/"outputs/africa/seasonal")
    args=p.parse_args()
    plan=json.loads(args.config.read_text());slots=list(dekad_slots(plan))
    if len(slots)>36:raise ValueError("Research run is bounded to 36 temporal slots")
    if plan["max_attempts_per_dekad"] not in (1,2,3):raise ValueError("Candidate budget must be 1-3")
    # Reuse the independently archived historical land-cover source, not a crop label.
    context_root=ROOT/"outputs/africa/crop-context"
    context_path=context_root/json.loads((context_root/"latest.json").read_text())["manifest"]
    context=json.loads(context_path.read_text())["contexts"][plan["location_id"]]
    grid=context["recipe"]["grid"]
    if list(plan["bbox"])!=[33.4,.65,33.5,.75] or plan["location_id"]!="iganga-study":
        raise ValueError("This first adapter is limited to the existing Iganga study grid")
    transform=Affine(*grid["transform"][:6])
    catalog=json.loads((context_root/(plan["location_id"]+"-worldcover.stac.json")).read_text())
    wc=next(i for i in catalog["features"] if i["id"]==context["recipe"]["worldcover_id"])
    classes=cached_asset(wc,"map",transform,grid["width"],grid["height"],False)
    if hashlib.sha256(classes.tobytes()).hexdigest()!=context["recipe"]["raw_classification_sha256"]:
        raise ValueError("Historical land-cover input changed")
    source.signed=ContainerSigner(source.SESSION)
    root=args.out/fingerprint(plan)[:20];root.mkdir(parents=True,exist_ok=True)
    scenes_root=root/"scenes";scenes_root.mkdir(exist_ok=True)
    metadata={}
    for path in source.CACHE.glob("*.txt"):
        text=path.read_text(encoding="utf-8")
        if "BOA_QUANTIFICATION_VALUE" in text:metadata[hashlib.sha256(text.encode()).hexdigest()]=text
    index_path=root/"metadata-index.json"
    metadata_index=json.loads(index_path.read_text()) if index_path.exists() else {}
    calendar_rows=json.loads(args.calendars.read_text()) if args.calendars else []
    if len({(r["location_id"],r["year"]) for r in calendar_rows})!=len(calendar_rows):raise ValueError("Duplicate calendar records")
    calendars={year:calendar_readiness(next((r for r in calendar_rows if r["location_id"]==plan["location_id"] and r["year"]==year),None),plan["location_id"],year) for year in plan["years"]}
    records=[];all_scenes=[];catalog_hashes={};diagnostics=[]
    for year in sorted(plan["years"]):
        for month in sorted(plan["months"]):
            path=root/f"{year}-{month:02}.stac.json"
            try:
                if not path.exists():
                    if not args.allow_downloads:raise FileNotFoundError("Catalog not cached")
                    interval=f"{year}-{month:02}-01T00:00:00Z/{year}-{month:02}-{calendar.monthrange(year,month)[1]}T23:59:59Z"
                    url="https://planetarycomputer.microsoft.com/api/stac/v1/search?"+urlencode(dict(collections=plan["collection"],bbox=','.join(map(str,plan["bbox"])),datetime=interval,limit=100))
                    response=json.loads(source.fetch(url))
                    if any(l.get("rel")=="next" for l in response.get("links",[])):raise ValueError("Truncated monthly search")
                    atomic_json(path,dict(request_url=url,response=response))
                response=json.loads(path.read_text())["response"]
                if any(l.get("rel")=="next" for l in response.get("links",[])):raise ValueError("Truncated monthly archive")
                catalog_hashes[path.name]=sha256_file(path)
            except Exception as exc:
                for slot in slots:
                    if slot["year"]==year and slot["month"]==month:records.append(dict(**slot,status="catalog_unavailable",attempts=[],observation=None))
                diagnostics.append(dict(year=year,month=month,error_type=type(exc).__name__))
                print(f"{year}/{month}: catalog unavailable {type(exc).__name__}",flush=True)
                continue
            for slot in (s for s in slots if s["year"]==year and s["month"]==month):
                candidates=slot_candidates(slot,response["features"],plan["bbox"])
                entry=dict(**slot,status="no_suitable_catalog_acquisition" if not candidates else "acquisition_failed",candidate_count=len(candidates),attempts=[],observation=None)
                for item in candidates[:plan["max_attempts_per_dekad"]]:
                    try:
                        key=item["id"]
                        xml=metadata.get(metadata_index.get(key))
                        if xml is None:
                            if not args.allow_downloads:raise FileNotFoundError("Metadata not cached")
                            xml=source.fetch(source.signed(item["assets"]["product-metadata"]["href"]))
                            digest=hashlib.sha256(xml.encode()).hexdigest();metadata[digest]=xml;metadata_index[key]=digest
                            atomic_json(index_path,metadata_index)
                        scene=make_scene(dict(location_id=plan["location_id"],bbox=plan["bbox"]),item,xml,scenes_root,args.allow_downloads)
                        validate_scene(scene,scenes_root)
                        with rasterio.open(scenes_root/scene["artifact_id"]/scene["assets"]["reflectance"]["href"]) as ds:cube=ds.read()
                        evidence=crop_evidence(cube,np.isfinite(cube).all(axis=0),classes)
                        entry.update(status="processed",scene_id=item["id"],acquired_at=scene["acquired_at"],artifact_id=scene["artifact_id"],observation=evidence)
                        entry["attempts"].append(dict(scene_id=item["id"],status="processed"));all_scenes.append(scene)
                        break
                    except Exception as exc:
                        entry["attempts"].append(dict(scene_id=item["id"],status="failed"))
                        diagnostics.append(dict(slot_id=slot["slot_id"],scene_id=item["id"],error_type=type(exc).__name__))
                records.append(entry)
                print(f'{slot["slot_id"]}: {entry["status"]}',flush=True)
                # Retain partial progress without presenting it as a final cohort.
                atomic_json(root/"progress.json",dict(completed_slots=len(records),requested_slots=len(slots),slots=records))
    recipe=dict(plan=plan,catalog_hashes=catalog_hashes,artifact_ids=sorted(s["artifact_id"] for s in all_scenes),
                slot_outcomes=[dict(slot_id=r["slot_id"],status=r["status"],scene_id=r.get("scene_id"),attempts=r["attempts"]) for r in records],
                context_sha256=sha256_file(context_path),calendars=calendars,
                code={p:sha256_file(ROOT/p) for p in ("scripts/build_seasonal_series.py","vantage/seasonal.py")})
    dataset_id=fingerprint(recipe)[:24]
    report=dict(schema_version="seasonal-series-1",dataset_id=dataset_id,recipe=recipe,slots=records,
                requested_slots=len(slots),processed_slots=len(all_scenes),scenes=all_scenes,
                sequences={str(y):temporal_index([r for r in all_scenes if r["acquired_at"].startswith(str(y))]) for y in plan["years"]},
                independent_field_labels=0,trained_model=False,foundation_ready=False,agronomic_review_eligible=False,
                limitation="One candidate per dekad, not all acquisitions or confirmed crop stages. Historical crop context only. No imputation, diagnosis, field outcome validation or operational replay.")
    atomic_json(root/(dataset_id+".json"),report)
    diagnostic_report=dict(dataset_id=dataset_id,allow_downloads=args.allow_downloads,diagnostics=diagnostics)
    atomic_json(root/"attempts"/(fingerprint(diagnostic_report)[:24]+".json"),diagnostic_report)
    atomic_json(args.out/"latest.json",dict(directory=root.name,manifest=dataset_id+".json"))
    print(f"Seasonal dataset {dataset_id}: {len(all_scenes)}/{len(slots)} observed slots",flush=True)
    if any(r["status"] in ("catalog_unavailable","acquisition_failed") for r in records):sys.exit(1)


if __name__=="__main__":main()
