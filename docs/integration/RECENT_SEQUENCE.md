# Recent multi-date sequence and cloud-gap baseline

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/process_recent_pixels.py --inventory outputs/africa/recent/a013b10c8db819241036/inventory.json --scenes-per-location 6 --online
python scripts/benchmark_recent_gaps.py --sequence outputs/africa/recent/a013b10c8db819241036/pixels/sequence-observations.json
```

Selection is bounded to six latest eligible distinct acquisitions per study
box (18 total here), with deterministic duplicate processing-version selection.
Cloud metadata does not rank candidates. Sequence output is separate from the
single-scene `observations.json`; existing quality audit input remains intact.
Numerical decoding, masks and immutable derived-array checks reuse the preceding
pixel recipe. Artifacts remain ignored outputs, not committed imagery.

## Actual coverage

All 18 scene processing attempts succeeded. Five meet the research 70% whole-box
coverage gate. At the 23 October 2026 00:00 UTC cutoff:

| Box | Qualified scenes / processed | Latest qualifying date | Age, days |
| --- | --- | --- | ---: |
| Iganga | 1 / 6 | 5 October | 17.67 |
| Lira | 2 / 6 | 10 October | 12.67 |
| Kasese | 2 / 6 | 8 October | 14.66 |

All remain stale under the seven-day rule. These are research boxes, not
confirmed fields/crops. Coverage is neither current cropland coverage nor a
field-eligibility decision. No dashboard refresh or field priority is enabled.

## Persistence benchmark

The offline benchmark verifies NPZ checksums and exact CRS/transform/shape
agreement. For each target date it withholds every available clear NDVI pixel
and predicts using that pixel's most recent earlier clear value, at most seven
days old. Current-date values enter the source history only after scoring.
Missing targets and expired predictions are not scored. Partial scenes can
provide clear targets even when whole-box coverage fails. Each date reports the
clear-target and scored denominators, mean absolute error (MAE) and signed bias.

Actual scored pixel-date pairs and ranges of per-date MAE in NDVI units:

| Box | Scored pixel-date pairs | Per-date MAE range |
| --- | ---: | --- |
| Iganga | 251,517 | 0.0380–0.0429 |
| Lira | 236,224 | 0.0560–0.0636 |
| Kasese | 288,787 | 0.0637–0.1344 |

These counts are correlated pixel-date pairs, not independent field samples.
This is a descriptive clear-pixel persistence diagnostic, not an ML model,
actual-cloud ground truth, crop performance result or early-warning evaluation.
It has no realistic cloud-footprint sampling, independent season/location test,
uncertainty calibration or anomaly-preservation validation. Acquisition ordering
prevents future-acquisition leakage, but source delivery latency is still unknown;
this is not proof the inputs were operationally available at the time.

No reconstructed map is published, no estimates enter observed coverage, and no
source observation dates are refreshed. Next: establish a broader verified
sequence and frozen spatial/seasonal splits, then realistic gap masks and
uncertainty-aware candidate comparison. Confirmed crop calendars and independent
field findings remain necessary for agricultural decision validation.
