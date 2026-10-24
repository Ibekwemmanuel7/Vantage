# Vantage

<!-- LILLIE_US_PORTFOLIO_START -->
**Part of [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US)** · [Portfolio map](https://github.com/Ibekwemmanuel7/Lillie_US/blob/main/docs/PORTFOLIO.md) · [Scope and boundaries](docs/portfolio/SCOPE.md)

**Product:** Vantage, agricultural evidence and scouting support across separately configured markets. **First active pilot:** Uganda, within the current African agriculture development priority. **Status:** Local public-imagery research prototype; no independently validated agriculture service. Texas work is deferred.
<!-- LILLIE_US_PORTFOLIO_END -->


Vantage leads the product identity. Uganda is the first pilot geography within
Vantage, not the boundary of the product. Geography, crops, calendars and
validation belong to individual market profiles; entering another market does
not transfer evidence or imply an implemented service there.

The initial market definition is documented. Vantage is a new product and does not copy CropSight or inherit its validation.

## Current priority: Uganda

The [private field evidence intake](docs/integration/FIELD_EVIDENCE_INTAKE.md)
now checks dated scouting, planting and harvest submissions, boundary references,
provenance and harvest units. Public reports remain investigation leads; no
submitted record automatically becomes a training or evaluation label. Actual
independently verified field outcomes remain zero.

The [partner-application integration brief](docs/integration/PARTNER_PLATFORM.md)
defines the proposed Vantage maps/reporting component for David's broader
application: Uganda first, with the Philippines and Nigeria as future candidate
markets. It separates current research capabilities from proposed weather,
climate, agricultural land-cover-change and government-reporting modules.
The partner integration and government engagement are not yet established.

A portable, unreviewed historical partner example can now be exported with
`python scripts/export_partner_bundle.py`. It writes `evidence.json` and
`report.html` under `outputs/partner-example`, retaining source lineage,
recomputed freshness at the frozen cutoff and withheld field priorities.
It supplies no live API, preview imagery, yield forecast, input prescription,
water allocation or validated farmland-change result. See the
[example contract](docs/integration/HISTORICAL_BUNDLE.md).

The [recent catalog inventory](docs/integration/RECENT_INVENTORY.md) now archives
and replays bounded Sentinel-2 searches over the three Uganda study boxes.
The 23 October 2026 cutoff run found six catalog items per box; usable pixels,
crop condition and field priorities remain unassessed. This inventory does not
refresh the historical dashboard or connect a live monitoring service.

The [bounded recent pixel processor](docs/integration/RECENT_PIXELS.md) now
processes the latest eligible scene per study box using physical reflectance
decoding and buffered quality masks. The 20 October acquisitions produced zero
accepted pixels in all three boxes; crop-condition assessments remain withheld.
An offline quality audit now attributes these exclusions to source SCL classes
8/9/10, retaining per-class counts and exclusive rejection accounting. Run
`python scripts/audit_recent_quality.py --inventory outputs/africa/recent/a013b10c8db819241036/inventory.json`.
See the [audit and cloud-gap gates](docs/integration/CLOUD_GAPS.md).
The [recent multi-date sequence and persistence benchmark](docs/integration/RECENT_SEQUENCE.md)
now process 18 scenes across the three boxes. Five pass the whole-box coverage
rule, but the latest qualifying observations remain stale. A causal last-clear
NDVI benchmark is implemented; operational infill remains unavailable.
The [transferred-mask evaluation](docs/integration/MASKED_GAP_EVALUATION.md) now
tests prior quality-mask footprints against known clear targets, reports
prediction coverage/abstentions and prevents hidden targets from updating history.
The [cloud-gap dataset split gate](docs/integration/GAP_DATASET.md) now freezes
disjoint location/year assignments and verifies numerical inputs. The current
historical acquisition follow-up now supplies five training, six validation and
six development-test scenes. The minimum date-count gate passes; independent
validation remains pending. See the
[historical acquisition results](docs/integration/GAP_ACQUISITION.md).
An [exploratory learned cloud-gap baseline](docs/integration/GAP_LEARNED_BASELINE.md)
is now fitted on causal training transitions. It has no supported transferred-mask
validation predictions and is blocked from promotion; no operational infill or
agricultural accuracy claim is enabled.
The [May–June expansion](docs/integration/GAP_JUNE_EXPANSION.md) now contains 11
training and 12 validation scenes. The rerun fitted 61,415 samples from eight
target dates, but still has zero supported transferred-mask validation targets;
the learned model is not promoted and uncertainty calibration remains pending.
The [isolated-versus-sequential gap comparison](docs/integration/GAP_PROTOCOL_COMPARISON.md)
confirms zero supported Lira gap predictions in either protocol. On available
clear-transition validation pairs, regression MAE is 0.0708 versus persistence
0.0606; the learned baseline is not promoted.
The [radar availability check](docs/integration/GAP_RADAR_AVAILABILITY.md) finds
causal <=7-day Sentinel-1 RTC catalog matches for 8/9 Lira optical coverage-gap
dates and 2/6 Iganga dates in May–June. No radar pixels or terrain validity are
established by these catalog matches; no radar model is trained.
The [bounded Lira radar sample](docs/integration/LIRA_RADAR_PIXELS.md) now extracts
two same-track June passes on the optical grid. Both have 100% positive numerical
VV/VH support; terrain and agricultural validity remain withheld. No optical
values are reconstructed and no radar-assisted model is trained.
An [independent Lira surface-slope proxy](docs/integration/LIRA_TERRAIN.md) now
excludes 0.73% of the whole-box grid at the fixed 10-degree rule. This is not
acquisition-specific terrain validity; radar illumination and agricultural
eligibility remain unverified.
The [Lira acquisition-specific local geometry check](docs/integration/LIRA_VIEWING.md)
now verifies both source annotations against SAFE references and flags 18 of
307,468 pixels per pass for local geometry risk. Locally unflagged pixels remain
uncertified: full nonlocal shadow analysis and trusted-processor agreement are still absent.
The [bounded Lira visibility follow-up](docs/integration/LIRA_VISIBILITY.md) now
finds no obstruction within the sampled 5km search for either pass. All 307,468
whole-box pixels pass that bounded test; full illumination certification and
independent processor agreement remain absent.
The [Lira comparison requests and causal pairing table](docs/integration/LIRA_PAIRING.md)
are now prepared. Three of six June optical dates match one of the two processed
ascending passes within seven days. No external provider exports were supplied:
zero independent comparisons and no radar-assisted model or gap-filled imagery.
The [local CDSE export fetcher](docs/integration/CDSE_EXPORT_FETCH.md) is now
implemented and dry-run tested. Authenticated processing is explicit, validates
outputs before publishing local export folders and never saves OAuth secrets.
No real provider request was submitted in this implementation run.
The [Iganga radar training-cohort numerical sample](docs/integration/IGANGA_RADAR_PIXELS.md)
now processes three fixed ascending passes with full numerical support. Four
of six June optical dates have causal <=7-day pairs. These remain unverified
research references; independent processor comparisons remain pending,
and no radar-assisted model is trained.
The [Iganga-specific quality follow-up](docs/integration/IGANGA_RADAR_QUALITY.md)
now verifies all three SAFE annotations and applies independent slope, local
geometry and bounded 5km sightlines. All study pixels pass the local/bounded
checks; independent processor agreement and agricultural eligibility remain absent.
The [versioned radar–optical research samples](docs/integration/RADAR_OPTICAL_SAMPLES.md)
now contain four Iganga training-reference dates and three Lira validation-reference
dates. Radar features, observed optical references and unlabeled gaps are separate;
the manifest explicitly keeps training ineligible pending external processor
outputs and independent evaluation. No optical values are imputed.
The [local evidence review report](docs/integration/EVIDENCE_REVIEW.md) now combines
dated optical coverage, sample readiness and negative model findings in one
self-contained HTML/JSON export. It is an unreviewed research artifact, not a
live farmer report or partner integration. The customer workspace is unchanged.

The [customer-workspace design and market research](docs/africa/CUSTOMER_WORKSPACE.md)
now informs the default dashboard: a local field register, review plan, real dated
satellite/anomaly previews, coverage history and unverified review notes. Importing
a field never grants a satellite priority. The current Kween view is explicitly
historical; live service and customer fit remain unvalidated.

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
An [independent surface-slope proxy](docs/africa/KWEEN_TERRAIN.md) now measures
terrain-risk sensitivity on the same radar grid. It excludes 1.5% of historical
cropland under the fixed primary rule; passing it does not certify radar
illumination, remove the need for field outcomes or enable agricultural ranking.
The [acquisition-specific local geometry slice](docs/africa/KWEEN_VIEWING.md)
now verifies product annotations through SAFE checksums and derives approximate
local incidence/facet risks. Distant-terrain shadow and trusted-processor
agreement remain unchecked; locally unflagged cells are not healthy-crop labels.
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

Open http://127.0.0.1:8917 for the customer workspace. The preserved analyst desk
with separate Texas/Uganda profiles, review queue, imagery and demonstration
feedback is at http://127.0.0.1:8917/research.html. Cached serving uses only the
Python standard library; scientific rebuilding needs `requirements-geo.txt`.
Run `python scripts/build_dashboard.py` with the pinned Kween artifacts and
`requirements-dashboard.txt` to rebuild the customer snapshot and local previews.

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

The [independent processor comparison workflow](docs/africa/KWEEN_PROCESSOR_BENCHMARK.md)
now prepares three exact Copernicus requests and checks exported scene identity,
grid alignment, nodata and descriptive differences. Provider exports are still
pending: zero independent acquisitions compared, with no agreement or accuracy claim.

Uganda radar research now includes [bounded terrain sightlines](docs/africa/KWEEN_VISIBILITY.md):
three acquisition-specific passes, a larger 30 m elevation window and explicit
unknown/obstruction/clearance-guard states. All 105,091 historical crop-mask pixels
passed the sampled 5 km check on each pass. This does not certify radar illumination;
optical evidence remains stale and independent field labels remain absent.
The CLI artifacts and replay verifier are implemented. The customer workspace
now summarizes this status; detailed terrain maps remain research artifacts.

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
