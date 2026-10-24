# Dated observed field vegetation change

Vantage now compares two observed NDVI artifacts on common valid pixels inside
the same declared field boundaries. It produces a private JSON report and a
masked, georeferenced GeoTIFF of **after minus before NDVI**. Negative values
mean lower observed NDVI. They do not identify pests, disease, nutrient shortage,
water stress or a need to change irrigation. This is a research change map,
not a validated anomaly detector or operational scouting recommendation.

No real consented farm boundaries or independent field outcomes have been
supplied. This increment was exercised with synthetic fields and observations
only; no new farm-level result, training label or model was created.

## Inputs and replay

Use dependencies in `requirements-field.txt`. Copy
`configs/field_change_template.json` into `outputs/private`, then populate it
with two original observed optical NPZ artifacts and a reviewed GeoJSON boundary
collection following the [field-pixel contract](FIELD_PIXELS.md). All paths are
resolved relative to the pair JSON; absolute paths are also accepted. The
template contains no real dates, hashes, fields or pixel data and cannot run
until completed. No example farmer observations are fabricated.

For both `before` and `after`, provide:

| Field | Meaning |
| --- | --- |
| `pixels`, `sha256` | Existing observed NDVI NPZ path and expected hash from its processing report |
| `acquired_at` | Actual acquisition timestamp, with timezone |
| `available_at` | When all input and processed evidence became available, with timezone |
| `source_ref` | Distinct traceable scene/processing references for the two dates |
| `recipe_ref` | Same versioned optical processing and quality recipe for both dates |

Set `boundaries` to the field GeoJSON and `cutoff` to the decision timestamp.
Use the actual receipt/processing date for retrospective work; do not backdate
availability to the historical acquisition date. Acquisition <= availability <=
cutoff is checked independently for both dates. Recipe and availability are
operator declarations, not authenticated provenance. A matching recipe string
does not prove matching sensors, radiometric calibration or actual processing;
audit the source reports and metadata. Predicted or filled cloud-gap pixels are
not valid inputs to this observed-change workflow.

```powershell
python scripts/compare_field_pixels.py outputs/private/field-pair.json --out-dir outputs/private/field-change-001
```

The output directory must be new and beneath ignored `outputs/private`. Existing
packets are never overwritten. Keep reports private: they contain field IDs,
season/crop declarations, geometry hashes and private source references.

Outputs:

- `report.json`: original date summaries, field/common pixel support, eligibility
  blockers, paired mean/median change, exploratory increasing/declining pixel
  counts, input hashes, GeoTIFF hash, dates, policy and software versions.
- `observed-change.tif`: float32 single-band GeoTIFF on the input grid, with an
  internal valid-data mask, NaN nodata, acquisition/cutoff tags and a band
  description. It is a local analysis GeoTIFF, not a claimed COG, map server or
  customer-dashboard layer.

The mask uses GDAL's valid-data convention (nonzero means valid), as described
in the [Rasterio mask documentation](https://rasterio.readthedocs.io/en/stable/topics/masks.html).
The raster covers the union of eligible fields. Overlapping declarations are
not dissolved or independently sampled; a pixel shared by fields appears once
in this map. Consult each field's blockers separately. If every field is
withheld, a fully masked map is written, rather than inventing zero change.
An interrupted write may leave an incomplete directory; investigate it and
use a new output directory. Only a completed report with a matching raster
hash constitutes a complete local packet.

## Comparison safeguards

Both dates must use exactly the same CRS, transform and dimensions; acquisition
times must increase. No imagery alignment, resampling or implicit reprojection
is performed. One boundary collection, version and declared crop/season context
is applied to both dates. A boundary change requires separately reviewed
reprocessing; results from different boundary versions are not subtracted.
The tool cannot prove the crop or management system stayed unchanged between dates.

The defaults require full field footprint coverage, at least nine accepted
pixels, and at least 70% usable field support on each date **and their common
intersection**. Two individually clear observations can still have too little
overlapping support. Missing observations never become zero NDVI or zero change.

The latest observation must be no older than seven days at cutoff. The pair
interval must be at most 21 days, allowing the earlier reference to be up to
28 days old at cutoff. Older/latest-stale dates are retained in the report
with blockers, but do not contribute to the change raster. These temporal and
coverage defaults are research engineering policies requiring local validation,
not established crop-stage rules. The library permits explicitly declared
alternative policies; the CLI uses the defaults.

Statistics are computed from per-pixel differences on the exact same common
support, not by subtracting independently sampled date medians. Counts of pixels
below -0.1 or above +0.1 are exploratory absolute NDVI-change thresholds, not
calibrated crop-health alerts. Grid pixels are correlated and are not independent
farms. No confidence interval or percentage yield loss is inferred.

## Next dependencies

We still need consented field boundaries, confirmed crops and calendars, suitable
dated observations and independent scouting findings. Crop-stage context,
seasonal baselines, independent anomaly evaluation, field-edge uncertainty and
customer-dashboard integration remain pending. The report is not automatically
exported into a frozen visit protocol. Uganda is Vantage's first active pilot;
the component is market-independent. Forestry remains with Vepris and CropSight
validation does not transfer.

Verification on 24 October 2026: **34 tests passed** across dated field change,
field pixels, recent pixels, field protocols and field intake. Checks include
known paired change, common-support rejection, staleness/interval gates, grid
and recipe rejection, GeoTIFF data/mask/tag/hash round-trip, valid zero change,
input hash rejection and overwrite protection. CLI help and `git diff --check`
passed. All field-change tests used synthetic inputs; no real field comparison
or new agricultural accuracy result was produced.
