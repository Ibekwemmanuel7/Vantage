# Seasonal observations and calendar confirmation

20 October 2026. Independent Vantage research within
[Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US). Uganda remains the active
priority; no transferred CropSight validation or forestry work.

## Bounded increment

The first denser series targets the existing Iganga box for March–July in 2023
and 2024. Five months per year, three ten-day slots per month: **30 requested
slots**. This expands within-year temporal coverage rather than adding a
single May/November snapshot. It is deliberately one box first. Lira and
Kasese retain their separate sparse archive; do not transfer this calendar.

The [executed run](SEASONAL_RUN.json) processed **30/30 slots**, generating
**90 validated COGs**. Nine of 15 observations in 2023 and eight of 15 in 2024
pass the historical-cropland development coverage rule; the remaining 13
withhold spectral summaries. Maximum gaps between selected observations are
about 15 days; quality-qualified observations have additional gaps. A complete
acquisition schedule is not complete clear-sky coverage.

Dataset `07fa4c41a15602ce91679d68` has one independent study area, zero confirmed
field calendars and zero independent scouting outcomes. **71 tests passed**;
offline replay preserved the same final manifest bytes, and all actual COGs
and both yearly sequence loads were checked. The standalone figure
`outputs/africa/seasonal/seasonal-observations.png` plots observed points and
withheld dates, not interpolated trends. Export it with
`python scripts/plot_seasonal_series.py` using optional `requirements-reporting.txt`.

The plan is a provisional research window, not a confirmed growing season.
[FAO's Uganda country briefs](https://www.fao.org/giews/countrybrief/country.jsp?code=UGA)
distinguish regional cropping and rainfall conditions. Its current account
does not confirm particular farms' 2023/2024 planting dates. The Uganda
Ministry's [maize extension training manual](https://extension.agriculture.go.ug/kmu_content/Maize-training-manual-for-extension-workers-in-Uganda_Reduced.pdf)
and [FAO crop calendar platform](https://cropcalendar.review.fao.org/) are
discovery sources, not automatically imported field-calendar labels.

## Selection and processing

Archive each monthly public STAC query and reject truncated responses. Within
each dekad (days 1–10, 11–20, 21–month end), require a full bounding-box candidate
and all six physical bands/SCL/metadata assets. Rank by scene cloud metadata,
then timestamp and item ID; deduplicate matching acquisition timestamps before
attempting at most three candidates. Failed attempts are retained. This
selection favours apparent coverage and is not a random scene sample.

The first successfully processed acquisition occupies the slot even if actual
historical-cropland coverage is poor; do not keep shopping for a favourable
vegetation measurement. Bounding-box coverage and scene cloud estimates never
substitute for measured valid pixels. The physical decoder and COG checks are
the same as the established [multispectral pipeline](MULTISPECTRAL.md).

Each observation records historical WorldCover 2021 cropland counts, usable
coverage and quality-gated spectral summaries. Features are withheld below
the development coverage policy. No interpolated dates, crop-stage labels,
synthetic clear pixels, irrigation prescriptions or inferred causes.

## Execute and replay

```powershell
python scripts/build_seasonal_series.py --allow-downloads
# Offline cached replay:
python scripts/build_seasonal_series.py
```

`configs/uganda_seasonal.json` defines the initial plan. Outputs live under
`outputs/africa/seasonal/<plan_id>/`, with monthly catalog responses, metadata
index, per-slot progress, six-band COGs under `scenes/`, and a final dataset
manifest. `outputs/africa/seasonal/latest.json` selects the recorded run.
Source availability failures and real no-acquisition slots remain distinct.
No scenes or slot summaries are automatically added to model training or the
adviser queue. This series is not yet shown in the browser coverage panel.

The existing sequence loader can read a seasonal manifest's `scenes` with the
root set to its `scenes/` directory. Filter the manifest's scenes by year for
within-year arrays. Report real observation dates and gaps; an acquisition
cutoff is not proof of contemporaneous publication/arrival time.

## Independent crop-calendar contract

Copy `examples/uganda-calendar-template.json` to a private operational path
and fill it only with permitted, traceable references. The blank template
contains no inferred crop or dates. Pass it with `--calendars path/to/file.json`.
The check requires matching location/year, a confirmed crop identity, dated
planting/harvest evidence, a field-record or partner-agronomist confirmation,
source/reviewer references, review timestamp and approved permission status.
Missing and regional desk-calendar records do not pass. Calendar confirmation
alone never establishes useful scouting findings or authorizes model fitting.
The review timestamp must not precede the declared planting observation.

The check validates declarations and chronology; it cannot independently prove
the references true. Historical reconstruction needs contemporaneous records.
A current visit cannot verify crop conditions in 2023 or 2024. Keep current
crop-stage confirmation separate from this retrospective completed-season
calendar contract. Do not publish personal references or field records.

## Validation boundary

Independent field outcome labels remain zero unless actually supplied and
validated under the existing label contract. The series does not train a model,
claim accuracy or satisfy the HLS input requirement for a Prithvi benchmark.
Regional calendars, WorldCover class 40 and anomaly flags are not independent
labels. The next comparison needs independently verified outcomes on held-out
regions/seasons, with a predeclared baseline and useful findings at capacity.

The owner confirmed there is no field partner and requested public internet
evidence. The [public-source program](PUBLIC_EVIDENCE.md) now supplies a first
registry and reproducible eligibility checks. Public sources may support
event cases at their stated scale; they are not automatically field labels.
