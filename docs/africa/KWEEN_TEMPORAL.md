# Kween temporal follow-up: acquisition is not usable coverage

Independent Vantage research within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda remains the priority; Texas is deferred. No CropSight validation is inherited.

This is an **exploratory follow-up** to the [original Kween case](KWEEN_CASE.md),
whose selected May 21 scene preceded the June 6 report by 16 calendar days.
The original findings are preserved. This new analysis does not become a blinded
validation exercise because its configuration was fixed before new downloads.
No new field outcome, model training or agricultural accuracy claim is supplied.

## Fixed design

The [follow-up configuration](../../configs/kween_2023_followup.json) fixes
May 1–June 5, 2023, the original Ngenge core box, a maximum of twelve unique
acquisitions and a seven-day research freshness limit at the June 5 cutoff.
The local frozen plan is written before the new catalog query. The exact parent
run and manifest checksum are pinned; changing a latest pointer cannot silently
change the inherited grid, historical crop mask or reference years.

Process **every eligible full-box acquisition** in the fixed interval, including
cloudy observations. Alternate processing/tile versions with identical acquisition
times are deduplicated using scene-cloud metadata, timestamp and item ID. Do not
select by measured NDVI or keep only the clear observations. Reject truncated
catalogs and an exceeded acquisition budget rather than silently sampling them.
This is not every intersecting satellite tile or every observation from all sensors.

Keep the six physical bands, per-band and common masks, actual dates and all
failures. Use the original historical-cropland quality rules: at least 60% usable
cropland and 100 valid pixels. The seven-day freshness limit is an unvalidated
research policy, not a promised service interval. It is applied to acquisition
time; historical product delivery times are unverified.

Compute earlier-year anomaly maps only for acquisitions inside the original
May 21–June 5 reference calendar window. Earlier May observations retain absolute
NDVI summaries, with no calendar-mismatched anomaly maps. Use exactly the original
four earlier-year references and per-pixel comparison gates. There is no temporal
interpolation, cloud-gap filling or new threshold tuning.

## Executed findings

Run `f304c87fc3a00d36966ab77f` processed **8/8 eligible acquisitions**, producing
**24 validated scene COGs and two reproduced anomaly COGs**. Four acquisitions
pass coverage checks. Both available anomaly maps are stale at the final cutoff.

| Acquisition | Usable historical cropland | Coverage status | Research age status at cutoff |
|---|---:|---|---|
| May 1 | <0.01% | Withheld | Outside seven days |
| May 6 | 35.8% | Withheld | Outside seven days |
| May 11 | 76.2% | Qualified | Outside seven days |
| May 16 | 98.9% | Qualified | Outside seven days |
| May 21 | 98.4% | Qualified | Outside seven days |
| May 26 | 99.1% | Qualified | Outside seven days |
| May 31 | 32.3% | Withheld | Inside seven days |
| June 5 | 1.2% | Withheld | Inside seven days |

The latest qualifying observation is **May 26, 10.676 days old** at the cutoff,
despite a catalog acquisition less than one day old. The series correctly returns
`stale_research_context`. Recent cloud-obscured acquisitions do not refresh an
older qualifying observation. Missing observations are neither healthy crops nor
negative outcomes. Four qualified observations are separated by approximately
five days, followed by the explicit 10.7-day gap to the cutoff.

The May 26 comparison has median NDVI difference **+0.014**, versus **+0.026** on
May 21. These positive area medians coexist with localized negative differences;
they do not establish crop damage or its absence. Observation medians can cover
different valid pixels. The last two maps are withheld, so this optical series
cannot establish conditions near publication. Neither geographic proxies nor
crop calendars have been independently confirmed.

## Reproduction and verification

Use the existing imagery dependencies and optional `requirements-reporting.txt`.
The exact pinned parent case and its local caches must already exist. Those
large artifacts are not in Git; the commands below replay this local archive.
A fresh checkout cannot recover this exact frozen run from the compact summary
alone. From the repository root:

```powershell
python scripts/build_event_series.py --allow-downloads --write-summary
python scripts/verify_event_series.py
python scripts/plot_event_series.py
python scripts/build_event_series.py
python -m unittest discover -s tests -v
```

For a separate replication, first execute the parent builder and its verifier
with `--write-summary`. A new frozen timestamp can produce a new parent run ID.
Review that newly generated parent summary, copy the follow-up configuration
into `outputs/`, explicitly replace its `parent_run_id` with the reviewed new
ID, and pass that copy using `--config`. This is a new follow-up run, not a
byte-identical recovery of this published run. Preserve the original tracked
configuration and prior Git history; do not silently redirect the pinned ID.

Artifacts are under `outputs/africa/event-series/`; the figure is
`outputs/africa/event-series/kween-temporal.png`. The
[compact executed record](KWEEN_TEMPORAL_RUN.json) is tracked; imagery, caches
and raw catalog responses remain outside Git.

Verification checks source/plan/code hashes, the exact eligible catalog cohort,
dates, freshness flags, original crop-mask provenance, every scene's COGs and
recomputed crop evidence. It independently reproduces the anomaly arrays and
summaries and recomputes the final timeline status. The download-disabled replay
preserved identical manifest bytes, SHA256
`9e156d67acb07ab0ea217d5884f66286399e58b39be6fe40a7b3beab447054ae`.
The full regression suite passed **86 tests**, including cloud-versus-freshness,
exact age boundaries, missing/failed observations, duplicate timestamps, future
dates, timezone ambiguity and parent-cutoff checks. Lint checks passed for this
increment. The generated figure was visually inspected.

## Product implication and remaining dependencies

The observation desk needs separate fields for latest acquisition, latest usable
observation, age at decision cutoff and quality-qualified gaps. A recent catalog
timestamp must not be displayed as fresh agricultural evidence. This increment
implements that contract in the research pipeline and local report; it does not
add a live operational feed or a new dashboard panel.

The next sensor investigation should assess whether radar observations can add
independent usable information during these optical gaps. Sensor availability
alone would not establish crop stress or validate fusion.
The [executed radar investigation](KWEEN_RADAR.md) now provides three same-track
numerical observations while retaining the terrain-quality and agricultural gates.
Confirmed boundaries, crop identity and calendars, independent dated outcomes, unaffected/affected
cohorts and additional independent events remain necessary for supervised
training and performance claims. Public internet records can provide candidate
evidence through the existing admissibility review; absent reports are not labels.
