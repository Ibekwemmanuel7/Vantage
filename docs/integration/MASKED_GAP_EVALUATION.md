# Transferred-mask cloud-gap baseline

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

Run the existing benchmark command against `sequence-observations.json`.
It now writes `gap-mask-baseline.json` with schema
`gap-persistence-benchmark-2`, preserving the earlier `gap-baseline.json` artifact.
Inputs remain the 18-scene sequence; no new imagery acquisition or ML training
is performed. Artifact checksums and grid alignment checks remain enforced.

## Protocol

At each target date, transfer the immediately preceding acquisition's rejected
pixel footprint onto known clear target pixels. Mask donors precede targets;
future images never provide prediction features or masks. The original masks
include all numerical/quality exclusions, so these are realistic-shaped quality
gaps, not independently verified cloud-only masks. Shapes are transferred within
the same study grid; this does not reproduce every real cloud process.

Predict with the last actually available clear NDVI within seven days. Simulated
hidden target values never enter prediction history. Expired and unsupported
predictions remain withheld. At the first date, no preceding footprint exists;
its clear pixels seed the history after scoring. This is a sequential stress test,
not independent masking of every target and not spatial/seasonal holdout.

Each date reports hidden clear targets, predicted pixels, prediction coverage,
MAE, signed bias, 90th percentile absolute error and fraction with absolute NDVI
error above 0.1. The 0.1 threshold is descriptive, not a validated agronomic
threshold. Null errors mean no supported predictions, never zero error.

## Actual diagnostic results

| Box | Hidden pixel-date pairs | Predicted pairs | Pooled prediction coverage |
| --- | ---: | ---: | ---: |
| Iganga | 313,544 | 133,467 | 42.6% |
| Lira | 236,868 | 236,122 | 99.7% |
| Kasese | 218,827 | 22,641 | 10.3% |

Only one target date per box had supported predictions. MAE on these supported
subsets was 0.0418 (Iganga), 0.0636 (Lira), 0.1105 (Kasese) in NDVI units.
Errors on supported subsets cannot characterize withheld pixels. Pixel-date
pairs are correlated samples, not independent farms. The location differences
and sparse support prevent any claim of general cloud-gap performance.

No clear-image ground truth exists beneath the actual clouds. This diagnostic
does not validate uncertain estimates, anomaly preservation, crop diagnosis or
yield prediction. Acquisition-time ordering does not establish historical source
delivery availability. Confirmed crops/calendars and independent field findings
are still absent. No reconstructed map enters the dashboard or observed coverage.

Next gate: broader season/location cohorts and frozen evaluation splits, then
uncertainty-aware model candidates using compatible inputs. Compare error and
abstention together, retain a no-estimate baseline and test whether real changes
are suppressed or invented. Do not train and evaluate on the same cohort.
