# Private field evidence review in the Vantage workspace

The workspace now links to **Field evidence review** (`web/field-review.html`).
It opens a local review JSON in browser memory and displays dated observed NDVI
change, per-field support, withheld comparisons and provenance. It is a research
review interface, not a validated scouting queue or shared farmer-data service.
No real independent field outcomes or consented farm boundaries are bundled.

## Prepare and open a packet

First create a [dated field-change packet](FIELD_CHANGE.md) from reviewed
boundaries and original observed optical artifacts. Then run:

```powershell
python scripts/build_field_review.py outputs/private/field-change-001 --out outputs/private/field-review-001.json
python scripts/serve_demo.py --port 8917
```

Open the local workspace and select **Field evidence review**, then **Open review
packet** and choose the generated JSON. No private dataset is copied into `web/`
or served through a new API. The page makes no data requests and uses no browser
storage. Clearing or reloading resets the opened review. Do not expose the local
demo server publicly; it supplies no production authentication or tenant isolation.

The packager checks the fixed GeoTIFF filename, its archived SHA-256, reported
grid and acquisition/cutoff tags, finite data/mask agreement, NDVI difference
range and support bounds against eligible field counts. It exclusively creates
the output under ignored `outputs/private`; existing files are not replaced.
Checksums and declarations are not independently authenticated evidence.

## What the customer sees

- Earlier/later observation dates and decision cutoff in explicit UTC.
- An observed vegetation-change overview with an explicit numerical legend.
  Lower/higher NDVI colours are not crop-health categories or a diagnosis.
- A selectable field list with support status, boundary version, declared crop
  and season, common valid pixel counts, usable fraction and paired mean/median.
- Explicit blockers and withheld statistics for unsupported fields.
- Source references, recipe, report/raster hashes and limitations.
- A print button for the current field details and shared map overview.

Selecting a field updates the details, not the map footprint. The map continues
to show the union of supported fields. No boundary highlight is invented from
summary statistics, and unsupported fields do not receive fabricated imagery.
The checkerboard denotes no supported comparison, not healthy or unchanged
crops. A valid zero-change pixel remains visible with the neutral colour.
The raster is a north-up grid-cell overview, not a basemap, navigable farm map
or area-weighted geographic rendering.

## Preview precision and privacy

The packager samples the original grid at an integer stride so the preview is
no larger than 1024 cells on either axis. Small features can disappear from this
nearest-sampled overview; full-resolution statistics remain unchanged. Preview
values are rounded to 0.0001 NDVI-change units and encoded as little-endian int16,
with 32767 as nodata. Colours saturate at +/-0.30, while pixel inspection reports
the encoded value. This is not sensor precision, statistical confidence or a
validated agronomic threshold. Use the original GeoTIFF for full-resolution GIS
analysis. Browser packets are capped at 12 MiB.

The browser validates the packet schema, bounded dimensions/values, date order,
field status/statistic consistency and research-only status. All source labels
are rendered as text rather than HTML. A restrictive content security policy
blocks data connections. The review JSON still contains private field identifiers
and source references; treat the file and any printouts as private. This local
workflow does not supply consent administration, encryption, durable team records
or role-based access control.

## Verification and limits

Python tests use synthetic fields to check packing, hashes, grid/support
inconsistency rejection, private output enforcement and overwrite refusal.
JavaScript tests cover zero-versus-nodata, malformed packets, withheld records,
duplicate IDs, safe label handling and absence of data connections/persistence.
The existing workspace model tests also remain in the selected regression suite.

Browser QA opened a clearly synthetic test packet, checked populated and empty
states, explicit UTC dates, map scaling, field details, clear/reload behaviour
and a 390-pixel layout without horizontal overflow. No browser console errors
were observed. The print dialog and real farmer datasets were not exercised.
The first sandboxed preview was unreachable; the approved loopback preview
outside the sandbox worked and was stopped after QA. Nothing was deployed.

The next data dependencies remain actual consented boundaries, confirmed
calendars/crop context and independent scouting outcomes. No new model, field
priority, diagnosis, irrigation prescription or agricultural accuracy claim is
enabled. Uganda remains Vantage's first pilot within its broader agriculture
scope; forestry stays with Vepris and CropSight validation does not transfer.

Verification on 24 October 2026: **19 Python tests and 15 JavaScript tests passed**
in the selected field-review/change/pixel and workspace model suites. Browser QA
and `git diff --check` passed as described above. Generated synthetic packets
and screenshots remain in ignored private outputs, outside Git.
