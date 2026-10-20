# Numerical multispectral dataset

20 October 2026. Independent Vantage research within
[Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US). Uganda is active; Texas
is deferred and forestry remains with Vepris. No CropSight validation is used.

## Current executed result

The [current recorded run](MULTISPECTRAL_RUN.json) identifies dataset
`0291a271bc34131db96c4f96`: **18/18 frozen scenes, 54 validated COGs**, and six
observed frames for each study box. Container-token caching, expiry validation
and bounded retries recovered the eight previously failed acquisitions without
changing scene IDs. The diagnostic verified access to a previously failed band;
the prior failures did not establish permanent source absence. Tokens remain
in memory and are not exported. The implementation follows the container-token
pattern in the [Microsoft SDK](https://github.com/microsoft/planetary-computer-sdk-for-python/blob/main/planetary_computer/sas.py).

The full regression suite now passes **63 tests**. Complete cached replay and
sequence loading were verified. Crop-specific spatial eligibility remains
unconfirmed; historical crop-context coverage is available separately in the
[crop context report](CROP_CONTEXT.md). No new model training or accuracy result.

## Earlier partial milestone

The [recorded run](MULTISPECTRAL_RUN.json) identifies dataset
`ab014043eea7a612477a7c6c`: **10 of 18 requested scenes**, **30 validated COGs**
(53,759,415 bytes), with eight scenes unavailable after failed band acquisition.
The previous red/NIR archive still contains all 18 scenes. That does not mean
the same scenes supplied every additional band. No different acquisition was
silently substituted, and no permanent source unavailability is established.

Actual sequence loading passed for Iganga (4 frames), Lira (4 frames) and
Kasese (2 frames), each with six bands. These have substantial temporal gaps;
the Kasese sequence only includes the two 2023 windows. Whole-box quality
fractions do not establish crop eligibility. Independent field labels remain
zero and no model was fitted in this increment.

**55 regression tests passed.** Cached replay reproduced the same dataset ID,
manifest bytes and verified COGs. Its nonzero exit status correctly continues
to signal the eight missing scenes. A standalone loader test caught a conflict
with the host's unrelated PostGIS projection database; the loader now selects
the rasterio wheel's matching PROJ data, and an isolated subprocess regression
test covers that case. No browser/UI changes or new browser QA were performed.

## Implemented measurements

The dataset builder consumes the frozen [Uganda archive](ARCHIVE.md), preserves
its selected scene IDs, and reads B02, B03, B04, **B8A**, B11 and B12 plus SCL.
It never trains on RGB screenshots or coloured NDVI maps. Original public band
cutouts remain cached; source asset URLs, array hashes, XML metadata hash,
software versions, code hashes, transform and processing policy are recorded.

Physical surface reflectance = (DN + band-specific BOA_ADD_OFFSET) /
BOA_QUANTIFICATION_VALUE. XML band IDs differ from display band names; B8A
uses index 8, B11 index 11 and B12 index 12. Offsets must be present for baseline
4+ products. This follows the product metadata contract rather than assuming
one offset based on image date. See [Copernicus product documentation](https://sentiwiki.copernicus.eu/web/s2-products).

All bands share the established study-box grid, approximately 20m UTM36N:
average resampling for physical bands, nearest-neighbour SCL. Native 10m RGB
bands are aggregated; native 20m bands and any off-zone tile are reprojected.
Resampling is not extra spatial detail. Processing first reprojects DN then
applies each band's constant physical scaling, preserving the existing adapter.
No HLS spectral or BRDF harmonization is performed.

Quality policy: SCL classes 4/5, one-pixel buffer around rejected classes, raw
nodata withheld, finite nonnegative physical reflectance. Negative retrievals
are withheld conservatively, not clipped to zero; values above one are retained.
Each band has its own validity mask; the common mask requires all six valid.
No cloud filling, image generation, interpolation or artificial sharpening.

Per-scene outputs are three actual COGs: six-band float32 physical reflectance
with NaN nodata, six-band uint8 validity, and one-band common validity. Band
names/order, grid, layout, hashes and finite-value/mask consistency are checked.
Existing versioned outputs are checked before reuse; incomplete output folders
require inspection. Derived-raster STAC export is not added in this increment;
the archived source STAC and existing demo STAC remain separate.

## Reproduce and inspect

```powershell
# Scientific environment: requirements-ml.txt
# First run permits acquisition of missing public band cutouts:
python scripts/prepare_multispectral.py --allow-downloads
# Exact cached replay, no network:
python scripts/prepare_multispectral.py
# Explicitly select the nonempty partial dataset for inspection:
python scripts/prepare_multispectral.py --publish-partial
```

The default input is the 18-scene archive report. `--limit` permits a bounded
1–18 scene run, ordered latest year first across locations/windows. Failures
are explicit and the exit code is nonzero. Failed scenes are not silently
replaced with different acquisitions. A partial manifest is retained but does
not replace `latest.json` unless `--publish-partial` is explicitly supplied.
That option does not change its incomplete status or suppress the failing exit
code. It was used for the earlier partial milestone; the current pointer selects
the complete 18-scene dataset. Empty datasets never replace the pointer.
The existing browser/demo/model datasets stay intact.

Scene artifacts live at `outputs/africa/multispectral/<artifact_id>/`; dataset
manifests are `<dataset_id>.json`. IDs fingerprint physical inputs and recipes.
The dataset records the full source-archive hash and its requested scene IDs,
so incomplete runs cannot be mistaken for a complete request. Dataset manifests
include unlabelled numerical summaries for tabular baseline development:
six reflectance medians and narrow-NIR NDVI/NDMI. These summaries use common
valid pixels across the whole box, not confirmed crop pixels. `ndvi_b8a` is
explicitly different from the original B08-based NDVI; do not pool them blindly.

```python
import json
from pathlib import Path
from vantage.multispectral import load_sequence

root = Path("outputs/africa/multispectral")
latest = json.loads((root / "latest.json").read_text())
data = load_sequence(root / latest["manifest"], root, "iganga-study",
                     as_of="2024-05-31T23:59:59Z")
# data["reflectance"]: T,C,H,W physical float32 values, retaining NaNs
# data["band_valid"]: T,C,H,W; data["common_valid"]: T,H,W
# data["frames"]: actual observation dates and gaps in days
```

The sequence loader verifies asset checksums and spatial/band consistency,
rejects paths outside the dataset root, duplicates and mixed grids, and applies
an acquisition cutoff. It does not fill missing dates or replace NaNs. A
training adapter must explicitly use masks rather than treating missingness as
zero reflectance. No normalization is fitted here; future learned scaling
must use training regions/seasons only. Cutoff filtering does not establish
historical publication-time availability.

## Model evaluation boundary

These are sparse May/November observations across 2022–2024, not a dense
phenological sequence or proof of comparable crop stages. Crop masks,
planting dates, crop identity and independent field outcomes remain absent.
Do not fit a supervised agricultural model on invented labels or use the
imagery-only anomaly flag as ground truth. Whole-box indices are investigation
context, not a diagnosis or irrigation instruction.

The [Prithvi publisher model card](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-100M-TL)
uses chronological HLS 30m reflectance in this spectral order. Six matching
Sentinel-2 channels at 20m are **not** the HLS product. Every new scene and
dataset remains `foundation_ready=false`. Next model work needs a pinned,
licensed checkpoint, exact preprocessing/normalization adapter, compatible
quality-aware HLS inputs, and independent held-out regional/seasonal outcomes.
No weights, embeddings, encoder training or agricultural accuracy are supplied.

Baseline and encoder comparisons must use the same permitted crop/season
cohorts, spatial buffers, chronological exclusions and field outcome rubric.
Use useful findings at inspection capacity with the existing
[evaluation protocol](EVALUATION.md), not impressive-looking map colours.
