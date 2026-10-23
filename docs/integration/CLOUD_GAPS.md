# Quality audit before cloud-gap modeling

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

The offline `audit_recent_quality.py` command reads the preceding inventory,
observations and cached B04/B08/SCL arrays and reflectance metadata. It performs
no downloads, interpolation, mask relaxation or model training. Source inventory
and catalog checksums are verified; raw array hashes and observation-report
identity are recorded in `pixels/quality-audit.json`. Input arrays must reproduce
the original accepted-pixel count.

Rejection stages are ordered and exclusive: source SCL exclusion, mask buffer,
source nodata, invalid physical reflectance, nonpositive red-plus-NIR, invalid
NDVI. Their total plus accepted pixels must account for the entire grid. Later
zero counts mean no additional exclusions among surviving pixels, not that
masked pixels were independently verified numerically correct.

Actual 20 October 2026 observations:

| Study box | SCL 8 | SCL 9 | SCL 10 | Accepted |
| --- | ---: | ---: | ---: | ---: |
| Iganga | 254,636 | 53,284 | 101 | 0 |
| Lira | 255,330 | 690 | 51,448 | 0 |
| Kasese | 308,300 | 832 | 0 | 0 |

All exclusions occur at the source-classification gate. These are provider SCL
labels, not independently verified clouds or ground truth about crop condition.
This audit does not independently verify raster geolocation or source quality.
The command uses rasterio's matching PROJ database to avoid system PostGIS
runtime conflicts and normalizes cached XML text consistently with the builder.

## Next evaluation gates

1. Process a bounded multi-date sequence, retaining each date and mask. Build
   coverage summaries before selecting a modeling cohort.
2. Compare causal last-clear-observation and temporal baselines. Future imagery
   cannot enter historical decisions; retrospective interpolation is separate.
3. Evaluate radar features as separate observations with geometry/quality checks.
4. Benchmark an uncertainty-aware ML candidate using withheld clear observations,
   realistic cloud footprints and held-out seasons/locations. Include NDVI error,
   anomaly preservation, false flags and uncertainty calibration; visual appeal
   alone is insufficient. Synthetic masking does not validate every real cloud gap.
5. Preserve observed/estimated/withheld provenance and maximum supported gap
   duration. Predicted pixels must not count as observed clear coverage or silently
   refresh observation dates. Withhold unsupported estimates.

No cloud-gap model, new accuracy claim, field diagnosis, irrigation prescription
or operational field priority is supplied by this release. Confirmed crops,
planting calendars and independent field outcomes remain missing.
