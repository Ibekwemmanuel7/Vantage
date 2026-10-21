# Kween radar context: measured values, unverified agricultural suitability

Independent Vantage research within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda remains the priority; Texas stays deferred and forestry remains with Vepris.
No CropSight validation is inherited.

The [optical follow-up](KWEEN_TEMPORAL.md) ended with stale evidence despite recent
acquisitions. This increment checks whether Sentinel-1 supplies a separate
observation stream during that interval. It does not fill optical gaps, classify
crop condition, retrieve soil moisture or train a model.

## Source and access findings

The primary source is Microsoft's [Sentinel-1 RTC collection metadata](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc),
with ESA Sentinel-1 acquisitions processed by Catalyst and hosted by Microsoft.
It describes terrain-corrected gamma0 intensity, with VV/VH assets and a -32768
nodata value. The [publisher's example](https://github.com/microsoft/PlanetaryComputerExamples/blob/main/datasets/sentinel-1-rtc/sentinel-1-rtc-example.ipynb)
demonstrates `10 * log10(intensity)` for dB conversion. Attribution: ESA/Copernicus,
Catalyst and Microsoft; collection license [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The metadata and example say that an account is needed. However, the archived
anonymous token probe returned **HTTP 200**, and bounded VV/VH window reads for
all three selected passes succeeded on this run. That observed result does not
guarantee future access or anonymous access to every product. No account was
created, key discovered or credential requested; tokens remained in memory and
were not persisted in run records. Public summaries omit raster access URLs.

## Frozen design and actual coverage

Separate fixed plans cover [catalog feasibility](../../configs/kween_2023_radar.json)
and [numerical pixel processing](../../configs/kween_2023_radar_pixels.json).
The latter was frozen after metadata inspection and before radar pixel inspection.
Both are exploratory analyses, not blinded validation or registered experiments.
They inherit the original Ngenge box and June 5, 2023 end-of-day acquisition cutoff.

Require the actual item polygon to cover the whole box: a bounding-box intersection
is insufficient for oblique radar footprints. Require IW, VV/VH and complete
platform/orbit metadata. Count alternate slices/versions from one platform and
absolute orbit as one pass. Keep platform, relative orbit, direction, mode and
polarizations separate when comparing observations.

The catalog contains **three eligible passes**, all **Sentinel-1A, relative orbit
130, ascending, IW, VV/VH**. There is one orbit group, not three independent regions.
The numerical run processed **3/3 passes**, writing **nine scene COGs and two
descriptive change COGs** from six bounded native clips.

| Acquisition (UTC) | Historical-cropland numerical support | Median VV (dB) | Median VH (dB) |
|---|---:|---:|---:|
| May 12, 15:57 | 100% | -9.002 | -15.257 |
| May 24, 15:57 | 100% | -8.151 | -14.231 |
| June 5, 15:57 | 100% | -9.979 | -15.514 |

**Numerical support is not independently terrain-screened usable agricultural
evidence.** The analyzed historical-crop mask has 105,091 analysis cells; these
are correlated measurements, not independent field outcomes. The collection
applies terrain correction and describes shadow flagging, but the returned assets
do not supply separate layover/shadow or incidence-angle quality layers for our
independent screen. `terrain_screen_verified` and `agronomic_review_eligible`
remain false. Current crop identity and planting stage are unconfirmed.

For the withheld May 31 morning optical observation, the latest prior radar pass
is May 24, about **6.66 days** earlier. For June 5 at **07:46 UTC**, it is still
May 24, about **11.66 days** earlier. The June 5 radar pass at **15:57 UTC** must
not leak into that morning comparison. At the end-of-day cutoff it is about
**0.335 days** old, but historical product delivery is unverified.

## Numerical contract and limits

Read bounded native windows, not full remote products. Reject nonfinite,
nonpositive and nodata intensity samples; average valid **linear intensity** onto
the original 20m analysis grid. Separately resample the native positive-sample
fraction, requiring at least 80% support per polarization per analysis cell.
Convert retained intensity to dB only afterward. Preserve separate VV/VH intensity,
support fractions and the common numerical-validity mask as COGs. Do not average
dB values, clip numerical returns or infer that nominal pixels are independent.

Summaries require 60% numerical coverage of historical cropland and 100 pixels.
Consecutive comparisons require the same track and sufficient common support.
Both pairs pass those numerical checks. Median per-pixel changes are:

| Pair | VV change | VH change |
|---|---:|---:|
| May 24 minus May 12 | +0.762 dB | +0.919 dB |
| June 5 minus May 24 | -1.628 dB | -1.110 dB |

These are changes in measured radar return, **not crop-stress or crop-loss
estimates**. A median of per-pixel changes differs from a difference of observation
medians. Same-track matching is necessary but does not establish equal incidence
conditions, processing stability, crop stage or causal interpretation. No speckle
filter, anomaly threshold or agricultural significance test is introduced.

Copernicus describes [multiple radar scattering mechanisms](https://dataspace.copernicus.eu/news/2024-8-6-announcing-sentinel-1-monthly-mosaics-copernicus-data-space-ecosystem).
Vegetation, surface properties, geometry and other factors affect the return;
this three-pass series cannot isolate a cause. It does not validate the public
crop-loss account. Optical evidence remains `stale_research_context`; no radar
value is substituted for missing NDVI, and no radar score enters the scouting queue.

## Reproduce, verify and inspect

Use the existing `requirements-geo.txt`, optional `requirements-radar.txt` for
geometric checks and `requirements-reporting.txt` for the plot. The catalog step
can use the tracked compact optical summary. Exact pixel replay requires the
original local crop-context archive and cached native clips, which are not in Git.

```powershell
python scripts/inspect_radar_coverage.py --allow-downloads --write-summary
python scripts/build_radar_series.py --allow-downloads --write-summary
python scripts/verify_radar_series.py
python scripts/plot_radar_series.py
# Download-disabled cached replay:
python scripts/inspect_radar_coverage.py
python scripts/build_radar_series.py
python -m unittest discover -s tests -v
```

Catalog run `fb0cf9322806ed8046aaa01c` and numerical run
`c193f0b7728d5ea5b8f36809` have compact tracked
[catalog](KWEEN_RADAR_RUN.json) and [pixel](KWEEN_RADAR_PIXELS_RUN.json) records.
Outputs and native clips remain under `outputs/africa/radar/` and
`outputs/africa/radar-pixels/`. The inspected figure is
`outputs/africa/radar-pixels/kween-radar.png`; its ±6 dB display limit does not
change the underlying numerical values.

Verification checks frozen plans, code/source/clip/COG hashes, geometric cohort
selection, timestamps, orbit groups, masks and band/grid contracts. It resamples
all six native clips again, reproduces all eleven COG arrays and recomputes the
evidence and pair changes. The **97-test regression suite passed**, including
linear-before-log resampling, invalid native support, cross-orbit rejection and
the morning-versus-afternoon cutoff. Increment lint checks passed.

Download-disabled replay preserved both manifests byte for byte:

- Catalog SHA256: `d963b5e2789b8c804d0e065d037a1d197eda11380526f786cad9d5b354afa6b8`.
- Pixel SHA256: `045be31dcc1e75d0f7574bac71528ee69069d56aaebc9c8e4c508d04be4a794e`.

These are local frozen-run replay results. Fresh acquisition can produce a new
plan timestamp/run identity; full remote-product checksums were not verified by
downloading entire multi-gigabyte products. Native cutouts and their hashes are
the numerical replay inputs.

## Next gates

Add an independently inspectable terrain/incidence-quality screen, assess
processing consistency and characterize speckle and temporal variability across
additional seasons. Establish confirmed crop boundaries/calendars and independent
dated outcomes before fitting or evaluating sensor fusion. Compare optical-only,
radar-only and combined candidates on held-out regions/seasons and actual
inspection capacity. This single event supplies no supervised labels, accuracy
estimate, cause diagnosis, irrigation recommendation or operational early warning.

The [executed surface-slope sensitivity](KWEEN_TERRAIN.md) now supplies a separate
DSM-based risk proxy. It preserves the original radar results and does not mark
illumination or agricultural eligibility as verified.
