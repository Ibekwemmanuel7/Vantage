# Iganga-specific radar terrain and viewing research checks

24 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/check_gap_radar_quality.py --config configs/iganga_gap_quality.json --online
python scripts/check_gap_radar_quality.py --config configs/iganga_gap_quality.json
```

The reusable fixed-cohort workflow covers three Iganga ascending orbit-028
passes. It does not inherit Lira orbit-029 results. Config fixes the 30 m
derivative grid, 180 m local padding, 5/10/15-degree slope sensitivity,
5–85-degree local-incidence guards, 0.25-degree annotation consistency tolerance,
5 km visibility horizon, 15 m steps and 5 m engineering clearance guard.
These settings were fixed before inspecting this cohort's terrain/annotations.

The workflow reuses tested mathematics/readers without changing earlier Lira
scripts/reports. It checks the source radar catalog, numerical artifacts and
grids. Independently acquired elevation is Copernicus DEM GLO-30 tile
`Copernicus_DSM_COG_10_N00_00_E033_00_DEM`: a surface model, not surveyed bare
earth or verified contemporaneous 2023 terrain. Native clips, annotation bytes,
lineage hashes, derived arrays and code identities stay in ignored outputs.
No authenticated CDSE processing or quota is used.

## Actual slope sensitivity

| Neighborhood maximum slope threshold | Lower-slope pixels | Elevated-slope pixels | Unknown |
| --- | ---: | ---: | ---: |
| 5 degrees | 285,110 | 22,911 | 0 |
| 10 degrees | 308,021 | 0 | 0 |
| 15 degrees | 308,021 | 0 | 0 |

Whole-box counts are identical across passes because the DSM and numerical radar
coverage are shared. No threshold is calibrated against crop outcomes, radar
differences or a trusted terrain processor. Mapping derivatives onto the optical
grid does not create independent 20 m elevation information.

## Verified acquisition-specific geometry

Follow RTC `derived_from` GRD links and actual SAFE manifest references, checking
VV annotation size/MD5 on download and cached replay. Product parsing verifies
identity, absolute orbit, acquisition containment, Earth-fixed orbit states and
geolocation support. No orbit/vector extrapolation is permitted. Maximum
annotation/orbit incidence discrepancy is about 0.002402 degrees, within the
fixed tolerance for all three passes.

| Acquisition | Locally unflagged | Local risk / unknown | Clear within sampled 5 km | Joint numerical/local/bounded-clear |
| --- | ---: | ---: | ---: | ---: |
| 29 May 2023 | 308,021 | 0 | 308,021 | 308,021 |
| 10 June 2023 | 308,021 | 0 | 308,021 | 308,021 |
| 22 June 2023 | 308,021 | 0 | 308,021 | 308,021 |

Approximate local incidence spans about 31.60–48.45 degrees. The sightline test
uses an expanded independent elevation window and 334 samples per ray. Missing
heights cannot pass; detected obstructions take precedence over missing support
farther away. Counts are study-box analysis pixels, not confirmed fields/crops.

Report: `outputs/africa/gap-quality/eafa754ab92ade35e4c4/report.json`.
Offline replay reproduced all slope, geometry and visibility arrays. Changed
artifacts are rejected, not overwritten. A final report is written only after
the complete cohort succeeds; acquisition failure cannot become a clear result.

## Remaining gate

This local/finite-range approximation omits subcell and beyond-5-km obstructions,
full layover, curvature/refraction/geoid corrections, radiometric verification
and independent processor agreement. The DSM/engineering guard does not establish
calibrated uncertainty. No obstruction-positive study pixels are present, limiting
any future sensitivity claim.

`independent_processor_status=awaiting_exports`,
`radar_illumination_confirmed=false` and `usable_for_model_training=false` remain
explicit. Training/validation orbits differ and need explicit transfer evaluation.
No radar-assisted model is trained or optical values filled. Independent CDSE
outputs, confirmed crops/calendars, field outcomes and untouched evaluation remain
missing. Later-reprocessed optical inputs cannot establish 2023 operational
availability. No diagnosis or irrigation prescription is supplied; forestry stays
with Vepris and no CropSight validation transfers.

Verification: 103 focused tests passed. New checks exercise immutable array replay
and offline SAFE integrity without token requests; existing checks cover provider
exports, pairing, slope/viewing/visibility, raster IO and cloud-gap regressions.
