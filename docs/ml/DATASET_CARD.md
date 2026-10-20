# Dataset card: Iganga-area seasonal imagery research

## Purpose and population

Support reproducible imagery inspection, feature construction and initial model
experiments for agricultural extension investigation priorities. The study box is
33.40–33.50°E, 0.65–0.75°N, split into four approximately 5.5 km units. Current
district containment, crop identity and planting dates are unconfirmed. Maize is
the proposed extension workflow, not an image-derived label. No farmer identities,
customer boundaries or private field records are included.

## Sources and processing

Nine processed Sentinel-2 L2A acquisitions in May 1–15 windows across 2020–2024,
from the existing archived public-data run. Original IDs, offsets, quantification,
raw-array checksums and source metadata are preserved. Red/NIR and SCL are
available for every scene; RGB needs additional B02/B03, available for eight.

The approximately 20 m grid in UTM zone 36N is shared by all scenes. Reflectance
bands are averaged to this grid; SCL and WorldCover are nearest-neighbor sampled.
This resampling does not create finer observations. Decode physical reflectance
with band-specific XML offsets and quantification, exclude raw no-data and
invalid/nonnegative red/NIR failures, retain SCL 4/5 and reject a one-grid-pixel
buffer around other classes. Masked pixels remain NaN, not reconstructed values.

Historical ESA WorldCover 2021 class 40 is the cropland denominator. It does not
identify maize, current land use, parcel ownership or crop health. CHIRPS v3 final
May 11–15 pentads provide separate 0.05° area rainfall estimates for each year.
Rainfall is not soil moisture, a forecast or a cause label. The 2021 land-cover
product and later reprocessing mean this is retrospective reconstruction, not
proof of what an operational system could have used in 2020 or 2024.

## Artifact contract

- `manifest.json`: recipe/code/software/input fingerprints, source lineage,
  quality policy, grid, scene IDs, errors and asset hashes.
- `source-observations.json`: archived public observation/rainfall evidence.
- `observations.jsonl`: 36 scene/unit records with geometry, valid counts,
  coverage, feature values, IDs and spatial linkage. Excluded records remain.
- `assets/*-reflectance.tif`: float32 physical reflectance; band order is explicit
  and blue/green can be absent. NaN means no usable evidence.
- `assets/*-ndvi.tif`: float32 quality-masked NDVI, no-data NaN.
- `assets/*-quality.tif`: uint8 SCL, accepted-quality binary, historical-cropland
  binary, with explicit band descriptions. Zero in binary masks is meaningful.
- `stac/`: STAC 1.0.0 catalog/items using projection and raster extensions;
  assets carry checksums and grid metadata. Standard-schema validation is run
  separately with `scripts/validate_ml_dataset.py --schemas`.

Dataset IDs fingerprint source observations, raw arrays, processing recipe, code
and software versions. New raw assets, code or environment produce a new version.
Public previews use fixed RGB/NDVI scales; NDVI difference uses actual shared
valid pixels. Preview gamma is display-only and never a training feature.

## Training sample and features

One sample = one review unit in one May seasonal window/year, not one pixel or
one repeated acquisition. For each unit/year, median the accepted per-date
statistics. At least 60% usable historical-cropland coverage and 100 valid pixels
are required per accepted date. Target evidence must meet the 14-day research
freshness policy. No invalid NDVI is imputed from rainfall or other dates.

Features: NDVI median, NDVI interquartile range, red reflectance median, NIR
reflectance median, and separate five-day rainfall in mm. All
**20 area-season slots** are retained; the executed run has **12 usable earlier-year
samples and one usable target sample**, with the remaining slots excluded.
Sample/scene IDs, accepted dates, excluded reasons, source dataset and geometry
remain attached. The one-degree spatial grouping places this small area in one
group; it does not create four independent farms.

## Independent-label contract

`labels-template.csv` joins by `sample_id` and `dataset_id`. Required independent
records have `label_kind=field_visit`, `independently_verified=true`, a reference
record ID, dated visit, sampling method and a split. The reference ID is an opaque
operational identifier; private records stay outside the web directory.

Permitted outcomes: `useful_finding` or `no_useful_finding`, defined by the pilot
partner before evaluation. A suspected cause, satellite flag, weather event,
synthetic example or demonstration review is not a verified outcome. The current
21-day follow-up window is an engineering research gate, to be replaced/frozen
with the adviser/extension partner before prospective evaluation.

Split choices: `train`, `validation`, `test`. Rows remain tied to the actual
dataset-derived geography, not a group name supplied in the labeling CSV.
Require strict chronological order, disjoint spatial groups and a 10 km
bounding-box separation screen on a mean-radius sphere. Full cohort spatial QA
is still required; the screen is not cadastral/survey geometry. Train needs at
least three groups, 20 records and five examples in each class; validation/test
need at least 10 records, both classes and comparison checks beyond inspected
flags. These are engineering safeguards, not a power calculation or evidence of
scientific success. The present single-area, unlabeled archive cannot pass them.

## Bias, rights and intended use limits

Scene selection used low scene-cloud percentage within a bounded window, not a
random agricultural sample. Coverage and quality are uneven, and small mixed
fields, rotation, phenology and management confound vegetation comparisons.
WorldCover masks and resampling introduce additional error. Independent field
outcomes are absent. Uganda labels/validation do not transfer to Texas cotton.

Use source data under their terms and retain attribution: Copernicus Sentinel
data via Microsoft Planetary Computer; ESA WorldCover 2021 v200, CC BY 4.0;
UCSB Climate Hazards Center CHIRPS v3, public-domain rainfall data. The application
retains WorldCover attribution. No outreach or publication is authorized by the
creation of this dataset.
