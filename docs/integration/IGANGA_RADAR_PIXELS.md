# Iganga radar training-cohort numerical sample

24 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/process_gap_radar.py --config configs/iganga_gap_radar_pixels.json --online
python scripts/process_gap_radar.py --config configs/iganga_gap_radar_pixels.json
python scripts/summarize_radar_training_pairs.py --radar-report outputs/africa/gap-radar-pixels/e2ad309edd56e682d17d/report.json
```

The shared numerical processor now accepts an explicit config and bounds cohorts
to one fixed track and at most three passes. Default Lira config remains supported;
existing Lira reports and dependent manifests were not regenerated. The Iganga
config pins all three eligible ascending Sentinel-1A relative-orbit-028 passes in
the archived June window before examining pixels. Selection does not rank radar
returns. Complete cohorts report consecutive same-track changes; a failed middle
pass cannot silently produce a purported adjacent-pair comparison.

## Actual numerical data

| Radar acquisition | Positive VV/VH support / study pixels | Median VV, dB | Median VH, dB |
| --- | --- | ---: | ---: |
| 29 May 2023 | 308,021 / 308,021 | -8.4002 | -13.9425 |
| 10 June 2023 | 308,021 / 308,021 | -7.3261 | -13.2333 |
| 22 June 2023 | 308,021 / 308,021 | -7.9660 | -13.6164 |

All three raster reads and offline replay succeeded. Reflectance/NDVI is not
derived from radar; provider gamma0 positive linear intensity is averaged before
conversion to dB, with the same 0.8 native-support threshold and exact optical
grid contract as Lira. Whole-box numerical coverage is not agricultural validity.
Source clips, derived arrays and source/implementation hashes remain local under
`outputs/africa/gap-radar-pixels/e2ad309edd56e682d17d/`.

## Candidate causal references

The diagnostic script verifies source sequence/array hashes, grids, mask/NDVI
agreement and one-track temporal pairing. Only acquisitions preceding or equal
to the optical timestamp and within seven days are selected. Iganga's orbit 028
is not pooled into Lira's orbit 029 for backscatter comparison.

| Optical date | Prior radar | Lag, days | Clear optical references | Missing optical pixels with numerical radar |
| --- | --- | ---: | ---: | ---: |
| 3 June | 29 May | 4.66 | 240,300 | 67,721 |
| 13 June | 10 June | 2.66 | 1,336 | 306,685 |
| 23 June | 22 June | 0.66 | 19,174 | 288,847 |
| 28 June | 22 June | 5.66 | 301,963 | 6,058 |

8 June and 18 June are withheld: their prior passes are 9.66 and 7.66 days old.
Clear references are candidate reconstruction targets, not crop-health outcomes;
missing pixels have no measured optical target. Counts are correlated pixel-date
pairs, heavily unbalanced across dates, not independent farms or achieved ML
gap coverage. No tensors are admitted to training by this diagnostic.

Some archived 2023 acquisitions use 2024 reprocessed Sentinel-2 product versions,
as identified by their product IDs. This retrospective research cannot demonstrate
that those exact inputs were available to a decision-maker in 2023. The report
retains `historical_delivery_time_verified=false`.

## Remaining checks

Iganga requires its own independent DSM, verified product viewing annotations,
local geometry and bounded visibility screening. Lira checks do not transfer
across geography or orbit. Independent provider exports remain outstanding;
the authenticated fetcher was not run and no credentials were requested in chat.
Different incidence/viewing conditions require explicit treatment in any model.

No radar-assisted model was trained, optical values imputed, crop cause diagnosed
or irrigation prescribed. Crop calendars, independent field outcomes, uncertainty
evaluation and an untouched final test remain dependencies. Forestry stays with
Vepris and no CropSight validation transfers.

Verification: 101 focused tests passed, including fixed-track budgets and duplicate
rejection, temporal withholding, provider-export fixtures, numerical radar,
terrain/viewing/sightline mathematics and cloud-gap regressions. Actual cached
replay checked the Iganga arrays without new network reads.
