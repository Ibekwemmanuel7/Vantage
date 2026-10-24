# Vantage platform design direction

Implemented 24 October 2026. The product is Vantage; Uganda is the selected
pilot. Texas remains separate and deferred. This increment redesigns the local
scouting workspace and aligns the field review and research desk presentation.
It does not establish production readiness or new agricultural performance.

## Reference investigation

- [Planet agriculture](https://www.planet.com/industries/agriculture/) emphasizes
  imagery monitoring and an integrated Earth-observation platform. Vantage takes
  an imagery-led workspace direction; it does not claim Planet data, daily
  coverage, commercial resolution or equivalent processing capability.
- [TELUS agronomy software](https://www.telus.com/agcg/en-us/agriculture/agronomy-software)
  describes digital scouting, georeferenced observations, crop records and
  connected workflows. Vantage foregrounds field import, review preparation,
  dated notes and evidence export. These are existing local prototype functions,
  not cloud collaboration or validated agronomic recommendations.
- The user-supplied [NASA Earthdata agriculture page](https://www.earthdata.nasa.gov/topics/human-dimensions/agriculture-production)
  returned HTTP 403 during investigation. The official
  [NASA Landsat agriculture overview](https://science.nasa.gov/mission/landsat/benefits/agriculture-food-security/)
  and [NASA Harvest data portal](https://data.harvestportal.org/) provide supporting
  context on agricultural Earth observations and data discovery. We do not claim
  to have inspected the blocked page visually.

These are design and workflow references, not evidence of user preference,
certification, endorsement or a completed usability study. No competitor assets,
logos, page layouts or marketing claims are copied into the application.

## Product experience

1. Orient the user: Vantage identity, workspace context and Uganda pilot.
2. Distinguish historical evidence from current operational information.
3. Explore actual imagery and vegetation differences next to an evidence brief.
4. Prepare fieldwork using the register, notes and local review plan.
5. Inspect observation history, regional season context and source lineage.

The workspace has a persistent dark navigation rail, white content surfaces,
forest-green actions and a restrained lime accent. A larger imagery viewport
and adjacent evidence brief carry the primary task. Compact metrics distinguish
registered fields, readiness, research localities and independent outcomes.
Missingness is visible in context rather than replaced by invented metrics.

Four section links connect Monitor, Fieldwork, Seasonal context and Data &
provenance. They navigate real sections; they do not imply separate live products.
The imagery expand action changes the layout without cropping or generating
replacement imagery. Satellite/vegetation switching keeps the existing dated
snapshot and source checks. No decorative zoom or pan controls suggest an
interactive geospatial service that is not connected.

On phones, section links form a two-column layout and imagery/evidence stack.
Field evidence, research and the Lillie US backlink remain reachable. No external
font, image or UI-library dependency was introduced. Inter is preferred when
installed; Segoe UI and system fonts provide local fallbacks. Focus indicators,
reduced-motion support, semantic controls and existing dialogs are retained.

## Implementation and verification

- `web/platform.css` and `web/platform.js` extend the existing workspace.
- `web/field-review.css` and `web/style.css` align the other two tools.
- Existing field records, drafts, raw imagery and scientific outputs are unchanged.
- Eighteen existing workspace, regional-context and field-review model tests pass.
- Browser checks exercised layer switching, imagery expansion/restoration and
  the evidence dialog. Main workspace, field review and research were inspected
  at 390 px with no horizontal document overflow. The main workspace was also
  visually inspected at desktop width. These checks are not a full accessibility
  audit, farmer usability study or exhaustive end-to-end regression suite.
- Screenshots are local proof artifacts under ignored `outputs/private`.
- The user-requested local preview remains at `http://127.0.0.1:8917/`.

## Remaining product work

The visual system can support an enterprise application, but current capabilities
remain a local prototype: no tenant accounts, team assignment, cloud sync,
authenticated partner API, production tile service or operational alert delivery.
The V avatar explicitly represents the workspace, not a signed-in account.

Next design validation should observe consultants/extension users completing
three tasks: identify usable evidence, prepare a field check and return a dated
finding. Measure completion, misunderstanding of quality/freshness and mobile
friction before adding more layers. Production maps, weather, rainfall, reports
and partner integration must be driven by real connected data and tested needs.
Current rainfall acquisition and independent field validation gaps remain open.

Forestry remains with Vepris; Vantage does not inherit CropSight validation.
The product retains the Lillie US backlink and avoids imagery-only diagnosis
or irrigation prescriptions.
