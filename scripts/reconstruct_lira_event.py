"""Offline replay or bounded public CHIRPS native-window acquisition for Lira 2024."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
proj = Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data'
os.environ['PROJ_DATA'] = os.environ['PROJ_LIB'] = str(proj)
import numpy as np
import rasterio
from rasterio.windows import from_bounds, bounds, Window
from vantage.event_reconstruction import rainfall_comparison, optical_difference


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def acquire(root, plan, year, month, online):
    path = root/f'{year}-{month:02}.json'
    url = plan['rain_base_url']+f'chirps-v3.0.{year}.{month:02}.cog'
    if not path.exists():
        if not online: raise ValueError(f'Missing cached rainfall {year}-{month:02}')
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_TIMEOUT='25',
                          GDAL_HTTP_MAX_RETRY='1', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.cog'):
            with rasterio.open(url) as source:
                if source.crs != rasterio.crs.CRS.from_epsg(4326) or source.count != 1:
                    raise ValueError('Unexpected rainfall CRS/band count')
                if not np.allclose([source.transform.a, source.transform.e], [.05, -.05], rtol=0, atol=1e-8):
                    raise ValueError('Unexpected native rainfall resolution')
                fractional = from_bounds(*plan['bbox'], source.transform)
                window = Window(*(round(v) for v in (fractional.col_off, fractional.row_off, fractional.width, fractional.height)))
                if not np.allclose(bounds(window, source.transform), plan['bbox'], rtol=0, atol=1e-5):
                    raise ValueError('Study box must align with native rainfall cells')
                values = source.read(1, window=window, masked=True)
                if values.shape != (2,2) or np.ma.getmaskarray(values).any() or not np.isfinite(values).all() or (values < 0).any():
                    raise ValueError('Missing or invalid rainfall; no fill permitted')
                record = dict(year=year, month=month, url=url, bbox=plan['bbox'],
                              retrieved_at=datetime.now(timezone.utc).isoformat(),
                              values_mm=values.tolist(), source_tags=source.tags(),
                              native_transform=list(source.transform), subset_transform=list(source.window_transform(window)),
                              provenance='Extract checksum only; whole remote COG not downloaded or hashed')
        write_json(path, record)
    record = json.loads(path.read_text())
    if record['year'] != year or record['month'] != month or record['url'] != url or record['bbox'] != plan['bbox']:
        raise ValueError('Cached rainfall identity differs')
    return (year,month), record['values_mm'], dict(file=path.name, sha256=digest(path), url=url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--online', action='store_true', help='Allow 123 fixed public COG window reads; 3 workers')
    parser.add_argument('--report-name', default='report.json', help='New report basename when adding previously missing data')
    args = parser.parse_args()
    if Path(args.report_name).name != args.report_name or not args.report_name.endswith('.json'):
        raise ValueError('JSON report basename required')
    config = ROOT/'configs/lira_2024_event.json'
    plan = json.loads(config.read_text())
    if (plan['bbox'] != [32.85,2.2,32.95,2.3] or plan['target_year'] != 2024
            or plan['rain_months'] != [3,4,5] or plan['rain_baseline_years'] != [1981,2020]
            or plan['optical_reference_year'] != 2023 or plan['optical_month'] != 5
            or plan['optical_min_common_fraction'] != .7):
        raise ValueError('Adapter limited to the frozen Lira MAM study design')
    root = ROOT/'outputs/africa/lira-event'/digest(config)[:20]
    root.mkdir(parents=True, exist_ok=True)
    frozen = root/'frozen-plan.json'
    if not frozen.exists(): write_json(frozen, dict(plan=plan, frozen_at=datetime.now(timezone.utc).isoformat()))
    elif json.loads(frozen.read_text())['plan'] != plan: raise ValueError('Frozen plan changed')
    cache = root/'rainfall'; cache.mkdir(exist_ok=True)
    years = list(range(1981,2021))
    tasks = [(y,m) for y in [*years,2024] for m in (3,4,5)]
    months, lineage = {}, []
    # Stop requesting new batches after a provider failure; do not hammer a denied endpoint.
    for start in range(0,len(tasks),3):
        batch = tasks[start:start+3]
        if not args.online:
            batch = [(y,m) for y,m in batch if (cache/f'{y}-{m:02}.json').exists()]
        failed = False
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(acquire,cache,plan,y,m,args.online) for y,m in batch]
            for future in as_completed(futures):
                try:
                    key, values, source = future.result(); months[key]=values; lineage.append(source)
                except Exception as exc:
                    if not args.online: raise
                    print(f'Rainfall acquisition stopped: {type(exc).__name__}: {exc}',flush=True)
                    failed = True
        if failed: break
        if start % 12 == 0: print(f'Rainfall windows cached: {len(months)}/123',flush=True)
    missing = [f'{y}-{m:02}' for y,m in tasks if (y,m) not in months]
    rain = dict(status='unavailable',expected_months=123,cached_months=len(months),missing_months=missing,
                interpretation='Incomplete rainfall cohort; no totals, departures or drought class produced') if missing else dict(status='complete',**rainfall_comparison(months,2024,years))
    report_path = ROOT/plan['archive_report']
    if digest(report_path) != plan['archive_report_sha256']: raise ValueError('Pinned optical archive differs')
    archive = json.loads(report_path.read_text())
    records = [next(r for r in archive['windows'] if r['location_id']=='lira-study' and r['year']==y and r['month']==5) for y in (2023,2024)]
    arrays, optical_sources = [], []
    for record in records:
        path = report_path.parent/record['artifact']
        if digest(path) != record['artifact_sha256']: raise ValueError('Optical artifact differs')
        catalog_path = report_path.parent/f"lira-study-{record['year']}-05.stac.json"
        if digest(catalog_path) != record['archive_sha256']: raise ValueError('Optical catalog differs')
        catalog = json.loads(catalog_path.read_text())
        item = next(i for i in catalog['response']['features'] if i['id']==record['processed_scene_id'])
        if item['properties']['datetime'][:7] != f"{record['year']}-05": raise ValueError('Optical acquisition outside May')
        with np.load(path,allow_pickle=False) as data: arrays.append({k:data[k].copy() for k in data.files})
        optical_sources.append(dict(scene_id=item['id'], acquired_at=item['properties']['datetime'],
                                    artifact_sha256=digest(path), catalog_sha256=digest(catalog_path)))
    if not np.array_equal(arrays[0]['transform'],arrays[1]['transform']) or str(arrays[0]['crs']) != str(arrays[1]['crs']):
        raise ValueError('Optical grids differ')
    delta, optical = optical_difference(arrays[0]['ndvi'],arrays[0]['valid'],arrays[1]['ndvi'],arrays[1]['valid'],.7)
    from rasterio.transform import Affine
    transform = Affine(*arrays[0]['transform'][:6])
    raster = root/'observed-ndvi-difference.tif'
    if not raster.exists():
        with rasterio.open(raster,'w',driver='GTiff',height=delta.shape[0],width=delta.shape[1],count=1,
                           dtype='float32',crs=str(arrays[0]['crs']),transform=transform,nodata=np.nan,compress='deflate') as dest:
            dest.write(delta,1);dest.write_mask(np.isfinite(delta).astype('uint8')*255)
    else:
        with rasterio.open(raster) as source:
            if not np.array_equal(source.read(1),delta,equal_nan=True): raise ValueError('Existing difference raster differs')
    report = dict(schema_version='vantage-event-reconstruction-1',plan=plan, plan_sha256=digest(config),
                  rainfall=rain,rainfall_lineage=sorted(lineage,key=lambda r:r['file']),
                  optical=optical,optical_sources=optical_sources,optical_difference_sha256=digest(raster),
                  independent_field_outcomes=0,crop_loss_attribution_available=False,
                  historical_operational_availability_confirmed=False,
                  implementation_sha256={name:digest(ROOT/name) for name in ('vantage/event_reconstruction.py','scripts/reconstruct_lira_event.py')})
    output = root/'report.json'
    if not output.exists(): write_json(output,report)
    elif json.loads(output.read_text()) != report: raise ValueError('Replay differs from pinned result')
    print(json.dumps(dict(rainfall=rain,optical=optical,report=str(output)),indent=2),flush=True)


if __name__ == '__main__': main()
