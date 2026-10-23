# Adjacent June expansion: actual cloud-gap benchmark results

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

The June extension was fixed before inspecting its outcomes, retaining existing
location/year partitions, latest-six selection, seven-day source age, fixed ridge
penalty and clear-transition training protocol. No hyperparameter was tuned on
validation or development-test errors. It is an exploratory data expansion after
seeing the initial missing validation support, not a preregistered final study.

```powershell
python scripts/acquire_gap_cohorts.py --plan configs/gap_acquisition_june.json
python scripts/acquire_gap_cohorts.py --plan configs/gap_acquisition_june.json --online
```

The first command prints the plan; the second executes bounded acquisition.
Actual queries returned 11 Iganga June 2023 catalog items and 7 Lira June 2024
items. Six latest eligible distinct acquisitions per box were processed, all
successfully. These are research windows, not confirmed crop stages.

## Combined manifest and training

```powershell
python scripts/prepare_gap_dataset.py --sequence outputs/africa/recent/c990c8c23060aea1302a/pixels/sequence-observations.json outputs/africa/recent/954abd0883653516f0d5/pixels/sequence-observations.json outputs/africa/recent/ef95be98f85b606e9313/pixels/sequence-observations.json outputs/africa/recent/e285b40bbdfb86b1cc40/pixels/sequence-observations.json outputs/africa/recent/a013b10c8db819241036/pixels/sequence-observations.json
python scripts/train_gap_baseline.py --manifest outputs/ml/cloud-gaps/41353b869729ec810781/manifest.json --sequence outputs/africa/recent/c990c8c23060aea1302a/pixels/sequence-observations.json outputs/africa/recent/954abd0883653516f0d5/pixels/sequence-observations.json outputs/africa/recent/ef95be98f85b606e9313/pixels/sequence-observations.json outputs/africa/recent/e285b40bbdfb86b1cc40/pixels/sequence-observations.json outputs/africa/recent/a013b10c8db819241036/pixels/sequence-observations.json
```

Manifest `41353b869729ec810781`: 11 training scenes, 12 validation scenes, 6
development-test scenes. The minimum date-count gate passes. The fit uses 61,415
sampled clear-pixel transitions across eight target dates. Ridge regression
minimizes squared residual error on sampled points; it need not improve MAE on
the full training cohort. Adjacent pixels are correlated, not independent farms.

| Cohort | Supported pairs | Supported fraction | Learned NDVI MAE | Persistence MAE |
| --- | ---: | ---: | ---: | ---: |
| Training clear transitions | 369,412 | 22.5% | 0.0613 | 0.0543 |
| Validation transferred masks | 0 | 0% | unavailable | unavailable |
| Development test transferred masks | 22,641 | 10.3% | 0.0849 | 0.1105 |

Training MAE is worse than persistence on its full supported set. The development
test remains the already inspected small Kasese cohort, with only one supported
target date. Its lower error does not establish general superiority. Expanded
training still has zero supported transferred-mask targets; the clear-transition
training/evaluation mismatch persists. The runner now reports this support count
and supported validation-date count explicitly rather than hardcoding an earlier
limitation. Both are zero in this run.

Promotion remains `blocked_no_supported_validation_predictions`; no prediction
enters the dashboard, no acquisition dates/observed coverage are refreshed, and
no uncertainty calibration or agriculture-performance claim is made. Source
rasters, model coefficients and generated reports remain ignored artifacts.

## What the negative result means

Adding dates alone did not solve causal support under persistent transferred
gaps. Before further model complexity, inspect missingness duration and compare
clearly separated evaluation protocols: independent target-mask experiments
versus this sequential stress test. Do not silently extend source age or admit
hidden targets to improve headline coverage. A radar-assisted model needs its
own quality/geometry checks and compatible training inputs. Independent future
evaluation, crop calendars and field outcomes remain missing.
