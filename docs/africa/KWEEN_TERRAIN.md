# Kween surface-slope screening and sensitivity

Independent Vantage research within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda remains the development priority; Texas is deferred. Forestry stays with
Vepris, and no CropSight validation is inherited.

This increment adds an independently sourced **surface-slope risk proxy** to the
[radar numerical slice](KWEEN_RADAR.md). It is not a complete radar terrain-quality
screen. Passing this proxy does not confirm radar illumination, local incidence,
absence of layover/shadow or agricultural suitability. Radar remains separate
from optical observations and ineligible for agricultural ranking.

## Source and fixed analysis

The [Copernicus GLO-30 collection](https://planetarycomputer.microsoft.com/api/stac/v1/collections/cop-dem-glo-30)
provides a nominally 30m digital **surface** model, including vegetation and
structures. The [producer's data description](https://copernicus-dem-30m.s3.amazonaws.com/readme.html)
documents the TanDEM-X-derived product and its COG distribution. This is not
surveyed bare-earth terrain or confirmed 2023 field condition. Source attribution:
Copernicus DEM, European Space Agency, DLR/Airbus; Sinergise processing and
Microsoft hosting. Its source-specific [Copernicus DEM license](https://spacedata.copernicus.eu/documents/20126/0/CSCDA_ESA_Mission-specific+Annex.pdf)
applies; do not transfer the radar collection's CC BY license to this product.

The [fixed configuration](../../configs/kween_2023_terrain.json) pins radar run
`c193f0b7728d5ea5b8f36809`, the original box and a 30m metric derivative grid in
EPSG:32636 with 180m padding. The local plan was frozen before elevation inspection.
This remains exploratory research after inspecting the original event, not a
blinded or independently validated study.

Read one bounded native elevation window from item
`Copernicus_DSM_COG_10_N01_00_E034_00_DEM`. Reproject elevations and finite-input
support bilinearly to the 30m grid; require at least 0.999 support. Negative or
zero elevations are valid measurements, not nodata. Compute surface slope from
metric finite differences and require complete 3×3 derivative neighborhoods.
Then compute a 3×3 maximum slope, again requiring complete support. Missing
heights and unsupported derivative neighborhoods remain unknown.

Transfer this maximum-slope surface to the original radar grid using nearest
neighbor. This does not create independent 20m elevation detail. Class codes are
**0 unknown, 1 lower-slope proxy, 2 elevated-slope proxy**. Preserve categorical
nearest-neighbor overviews separately from continuous slope/elevation rasters.

The **primary threshold is 10°**, with fixed **5° and 15° sensitivity alternatives**.
These are analyst-selected research settings, not accepted SAR artifact thresholds
or empirically calibrated agricultural rules. No setting is chosen after observing
its effect on radar values. This direction-independent slope measure does not
use sensor-facing range slopes, orbital vectors, local incidence or nonlocal
line-of-sight terrain occlusion.

## Executed findings

Run `f087c0ca9dd977c4a3ae74d0` produced **three terrain COGs and six filtered-change
COGs**, all independently recomputed from the cached numerical inputs.

| Fixed threshold | Historical-cropland cells retained | Retained fraction | Elevated-slope cells excluded | Unknown cells |
|---|---:|---:|---:|---:|
| 5° sensitivity | 100,388 | 95.52% | 4,703 | 0 |
| **10° primary** | **103,508** | **98.49%** | **1,583** | **0** |
| 15° sensitivity | 104,648 | 99.58% | 443 | 0 |

The denominator is always the **original 105,091 historical-cropland cells**.
Excluded cells are not silently removed from the coverage denominator. These
correlated cells are not independent field observations, and zero unknown cells
does not establish elevation accuracy or the absence of original product edits.
The catalog supplies the DSM data asset; independent elevation-error and
source-filling/edit masks have not been incorporated.

Mask the original VV/VH intensities with each slope proxy before recomputing
consecutive, same-track radar changes. Retain the original 60%/100-pixel numerical
support gates. All six comparisons meet those numerical gates. For June 5 minus
May 24, the median per-pixel changes are:

| Filter | VV change | VH change |
|---|---:|---:|
| Original numerical support | -1.628 dB | -1.110 dB |
| 5° sensitivity | -1.693 dB | -1.154 dB |
| **10° primary** | **-1.651 dB** | **-1.126 dB** |
| 15° sensitivity | -1.635 dB | -1.114 dB |

The medians change little under these selected rules in this one box. This is a
descriptive sensitivity finding, not statistical robustness across regions,
proof that terrain effects are negligible or evidence of crop stress. Surface
structures, vegetation, illumination geometry, speckle, processing and crop stage
remain possible contributors. No cause is diagnosed and no irrigation action is
recommended. The original optical state remains `stale_research_context`.

## Reproduction and checks

Use the existing geography dependencies and optional reporting dependencies.
The pinned original radar/crop-context archive is required locally. It and the
large raster caches are not distributed in Git; a fresh checkout cannot recover
the exact frozen run from compact records alone. From the repository root:

```powershell
python scripts/build_terrain_screen.py --allow-downloads --write-summary
python scripts/verify_terrain_screen.py
python scripts/plot_terrain_screen.py
# Download-disabled cached replay:
python scripts/build_terrain_screen.py
python -m unittest discover -s tests -v
```

The [compact executed record](KWEEN_TERRAIN_RUN.json) is tracked. Outputs remain
under `outputs/africa/terrain/`; the inspected figure is
`outputs/africa/terrain/kween-terrain.png`. No live feed or dashboard integration
is added by this research slice.

Verification checks the frozen plan, code/source/native-clip hashes, metric
grids, original crop mask and parent radar inputs. It recomputes the elevation
reprojection, slope neighborhoods, all proxy classes, retained counts, numerical
summaries and all nine COG arrays, including layout and band contracts. A
download-disabled replay preserved identical manifest bytes, SHA256
`1544123acda5c39829bf787ce900db6d04516633d1c51b4e2f7e18d0ad3c5ae1`.

**103 regression tests passed**, including analytic flat/planar slopes, unequal
metric cell spacings, negative/zero elevations, missing-neighbor propagation,
threshold boundaries, monotonic sensitivity masks and retention against the
original denominator. Increment lint checks passed. No new trained model,
supervised labels or agricultural accuracy result is reported.

## Remaining gate

Keep `terrain_risk_proxy_applied=true`, `terrain_screen_verified=false`,
`radar_illumination_confirmed=false` and `agronomic_review_eligible=false`.
[Copernicus' SAR processing documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html)
distinguishes local-incidence and shadow-related outputs; a surface-slope
threshold does not replace them. The next geometry step needs acquisition-specific
viewing/orbit inputs, a documented local-incidence and layover/shadow method,
adequate surrounding terrain for occlusion and comparison with a trusted
processor. Independently dated crop outcomes and confirmed field/calendar data
are still required before evaluating radar's value for scouting priorities.
