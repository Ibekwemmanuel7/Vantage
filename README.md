# Vantage

<!-- LILLIE_US_PORTFOLIO_START -->
**Part of [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US)** · [Portfolio map](https://github.com/Ibekwemmanuel7/Lillie_US/blob/main/docs/PORTFOLIO.md) · [Scope and boundaries](docs/portfolio/SCOPE.md)

**Current development focus:** African agriculture, starting with a candidate Uganda extension pilot. **Status:** Local public-imagery research prototype; no independently validated agriculture service. Texas work is deferred.
<!-- LILLIE_US_PORTFOLIO_END -->


The initial market definition is documented. Vantage is a new product and does not copy CropSight or inherit its validation.

## Current priority: Uganda

As of 20 October 2026, Uganda is the active development priority; Texas is
retained for a later phase. Support an extension coordinator deciding which
agricultural areas to investigate this week. The candidate Iganga-area study
is a starting point, not validation across Uganda or Africa. Partner, crop,
season and operational boundaries still require confirmation.

See the [Africa development architecture and delivery gates](docs/africa/ROADMAP.md)
and [field sampling / capacity evaluation contract](docs/africa/EVALUATION.md).
The [multi-location Uganda archive](docs/africa/ARCHIVE.md) now supplies a
bounded acquisition/replay tool for three study boxes and two annual calendar
windows in 2022–2024. These geographic probes require partner and crop-calendar
confirmation before use as agricultural validation cohorts.
The [numerical multispectral builder](docs/africa/MULTISPECTRAL.md) preserves
physical reflectance, per-band masks and chronological sequences for research;
it does not fabricate labels or automatically retrain the model.
The [historical-cropland coverage desk](docs/africa/CROP_CONTEXT.md) now separates
whole-box quality from coverage over WorldCover 2021 cropland across all three
Uganda study boxes. The six-band archive now has 18/18 scenes after access
recovery. Current crop confirmation and independent field labels remain absent.
The [seasonal series](docs/africa/SEASONAL.md) adds ten-day research observations
through March–July 2023 and 2024 in Iganga. The [public-evidence program](docs/africa/PUBLIC_EVIDENCE.md)
records internet-sourced event leads and rejects unverified automatic labels.
The [Kween 2023 reconstruction](docs/africa/KWEEN_CASE.md) adds a frozen public-event
case with six-band acquisitions, quality-gated pixel comparisons and native-grid
rainfall context. It retains withheld results and does not turn news reports
into field labels or claim historical warning performance.
Its [denser temporal follow-up](docs/africa/KWEEN_TEMPORAL.md) processes all eight
eligible May–early June acquisitions and separates recent acquisitions from
usable observations. The final optical evidence remains stale despite two
recent images; this limitation is retained rather than filled through clouds.
The [radar feasibility and numerical slice](docs/africa/KWEEN_RADAR.md) adds three
same-track Sentinel-1 RTC observations and reproducible backscatter changes.
Independent terrain screening remains absent; radar does not refresh the optical
evidence or enter the scouting queue as a crop-condition score.
An offline sampling and paired baseline evaluation tool is now implemented;
no actual field outcomes or new agricultural performance results are supplied.

## Original Texas definition — deferred

First test: support an independent crop consultant prioritising field and zone inspections in irrigated upland cotton in Hale and Floyd counties, Texas. Proposed pilot: 3-5 growers and 20-40 fields, with farmer records and independent scouting. Broader crop, pasture and farm-water services require separate design and validation.

## Relationship to Lillie US

Vantage owns farmer/adviser decisions and crop/pasture workflows. Vepris owns forestry. Velo can supply water context and Vaughan event flood/coastal layers; these interfaces are planned. Scouting support is not automatic irrigation control or a diagnosis.

This is an independent repository linked to the Lillie US portfolio. It now has an offline Python prototype; it has no deployed service or Lillie US runtime integration. See the [scope brief](docs/portfolio/SCOPE.md) for design requirements.

## Initial market definition

See [the cotton-scouting market and pilot definition](docs/portfolio/INITIAL_MARKET.md), including sourced regional context and proposed evaluation.

## Texas-first product strategy

Updated 20 October 2026:

- [Market desk survey and positioning](docs/strategy/TEXAS_MARKET.md): sourced Texas/county context, competitor capabilities, buyer and price hypotheses, discovery and expansion.
- [Production architecture target](docs/strategy/PRODUCTION_ARCHITECTURE.md): standards, deployment components, spatial/temporal data model, security, analytics and delivery gates. This is a proposed design, not deployed infrastructure.
- [Historical evidence program](docs/strategy/HISTORICAL_EVIDENCE.md): Plainview 2023 hail, 2022 drought and later coastal cases; reproducibility, controls and marketing claim limits.

The first real historical catalog query found 162 Sentinel-2 items across 23
acquisition dates near the Plainview hail report. This is metadata feasibility,
not completed pixel analysis, confirmed crop damage or product validation.
Run `python experiments/inventory.py --out outputs/plainview-inventory.json`
to refresh the public metadata inventory. Real-event geospatial reproduction
and customer interviews remain pending.

## Uganda extension evidence demonstration

Alongside the Texas profile, a separate local Uganda area-level workflow now
processes real public Sentinel-2, WorldCover and CHIRPS rainfall data. It is a
cached May 2024 retrospective reconstruction, not live monitoring or validated
maize diagnosis. The Iganga-area box and maize extension focus are candidate
choices requiring partner confirmation. No IDEA approval or engagement is implied.

```powershell
python scripts/serve_demo.py --port 8917
```

Open http://127.0.0.1:8917 for the analyst desk, separate Texas/Uganda profiles,
review queue, source evidence, printable weekly brief, CSV/GeoJSON exports and
local demonstration feedback. Cached operation uses only the Python standard
library; scientific rebuilding needs `requirements-geo.txt`.

- [IDEA fit assessment](docs/idea/ASSESSMENT.md)
- [Bounded pilot proposal and cost assumptions](docs/idea/PILOT_PROPOSAL.md)
- [Discussion brief for David S. Vanderpool](docs/idea/DISCUSSION_BRIEF.md)
- [Demo script and discovery questions](docs/idea/DEMO_AND_DISCOVERY.md)
- [Run/reproduction instructions, scientific limits and attribution](docs/idea/OPERATIONS.md)

The implemented reconstruction flags a rainfall difference while withholding
vegetation assessments in three of four units for insufficient coverage. It
does not establish crop damage or cause. No outreach or publication has occurred.

## Satellite imagery and ML workbench

The Uganda desk now includes actual dated RGB/NDVI imagery, quality overlays,
shared unit views, masked NDVI differences and georeferenced COG downloads.
A versioned COG/STAC dataset and independent-label template support reproducible
ML work. An exploratory earlier-year Isolation Forest has been fitted; no
supervised classifier is trained because independent outcomes are absent.

See [imagery/ML run instructions](docs/ml/README.md),
[dataset card](docs/ml/DATASET_CARD.md), [model card](docs/ml/MODEL_CARD.md) and
[architecture decisions](docs/ml/ARCHITECTURE.md). Restart the local server and
refresh the Uganda profile to use the new controls. Raster binaries and weights
are local generated artifacts, not an installed production service.

## Run the original Texas vertical slice

The original Texas CLI uses Python 3.11+ and the standard library. The full
regression suite also needs `requirements-ml.txt`. From this repository:

```powershell
python -m unittest discover -s tests -v
python -m vantage brief examples/synthetic.json --as-of 2027-07-15T12:00:00Z --out outputs/demo
python -m vantage feedback outputs/demo/brief.json --db outputs/demo/feedback.sqlite --tenant demo --zone west --visited-at 2027-07-16T12:00:00Z --outcome uncertain --finding "Field check needs follow-up; cause unconfirmed" --action "Return visit"
```

Open `outputs/demo/brief.html` for a responsive schematic zone map and ranked
evidence. `brief.json` preserves the decision evidence; `zones.geojson` supports
GIS inspection. The example is wholly synthetic, including its 2027 dates.
The original report records feedback via CLI. The shared local analyst desk
also offers labeled demonstration feedback for the Texas fixture.

Implemented in the original Texas engine: rectangular field/zone validation, dated NDVI import, quality and
freshness gates, same-field temporal anomaly scores, explainable maps and SQLite
scouting feedback snapshots. Real field polygons, imagery retrieval/masking,
before/after imagery and weather integration remain unimplemented in that engine.
The separate Uganda workflow implements retrospective imagery; production
authentication and deployment remain unimplemented. No real-world accuracy or customer value has been measured.

See [architecture and data model](docs/mvp/ARCHITECTURE.md) and
[evaluation and release gates](docs/mvp/EVALUATION.md) for policy assumptions,
limitations and remaining data dependencies. Missing or stale evidence does not
mean healthy cotton. Vantage neither diagnoses causes from imagery nor prescribes
irrigation. Forestry remains with Vepris.
