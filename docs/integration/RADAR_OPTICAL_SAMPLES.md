# Versioned radar–optical research samples

24 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/prepare_radar_optical_samples.py
```

Offline builder using `configs/radar_optical_samples.json`. Actual output:
`outputs/ml/radar-optical/af9b3069cdd50009e367dd96/manifest.json`.
The dataset identity includes the plan, frozen split plan, source report hashes,
implementation hashes and NumPy version. Source arrays must match their hashes
and exact grids. Replays compare arrays and immutable manifest text rather than
silently replacing them. Generated tensors and manifests remain ignored outputs.
No new imagery download, provider processing or training occurs.

## Explicit information contract

Each NPZ sample keeps five radar-only feature bands:

| Feature | Units |
| --- | --- |
| VV backscatter | dB |
| VH backscatter | dB |
| VH minus VV | dB |
| Approximate local incidence | degrees |
| Radar acquisition age at optical timestamp | days |

No observed target NDVI enters features. The manifest retains exact radar and
optical scene IDs/times, radar track, lag, location, partition and full analysis
grid. Native support fractions and local/slope/visibility class masks remain in
each artifact. Unsupported feature pixels are NaN, not zero-valued observations.

`feature_valid` requires positive finite radar values, native support >=0.8,
locally unflagged geometry, clear-within-5-km sightlines, lower-slope class under
the fixed 10-degree rule and a supported 5–85-degree local-incidence estimate.
`target_valid` further requires actually observed finite NDVI. `target_ndvi`
contains only those observed references; all other cells are NaN.
`observed_optical_valid` preserves original observed coverage separately.
`gap_candidate` identifies missing optical cells with research radar support;
it contains no estimated NDVI and never becomes a supervised target.

The builder rejects future/expired radar, mismatched scenes/grids/masks,
unrecognized class encodings, wrong split locations/years and scene reuse across
partitions. Source radar ages are at most seven days. Locations and years remain
separate under the existing frozen research split. Current samples cover one
track per geography, not a universal radar calibration across orbits.

## Actual dataset

| Partition | Geography/year | Sample dates | Observed NDVI reference pixel-date pairs | Unlabeled gap candidates |
| --- | --- | ---: | ---: | ---: |
| Training references | Iganga, June 2023 | 4 | 562,773 | 669,311 |
| Validation references | Lira, June 2024 | 3 | 638,880 | 276,777 |

Five other optical dates are withheld because they lack a prior fixed-track
radar pass within seven days. Counts are correlated pixel-date pairs with strong
date imbalance, not independent fields, labels of crop health or achieved
reconstruction coverage. Missing optical cells have no measured target.

Iganga reference dates are 3, 13, 23 and 28 June; Lira dates are 7, 17 and 22 June.
Lira applies the primary slope proxy here, unlike the earlier pairing table's
numerical/local/bounded-only screen, so its reference counts are lower. This
policy difference is explicit rather than a claimed performance change.

## Closed eligibility gate

Every sample retains `usable_for_model_training=false`; the manifest retains
`training_eligible=false` and `model_trained=false`. Independent processor outputs,
untouched final evaluation, uncertainty calibration and cross-track transfer
evaluation remain pending. This artifact does not silently override the preceding
quality reports' ineligibility. No radar-assisted trainer consumes these samples
in this release. The already inspected development cohort is not a final test.

The DSM and approximate geometry are research screens, not complete terrain
illumination certification. Reference NDVI depends on the existing optical quality
recipe, not independent field verification. Some 2023 acquisitions use later
reprocessed products, so source delivery availability and contemporaneous 2023
operational performance are unverified. Confirmed crop identity/calendars and
field outcomes remain required for agricultural decision claims.

No dashboard maps change, missing values are not filled, crop causes are not
diagnosed and irrigation is not prescribed. Forestry stays with Vepris and no
CropSight validation transfers. The Lillie US product backlink is retained.

Verification: 106 focused tests passed. New tests show that changing NDVI targets
cannot alter radar input features, missing optical values cannot become labels,
unknown/steep quality cells are excluded and future/expired ages or inconsistent
masks are rejected. Actual cached replay reproduced seven artifacts and the
immutable manifest; none of these software checks measures agricultural accuracy.
