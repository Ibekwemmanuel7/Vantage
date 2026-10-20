# Model card and executed experiment

20 October 2026. Research only. See `web/data/ml.json` and
`web/data/supervised-status.json` for current versioned results. Exact dataset/run
IDs and artifact hashes are recorded in `RUN_SUMMARY.json` and local run reports.

## Task

The commercial task is prioritizing agricultural investigation. The fitted
experiment has a narrower technical task: identify feature vectors unusual
relative to earlier same-season observations. Unusual is not a confirmed problem,
diagnosis, treatment need or probability of a useful finding.

## Fitted exploratory model

RobustScaler followed by scikit-learn IsolationForest, 256 trees, automatic
sample count, `contamination=auto`, fixed seed 42 and one fitting thread. Features
are NDVI median/IQR, red/NIR medians and five-day rainfall. Fit preprocessing and
the model on earlier-year rows only; target-year values never influence fitting.
The library's native zero decision boundary is an exploratory algorithm setting,
not a calibrated agricultural threshold. No target contamination percentage is
imposed and no confidence percentage is displayed.

The executed fit used **12 quality-eligible area-season samples from 2020, 2022
and 2023**, from **one spatial group**. It evaluated **one eligible 2024 sample**;
the three other target units remained unavailable. IG-11 entered the novelty
candidate state. Descriptive feature context includes low rainfall relative to
the training median; these differences are not SHAP/causal attribution.

There are **zero independent field labels**. Accuracy, precision and recall are
null/unreported. The experiment does not establish superiority over the existing
rules or prospective scouting utility. Units and years are correlated, the
reference is short and one area cannot test geographic generalization.

## Supervised training implementation

The separate pipeline supports class-weighted LogisticRegression after a
train-only RobustScaler. It requires the independent-label contract and disjoint,
chronological spatial cohorts. Select a classification threshold on validation
data only; keep test data untouched until evaluation. Report average precision,
ROC AUC, balanced accuracy, precision/recall and the prevalence baseline, with
explicitly uncalibrated probabilities and no confidence intervals unless a
proper clustered analysis is added. A classifier's raw output must not become a
customer confidence percentage.

**Actual supervised status: insufficient independent labels; no classifier fit.**
The code's successful fitting path is exercised only by explicitly synthetic
unit-test cohorts, whose numerical results are not product evidence. Demo
feedback, reconstructed weather and the program's own flags are never auto-labels.

## Release conditions and further work

Obtain crop/season confirmation and authorized, independently reviewed findings;
sample unflagged/routine comparison areas; agree useful outcome and delivery
cutoff; separate development from held-out events/farms/seasons. Estimate power
and clustered uncertainty, assess calibration if probabilities are needed, and
compare with simple baselines and the real analyst/adviser workflow. Publish
missingness, adverse cases, subgroup results, costs and no-visits alongside flags.

Do not use these models for disease/pest diagnosis, irrigation prescriptions,
yield/financial loss, emergency decisions or food-security impact claims. No
Southern US accuracy or Uganda crop-performance validation is inherited.

## Why this baseline precedes a foundation model

A geospatial foundation model is a candidate feature extractor, not a substitute
for ground truth. Prithvi has published model and fine-tuning resources, but its
documented multispectral input conventions require a compatible adapter; the
current RGB/B08 dataset must not be silently substituted for a different HLS
band/resolution contract. Any extension must pin checkpoint/licence/input
normalization and beat simpler baselines on independent cohorts and costs.
No foundation weights were downloaded or fine-tuned in this slice.

## Primary technical references

- [scikit-learn IsolationForest API](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html).
- [scikit-learn leakage/pipeline guidance](https://scikit-learn.org/stable/common_pitfalls.html).
- [NASA–IBM Prithvi model resources](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-600M).
