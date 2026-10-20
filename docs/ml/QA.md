# Imagery and ML verification

20 October 2026, local development only.

## Automated and artifact checks

- Full suite: **33 tests passed**, including the original Texas/area tests.
  Added coverage checks band-specific reflectance offsets, raw no-data,
  cloud/buffer masks, common grids, feature exclusions, missing-year slots,
  train-only preprocessing, deterministic fitting, independent-label gates,
  spatial overlap despite renamed groups and preservation of annotated CSVs.
- The supervised success path uses explicitly synthetic unit-test cohorts;
  those test metrics are never exported as product evidence.
- Local HTTP checks verify exact COG byte ranges, HEAD lengths, unknown-asset
  rejection, out-of-range responses and same-origin feedback restrictions.
- All **27 COGs across nine scenes** passed checksum, CRS, transform, dimensions,
  COG layout and mask/value checks. STAC catalog/items passed the official
  core/projection/raster JSON schemas using pinned validator dependencies.
- An offline rebuild preserved the dataset ID and exact manifest bytes. A repeat
  fit preserved the model checksum and full novelty report. Versions/IDs and
  measured artifact sizes are in `RUN_SUMMARY.json`.
- Browser JavaScript passed syntax checks; Python compiled; Git whitespace
  checks passed. A test file-handle warning was corrected and the affected module
  reran successfully.

## Browser checks

- Two acquisitions show explicit dates and source records on a shared grid.
  RGB, masked NDVI, NDVI difference and quality overlay controls were exercised.
- The missing-RGB date displayed an unavailable message; selecting NDVI recovered
  the imagery. No replacement bands or pixels were generated.
- Unit selection/zoom and keyboard pixel inspection were exercised. When one
  source pixel is rejected, its value and the difference remain unavailable.
- A comparison-scene NDVI COG downloaded through the browser.
- ML research displayed the selected unit's unavailable state when imagery
  coverage failed, independently of the rainfall-based expert queue.
- Desktop 1366×900 and mobile 390×844 breakpoints were checked. The mobile page
  did not overflow horizontally; controls and image panels stack. Screenshots
  are in ignored `outputs/uganda/imagery-desktop.png` and `imagery-mobile.png`.
- No browser console errors were observed during the exercised workflow.

## Evidence limits

These checks establish software/artifact behavior, not geospatial/agronomic
accuracy. Independent mask/georegistration review, crop/season confirmation,
multiple spatial cohorts, independently dated field findings, sampling design
and prospective utility evaluation remain required. No calibrated confidence
or performance claim is supported. Printable HTML remains available;
PDF export/pagination has not been newly validated in this slice.
