# Observed satellite pixels by declared field

Vantage now has an offline adapter that summarizes the existing quality-masked
observed NDVI artifacts within versioned field polygons. This replaces no
existing dashboard or rectangular prototype contract. It supplies research
vegetation summaries, not priorities, crop diagnoses, yield or water advice.
No actual consented farm boundary has been supplied or independently verified.

## Boundary contract

Copy `configs/field_boundaries_template.geojson` into `outputs/private` and add
your consented fields. The empty template is intentionally rejected by the
processor: no fields are invented. Each GeoJSON Feature must have a WGS84
longitude/latitude `Polygon` or `MultiPolygon` and these nonempty string properties:
`field_id`, `boundary_version`, `consent_ref`, `season_id`, `crop`.

Holes and multipart fields are supported. Two-dimensional finite coordinates,
explicit ring closure, valid topology and positive area are required. Invalid
shapes are rejected; there is no silent repair. A repaired boundary requires
human review and a new version. IDs must be unique; country/season/crop identity
and consent references remain declarations requiring review.

This bounded adapter allows 1-100 features, at most 10,000 vertices per feature,
at most one degree of extent per axis, and at most four million raster cells.
Antimeridian-crossing fields are unsupported. Fields are summarized separately;
overlapping declarations are not dissolved and must not be summed as unique
farmland or independently sampled farms.

## Existing raster input and command

Dependencies: `python -m pip install -r requirements-field.txt` in an appropriate
local environment. The current development environment already has these packages.

Use a local NDVI NPZ produced by `expand_uganda_archive.py` or the recent pixel
processor. Its arrays must be `ndvi`, boolean `valid`, affine `transform` and
scalar `crs`. The mask must exactly match finite NDVI values, and observed NDVI
must be within [-1, 1]. A finite, north-up, projected metre grid is required;
rotated, geographic and feet-based grids are rejected. No reprojection or
resampling of imagery is performed. Boundaries are transformed onto that grid.
The CLI uses its installed Rasterio wheel's PROJ database to avoid unrelated
system GIS installations; library callers manage their own GIS environment.

Supply `--pixels-sha256` from the archived processing report's `artifact_sha256`.
This detects changed pixel files; it does not independently prove that an NPZ
contains observed rather than reconstructed values. Use only the original
observed optical artifacts, never predicted cloud-gap targets. Keep the source
processing recipe, rejection masks and scene metadata with its `--source-ref`.

```powershell
python scripts/summarize_field_pixels.py outputs/private/fields.geojson outputs/path/to/observed-pixels.npz --pixels-sha256 HASH_FROM_PROCESSING_REPORT --source-ref PRIVATE_PROCESSING_REPORT_REF --acquired-at ACQUISITION_ISO_TIMESTAMP --available-at INPUT_AVAILABILITY_ISO_TIMESTAMP --cutoff DECISION_ISO_TIMESTAMP --out outputs/private/field-observation.json
```

The timestamps above are placeholders. Availability must reflect when all
inputs and processed evidence actually became available, no earlier than source
acquisition and no later than the decision cutoff. For a newly processed
historical scene, preserve the actual processing/receipt date; do not claim it
was operationally available during the historical event. The tool checks
ordering but cannot authenticate timestamp declarations.

## Quality, small fields and staleness

The default polygon mask uses Rasterio's `all_touched=False` burn rule: pixel
centres and the documented boundary-line rule, not fractional area weighting.
See the [Rasterio masking documentation](https://rasterio.readthedocs.io/en/stable/api/rasterio.mask.html).
Holes and multipart components are retained. This choice avoids treating every
edge-touching pixel as a full field pixel, but does not remove mixed-pixel
effects or guarantee exact area weighting on small/irregular plots.

Each report records projected geometric area, selected raster pixels, accepted
pixels, usable fraction, median observed NDVI, geometry hash, version, declared
season/crop, source timestamps and input file hashes. Selected pixels are a
grid denominator, not independent samples or a claim about harvested area.

The full polygon must be covered by the raster footprint. Partially covered and
outside fields have no field median or usable fraction; summaries are withheld
to prevent a clipped denominator from suggesting full coverage. Very small
fields may contain no selected pixels. Comparison eligibility requires all of:

- At least **9** selected pixels and at least **70%** accepted support.
- Acquisition no older than **7 days** at the declared cutoff.
- Complete raster footprint coverage of the field.

These are explicit research engineering defaults, not validated agronomic
thresholds. The library accepts declared alternative policies; the CLI retains
the defaults. A median requires at least nine accepted pixels, even where the
selected-pixel coverage gate passes. This extra support requirement also blocks
comparison eligibility. Stale observations may retain their historical median
but are ineligible for comparison. Missing pixels or stale dates never establish
healthy crops. The report supplies no anomaly score or current scouting rank.

## Implementation limits and next data dependencies

No farmer boundary is bundled with the code. Tests use synthetic geometry and
arrays only, including holes, multipart fields, invalid topology, partial
footprints, missing pixels, staleness and CLI hash/overwrite checks. No actual
farm observation or new agricultural performance result was created.

Before a pilot we still need consented, independently reviewed field boundaries,
confirmed crop/season context and calendars, dates with adequate usable imagery,
and independent field outcomes. Date-to-date anomaly calculation, field-edge
uncertainty, spatial weighting, reviewed protocol export and customer UI linkage
remain separate work. Uganda is Vantage's first pilot; this adapter is not
country-specific. Forestry stays with Vepris and CropSight validation does not
transfer.

Verification on 24 October 2026: **35 tests passed** across field pixels, recent
pixels, field protocols, field intake and the original prototype slice. The
first sandboxed run could not open the existing feedback test's temporary
SQLite database; the approved unrestricted rerun passed. CLI help and
`git diff --check` also passed. Tests used synthetic fields only; no real
field report, dashboard change, model training or performance claim was added.

Follow-up: [dated field change](FIELD_CHANGE.md) now supplies paired observed
NDVI differences and a masked GeoTIFF. Independently validated anomaly detection
and customer UI linkage remain pending.
