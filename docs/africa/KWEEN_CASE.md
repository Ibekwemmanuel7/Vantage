# Kween 2023 public-event reconstruction

Independent Vantage research within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda is the active priority; Texas remains deferred. This case supplies an
auditable geospatial example, not independently validated agricultural performance.

## Question and evidence

[Uganda Radio Network reported on 6 June 2023](https://ugandaradionetwork.net/story/prolonged-dry-spell-drying-up-crops-in-kween)
that farmers in lower-belt Kween localities described drying crops after a dry
spell beginning approximately mid-March. The report names Ngenge, Kiriki,
Sundet and Chepsuknya. It does not supply verified farm polygons, observation
dates or measured crop outcomes. Syndicated copies are the same evidence origin.

Question: do selected public satellite observations over **Ngenge locality
proxies** show lower vegetation index than comparable calendar windows in
2019–2022, and what does coarse rainfall context show? These boxes do not
establish the location of any quoted farmer's plot. A disagreement cannot
disprove their account, and an agreement cannot validate field-level detection.

The [district's natural-resources account](https://www.kween.go.ug/dept/natural-resources)
describes distinct ecological zones and lower-plains drought exposure. It is
geographic context, not independent confirmation of this particular event.

## Fixed design

The [versioned configuration](../../configs/kween_2023_case.json) fixes three
0.1-degree boxes: an Ngenge locality proxy, a shifted location-sensitivity box
and nearby eastern context. The [OSM locality node](https://api.openstreetmap.org/api/0.6/node/2229121548.json)
is archived and checked against the expected position. These are analyst
boxes, not official subcounty boundaries or smallholder parcels. They overlap
or neighbour each other and are correlated; none is an unaffected control.
The downloaded OSM node version is dated June 2024, after the event; its GNS
place-name anchor is not a surveyed 2023 farm location. Attribution:
[OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright).

Two observation windows are used in each of five years: 1–14 March and
21 May–5 June. The 2023 cutoff is the day before publication, since the
publication timezone is unverified. Current archive availability and historical
acquisition dates do not demonstrate that Vantage could have delivered an alert
at the time. Reprocessed products and a 2021 land-cover mask also introduce
hindsight. Event selection was already informed by the report: the frozen local
plan is **not** a blinded test or externally preregistered experiment.

For each of 30 area/year/window slots, require a full-box Sentinel-2 L2A
candidate with six bands, SCL and product metadata. Rank by scene cloud metadata,
then timestamp and ID; try at most three distinct acquisitions. Accept the first
successfully processed scene even if its measured coverage is inadequate.
Never select on the resulting vegetation index. Actual dates remain in the run
record; calendar windows do not establish matching crop stages.

Physical reflectance uses per-band product offsets and quantification, rejected
SCL classes plus their one-pixel buffer, and explicit per-band/common masks.
Versioned COGs preserve B02/B03/B04/B8A/B11/B12, with no missing-value filling.
WorldCover 2021 class 40 defines historical cropland only; it does not confirm
maize, current planting, crop stage, management or the presence of a crop in
2019. The same mask/grid is used throughout each area's comparison.

An eligible observation needs at least 60% usable historical cropland and 100
valid pixels. A map additionally needs three eligible earlier reference years
and at least three finite references per compared pixel, with that overlap
covering 60% of historical cropland and 100 pixels. Otherwise the whole map is
withheld. Available maps contain target minus reference-median NDVI (B8A/red),
reference counts and a descriptive flag for a drop of at least 0.10 **and** a
value below every eligible reference. These development thresholds are not
empirically calibrated crop-damage thresholds; the six comparison maps are not
statistical significance tests. The source itself describes recurring dry spells
in previous years, so earlier years cannot be assumed healthy controls.

[CHIRPS v3 final monthly Africa rasters](https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/africa/tifs/)
provide March–May totals for the same five years. Each box contains four native
0.05-degree cells; retain those values and their mean rather than creating a
field-resolution rainfall map. Compare 2023 with the median of four reference
years. This is a short-reference ratio, not climatological drought severity,
soil moisture, a within-month dry-spell test or causal explanation. Monthly sums
can conceal agriculturally important rain timing.

## Executed findings

Run `8bfc86ae343f196c7a188e60` processed **30/30 observations**; 25 pass the
historical-cropland coverage rule. Verification checked **90 scene COGs and
four derived anomaly COGs**, including pixel-by-pixel recomputation. Four of six
comparisons are available; the two Ngenge early-period maps are withheld.
The final regression suite passed **80 tests**. A download-disabled rebuild
preserved the exact manifest bytes (SHA256
`4b333d092264a0e2e557bd4f7b23da27c15691c6c4c0b71fb187e05477718ff2`).

For the selected **21 May 2023** acquisition:

| Proxy box | Comparable historical cropland | Median NDVI difference | Pixels below all references with ≥0.10 drop | MAM rainfall / short reference median |
|---|---:|---:|---:|---:|
| Ngenge core | 97.9% | +0.026 | 14.8% | 0.952 |
| Shifted Ngenge | 99.5% | +0.062 | 11.3% | 0.901 |
| Nearby east | 98.5% | +0.116 | 6.8% | 0.974 |

**This does not reproduce a uniform area-wide vegetation decline.** There are
localized negative differences alongside positive area medians. The flagged
fractions are descriptive spectral results, not percentages of damaged crops.
Rainfall totals are approximately 3–10% below the short reference median, which
does not establish the timing, severity or agricultural effect of a dry spell.
The available nearby-east early-period comparison has median difference +0.009,
65.3% comparable cropland and a 1.9% descriptive flag fraction.

The selected May 21 scene is approximately 15.7 days before the cutoff and
16 calendar days before the report. It cannot establish conditions on the
publication day. Early-March Ngenge coverage failures also prevent a reliable
before/after sequence. The result remains inconclusive about the reported
farms: do not move the boxes, change thresholds or select a greener/browner
acquisition after seeing these findings. A denser temporal follow-up must be
identified as a separate analysis with its own fixed plan.
The [executed temporal follow-up](KWEEN_TEMPORAL.md) now supplies that separate
analysis; it preserves this original case and explicitly reports stale evidence.

## Reproduce and inspect

Install the existing imagery dependencies and optional reporting dependencies.
From the repository root:

```powershell
python scripts/build_kween_case.py --allow-downloads
python scripts/verify_kween_case.py --write-summary
python scripts/plot_kween_case.py
# Cached rebuild: no download permission is supplied.
python scripts/build_kween_case.py
python scripts/verify_kween_case.py
python -m unittest discover -s tests -v
```

The builder archives its plan before new acquisition, source geography, STAC
responses, metadata indexes, hashes, failures, COGs and numerical results under
`outputs/africa/kween/`. `latest.json` points to the immutable run manifest.
Verification checks identities and hashes, validates each scene COG, and
recomputes derived maps and summaries pixel by pixel. The generated figure is
`outputs/africa/kween/kween-case.png`. Generated imagery and caches stay out of
Git; the compact [executed run record](KWEEN_RUN.json) is published with the code.

## What this permits

Present this as a reproducible public-data research case with its exact dates,
proxy boundaries, coverage failures and descriptive findings. It does not
permit an accuracy percentage, crop-loss estimate, verified historical early
warning, cause diagnosis or irrigation recommendation. No new model is trained.
Foundation models remain benchmark candidates requiring compatible inputs and
independent held-out outcomes.

Next scientific dependencies are confirmed crop calendars and boundaries,
independent dated field outcomes, unaffected/affected reference cohorts, and
multiple independent events and regions. Internet sources can supply candidates;
they must pass the existing evidence provenance and admissibility checks before
becoming labels. Missing reports are never healthy-field labels. Engineering
reproducibility and agricultural usefulness are separate claims.
