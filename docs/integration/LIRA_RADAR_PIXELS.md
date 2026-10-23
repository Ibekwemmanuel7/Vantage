# Lira fixed-track numerical radar sample

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/process_gap_radar.py --online
python scripts/process_gap_radar.py
```

The first permits bounded native VV/VH reads; the second requires cached clips
and does not request access tokens. Actual offline replay reproduced derived
arrays. Requires the existing scientific runtime and prior Lira catalog/optical
artifacts. Source rasters, access tokens and derived arrays are not committed.

`configs/lira_gap_radar_pixels.json` pins the catalog checksum, optical sequence,
ascending Sentinel-1A relative orbit 029 and maximum two passes. This plan was
fixed before pixel inspection. Descending orbit 123 is not merged into the series.
The catalog, source sequence and optical grid artifact identities are verified.

Asset metadata must describe gamma-naught float32 with nodata -32768 and identity
scale/offset. The existing native reader also checks raster count, nodata and CRS.
Bounded native windows are read on the provider grid, with positive linear
intensity averaged before conversion to dB. Reprojected native valid-support
fraction must be at least 0.8 per polarization. Exact optical CRS, affine grid
and shape are used; matching grids do not prove independent co-registration.

## Actual measurements

| Acquisition, UTC | Numeric pixels / total | Median VV, dB | Median VH, dB |
| --- | --- | ---: | ---: |
| 4 June 2024, 16:06 | 307,468 / 307,468 | -6.1543 | -12.3011 |
| 16 June 2024, 16:06 | 307,468 / 307,468 | -8.2273 | -14.1345 |

Both passes have 100% positive numerical support under this recipe. On common
pixels, median per-pixel later-minus-earlier differences are -2.0943 dB VV and
-1.8046 dB VH. These are descriptive backscatter differences, not crop-condition
labels or evidence of moisture loss. Median differences are not differences of
the separate medians. No speckle filtering, crop mask or confirmed field records
are applied. SAR sampling spacing does not equal independent spatial resolution.

Generated report:
`outputs/africa/gap-radar-pixels/b9e3ac527f496525a5d7/report.json`.
It retains native/derived artifact hashes, source and implementation identities,
grid and units. Derived NPZ arrays must match on replay rather than silently
overwrite earlier values. Source native clips are cached; independent source
processor agreement is not established by these internal checks.

`terrain_screen_verified=false`, `usable_agricultural_evidence=false` and
`optical_values_imputed=false` remain explicit. Positive gamma0 is not evidence
of correct illumination, absence of layover/shadow/noise, a healthy crop or
agricultural suitability. Kween terrain checks do not transfer to Lira.

Next: independent terrain/illumination checks for these acquisitions, followed
by causal radar/optical pairing. A compatible radar training cohort must be
processed separately; this Lira validation sample alone cannot train and validate
a model. Confirmed crop calendars, field outcomes and an untouched final test
remain absent. No cause diagnosis or irrigation prescription is supplied.

Verification: 59 focused radar/cloud-gap/imagery tests passed, including cached
native raster fixtures, linear-before-log averaging, partial-support exclusion,
source metadata checks and unchanged withheld agricultural eligibility.
