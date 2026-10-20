# Uganda multi-location imagery archive

20 October 2026. Implemented bounded public-data acquisition, separate from the
original Uganda demo and model training dataset. No independent field labels.

## Recorded run

The [compact run record](ARCHIVE_RUN.json) reports **18/18 catalog windows**,
**129 distinct STAC items** and **18 processed cutouts** across three locations,
two calendar windows and three years. All 18 artifact checksums were verified.
Twelve candidate download attempts failed before alternate candidates succeeded;
those failures remain in the private full report. There are zero independent
field labels and no new fitted model.

Four cutouts have less than 60% whole-box usable coverage, including one with
zero usable pixels. Sixty percent here is a descriptive summary, not a newly
validated eligibility threshold. Kasese November is particularly sparse in
these selected scenes: about 1.8% in 2022, 51.0% in 2023 and 0% in 2024.
No crop condition or cause follows from these coverage measurements.

The full regression suite passed **45 tests**, including four archive tests
covering leap-year intervals, bounded geometry, truncated searches, missing
assets and separation of scene cloud metadata from measured usable coverage.
Python compilation and whitespace checks passed. Offline catalog replay passed.
Network acquisition needed approved access outside the restricted sandbox.
The existing browser desk was not modified or revalidated in this increment.

## Scope and selection

`configs/uganda_archive.json` specifies analyst-selected 0.1-degree study boxes
near Iganga, Lira and Kasese, May and November in 2022–2024: 18 windows. These
are geographic feasibility probes. Administrative containment, contemporary
cropland, crop identity and planting calendars are unconfirmed. May/November
are calendar windows, not a claim of comparable crop stages across regions.

Every monthly Sentinel-2 L2A catalog response is archived with request URL,
retrieval time and checksum. No scene-cloud cutoff hides cloudy observations.
Truncated responses fail rather than being presented as complete. Empty
windows and missing required assets remain explicit. Catalog completeness
means the query completed, not complete satellite observations or valid pixels.

Within a window, try at most three full-bounding-box candidates in increasing
scene-cloud order, breaking ties by item ID. Every failed attempt is retained.
This is availability-biased feasibility sampling, not a representative seasonal
series. Different tiles/processing versions may depict the same acquisition;
catalog item counts are not independent observations. Only one successful
candidate per window enters this initial processing pass.

## Run and replay

```powershell
# Download public metadata; archive before interpreting availability.
python scripts/expand_uganda_archive.py --online
# Replay catalog inventory offline, with missing archives treated as failures.
python scripts/expand_uganda_archive.py
# Real raster cutouts: latest-year location/window pairs first, then references.
python scripts/expand_uganda_archive.py --online --pixels 18
```

Raw responses and reports are under `outputs/africa/archive/<plan_id>/`.
`inventory-report.json` records catalog feasibility; `pixels-report.json`
records the explicit pixel budget and results. Each report can be regenerated;
source response files are not silently replaced. The plan ID fingerprints the
configuration; report hashes also record the acquisition-script version.
This is not yet the full content-addressed model dataset contract. No archive
observations are silently appended to training or public desk data.

Pixel processing reuses physical red/NIR decoding, band offsets, shared 20m
UTM36N grid, SCL classes 4/5, one-pixel rejection buffer and NDVI nodata rules.
Usable fraction is over the **whole study box**, not historical or current
cropland. Water, built-up areas and terrain differences affect it. Compare
neither these fractions nor box medians as crop performance without a proper
crop/land-cover and seasonal eligibility design.

Processed cutouts are compressed NPZ analysis caches containing NDVI, validity,
affine transform and CRS. Checksums and existing-array verification detect
changed output before reuse. They are not COGs, a STAC derived-raster catalog,
browser imagery or foundation-model inputs. The original COG/STAC pipeline
remains unchanged. CHIRPS, field masks, multitemporal feature cubes and cloud
coverage assessment across every acquisition are not expanded by this tool.

## Foundation-model candidate contract

The publisher's [Prithvi EO 2.0 model card](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-100M-TL)
specifies chronological HLS 30m images in physical reflectance, with blue,
green, red, narrow NIR, SWIR1 and SWIR2 in that order. Raw Sentinel-2 B02,
B03, B04, B8A, B11, B12 asset presence is useful acquisition planning metadata,
but is not HLS harmonization or proof of model compatibility. The catalog
report deliberately separates multispectral asset availability from actual
pixel processing. Current processed B04/B08 NDVI caches are incompatible.

Before a candidate fit: pin a licensed checkpoint/revision and preprocessing
recipe; obtain compatible HLS scenes and quality masks; verify units, band
order, grids, temporal ordering, normalization and missingness; freeze held-out
regions and seasons. Compare with seasonal rules and tabular baselines on the
same independent field outcomes. No model weights, embeddings, inference or
foundation-model training are added here. Earthdata access and field outcomes
remain external dependencies; no agricultural accuracy is claimed.

## Independent outcomes

For 2022–2024 reconstructions, obtain **contemporaneous archived** extension or
field records with permissions, observation dates, geolocation, crop/stage,
finding rubric and provenance. A visit today cannot verify crop conditions in
2024. Expert review of the same satellite imagery is not independent ground
truth. Keep uncertain/unmatched records separate from verified outcomes.

For a future prospective pilot, establish current crop and boundary references,
freeze predictions before visits, and collect both flagged and unflagged field
outcomes using the [sampling protocol](EVALUATION.md). Existing history cannot
be called a historic early-warning replay without contemporaneous source
publication and arrival timestamps. The expanded archive is retrospective.
