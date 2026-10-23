# Exploratory learned cloud-gap baseline

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/train_gap_baseline.py --manifest outputs/ml/cloud-gaps/8df8e140fc0355075da5/manifest.json --sequence outputs/africa/recent/c990c8c23060aea1302a/pixels/sequence-observations.json outputs/africa/recent/ef95be98f85b606e9313/pixels/sequence-observations.json outputs/africa/recent/a013b10c8db819241036/pixels/sequence-observations.json
```

The offline runner verifies the frozen manifest content identity, disjoint
partitions, source report/array hashes, mask counts and exact grids. Coefficients,
implementation hashes, NumPy version and diagnostics are saved in ignored
`learned-baseline.json` beside the manifest. No model binary or imagery is committed.

## Method and actual fit

A fixed residual ridge regression predicts a correction to persistence using
prior clear NDVI, elapsed time, their interaction and squared prior NDVI. Penalty
is fixed at 1; seed is 20261023, sampling at most 10,000 pixels per target date.
Predictions are clipped to [-1,1]. No parameter selection uses validation/test
results. This is a small learned reference, not a foundation model or a claim
of state-of-the-art performance. It does not quantify predictive uncertainty.

Training uses clear-pixel transitions, with each target excluded from features
and admitted to subsequent history only after sample construction. Actual fit:
20,000 correlated pixel samples from **two** Iganga 2023 target dates. Two dates
provide very limited temporal diversity and are not 20,000 independent farms.

The stricter transferred-mask setup produced no supported training targets under
the fixed seven-day limit. Therefore training uses clear transitions while
validation and development test retain transferred rejection masks and never
refresh history with hidden values. This distribution mismatch is explicit;
successful fitting does not demonstrate performance through persistent clouds.

## Actual evaluation

The following is the initial May-only run. The
[May–June expansion](GAP_JUNE_EXPANSION.md) supersedes it as the latest experiment;
its validation gate also remains blocked.

| Cohort/protocol | Supported pixel-date pairs | Supported fraction | Learned MAE | Persistence MAE |
| --- | ---: | ---: | ---: | ---: |
| Iganga training, clear transitions | 200,531 | 25.1% | 0.0336 | 0.0379 |
| Lira validation, transferred masks | 0 | 0% | unavailable | unavailable |
| Kasese development test, transferred masks | 22,641 | 10.3% | 0.0937 | 0.1105 |

MAE is in NDVI units, on the identical supported subsets for both methods.
Training diagnostics include fitting samples and must not be treated as held-out
performance. No supported Lira validation predictions exist, so model promotion
status is `blocked_no_supported_validation_predictions`. Null error is not zero
error. The already inspected Kasese cohort is development-only; its lower error
does not establish general superiority, uncertainty calibration or accuracy
beneath real clouds. Unsupported targets stay withheld and are excluded from MAE.

No dashboard maps, observed coverage or acquisition dates change. Crop diagnosis,
yield prediction, irrigation prescription and agricultural accuracy claims remain
unavailable. Next requirements: additional temporal diversity and causal support
in training/validation, independent evaluation cohorts, realistic missingness
experiments, uncertainty calibration and anomaly-preservation tests. Confirmed
crop calendars and field outcomes remain necessary for agricultural use.
