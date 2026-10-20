# Verification record

Local checks, 20 October 2026. No deployment or prospective agronomic evaluation.

- Seventeen Python tests passed: original Texas regression tests plus area-level
  rainfall/vegetation separation, quality, staleness, future acquisition exclusion,
  reference sufficiency, duplicate rejection, export/HTML escaping and local
  feedback persistence/linkage/demo-only validation.
- Browser JavaScript passed `node --check`; Python modules compiled; `git diff
  --check` passed.
- Public-data acquisition executed: nine selected Sentinel-2 scenes processed,
  five annual CHIRPS pentads and a historical WorldCover tile subset. Six scene
  failures are retained in the run record. Rainfall raster scales/offsets were
  checked (1/0), native resolution approximately 0.05°. Cached footprint about
  35.4 MB; partly cached build approximately 196 seconds.
- Desktop browser verified rendered measurements, source details, independent
  profile switching, gap filter including partially usable review units, empty
  filter state and CSV download. Actual downloaded file was produced.
- Keyboard Enter activated area selection; Escape closed the feedback dialog.
  Semantic labels, focus styling, skip link and native dialog controls are present.
  This is not a full assistive-technology accessibility audit.
- A clearly marked demonstration review saved through the UI and was returned
  from SQLite. It is tied to that brief revision and does not appear under another
  profile/revision. No real historical field validation was recorded.
- At a 390×844 viewport, the layout and feedback dialog were inspected. Document
  width did not exceed the viewport. Long evidence tables scroll within their
  container. Desktop and mobile screenshots are under `outputs/uganda/`.
- A generated missing-data QA route returned 404 for the evidence file: the UI
  displayed a clear error with no live fallback. After restoring its cached JSON,
  Try again recovered the four-unit view. Generated QA files are ignored.
- Stale, unavailable, short-reference and normal evidence distinctions are
  covered by scientific tests; not every combination has a separate screenshot.
- The standalone weekly brief is generated HTML with print styles and source
  links. The interface print action was invoked, but in-app browser automation
  timed out on the browser print flow. Final PDF pagination/export has **not**
  been verified and no PDF artifact is claimed. The print-ready HTML is provided.

Remaining: browser/device matrix, full screen-reader audit, authenticated hosting,
operational timing/availability, cold-run cost profiling, independent geospatial
QA and partner field evaluation. The schematic map is not a raster/basemap viewer.
