# Historical event reproduction and evidence policy

Plan and initial catalog feasibility check, 20 October 2026. This document does
not claim an event has been detected or reproduced in pixels. Historical cases
can demonstrate observable behavior; prospective field checks establish whether
the product improves scouting decisions. Market findings: [Texas assessment](TEXAS_MARKET.md).

## Prioritized cases

| Priority | Documented event | Proposed geospatial experiment | What it cannot establish by itself |
|---|---|---|---|
| 1 | 23 June 2023 hail: NWS report of 1-inch hail 4 miles west of Plainview, Hale County [1] | Before/after Sentinel-2 canopy trajectories near the report; candidate cotton fields and comparison areas | Exact damage swath, affected field identity, irrigation eligibility or causal attribution |
| 2 | 2022 Texas drought; contemporary AgriLife economic assessment [2] | Hale/Floyd May–September crop trajectories, weekly drought context and same-stage/year comparisons | Field irrigation failure, per-field yield loss, or preventable financial losses |
| 3 | Hurricane Beryl, Texas landfall near Matagorda on 8 July 2024 [3] | Coastal crop exposure and post-event optical/radar change; explicitly test cloud-induced evidence gaps | Validated flooding, crop loss or scouting value without independent references; different launch geography |
| 4 | Hurricane Harvey, August 2017; Texas GLO records substantial agricultural losses [4] | Coastal cotton/rice crop impact documentation with Landsat/Sentinel-1 and available optical products | Direct validation of the High Plains model, loss valuation or operational alert performance |

Beryl/Harvey are later crop-impact demonstrations requiring their own stage and
harvest rules. Vaughan owns event flood intelligence; Vantage evaluates its
agricultural relevance. A coastal catastrophe is not evidence that a High Plains
cotton priority list works. Foreground local routine usefulness, not disaster imagery.

Also prespecify negative and difficult cases: normal canopy development,
deliberate management changes, harvest/defoliation, healthy fields with cloudy
imagery, no reported event, and widespread same-direction change. A famous-event
gallery without controls will exaggerate performance. A storm report's absence
does not prove absence of hail; reporting is spatially uneven.

## First experiment: Plainview hail

Machine-readable specification: `experiments/plainview_hail_2023.json`.
The exploratory box [-101.90, 34.10, -101.68, 34.28] is analyst-selected around the
reported point. It is not a verified damage swath or a set of customer fields.
The source reports approximate event location and hail size, not a cotton outcome.
June crop establishment may be outside the initial product's stage window. If
eligible canopy cannot be confirmed, retain this only as a sensor/event feasibility
case or replace it for the core product evaluation.

Working windows: 24 May–22 June 2023 before; 24 June–24 July after. Explicitly
exclude the local event day from the illustrative windows. Crop-stage and clear
scene availability may require a documented amendment before locking evaluation.
Use an appropriate UTM projection for geometry/pixels and equal-area/geodesic
calculations for area summaries. Never infer a damage polygon from a point buffer.

An executed metadata query to the public Microsoft Planetary Computer Sentinel-2
L2A STAC endpoint returned **162 items across 23 distinct UTC acquisition dates**,
27 May–24 July 2023; all returned items contain B04, B08 and SCL assets. The response
had no next-page link. Items can include overlapping tiles and processing versions;
this is not 162 independent observations. The first catalog date after the event
was 26 June; usable date remains unknown until masking.

Raw catalog response and query lineage are saved locally at
`outputs/plainview-inventory.json` (ignored generated output). Reproduce:

```powershell
python experiments/inventory.py --out outputs/plainview-inventory.json
```

The script queries a bounded window with a 1,000-item limit, records response
hash and retrieval timestamp, and reports whether pagination would be required.
It does not follow pages, download pixels, infer field coverage or select the
best-looking scene. If `complete` is false, expand the inventory before analysis.
Historical provider publication time is not established by this query.

## Processing protocol to implement next

1. Save the event report, precise source citations, case manifest and exploratory
   AOI. Obtain consented field boundaries and historical crop/stage/irrigation
   records when possible. Public USDA crop layers may identify candidate cotton,
   but are classifications, not grower declarations or pivot confirmation.
2. For a public-only demonstration, use public crop-area polygons or manually
   delineated research regions with their provenance and uncertainty. USDA Crop
   Sequence Boundaries estimate crop areas, not ownership or cadastral parcels [5].
   Do not label a public polygon as an identified customer's field.
3. Inventory all acquisitions, tile footprints, overlap, processing baselines and
   quality assets. Select a deterministic processing revision for each datatake;
   deduplicate overlapping coverage. Retain rejected scenes and reasons.
4. Read raster windows; correctly decode reflectance scaling/offset. Reproject
   onto a documented common grid. Use nearest-neighbor for quality classes;
   document reflectance resampling. Mask cloud/shadow/no-data and buffer edges.
   Calculate valid area per field/zone rather than using scene cloud percentage.
5. Calculate NDVI at appropriate native resolution and retain red/NIR/masks.
   Show all usable dated observations and missing dates. No synthetic filling of
   clouds may be presented as satellite evidence. Consider EVI2/red-edge only
   after an explicit method comparison and resolution checks.
