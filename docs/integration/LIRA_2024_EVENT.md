# Lira 2024 exploratory event reconstruction

Vantage agriculture, Uganda pilot, within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Implemented 24 October 2026. This is an incomplete retrospective research case,
not a validated drought detector or evidence that Vantage improved farmer outcomes.

## Question and frozen scope

[FEWS NET's May 2024 update](https://fews.net/east-africa/uganda/key-message-update/may-2024)
reports substantial March–May rainfall deficits in northern Uganda, including
Lango and Acholi. It does not establish a measured loss inside Vantage's Lira
study box. The report's exact publication day was not established; the month
is retained without inventing a daily operational cutoff.

The analyst box is 32.85–32.95 E, 2.20–2.30 N. The frozen plan is
`configs/lira_2024_event.json`. Its choices followed event and archive inspection;
this is exploratory, not preregistered or blinded. No matched control was selected.

Rainfall design: CHIRPS v3 final March, April and May totals in 2024 against
the same months in every year 1981–2020. The adapter requires all 123 monthly
windows and all four native 0.05-degree cells before calculating a departure.
Monthly cell values are summed first, then compared with the 40-year mean and
area-weighted using the study-cell latitudes. No missing month becomes zero.
This estimates seasonal context; it does not resolve dry-spell timing.

The [CHC documentation](https://www.chc.ucsb.edu/data/chirps3) describes v3 as
a satellite/gauge product, with final observations and a version distinct from
v2. Using the current v3 archive is not an exact replication of the product
available to FEWS NET in 2024. Provider attribution and source dates are retained.
Do not compare rainfall against another CHIRPS-derived report and call that
independent gauge validation.

## Actual implemented result

| Component | Actual status |
| --- | --- |
| Optical source dates | 24 May 2023 and 28 May 2024, Sentinel-2 L2A |
| Source handling | Pinned existing archive, catalog and NPZ hashes; identical projected grids |
| Optical quality | Accepted SCL 4/5 with the archive's one-pixel rejection buffer; finite NDVI support checked |
| Common observed support | 290,317 / 307,468 pixels, 94.4219% of the entire study box |
| Median 2024 minus 2023 NDVI | −0.0108516 on common observed pixels |
| Raster/map | Masked float GeoTIFF and three-panel PNG created locally |
| Rainfall | Unavailable: no complete cached monthly cohort; cloud raster requests returned HTTP 403 |
| Independent field outcomes | 0 |
| Crop-loss attribution | Unavailable |

The first isolated May 2024 rain-window probe succeeded, but did not produce
a persisted cohort. The archive run first exposed an alignment tolerance issue;
subsequent requests were denied by the endpoint. No probe value was promoted
to a seasonal result. The adapter rounds only nearly aligned native window
indices and verifies the resulting bounds to 0.00001 degrees; it never resamples
rainfall to the optical grid. Additional live verification remains required.

The median optical difference is not a crop-health threshold or a yield-loss
estimate. These are whole-box observations, without current crop masking or farm
boundaries. The four-day calendar-date difference, variable planting dates, land
cover, interannual phenology and other factors can affect NDVI. One reference
date is not a normal seasonal baseline, and 2023 must not be presumed unstressed.
Positive and negative local differences coexist; the box median can hide them.

The map displays NDVI on 0–1 and differences on ±0.30; display saturation is
not a classification rule. Gray means unavailable. The GeoTIFF retains full
numeric differences and valid zero separately from masked cells.

## Replay

Requires the pinned, ignored optical archive from the earlier archive run and
`requirements-geo.txt`. Plotting additionally uses matplotlib 3.9.2 locally.

```powershell
python scripts/reconstruct_lira_event.py
python scripts/plot_lira_event.py outputs/africa/lira-event/9f44e162ae146a528bb6/report.json
python -m unittest tests.test_event_reconstruction tests.test_event_series
```

The first command works offline and records missing rainfall explicitly.
Report/plan files are exclusive; replay refuses a changed result. Raw imagery,
rainfall extracts and plots remain in ignored `outputs/africa/lira-event/`.
The tracked `docs/africa/LIRA_2024_EVENT_RUN.json` pins the inspected report and
artifact checksums. A new checkout does not contain the raw optical inputs.

When public access is restored, optional `--online --report-name report-v2.json`
permits the fixed 123 COG window reads with three workers. The adapter stops new
request batches after a provider error. It stores native extract values, URLs,
retrieval dates, raster transforms and tags. Extract checksums do not certify the
entire remote file: whole COGs are not downloaded or hashed. Pin and review a
completed acquisition before making any rainfall claim. No authentication bypass,
paid service or alternative weather product was substituted.

## Remaining work

1. Obtain the full rainfall cohort through permitted public access and verify
   native-window alignment against actual archive transforms.
2. Expand the optical seasonal series and baseline before interpreting departures;
   retain cloud gaps and account for land-cover/crop and calendar uncertainty.
3. Select defensible comparison areas before causal evaluation. Nearby locations
   or different countries are not automatically unaffected controls.
4. Obtain independent, geographically aligned field observations and crop records.
   Public event narratives and survey yields from 2020 are not 2024 field outcomes.

No imagery-only diagnosis, irrigation prescription, new model or agricultural
accuracy claim is produced by this increment.
