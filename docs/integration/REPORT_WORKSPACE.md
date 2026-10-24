# Local evidence report workspace

Open `http://127.0.0.1:8917/reports.html` while the local demo server is running.
The main workspace links to Reports on desktop and phones. The page follows
Vantage's platform design and supports the existing Kween historical snapshot.
It is not a live portfolio report or a government-approved reporting format.

## Implemented

- A document preview, editable title and optional self-entered preparer.
- Historical evidence cutoff separately displayed from report generation time.
- Dated optical coverage, freshness limitations, radar context and source hashes.
- Optional import of a browser-exported `local-review-pack-1` JSON, up to 1 MB,
  50 field-name references and 100 notes. The exact snapshot ID and cutoff must
  match. Unknown note targets, duplicate field IDs, promoted validation status
  and future note dates are rejected.
- Later local notes appear only in an explicitly unverified appendix. Field
  boundaries, raw field records and geometries are not copied into the report.
  Notes are not joined to pixels or counted as independent historical outcomes.
- Standalone HTML and structured report JSON downloads. Editing report details
  disables exports until the preview is rebuilt. The same report object drives
  preview and export, keeping the generation timestamp consistent.
- Removing the appendix or reloading clears imported notes from page memory.
  No automatic local-storage read or note upload is performed.

HTML contains no scripts, images or network dependencies. Dynamic strings are
escaped, the preview iframe is sandboxed, and the exported document includes a
restrictive content policy. This reduces active-content risk; it is not a digital
signature, independent provenance verification or authenticated author identity.
The app displays only a self-entered preparer and source-consistency identifiers.

## Use

1. Open Reports and inspect the default evidence preview.
2. Optionally export a review pack from the scouting workspace and open it here.
3. Set a title and preparer, then update the preview.
4. Download HTML or JSON. Review the included notes before sharing the file.
5. For PDF, open the downloaded HTML in a browser and use Print / Save as PDF.
   The application does not generate a PDF itself.

Only known historical numerical evidence is included; no imagery-only diagnosis,
irrigation prescription, yield-loss estimate or invented live result is added.
Uganda remains a pilot subset of Vantage, and the Lillie US backlink is retained.

## Checks and limits

`node --test tests/test_report_model.cjs tests/test_workspace_model.cjs`
passes 15 selected tests, covering date separation, note isolation, stale-pack
rejection, bounds and escaped export content. Browser QA loaded the real snapshot,
opened a synthetic matching pack, verified both download actions, and checked
that metadata edits disable export. The downloaded HTML/JSON were read back and
confirmed to contain the synthetic draft without changing zero outcome counts.
Main-page width was checked at 390 px without horizontal document overflow;
desktop preview was visually inspected. These checks are not a full accessibility
audit. The system print/PDF dialog was not exercised.

Remaining scope: connected maps in reports, additional pinned research cohorts,
actual farmer data, independently validated outcomes, team approvals, authenticated
signatures, cloud report history and partner-specific reporting contracts. No
external sharing, email delivery or public deployment is implemented.
