"""Build a versioned geospatial dataset and imagery viewer assets from public data.

Default offline mode uses cached red/NIR/SCL and metadata. --allow-downloads
permits public green/blue asset reads for RGB. No imagery labels are fabricated.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_uganda_demo as source
from vantage.area import units
from vantage.imagery import decode_metadata, derive_scene, zone_features, rgba_rgb, rgba_ndvi, sha256_file, stable_hash,atomic_json,atomic_text

import numpy as np
from PIL import Image
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import from_bounds
from rasterio.warp import transform_bounds, transform_geom


def cached_asset(item, key, transform, width, height, allow_downloads):
    href = item["assets"][key]["href"]
    path = source.CACHE/(hashlib.sha256((href+str(transform)+str(width)+str(height)).encode()).hexdigest()+".npy")
    if path.exists():
        return np.load(path,allow_pickle=False)
    if not allow_downloads:
        raise FileNotFoundError("Asset not cached")
    return source.read_asset(item,key,transform,width,height,"EPSG:32636",key=="SCL")


def write_cog(path,array,transform,descriptions):
    if path.exists():
        return  # Existing versioned COGs were checked against their manifest before reuse.
    if array.ndim == 2:
        array = array[None,...]
    with rasterio.open(path,"w",driver="COG",width=array.shape[2],height=array.shape[1],
                       count=array.shape[0],dtype=array.dtype,crs="EPSG:32636",transform=transform,
                       compress="DEFLATE",blocksize=256,nodata=np.nan if array.dtype.kind=="f" else None,
                       overview_resampling="nearest" if array.dtype.kind!="f" else "average") as dst:
        dst.write(array)
        for i,name in enumerate(descriptions,1):
            dst.set_band_description(i,name)


def make_dataset(observations_path, destination, allow_downloads=False):
    data = json.loads(Path(observations_path).read_text(encoding="utf-8"))
    config = data["config"]
    bbox = config["bbox"]
    bounds = transform_bounds("EPSG:4326","EPSG:32636",*bbox)
    width,height = int(np.ceil((bounds[2]-bounds[0])/20)),int(np.ceil((bounds[3]-bounds[1])/20))
    transform = from_bounds(*bounds,width,height)
    geometry_units = units(config)
    items = []
    # Reuse archived source STAC responses; do not rediscover or silently replace inputs.
    for path in source.CACHE.glob("*.txt"):
        try:
            response = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(response,dict):
                items.extend(response.get("features",[]))
        except (ValueError,UnicodeError):
            continue
    index = {i["id"]:i for i in items}
    metadata = {}
    for path in source.CACHE.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        if "BOA_QUANTIFICATION_VALUE" in text:
            metadata[hashlib.sha256(text.encode()).hexdigest()] = text
    wc_lineage = next(l for l in data["lineage"] if l["source"].startswith("ESA WorldCover"))
    wc = index[wc_lineage["id"]]
    crop = cached_asset(wc,"map",transform,width,height,allow_downloads) == 40
    unit_masks = {u["id"]:crop & geometry_mask([transform_geom("EPSG:4326","EPSG:32636",u["geometry"])],
                  out_shape=(height,width),transform=transform,invert=True) for u in geometry_units}
    scene_inputs = sorted([l for l in data["lineage"] if l["source"]=="Sentinel-2 L2A"],key=lambda l:(l["acquired_at"],l["id"]))
    preloaded,errors,input_hashes = {},[],{}
    for record in scene_inputs:
        sid = record["id"]
        print("Checking cached/downloaded bands",sid,flush=True)
        preloaded[sid],input_hashes[sid] = {},{}
        for band in ("B04","B08","B02","B03","SCL"):
            try:
                array = cached_asset(index[sid],band,transform,width,height,allow_downloads)
                preloaded[sid][band] = array
                input_hashes[sid][band] = stable_hash(dict(dtype=str(array.dtype),shape=list(array.shape),sha256=hashlib.sha256(array.tobytes()).hexdigest()))
            except Exception as exc:
                if band in ("B04","B08","SCL"):
                    raise
                errors.append(dict(scene_id=sid,asset=band,error_type=type(exc).__name__))
                input_hashes[sid][band] = "unavailable"
    recipe = dict(version="imagery-dataset-1",config=config,source_sha256=sha256_file(observations_path),
                  scene_ids=[l["id"] for l in scene_inputs],rgb_stretch=[0,.3],gamma=2.2,
                  mask="SCL 4/5; one analysis pixel rejection buffer; nonnegative physical reflectance",
                  feature_version="area-season-features-1",input_hashes=input_hashes,
                  worldcover_mask_sha256=hashlib.sha256(crop.tobytes()).hexdigest(),
                  code_hashes={"prepare":sha256_file(__file__),"imagery":sha256_file(ROOT/"vantage/imagery.py"),"source_adapter":sha256_file(ROOT/"scripts/build_uganda_demo.py")},
                  software={x:importlib.metadata.version(x) for x in ("numpy","rasterio","scipy","Pillow")},
                  gdal_version=rasterio.__gdal_version__)
    dataset_id = stable_hash(recipe)[:20]
    out = Path(destination)/dataset_id
    out.mkdir(parents=True,exist_ok=True)
    assets = out/"assets";assets.mkdir(exist_ok=True)
    stac = out/"stac";stac.mkdir(exist_ok=True)
    if (out/"manifest.json").exists():
        previous=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
        for sid,hashes in previous["asset_hashes"].items():
            for kind,digest in hashes.items():
                if sha256_file(assets/(sid+"-"+kind+".tif"))!=digest:
                    raise ValueError("A versioned raster changed; refusing to overwrite or train from it")
    public = ROOT/"web/data/imagery"/dataset_id
    public.mkdir(parents=True,exist_ok=True)
    scenes,records = [],[]
    inv = ~transform
    pixel_polygons = {u["id"]:[list(inv*tuple(p)) for p in transform_geom("EPSG:4326","EPSG:32636",u["geometry"])["coordinates"][0]] for u in geometry_units}
    for source_record in scene_inputs:
        sid = source_record["id"]
        item = index[sid]
        print("Preparing",sid,flush=True)
        q,offsets = decode_metadata(metadata[source_record["metadata_sha256"]],source_record["baseline"])
        raw = {band:array for band,array in preloaded[sid].items() if band!="SCL"}
        scl = preloaded[sid]["SCL"]
        reflectance,valid,ndvi = derive_scene(raw,scl,q,offsets)
        rgba = rgba_rgb(reflectance,valid)
        rgb_path = public/(sid+"-rgb.png")
        if rgba is not None:
            Image.fromarray(rgba).save(rgb_path)
        ndvi_path = public/(sid+"-ndvi.png")
        Image.fromarray(rgba_ndvi(ndvi)).save(ndvi_path)
        rejected = np.zeros((height,width,4),dtype=np.uint8)
        rejected[~valid] = [179,68,72,150]
        quality_path = public/(sid+"-quality.png")
        Image.fromarray(rejected).save(quality_path)
        raw_path = public/(sid+"-ndvi.f32")
        ndvi.astype("<f4").tofile(raw_path)
        paths = dict(reflectance=assets/(sid+"-reflectance.tif"),ndvi=assets/(sid+"-ndvi.tif"),quality=assets/(sid+"-quality.tif"))
        bands = [b for b in ("B02","B03","B04","B08") if b in reflectance]
        stack = np.stack([np.where(valid,reflectance[b],np.nan) for b in bands]).astype(np.float32)
        write_cog(paths["reflectance"],stack,transform,bands)
        write_cog(paths["ndvi"],ndvi,transform,["NDVI"])
        write_cog(paths["quality"],np.stack([scl.astype(np.uint8),valid.astype(np.uint8),crop.astype(np.uint8)]),transform,["SCL","accepted_quality","historical_cropland"])
        hashes = {k:sha256_file(p) for k,p in paths.items()}
        raster_bands={"reflectance":[dict(name=b,data_type="float32",nodata="nan",scale=1,offset=0,unit="1") for b in bands],
                      "ndvi":[dict(name="NDVI",data_type="float32",nodata="nan",unit="1")],
                      "quality":[dict(name=b,data_type="uint8") for b in ["SCL","accepted_quality","historical_cropland"]]}
        stac_assets = {k:dict(href="../assets/"+p.name,type="image/tiff; application=geotiff; profile=cloud-optimized",roles=["data"],**{"vantage:sha256":hashes[k],"raster:bands":raster_bands[k]}) for k,p in paths.items()}
        footprint=transform_geom("EPSG:32636","EPSG:4326",dict(type="Polygon",coordinates=[[[bounds[0],bounds[1]],[bounds[2],bounds[1]],[bounds[2],bounds[3]],[bounds[0],bounds[3]],[bounds[0],bounds[1]]]]))
        points=footprint["coordinates"][0]
        footprint_bbox=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
        stac_item = dict(type="Feature",stac_version="1.0.0",stac_extensions=["https://stac-extensions.github.io/projection/v1.1.0/schema.json","https://stac-extensions.github.io/raster/v1.1.0/schema.json"],id=sid,
                   geometry=footprint,
                   bbox=footprint_bbox,properties={"datetime":source_record["acquired_at"],"proj:epsg":32636,"proj:transform":list(transform),"proj:shape":[height,width],"vantage:study_bbox":bbox,"vantage:band_order":bands,"vantage:dataset_id":dataset_id},
                   links=[dict(rel="derived_from",href=f'https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/{sid}',type="application/geo+json")],assets=stac_assets)
        atomic_json(stac/(sid+".json"),stac_item)
        for u in geometry_units:
            row = zone_features(reflectance,ndvi,unit_masks[u["id"]])
            row.update(unit_id=u["id"],year=int(source_record["acquired_at"][:4]),source_id=sid,
                 acquired_at=source_record["acquired_at"],spatial_group=config["profile_id"]+":one-study-area",
                 geometry=u["geometry"],sample_id=stable_hash([dataset_id,sid,u["id"]])[:24],dataset_id=dataset_id)
            records.append(row)
        relative = "data/imagery/"+dataset_id+"/"
        scenes.append(dict(id=sid,acquired_at=source_record["acquired_at"],year=int(source_record["acquired_at"][:4]),
             rgb=relative+rgb_path.name if rgba is not None else None,ndvi=relative+ndvi_path.name,
             quality=relative+quality_path.name,ndvi_values=relative+raw_path.name,
             hashes=hashes,accepted_fraction=float(valid.mean()),
             offsets=offsets,quantification=q,source_url=stac_item["links"][0]["href"],
             availability="cached_retrospective",source_metadata_sha256=source_record["metadata_sha256"]))
    manifest = dict(schema_version="training-dataset-1",dataset_id=dataset_id,recipe=recipe,
         mode=config["mode"],profile_id=config["profile_id"],target_year=config["target_year"],
         reference_years=config["reference_years"],decision_cutoff=config["as_of"],
         source_availability="unknown_at_historical_cutoff",created_at=json.loads((out/"manifest.json").read_text())["created_at"] if (out/"manifest.json").exists() else datetime.now(timezone.utc).isoformat(),
         observation_records=len(records),independent_spatial_groups=1,
         quality_policy=dict(min_usable_fraction=config["min_usable_fraction"],min_valid_pixels=100),
         crs="EPSG:32636",transform=list(transform),shape=[height,width],bbox=bbox,
         scene_ids=[s["id"] for s in scenes],errors=errors,
         software={x:importlib.metadata.version(x) for x in ("numpy","rasterio","scipy","Pillow")},
         ground_truth_status="No independent field outcome labels supplied",data_licences=["Copernicus Sentinel data terms","ESA WorldCover CC BY 4.0","CHIRPS public domain"])
    manifest["quality_policy"]["freshness_days"]=config["freshness_days"]
    atomic_text(out/"observations.jsonl","".join(json.dumps(r,allow_nan=False)+"\n" for r in records))
    shutil.copyfile(observations_path,out/"source-observations.json")
    manifest["observations_sha256"]=sha256_file(out/"observations.jsonl")
    manifest["asset_hashes"]={s["id"]:s["hashes"] for s in scenes}
    atomic_json(out/"manifest.json",manifest)
    atomic_json(stac/"catalog.json",dict(type="Catalog",stac_version="1.0.0",id=dataset_id,
         description="Vantage retrospective georeferenced derivatives, not ground truth",links=[dict(rel="item",href=s["id"]+".json",type="application/geo+json") for s in scenes]))
    viewer = dict(schema_version="imagery-viewer-1",dataset_id=dataset_id,bbox=bbox,crs="EPSG:32636",width=width,height=height,
         transform=list(transform),pixel_polygons=pixel_polygons,scenes=scenes,
         target_year=config["target_year"],reference_years=config["reference_years"],
         rgb_display="Fixed 0–0.30 physical reflectance stretch; gamma 2.2; quality-rejected pixels transparent",
         ndvi_range=[-.2,1],change_range=[-.3,.3],
         limitation="Same-season comparisons from different years are not a damage before/after experiment. Clouds and rejected pixels are not reconstructed. Historical cropland is not confirmed maize.")
    atomic_json(ROOT/"web/data/imagery.json",viewer)
    atomic_json(Path(destination)/"latest.json",dict(dataset_id=dataset_id,path=dataset_id))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",type=Path,default=ROOT/"outputs/uganda/observations.json")
    parser.add_argument("--out",type=Path,default=ROOT/"outputs/ml/datasets")
    parser.add_argument("--allow-downloads",action="store_true")
    args = parser.parse_args()
    print(make_dataset(args.observations,args.out,args.allow_downloads),flush=True)
