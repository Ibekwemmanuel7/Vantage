# Vantage customer workspace: first-pilot research and implementation

Researched 20 October 2026 (America/Chicago). Part of
[Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda is the active market hypothesis; Texas is deferred. Vantage does not
inherit CropSight code or validation. Forestry remains with Vepris.

21 October clarification: the dashboard is Vantage's customer workspace.
Uganda is the selected first pilot, not the product's identity or total scope.
The current data and import extent remain Uganda-specific; broader branding
does not add other markets' datasets or validated capabilities.

## Customer and market interpretation

Design first for an extension coordinator or cooperative/program field-team
lead who prepares reviews and coordinates local investigation. Farmers are
beneficiaries and important research participants. A program manager,
cooperative lead or agricultural service organization is a proposed budget owner,
not an identified customer. Interviews, procurement, willingness to pay and
repeat use remain untested. Uganda is not a proxy for all African markets.

An August 2026 [IIED Uganda briefing](https://www.iied.org/22759iied) describes
limited public-extension reach alongside a diverse private digital-extension
ecosystem. It identifies affordability, connectivity and digital-literacy
constraints, with some services shaped by commercial or donor priorities.
This supports a constrained, assisted workflow as a design hypothesis; it does
not establish demand for Vantage or a market-size estimate.

[EzyAgric's own site](https://ezyagric.com/) presents farmer records, extension,
input and market services, plus a portal for farmer-network management and agent
work with cooperatives. These are vendor-described capabilities, not our
independent evaluation. Vantage should test whether a narrowly useful inspection
decision can complement existing records/advisory workflows rather than assume
another general farming dashboard is needed. No integrations have been built.

[Farmforce's Connect page](https://farmforce.com/products/farmer-app/) emphasizes
offline workflows, training and farmer-network engagement. Its page includes
older pilot and 2024 language, so it is a design reference, not proof of its
October 2026 deployment status or performance. We do not adopt its forestry
or compliance scope.

The proposed product question remains: which agricultural areas or confirmed
fields should the team inspect first on its next round, and what should it
check there? Vantage currently cannot answer that operationally: current fields,
crop calendars, fresh observations and independent outcomes are absent. The
dashboard makes that gap explicit while supporting useful preparation.

## Design decisions and supporting evidence

| Need or risk | Product response | Implemented now |
| --- | --- | --- |
| Coordinators need a next action, not a wall of sensor diagnostics | Field register → evidence review → local review plan → notes/export | Separate sections and clear primary actions |
| Limited connectivity and device access | Small local assets, system fonts, optional imagery, downloadable pack | No CDN, webfont, remote basemap or third-party browser SDK; no full offline guarantee |
| Historical evidence can be mistaken for a current alert | Persistent historical banner, cutoff and image dates, explicit stale state | Kween 2023 is labeled historical; zero field priorities |
| A new acquisition can still be unusable | Show coverage per acquisition and distinguish latest from latest usable | Eight real dated optical observations and 10.7-day age at cutoff |
| Boundary uncertainty can turn a box into a fictitious farm | Keep locality proxy separate from imported field geometry | Imports start unverified and awaiting observations; no automatic matching or analysis |
| Color can imply crop health or conceal missingness | Text statuses, patterned coverage gaps, labeled diverging change scale | Orange/blue mean below/above a reference, not damaged/healthy |
| Technical detail can overwhelm the daily workflow | Show dates and next steps first; source IDs on demand | Evidence dialog, details disclosure and separate research desk |
| Field observations must not become automatic truth | Keep local draft notes separate from validation and historical results | Notes never change independent-outcome count or eligibility |

The [Principles for Digital Development](https://digitalprinciples.org/principles/design-for-inclusion/)
recommend considering language, literacy, disability, affordability and access.
Their [design-with-people principle](https://digitalprinciples.org/principles/design-with-people/)
also requires meaningful participation across affected and administering groups.
Desk research does not substitute for that participation. This first version is
English only; language priorities must be established with the actual pilot
community and field team, with reviewed translations rather than invented local
advice or automatic disease diagnoses.

The [GOV.UK task-list guidance](https://design-system.service.gov.uk/components/task-list/)
supports visible progress through a set of activities. Its
[details guidance](https://design-system.service.gov.uk/components/details/)
supports revealing optional information without hiding information most people
need. Accordingly, dates, limitations and eligibility stay visible; source hashes
and research methods are secondary. This applies usability patterns, not the
GOV.UK visual identity or a claim that the Vantage workflow is user-validated.

[WCAG 2.2](https://www.w3.org/TR/WCAG22/) informs labeled controls, visible focus,
keyboard operation, non-color statuses and narrow reflow. Major action buttons
use 44 px targets; smaller controls must be assessed against the relevant
24 px minimum and exceptions. No full WCAG conformance audit is claimed.
The design uses restrained green, warm neutral surfaces and amber uncertainty;
it avoids fabricated risk scores, gains, yield predictions and customer counts.

## Implemented architecture and data contracts

`web/index.html` is now the customer workspace. The previous analyst interface
is preserved at `web/research.html`, with its original profiles, imagery viewer,
research archive and local demonstration-feedback endpoint. Those existing
feedback records are separate from the new workspace's browser drafts.

`scripts/build_dashboard.py` derives `web/data/scouting.json` from four committed
Kween run summaries, recording their run IDs and file checksums. The snapshot
keeps the 2023 cohort separate from the Iganga and multi-location archives.
Client validation rejects an unsupported or contradictory snapshot rather than
granting an operational priority. A source change requires rebuilding and, if
the evidence contract changes, an explicit contract update.

The builder also verifies the original optical manifest and selected raster
checksums before generating two real-pixel PNG previews in ignored `outputs/`.
The RGB uses B04/B03/B02, a fixed 0–0.30 reflectance display range and gamma 2.2.
The anomaly preview uses the existing 26 May 2023 comparison against its
2019–2022 calendar-window reference, with a fixed ±0.30 NDVI display range.
Clipping is for visualization only. Transparent pixels are unavailable, not
infilled observations. Neither image is a crop diagnosis or a field boundary map.

The loopback server serves only the fixed case/layer preview paths when the
requested snapshot and image checksums match. It does not expose arbitrary
output files or reach a remote imagery fallback. If previews are absent, the
UI retains a labeled unavailable state and the evidence facts remain readable.
Scientific raster assets, previews and private field records stay outside Git.

The browser stores fields, review items and notes under a versioned local-storage
key. Field imports accept a bounded GeoJSON FeatureCollection with Polygon or
MultiPolygon geometries, unique IDs, optional crop and planting date. Checks
reject open/self-intersecting/zero-area rings, invalid holes, overlapping
MultiPolygon components, excessive complexity and coordinates outside the
documented Uganda workspace bounding extent. This is a deliberately conservative
subset, not a complete OGC geometry or country-boundary/ownership validation.
Up to 50 fields, 1 MB per file, 500 vertices per ring and 10,000 coordinates per
import are supported. All fields remain `user_import_unverified` and
`awaiting_observations`, regardless of their crop/date properties.

Review items reference either the historical locality or an imported field.
Notes record date, type, finding, next step and `unverified_local_draft` status.
They do not update imagery, confirm crop identity or enter supervised training.
The review-pack export contains the snapshot ID, historical cutoff, fields,
checklist and notes. Browser-storage failures are visible and allow an in-memory
export. There is no authenticated account, team sync, submission, production
database, edit history, service worker, automatic field analysis or language
translation. A copied pack is an audit/export artifact; pack reimport is not
implemented. Existing field records cannot yet be edited or removed in this UI.

The pending independent-radar-processor comparison is now visible in the
customer evidence view. It still has zero evaluated provider exports. Account
credentials/actual outputs, difficult-terrain cases and processing/DEM alignment
remain external dependencies. No benchmark improvement is claimed.

## Reproduction and checks

Serving the cached dashboard needs the Python standard library. Rebuilding
previews also needs `requirements-geo.txt` and `requirements-dashboard.txt`, plus
the preceding pinned local Kween scene and event-series artifacts. A fresh clone
can show the committed snapshot and honest image-unavailable state, but needs
those artifacts to reproduce actual previews. Compact summaries do not replace
the original rasters.

```powershell
python scripts/build_dashboard.py
python scripts/serve_demo.py --port 8917
python -m unittest discover -s tests -q
node --test tests/test_workspace_model.cjs
```

Open `http://127.0.0.1:8917/`. The old analyst desk is at `/research.html`.
Browser QA uses `/?qa=1` for a separate storage namespace; synthetic fields and
notes created there never populate the default customer workspace. The browser
QA artifact files and screenshots remain ignored local outputs.

Verified in the browser: real RGB/anomaly switching, boundary import into the
unassessed register, review-plan persistence after reload, local-note saving and
review-pack download. Actual 390 px and 320 px iframe viewports show equal client
and scroll widths, with no horizontal overflow. This is responsive-browser QA,
not physical-device or field-connectivity testing. Python tests cover snapshot
eligibility and preview checksum/path contracts; HTTP tests cover GET/HEAD,
tampering, unknown assets and non-loopback hosts. Node tests exercise geometry,
duplicate imports, dates, missingness and the research-only evidence contract.

This change passed 137 Python tests and 9 JavaScript contract tests. Rebuilding
the snapshot and both preview PNGs reproduced their bytes exactly. Browser
review also corrected intrinsic-image clipping so the full study extent is
contained in the preview. Main muted, primary-button and amber-status color
pairs were spot-checked at 4.73:1, 9.56:1 and 5.68:1 respectively; this is not a
complete accessibility audit.

## Customer validation before claiming product fit

Recruit a proposed first discovery group of two coordinators, two field officers
and at least one participating farmer representative. These are suggested
research roles and a small usability round, not market validation or a
statistically representative survey. No outreach has been performed.

Use a participant's existing field workflow and appropriate consented examples.
Ask them to identify whether evidence is current, explain why the newest image
may be unusable, find the next review action, import a boundary, record an
uncertain finding and produce a pack for a colleague. Observe the device they
actually use, connectivity constraints, preferred language, existing paper or
messaging handoffs, who owns records, and who could approve a paid continuation.

Record task completion, time, assistance, abandoned steps and critical
misinterpretations. Distinguish formatting preferences from failures that could
cause a wrong field decision. Any interpretation of stale/missing evidence as
healthy or live should trigger redesign before an operational pilot. Agree
targets after formative observation, then freeze a subsequent test protocol.
Do not report a usability score, price acceptance or adoption rate from this
desk research. Real field-level imagery matching, confirmed calendars and
independent dated outcomes remain necessary for the eventual scouting product.
