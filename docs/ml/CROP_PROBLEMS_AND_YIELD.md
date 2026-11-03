# Crop-condition and yield ML: research programme

2 November 2026. Vantage agriculture within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda is the first pilot, not the product boundary. No CropSight validation is
inherited and forestry remains with Vepris.

## Decision and actual first experiment

The user authorized further model exploration. We implemented a separate,
explicitly exploratory supervised yield benchmark using the already pinned
public survey. This does not change the survey audit's field/scouting admission
flags, label intake gate, dashboard readiness or operational predictions.

The [One Acre Fund release](https://zenodo.org/records/11122388) documents maize
in pure stands, yield sampling in two 36 m² boxes, and farmer-reported adversities.
Some coordinates were replaced with town/district locations. Uganda's audited
subset has 109 rows, all 2020, with no recorded harvest dates. It cannot establish
future-season performance or precise field-to-satellite alignment.

We trained median-baseline, Ridge and random-forest candidates in five buffered
geographic folds. Inputs were only seven published static environmental features:
elevation, wetness index, water-holding capacity, clay, pH, organic carbon and ECEC.
We did not include yields, adversities, actual season rainfall, harvest-time plant
density, management outcomes or whole-cohort planting-date deviations as features.
These exclusions avoid obvious outcome/late-season leakage; original feature
release dates are still unverified, so this is not an as-of forecast experiment.

| Model | Pooled held-out MAE, kg/ha | RMSE, kg/ha | R² |
| --- | ---: | ---: | ---: |
| Train-fold median | 1024.67 | 1257.29 | −0.1483 |
| Ridge, alpha 10 | 970.91 | 1216.10 | −0.0743 |
| Random forest, 300 trees | 1012.86 | 1258.95 | −0.1513 |

Ridge reduced MAE by approximately 5.2% relative to the median baseline, but the
negative R² and substantial errors do not support practical field forecasts.
These point estimates have no uncertainty interval or significance claim. All
109 rows received out-of-fold predictions. No final all-data model, deployable
checkpoint or production predictor was produced; models were fit within folds.
Results are descriptive after examining this small cohort and must not be tuned
repeatedly and then relabeled an untouched test.

## Evaluation safeguards and practical limits

- Geographic groups use 0.1-degree cells on published coordinates. Duplicate
  coordinate pairs remain together, without assuming they represent one farm.
- Training rows less than 5 km from any test point are removed. Every fold needs
  at least 30 training rows; insufficient folds fail, rather than being skipped.
- Median imputation and scaling are fitted on training rows only. RF settings
  and Ridge strength were fixed before fitting, with no reported-score tuning.
- All models use exactly the same fold assignments and eligible evaluation rows.
- Reported location separation is only as reliable as the original coordinates.
  It does not demonstrate independent farms, remove shared collection effects
  or account for unknown coordinate error. Grid boundaries and buffer choice
  deserve sensitivity checks in a separately declared follow-up.
- One country-year, 16 reported coordinate cells and 109 rows are not an
  independent future-year test. No causal benefit of any soil property is inferred.
- No satellite imagery was joined. No new farmer consent or participation is
  inferred from public records. Raw labels and predictions stay outside Git.

## Crop problems are separate targets

The same Uganda subset has 109 `FALSE` disease reports and 109 `FALSE` pest
reports. It has 52 `TRUE`, 50 `FALSE` and 7 missing Striga reports, and 4 `TRUE`
excess-water reports. Missing is not negative. These are reported adversities,
not independently diagnosed, date-aligned satellite labels. No crop-problem
classifier was fitted. An all-negative disease classifier would be misleading.

Vantage should distinguish these outputs:

| Task | Candidate approach | Admission/evaluation requirement |
| --- | --- | --- |
| Locate unusual crop development | Seasonal vegetation trajectory residuals; compare robust calendar-stage reference against existing novelty/rules | Confirm crop/calendar, evaluate useful scouting findings with flagged and unflagged visits |
| Estimate condition or severity | Regularized regression/boosted trees on spectral, temporal, weather and ground-condition features | Dated independently assessed severity rubric; hold out farms, seasons and geography |
| Investigate a specific cause | Crop-specific field photos plus agronomist assessment, history and satellite/weather context | Positive and negative cause labels; externally adjudicated cases and an abstain/unknown state |
| Predict maize yield before harvest | Baselines → Ridge/boosted trees → temporal models → compatible foundation embeddings | Crop-cut/harvest labels, boundaries, explicit forecast date and feature availability; future-season test |

Leaf-photograph recognition is a different modality from satellite recognition.
[PlantDoc's primary dataset paper](https://arxiv.org/abs/1911.10317) offers a
field-image research candidate, not satellite disease labels or a ready Uganda
validation cohort. Source rights, crop relevance and external field generalization
must be checked before collection or training. Do not mix cassava disease labels
with a maize yield target or call online posts confirmed farm diagnoses.

## Architecture for a stronger benchmark

1. Version the field boundary, crop identity, planting dates, management records,
   yield units and measurement protocol. Distinguish crop cuts from full harvests.
   [Uganda yield-measurement research](https://fsi.stanford.edu/publication/eyes-sky-boots-ground-assessing-satellite-and-ground-based-approaches-crop-yield)
   shows why measurement method and intercropping matter to satellite evaluation.
2. Build a field-season observation cube: calibrated reflectance, red-edge/NIR/SWIR
   indices, accepted pixel support, cloud/missingness indicators and observed dates.
   Preserve radar geometry/quality and rainfall's native scale. Reconstructed pixels
   must remain flagged; do not treat ML-filled values as observed ground truth.
3. At each declared forecast horizon, materialize only features actually available
   by that cutoff. Separate static covariates from accumulated observations and
   forecasts. Exclude actual future rainfall, future acquisitions and harvest labels.
4. Freeze farm/source groups and leave future seasons/geographies untouched.
   Fit preprocessing and select parameters only within training/validation cohorts.
   Keep mean/median, simple vegetation models and persistence/seasonal baselines.
5. Report yield MAE/RMSE/bias in kg/ha, R², crop/region/field-size slices, coverage
   and abstention. Evaluate prediction-interval coverage/width on a separate
   calibration/test scheme; do not attach untested confidence percentages.
6. For condition classification report prevalence, precision–recall, sensitivity
   at scouting capacity, calibration and unknown cases. For a scouting ranker,
   measure useful findings per visit and misses among unflagged fields.

[Prithvi EO 2.0 model documentation](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M)
and the [NASA primary paper](https://ntrs.nasa.gov/api/citations/20240015391/downloads/RSE%20Prithvi%20Global.pdf)
support considering temporal foundation representations. They do not supply
Vantage's missing outcome labels. Benchmark a frozen compatible encoder only
after establishing sensor/band/scaling/time inputs. Do not feed rendered maps,
silently substitute bands or assume pretraining improves held-out Uganda results.
No model weights, new libraries, cloud compute or paid service were downloaded here.

## Replay and immediate next work

```powershell
python scripts/benchmark_uganda_yield.py outputs/research/2026-10-24/one_acre_csv.source --out outputs/private/uganda-yield-research-v3
python -m unittest tests.test_yield_research tests.test_survey_audit
```

Use a new output directory. The CLI checks the exact source hash and freezes the
plan before fitting. Reports pin implementation and environment versions. Individual
observations/predictions remain private. Dependencies are in `requirements-ml.txt`.
Ten selected software tests passed; an independent rerun to a new output directory
produced an identical report. Aggregate results and split checks are recorded in
`UGANDA_YIELD_RESEARCH_RUN.json`; raw observations/predictions are not published.

Next, obtain a suitable precisely geolocated, multi-season yield cohort and confirm
reuse/measurement protocols before satellite joins. Build an actual date-limited
seasonal benchmark, then test whether temporal/EO features improve it. For crop
problems, independent dated positive and negative field labels remain necessary.
This first benchmark establishes an executable comparison and exposes weak data
support; it does not establish a reliable crop-problem or yield product.
