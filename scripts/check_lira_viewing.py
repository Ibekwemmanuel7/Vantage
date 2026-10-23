"""Verify Lira source annotations and compute approximate local viewing risks."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from scripts.acquire_viewing_annotations import product_references
from scripts.build_terrain_screen import elevation_clip
from scripts.build_viewing_geometry import grid_geometry,calculate,radar_grid,geometry_summary
from vantage.archive import fingerprint
from vantage.planetary import ContainerSigner
from vantage.safe_annotations import verify_annotation
import numpy as np


def fetch_cached(path,href,online,signer=None):
    if not path.exists():
        if not online:raise FileNotFoundError("Required annotation input not cached")
        response=source.SESSION.get(signer(href) if signer else href,timeout=45)
        response.raise_for_status()
        path.write_bytes(response.content)
    return path.read_bytes()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online",action="store_true")
    args=parser.parse_args()
    plan=json.loads((ROOT/"configs/lira_gap_viewing.json").read_text())
    parent_root=ROOT/"outputs/africa/gap-radar-pixels"/plan["parent_radar_directory"]
    parent_path=parent_root/"report.json"
    parent=json.loads(parent_path.read_text())
    terrain_root=ROOT/"outputs/africa/gap-terrain"/plan["parent_terrain_directory"]
    terrain_path=terrain_root/"report.json"
    terrain=json.loads(terrain_path.read_text())
    if hashlib.sha256(parent_path.read_bytes()).hexdigest()!=terrain["source_radar_report_sha256"]:
        raise ValueError("Radar report differs from terrain parent")
    catalog=ROOT/"outputs/africa/gap-radar"/parent["plan"]["catalog_directory"]/"catalog.json"
    if hashlib.sha256(catalog.read_bytes()).hexdigest()!=parent["source_catalog_sha256"]:
        raise ValueError("Source catalog differs")
    items={i["id"]:i for i in json.loads(catalog.read_text())["response"]["features"]}
    elevation_catalog=terrain_root/"elevation-catalog.json"
    if hashlib.sha256(elevation_catalog.read_bytes()).hexdigest()!=terrain["elevation_catalog_sha256"]:
        raise ValueError("Elevation catalog differs")
    elevation_item=next(i for i in json.loads(elevation_catalog.read_text())["response"]["features"] if i["id"]==terrain["elevation_item_id"])
    native=terrain_root/terrain["elevation_lineage"]["cache"]
    if hashlib.sha256(native.read_bytes()).hexdigest()!=terrain["elevation_lineage"]["sha256"]:
        raise ValueError("Native elevation differs")
    derivative_grid=terrain["derivative_grid"]
    elevation,support,_=elevation_clip(elevation_item,derivative_grid,native,False)
    elevation[support<terrain["plan"]["native_support_required"]]=np.nan
    basis=grid_geometry(derivative_grid)
    root=ROOT/"outputs/africa/gap-viewing"/fingerprint(plan)[:20]
    root.mkdir(parents=True,exist_ok=True)
    signer=ContainerSigner(source.SESSION)
    if len(parent["observations"])>plan["max_passes"] or plan["max_passes"]>2:
        raise ValueError("Two-pass annotation budget required")
    rows=[]
    for index,record in enumerate(parent["observations"]):
        row=dict(item_id=record["item_id"],status="failed")
        try:
            item=items[record["item_id"]]
            links=[l["href"] for l in item["links"] if l.get("rel")=="derived_from"]
            if len(links)!=1 or not links[0].startswith("https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-grd/items/"):
                raise ValueError("Authoritative GRD source link required")
            grd_path=root/f"{index}-grd.json"
            grd=json.loads(fetch_cached(grd_path,links[0],args.online))
            manifest_path=root/f"{index}-manifest.xml"
            manifest_href=grd["assets"]["safe-manifest"]["href"]
            manifest=fetch_cached(manifest_path,manifest_href,args.online,signer)
            refs=product_references(manifest.decode(),manifest_href)
            refs=[r for r in refs if "vv" in urlparse(r["href"]).path.rsplit("/",1)[-1].lower()]
            if len(refs)!=1:raise ValueError("Exactly one manifest VV annotation required")
            reference=refs[0]
            annotation_path=root/f"{index}-product-vv.xml"
            if not annotation_path.exists():
                if not args.online:raise FileNotFoundError("Product annotation not cached")
                response=source.SESSION.get(signer(reference["href"]),timeout=45)
                if response.status_code==404:
                    mapped=grd["assets"]["vv"]["href"].replace("/measurement/","/annotation/").rsplit(".",1)[0]+".xml"
                    response=source.SESSION.get(signer(mapped),timeout=45)
                response.raise_for_status()
                verify_annotation(response.content,reference)
                annotation_path.write_bytes(response.content)
            raw=annotation_path.read_bytes()
            digest=verify_annotation(raw,reference)
            result,parsed=calculate(raw,record,elevation,derivative_grid,basis,plan)
            angles,classes=radar_grid(result,derivative_grid,parent["grid"])
            summary=geometry_summary(classes,angles,np.ones(classes.shape,dtype=bool))
            summary["whole_box_pixels"]=summary.pop("historical_crop_pixels")
            summary["locally_unflagged_whole_box_fraction"]=summary.pop("locally_unflagged_crop_fraction")
            asset=root/f"{index}-local-geometry.npz"
            if asset.exists():
                with np.load(asset,allow_pickle=False) as old:
                    if not np.array_equal(old["classes"],classes) or not np.array_equal(old["angles"],angles,equal_nan=True):
                        raise ValueError("Derived local geometry differs")
            else:np.savez_compressed(asset,classes=classes,angles=angles,transform=np.array(parent["grid"]["transform"]),crs=parent["grid"]["crs"])
            row.update(status="processed",acquired_at=record["acquired_at"],summary=summary,annotation_geometry=parsed,
                       track_id=record["track_id"],source_grd=grd_path.name,manifest=manifest_path.name,
                       annotation=annotation_path.name,annotation_reference_md5=reference["md5"],
                       annotation_reference_size=reference["size"],
                       source_grd_sha256=hashlib.sha256(grd_path.read_bytes()).hexdigest(),
                       manifest_sha256=hashlib.sha256(manifest).hexdigest(),annotation_sha256=digest,
                       artifact=asset.name,artifact_sha256=hashlib.sha256(asset.read_bytes()).hexdigest())
        except Exception as error:
            # Provider exception text may contain signed access URLs.
            row["error_type"]=type(error).__name__
        rows.append(row)
        print(json.dumps(row),flush=True)
    report=dict(schema_version="lira-local-viewing-1",plan=plan,observations=rows,
                processed_at=datetime.now(timezone.utc).isoformat(),
                source_radar_report_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),
                source_terrain_report_sha256=hashlib.sha256(terrain_path.read_bytes()).hexdigest(),
                code_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                    ["scripts/check_lira_viewing.py","scripts/acquire_viewing_annotations.py","vantage/safe_annotations.py","vantage/viewing.py","scripts/build_viewing_geometry.py"]},
                nonlocal_shadow_checked=False,radar_illumination_confirmed=False,usable_agricultural_evidence=False)
    (root/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(f"Report: {root / 'report.json'}")
    if any(r["status"]!="processed" for r in rows):sys.exit(1)


if __name__=="__main__":main()
