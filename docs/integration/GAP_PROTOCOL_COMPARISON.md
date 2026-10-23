# Gap protocol comparison and missingness diagnosis

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

Rerun the training command in [the June expansion](GAP_JUNE_EXPANSION.md).
The runner now writes `protocol-comparison.json` with schema
`gap-protocol-comparison-1`, preserving the previous `learned-baseline.json`.
It verifies the same frozen inputs and fits the same fixed model. Coefficients
and 61,415 sampled transitions from eight training target dates are unchanged.
No additional acquisitions, hyperparameter tuning or dashboard changes occur.

## Separate questions

1. **Sequential transferred gaps:** apply each preceding quality-mask footprint
   to a clear target, withholding those targets from all subsequent simulated
   history. This stresses repeated synthetic gaps.
2. **Isolated transferred gap:** each target is an independent gap experiment.
   All original earlier observations are available, including earlier dates
   hidden only in other experiments. Current target values never enter their own
   features. This is an easier protocol, not a solution for repeated real gaps.
3. **Clear transitions:** score known clear targets against causal clear history.
   This measures temporal prediction where repeat observations exist, not
   reconstruction beneath clouds. It must not replace the gap test.

All retain the seven-day source-age limit, same grids, source masks and fitted
regression. Original quality exclusions are transferred, not independent cloud
truth. Synthetic gaps require usable observations before the preceding rejected
acquisition, which can push source ages beyond seven days at the observed cadence.
The isolated protocol does not change that constraint.

## Actual findings

| Evaluation | Validation predicted pairs | Validation hidden targets | Learned MAE | Persistence MAE |
| --- | ---: | ---: | ---: | ---: |
| Sequential gaps | 0 | 1,029,284 | unavailable | unavailable |
| Isolated gap | 0 | 1,029,284 | unavailable | unavailable |
| Clear transitions | 593,660 | 1,622,944 | 0.0708 | 0.0606 |

Sequential validation unsupported targets split into 543,620 with no simulated
prior clear value and 485,664 with an expired prior. Under isolated experiments,
307,323 lack any original prior and 721,961 have expired original prior values.
Thus allowing original earlier history does not recover a valid <=7-day source
for these gap targets. This diagnoses the benchmark's support, not the correctness
of the provider cloud classification or real-world crop behavior.

Kasese development comparisons:

| Evaluation | Predicted pairs | Coverage | Learned MAE | Persistence MAE |
| --- | ---: | ---: | ---: | ---: |
| Sequential gaps | 22,641 | 10.35% | 0.0849 | 0.1105 |
| Isolated gap | 23,086 | 10.55% | 0.0847 | 0.1099 |
| Clear transitions | 288,787 | 37.21% | 0.0831 | 0.0741 |

Error is reported only on supported subsets shared by the two predictors.
Pixel-date pairs are correlated; these are descriptive point errors without
confidence intervals or uncertainty calibration. The already inspected Kasese
cohort remains development-only. Clear-transition errors are worse than
persistence in both validation and development test, despite improvement on
the small supported transferred-gap subset. No broad improvement claim follows.

## Decision

Keep model promotion blocked and preserve all missing observations. Do not
extend the maximum source age or switch evaluation protocols silently to improve
headline coverage. Next useful input is independently quality-screened radar
coincident with gaps, or other actual observations capable of supporting a
different explicitly declared model. A supported training/validation cohort must
precede claims about learned radar-optical reconstruction. This release provides
neither uncertainty-aware predictions nor a new radar model.

Crop identity, planting calendars, independent field outcomes and an untouched
future evaluation remain absent. No cause diagnosis, yield claim, irrigation
prescription or forestry scope is added.
