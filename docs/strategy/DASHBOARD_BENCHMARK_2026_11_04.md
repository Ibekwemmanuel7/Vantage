# Satellite agriculture SaaS dashboard benchmark

Research date: 4 November 2026. Vantage within
[Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

## Conclusion

A competitive agricultural dashboard connects trustworthy observations to completed
fieldwork. Visual polish, interaction quality, scientific interpretation and SaaS
operations must work together. Vantage has an improved visual prototype and useful
traceability, but does not yet meet that combined bar.

The next major increment should be a connected field workspace: boundaries,
dated imagery, linked charts, evidence readiness and a scouting task on one
screen. Keep Uganda as the active pilot and Vantage as the product identity.

## Review method and limits

Reviewed public first-party documentation, help guides, product pages and published
interface examples from six platforms. Planet's public Visual Analysis documentation
and its embedded map screenshot were inspected in a browser. Vantage's repository
and current implementation documentation were reviewed. This is not an authenticated
hands-on evaluation of competitor subscriptions, a new Vantage usability test,
measured performance comparison or independent verification of vendor agronomic
claims. Features may vary by region, plan and product version.

A Cropwise training PDF was indexed by search, but the web reader rejected its
12 MB length. Its screenshots were not visually inspected. No accounts, trials,
paid services or integrations were opened. No product code was changed for this review.

## What the reference platforms teach us

| Reference | Documented product pattern | Vantage recommendation |
| --- | --- | --- |
| [Planet Explorer](https://docs.planet.com/platform/get-started/access-data/search-and-preview/) and [Browser](https://docs.planet.com/platform/get-started/analyze-data/analyze-imagery-in-browser/) | AOI discovery, date/quality filters, imagery comparisons, index time series and distinct visual/analytical export workflows | Make map, acquisition selection and time-series inspection one linked experience |
| [Planet Visual Analysis](https://docs.planet.com/platform/get-started/analyze-data/analyze-imagery-in-visual-analysis/) | Public documentation shows collection/layer/date controls beside an interactive map, AOI tools and statistics; the application is described as beta | Use a persistent map and contextual controls. Distinguish collection, acquisition, observation and mosaic dates; do not merge beta and established product capabilities |
| [EOSDA field guide](https://eos.com/user-guide/crop-monitoring/fields/) and [team guide](https://eos.com/user-guide/crop-monitoring/team-management/) | Field/season management, imagery date line, indices/charts, image-quality context, team roles and field access | Field and season become primary navigation context. Scouting tasks need owners, permitted fields and completion states |
| [OneSoil Platform](https://onesoil.ai/en/platform) and its [developer-authored app listing](https://play.google.com/store/apps/details?id=io.onesoil.scouting) | Field onboarding, seasonal comparisons and connected web/mobile workflows; the listing describes offline notes with photos and geolocation | Prioritize simple boundary setup and field capture that survives weak connectivity |
| [Cropwise Operations](https://www.cropwise.com/operations) | Satellite monitoring connects to scouting tasks, mobile inspections, reports and farm operations | Keep the observation-to-visit-to-finding loop coherent, without copying the full machinery/stock-management suite |
| [TELUS Agronomy](https://www.telus.com/agcg/en-us/agriculture/agronomy-software) and [mobile workflow description](https://www.telus.com/agcg/en-us/blog-resources/mobile-agronomy) | Crop records, georeferenced scouting and mobile advisor workflows, with report sharing | Let an advisor capture a finding once, retain it with the field and reuse it in a report |
| [John Deere Work Plans API](https://developer.deere.com/dev-docs/work-plans) and [Work Planner explanation](https://www.deere.com.au/en/campaigns/youve-got-what-it-takes/help-me-improve/plan/your-plan/) | Persistent field-specific work plans link planning, mobile execution and integration | Design stable field/task identifiers and a partner integration contract. Machinery integration is optional for the first Uganda customer |

The lessons above concern workflows. Vendor claims about yield gains, diagnosis,
cost savings or precision are not adopted as verified performance. Public
documentation is not proof that any feature works for Uganda's crops, farm sizes
or connectivity conditions. No comparative pricing or subscription availability
was verified, and no procurement recommendation is made.

## The standard Vantage should aim for

### 1. A clear job at each level

An advisor's home should answer what needs a review, what evidence is missing,
what visits are due and what findings await verification. A field page should
answer what changed, when, over what observed area and what to do next.
Research/model diagnostics belong in an evidence/research view rather than
dominating the customer's operational home.

A government/programme overview should be a separate role/view with geographic
coverage, observation dates, sample support and aggregation rules. It must not
present a few monitored farms as representative national production estimates.
Farmers and scouts need a simpler phone experience than programme analysts.
Confirm language and units with actual users; support hectares, kg/ha and mm
consistently, with any conversions explicitly labelled.

### 2. Context that remains consistent across screens

Keep organization, pilot geography, crop season and selected field visible.
Changing context must update the map, list, chart and report together. Preserve
links back to the exact observation and field-boundary version. Historical
reconstructions, current observations and regional priors need visibly different
states. Do not let a user infer that Kween 2023, regional 2024 calendars and a
newly imported farm belong to one live portfolio.

### 3. Real spatial and temporal interaction

The map should support field selection, fit-to-boundary, pan/zoom, actual boundary
overlays and an accessible numerical equivalent. The date control should select
real available acquisitions and show missing periods. Selecting a point on the
chart should select the same observation on the map. A comparison tool should
state whether it compares two acquisitions, a seasonal reference or a model.

Use a stable legend for cross-date comparisons, or make any changed scale obvious.
Allow true-color inspection beside index layers. Layer names should say what
is measured: vegetation, moisture-related index, rainfall context or observed
surface water. Add layers only when they improve a user task and have supported
inputs; a long layer catalogue is not an outcome.

### 4. Evidence quality is part of the interaction

For every observation show acquisition time, usable coverage inside the selected
boundary, stale/fresh status, resolution, source and processing identity.
Scene-level cloud percentage cannot substitute for field-level accepted pixels.
Planet's [Browser documentation](https://docs.planet.com/platform/get-started/analyze-data/analyze-imagery-in-browser/)
itself notes that a scene-cloud filter can leave cloudy frames.

Unavailable pixels remain unavailable. Separate observed, composited, inferred
and ML-reconstructed products. A cloud-filled image needs source dates and model
quality information; a visually complete image is not a complete observation.
Show regional weather at its supported scale, rather than implying a coarse
grid is a field sensor. Avoid uncalibrated confidence percentages.

### 5. A complete scouting workflow

An investigation needs a field/zone, evidence link, question, assigned person,
due date and status. A visit records dated findings, location, photos, crop stage,
severity when supported, and an explicit uncertain/unknown option. A later review
can verify or reject the finding without rewriting its original submission.

Evidence gaps and agronomic concerns must remain distinct. A cloudy field can
need a visit to gather evidence; that is not a satellite-confirmed crop problem.
Field ranking should consider crop/calendar context, observation quality and
scouting capacity. Lowest NDVI alone is not a validated ranking method.

### 6. Mobile reliability and accessibility

Responsive CSS is only a starting point. Test capture offline, interrupted uploads,
queued changes, clear saved/sync states, duplicate submission prevention and safe
conflict handling. Let users prefetch a bounded set of assigned fields and avoid
large imagery downloads by default. A manual coordinate/location alternative is
needed when GPS permission is unavailable.

Target [WCAG 2.2 AA](https://www.w3.org/WAI/WCAG22/quickref/) and verify it, including
keyboard access, focus visibility, contrast, text resizing and reflow. Maps need
textual values and non-colour status cues. Use generous touch targets as a design
choice. A 390 px overflow check is not a conformance audit.

### 7. Reports and integration that preserve context

A report should retain the field/boundary, crop season, observation/cutoff date,
quality limits, map legend, findings, review status and source/model versions.
Readers must be able to distinguish actual measurements from estimates.
Provide portable data exports alongside a human-readable report. Draft and
approved documents need different states; a typed author is not authentication.

For David's application, define permissioned APIs and an embedded map/report
module using the same records. Keep private farm data separate from public
reference layers. Avoid manually maintaining a second copy of every field in
another product. Do not promise SSO or integration until implemented and tested.

### 8. Actual SaaS operation

Organization accounts, role/field permissions, durable records, audit events,
backups and recovery, monitored data jobs and understandable errors are product
capabilities, not cosmetic settings. Authorization must be enforced by the
service. Show whether data is loading, absent, stale or failed; do not silently
use an old result as current. Measure performance and reliability on representative
phones, networks, field counts and raster sizes.

## Vantage review

This assessment reflects repository evidence, not a new end-to-end audit:

| Dimension | Current status | Highest-value gap |
| --- | --- | --- |
| Visual system | Cohesive green navigation, content hierarchy and responsive layouts | More readable small labels and validation with target users |
| Map experience | Dated raster previews, layer switching, expanded view; separate private change-review canvas | A connected GIS workspace with selectable registered field boundaries |
| Time context | Observation coverage/history and separate regional calendar context | Linked date slider, chart and map with consistent field-season selection |
| Quality/provenance | Explicit missing/stale states and checked report imagery | Carry field-level quality and provenance through the complete task lifecycle |
| Fieldwork | Local checklist and unverified draft notes | Durable tasks, assignments, photos, review history and verified outcomes |
| Mobile | Responsive pages; earlier phone layout checks | Offline capture and tested synchronization/recovery |
| Reporting | Local HTML/JSON with embedded verified previews and source hashes | Shared report history, approvals, PDF workflow and integration contracts |
| SaaS | Local prototype | Authentication, tenant isolation, authorized APIs, storage, job operation and recovery |
| ML | Exploratory experiments; weak first yield benchmark | Appropriate labels and held-out validation before customer-facing prediction widgets |

The previous visual redesign was useful, but does not by itself establish
enterprise usability or operational readiness. No numerical maturity score is
assigned: we have not run a standardized comparative usability study.

Specific changes recommended:

- Keep the current Vantage branding and restrained palette; improve legibility
  of small text and use consistent icons with visible names where needed.
- Make empty onboarding useful: add/confirm a field, crop and season, then check
  available evidence. Do not make a new customer navigate a wall of zero metrics.
- Move internal research counters, including independent-label totals, into
  evidence/research detail while retaining clear operational readiness messages.
- Bring imported field boundaries into the main map. A register entry should open
  its own evidence state, never inherit an unrelated locality's imagery.
- Reduce disjoint navigation between workspace, research, file review and reports
  by preserving selection/context and offering clear return paths.
- Make the main field page the connection between observation, visit and report.

## Recommended information architecture

Primary navigation: **Overview, Fields, Scouting, Conditions, Reports**.
Secondary navigation: **Data & methods, Research, Administration**.

| Screen | Primary purpose |
| --- | --- |
| Overview | Reviews due, evidence gaps, recent findings and coverage for the selected portfolio |
| Fields | Searchable list synchronized with an interactive field map |
| Field detail | Map center, field context/selection left, evidence/action panel right, linked timeline below |
| Scouting | Assigned visits, offline field forms, review and completion history |
| Conditions | Supported vegetation, rainfall/weather and water context with date/scale controls |
| Reports | Reproducible briefs, export and eventually permissioned report history |

Use this sequence: portfolio → field → dated evidence → investigation → finding →
review → report. Role-specific home views should reuse the same permissioned data.
Forestry remains with Vepris; Texas and future geographies need their own data
and validation, not a cosmetic country switch.

## Recommended delivery order

**First: connected field workspace.** Implement the boundary map, consistent
field-season context, actual acquisition selection, linked quality/chart view
and explicit empty states. It can start with the historical research cohort and
label it honestly. No operational ranking without the required evidence.

**Second: durable fieldwork foundation.** Establish tenant/field permissions and
storage, then assigned tasks, offline observation capture, idempotent synchronization
and verification. This is also the path toward useful independent model labels.

**Third: report/integration completion.** Link reports to the same field/task
records; add approval history and partner/API integration. Scope actual PDF output
and end-to-end export checks before calling it complete.

**Parallel scientific track:** confirm crop calendars/outcomes and improve seasonal
data coverage. Add forecast or cause-specific modules only after honest task-specific
benchmarks. Maps and ML outputs must retain missingness and abstention states.

## Acceptance checks for the next increment

These are proposed Vantage engineering/user-research targets, not competitor
measurements or industry certification:

1. A user selects a registered field and the map, title, season and observations
   agree. Switching fields cannot retain the previous field's evidence.
2. Every displayed observation shows its date and accepted field coverage; a
   stale/missing observation never becomes a healthy/zero status.
3. Selecting an observation on the chart changes the map to the same acquisition.
4. Users can create a task with the field, evidence and question prefilled; later
   capture and review preserve the original timestamps and record identities.
5. An offline test creates a note/photo, restarts the app and reconnects. The note
   survives and synchronizes once, with visible failure/conflict handling.
6. A second organization cannot read the field or report through direct API calls.
7. Reports contain the selected field, period and quality limits; offline HTML
   imagery and any implemented PDF output agree with the preview.
8. Measure meaningful-content and map-interaction latency at the median and 95th
   percentile on agreed devices/networks. Set latency budgets after measuring the
   real dataset and test conditions; do not claim speed from an empty demo.
9. Conduct keyboard/contrast/reflow tests plus at least one screen-reader review.
   Test colour interpretation with users; do not rely on red/green alone.
10. Observe approximately five to eight intended users on field selection, evidence
    interpretation and visit/report tasks. Record completion, errors, time, and
    historical-versus-current misunderstandings. This is formative research, not
    proof of population-wide usability or agronomic benefit.

The product objective should be useful, traceable field investigations completed
with less effort. Track relevant user outcomes alongside evidence coverage and
model-validation work, rather than treating added widgets as progress.
