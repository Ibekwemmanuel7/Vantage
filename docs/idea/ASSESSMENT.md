# IDEA opportunity assessment

20 October 2026. Research and local development only. No outreach, publication,
approved engagement, customer validation or private-system access. Vantage remains
an independent [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US) product.

## Verified public fit

IDEA describes weekly agricultural intelligence, extension resources, human-reviewed
digital tools and agricultural program support [1]. Its public Uganda reporting
page contains dated weekly entries addressing regional weather, crop stages,
markets and field priorities, and requests local observations [2]. A reviewed
October report PDF contains regional practical-action sections [3]. This supports
a potential fit for a dated satellite-evidence insert reviewed by IDEA experts.
It does not prove procurement demand, budget or acceptance of satellite priorities.

The public AgriPortal URL was reachable, but the retrieved page exposed a static
shell/local-fixture loading message [4]. That limited inspection establishes
neither the complete portal capability nor an integration/API contract. Do not
assume a private API, authentication access or access to farmer records. Begin
with PDF-ready HTML, CSV and GeoJSON; confirm integration needs in discovery.

IDEA's public service descriptions include program design, coaching and on-site
work [5]. Vantage should complement that expert work with traceable measurements
and field questions. It should not impersonate IDEA advice or reuse its branding
as if approved. No relationship between IDEA and LiveBeyond is inferred. David S.
Vanderpool's role, intended organization and authority remain discovery questions.

## Recommended first slice and implementation

One candidate district: Iganga, Uganda, subject to partner confirmation. One crop
workflow: maize extension. District sources describe maize-related production
support and processing, and MAAIF publishes a maize extension manual [6][7]. This
justifies a candidate workflow, not an assertion that every study pixel is maize.

Implemented: a 0.1° study box at 33.40–33.50°E, 0.65–0.75°N, divided into four
0.05° area units. The box is analyst-selected; its relationship to the current
district boundary requires confirmation. A public boundary source inspected
represented old administrative geography, so it was not silently adopted as a
current district boundary. This is not district-wide coverage or farmer parcels.

Sentinel-2 L2A vegetation measurements are restricted to historical ESA WorldCover
2021 cropland class. That mask can be outdated or wrong and cannot identify maize,
planting dates, varieties or management. Small mixed fields and cloud gaps favor
area-level questions initially. The UI and exports carry this limitation.

The retrospective May 2024 dataset uses available public imagery and CHIRPS v3
rainfall. A build completed in about 196 seconds with caches partly populated;
that is not a cold-run benchmark or a weekly operating-cost measurement. Nine
selected scenes processed successfully and six failed with recorded errors in
that run. Keep failed sources and cloud-rejected observations in the evidence
record. All four units had rainfall evidence; only one passed target vegetation
coverage. Actual results are in `web/data/uganda.json` and the printable report.

## Changes from Texas

| Concern | Texas cotton configuration | Uganda extension configuration |
|---|---|---|
| Decision user | Independent crop adviser | Agricultural analyst / extension coordinator |
| Crop eligibility | Confirmed upland cotton and pivot records | Maize focus proposed; pixel-level crop identity unconfirmed |
| Spatial unit | Consented field/within-field zone | Area-level study grid; no parcel diagnosis |
| Season | Partner-confirmed cotton stage window | District crop calendar and actual planting/stage confirmation required |
| Baseline | Same-field paired changes | Matching seasonal windows across earlier years |
| Rainfall | Not connected in original slice | Separate CHIRPS estimate; no forecast or soil-moisture inference |
| Data gaps | Five-day freshness hypothesis | Fourteen-day demonstration policy, to be tested locally |
| Validation | Adviser visits and unflagged zones | Expert-reviewed areas and sampled extension checks, including unflagged controls |

Uganda has multiple rainfall regimes; national seasonal calendars cannot establish
one field's crop stage [8]. The original Texas engine remains unchanged. The area
engine, data schema and configuration are separate. Forestry stays with Vepris.

## Sources inspected

1. [IDEA public website](https://www.idea.ag/).
2. [Uganda report archive](https://www.idea.ag/uganda-ag-report).
3. [IDEA October report PDF](https://www.idea.ag/_files/ugd/32d709_4f0ac3fbbd0a45a79d2fef8538fbceed.pdf).
4. [Public AgriPortal](https://agriportal.idea.ag/).
5. [IDEA services](https://www.idea.ag/services).
6. [Iganga production and marketing](https://iganga.go.ug/dept/production-marketing).
7. [MAAIF maize extension manual](https://agriculture.go.ug/wp-content/uploads/2023/06/Maize-training-manual-for-extension-workers-in-Uganda_Reduced.pdf).
8. [FEWS NET Uganda seasonal calendar](https://fews.net/east-africa/uganda/seasonal-calendar/october-2024).

These sources establish published activities and crop context, not endorsements
or a completed customer interview. Pricing and pilot scope below remain proposals.
