# Satellite imagery and ML workbench

Implemented research slice, 20 October 2026. Independent Vantage work within
[Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US); no CropSight inheritance,
IDEA approval or validated customer performance. Texas cotton stays a separate
profile. Forestry remains with Vepris.

## What works

- A dated imagery comparison viewer: true-color RGB, quality-masked NDVI,
  pixel-wise NDVI differences, quality overlays, synchronized whole-area/unit
  views, source links and keyboard/pointer pixel inspection.
- Real public Sentinel-2 acquisitions, eight true-color previews from nine
  processed scenes. One reference scene lacks cached/downloaded blue/green
  bands; its RGB view is explicitly unavailable and NDVI remains available.
- Versioned, georeferenced reflectance/NDVI/quality COGs and a STAC catalog with
  projection/raster extensions. Official schema validation, checksums and grid
  checks passed for nine items and 27 COGs.
- A content-addressed dataset, explicit sample IDs, quality exclusions,
  area-season features, blank independent-label CSV and reproducible experiments.
- An actually fitted exploratory Isolation Forest; supervised training is
  explicitly gated because no independent outcomes have been supplied.

The viewer is an aligned study-area raster inspector, not a general slippy map
or navigation tool. Raster previews, COGs, source caches and weights are generated
locally and ignored by Git. Compact catalogs/reports remain in source. No cloud
or private data service has been deployed.

## Open the updated product

Restart the local server to load the new raster download endpoint:

```powershell
cd C:\Users\taylo\Lillie_US\Vantage
python scripts/serve_demo.py --port 8917
```

Open http://127.0.0.1:8917 and refresh. In the Uganda profile, scroll to **Inspect
the satellite evidence**. Select dates and display layer, enable the rejection
overlay and choose whole area or selected unit. Click a raster or focus it and
use arrow keys for physical NDVI values and projected coordinates. COG links
download the selected comparison scene; HTTP byte ranges support GIS readers.
The ML research bench explains model status separately from the expert queue.

Source/comparison dates are explicit. Different-year same-season images are not
an event-damage before/after validation. Red quality overlay means any rejected
pixel, not exclusively cloud. Checkerboard means unavailable/rejected data.

## Reproduce locally

The cached viewer/server needs only Python standard library. Scientific work
requires a separate Python environment with `requirements-ml.txt`. Exact direct
versions used are pinned; this is not a complete transitive/container lock.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-ml.txt
# First obtain/reconstruct the public-data observation archive if absent:
.\.venv\Scripts\python scripts/build_uganda_demo.py
# Reads archived inputs and caches; permits missing RGB band downloads:
.\.venv\Scripts\python scripts/prepare_ml_dataset.py --allow-downloads
# Rebuild without network after caching:
.\.venv\Scripts\python scripts/prepare_ml_dataset.py
.\.venv\Scripts\python scripts/validate_ml_dataset.py --schemas
.\.venv\Scripts\python scripts/train_baseline.py --mode novelty
.\.venv\Scripts\python scripts/train_baseline.py --mode supervised
.\.venv\Scripts\python -m unittest discover -s tests -v
```

The default dataset preparation is offline and never silently fetches missing
bands. Online access reads public data only, with no imagery purchase. A fresh
source reconstruction may differ as catalog versions or availability change;
it creates a different dataset ID. Exact replay requires its archived source
observations, raw caches and manifest, not a new search of a mutable catalog.

Datasets live under `outputs/ml/datasets/<dataset_id>/`; `latest.json` selects
the current one. Each includes source observations, records, checksums, COGs and
STAC. Experiments live under `outputs/ml/experiments/<run_id>/` with report,
model card and a model artifact only when fitting actually occurred. Do not load
untrusted joblib/pickle artifacts. Inputs, code, software versions and seed are
recorded. Manifests are published atomically; changed versioned rasters fail
validation rather than being silently reused.

## Train with independent field outcomes later

The generated `labels-template.csv` contains blank outcomes and split fields.
Copy it to a separate operational file before editing. Follow
[the dataset/label contract](DATASET_CARD.md). Demonstration feedback is not
automatically imported and cannot satisfy the field-visit contract.

```powershell
python scripts/train_baseline.py --mode supervised --labels path\to\independent-labels.csv
```

For multiple compatible study datasets, supply their directories after
`--dataset`. Geographically overlapping train/validation/test cohorts, future
chronology, weak/demo labels, quality-excluded samples and insufficient outcome
counts fail the engineering gates. A gate pass is not proof that label
declarations are true or that a study has adequate statistical power.

## Scientific limits

See [dataset card](DATASET_CARD.md), [model card and results](MODEL_CARD.md) and
[architecture/extension decisions](ARCHITECTURE.md). This is present-day
retrospective reconstruction: reprocessed scenes and CHIRPS v3 do not establish
historical operational availability. One study area with correlated units and a
short seasonal reference cannot validate Southern US or Uganda farm performance.
No imagery-only cause, irrigation prescription, yield loss, water saving or
food-security improvement is established.