6. Compare robust pre/post trajectories and matched local controls with similar
   planting/stage, soil/background and management. Report change and its
   sensitivity to scene dates, masks, boundary erosion and zone sizes. An
   event-aligned difference is an association; controls do not eliminate every
   confounder. Keep field-wide decline separate from within-field anomalies.
7. Seek independent dated scouting photos, extension assessments or consented
   adjuster/grower records. Record reference precision and certainty. A weather
   report confirms reported weather, not a plant-level diagnosis or exact polygon.
8. For retrospective decision replay, freeze each decision cutoff, baseline,
   due-field list, candidate order and data that would have been available then.
   If actual availability is unknown, label the run retrospective analysis rather
   than an operational replay. Reprocessed assets can demonstrate present-day
   reconstruction, not historical alert delivery.
9. Package results, unsuccessful cases, quality coverage and limitations. Decide
   whether to expand, amend the method on development data, or conclude that
   evidence is insufficient. Do not tune on a held-out case and still call it a test.

## Drought experiment differences

Use same-stage or planting-date-aware multi-year trajectories rather than a
single before/after pair. Archive weekly U.S. Drought Monitor vector layers [6]
and appropriate precipitation/temperature data with native scale and timestamps.
USDM is regional context, not a field moisture sensor. County NASS planted and
harvested acreage/yield [7] can contextualize outcomes but cannot label individual
zones. Confirm management differences before comparing irrigated and dryland areas.

The current within-field median detector can miss drought that affects all zones
together. This is an explicit stress test and motivates a separate field-wide
trajectory baseline. Do not silently call a lack of relative anomaly healthy.
Historical drought loss estimates are regional economic context, not a revenue
pool Vantage could have prevented.

## Evaluation design

Use development events to choose masks, baselines and thresholds; hold out entire
farms/seasons or events for evaluation. Keep adjacent zones and correlated dates
together. Freeze the case cohort before looking for attractive anomalies. Include
unflagged/random checks so misses are observable. Review findings blind to the
flag where possible; separate confirmed, uncertain and no-finding outcomes.

For sensor feasibility report eligible area, usable coverage, number of usable
dates, acquisition-to-first-usable gap, mask QA and missingness. With independent
labels report useful findings at the consultant's visit capacity, false-alarm
burden and missed findings in presampled controls. Report field/event counts and
cluster-aware uncertainty; pixels are not independent farms. Retrospective
association cannot establish hours saved or management benefit without the
relevant workflow observations. Prospective protocol remains in
[MVP evaluation](../mvp/EVALUATION.md).

## Evidence and marketing gates

| Level | Required evidence | Permitted example claim |
|---|---|---|
| Documented event | Reliable event source | "NWS reported hail west of Plainview on 23 June 2023." |
| Catalog feasibility | Archived source search, IDs, dates | "Historical imagery metadata is available for the study window." |
| Retrospective geospatial demonstration | Reproducible pixels/masks, controls, quality and limitations | "This retrospective analysis shows this measured vegetation change." |
| Retrospective validated finding | Independent dated field reference, locked holdout, uncertainty | "Among these independently checked cases, the method had these observed results." |
| Operational value | Prospective baseline comparison, field checks, timing and costs | "In this pilot, advisers achieved this measured workflow result." |

Currently only the first two levels have evidence for Plainview. No crop-change
result, accuracy, early detection, yield saved or money saved is established.
Never write "Vantage would have saved X" from historical loss totals. No irrigation
prescription or imagery-only diagnosis. Retain source attribution and obtain
permission before publishing identifiable grower boundaries, photos or testimonials.

Each public case study should include question, study region/date, input lineage,
method version, before/after with masks and scale, trajectory including gaps,
comparison areas, independent reference status, failed cases, uncertainty, what
was learned and an explicit retrospective label. Publish a small repeatable case
bundle and a consultant-facing brief, not just a dramatic map. No case study or
customer outreach has been published or sent in this work.

## Sources

1. [NWS Lubbock, 23 June 2023 storms](https://www.weather.gov/lub/events-2023-20230623-storms).
2. [Texas A&M AgriLife, State of 2022 Drought, September 2022](https://agecoext.tamu.edu/wp-content/uploads/2022/09/StateOf22Drought_09-22.pdf).
3. [NWS Houston/Galveston Beryl summary](https://www.weather.gov/hgx/beryl2024).
4. [Texas GLO Harvey action plan, agricultural impacts](https://www.glo.texas.gov/sites/default/files/resources/cdr/documents/action-plans/2017-hurricane-harvey/harvey-5b-sap.pdf).
5. [USDA Crop Sequence Boundaries](https://data.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/).
6. [U.S. Drought Monitor GIS archive](https://droughtmonitor.unl.edu/DmData/GISData.aspx).
7. [USDA Texas agricultural statistics, 2024 bulletin](https://www.nass.usda.gov/Statistics_by_State/Texas/Publications/Annual_Statistical_Bulletin/tx-bulletin-2024-web-updated.pdf).
8. [Microsoft Planetary Computer STAC documentation](https://planetarycomputer.microsoft.com/docs/).
9. [NOAA Storm Events database](https://www.ncei.noaa.gov/access/storm-events-database/) for structured event discovery and source reports.
