# Run, reproduce and evaluate the local prototype

## Cached demonstration

From `Vantage/`, Python 3.11+:

```powershell
python scripts/serve_demo.py --port 8917
```

Open http://127.0.0.1:8917. The cached UI, exports and local SQLite feedback need
no third-party packages or internet access. The port is deliberately distinct
from other local Lillie previews. Stop with Ctrl+C. Bind remains loopback-only.
This is a single-operator research tool, not a production multi-user service.

The printable standalone brief is `web/data/weekly-brief.html`; open it from the
Weekly brief link and use the browser's Print / Save as PDF. The analyst desk
also has print styling. CSV, GeoJSON and full evidence JSON download from the UI.
Demo feedback persists at `outputs/uganda/feedback.sqlite`, separate from source
control. It is tied to the exact brief ID and snapshot. No personal information
is needed. Every saved entry is marked as demonstration feedback.

## Rebuild from public sources

Use a separate Python environment; optional scientific dependencies are pinned
in `requirements-geo.txt` to the versions used in this session:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-geo.txt
.\.venv\Scripts\python scripts/build_uganda_demo.py
```

This accesses public Microsoft Planetary Computer STAC/asset signing, Copernicus
Sentinel-2 L2A, ESA WorldCover 2021 and UCSB CHIRPS v3. It caches source metadata,
decoded raster windows and rainfall TIFFs under ignored `outputs/uganda/cache/`.
The builder prefers Rasterio's matching PROJ database to avoid a conflicting
system PostGIS installation. It requires network access; it purchases no imagery.

Configuration: `configs/uganda_iganga.json`. This adapter is deliberately limited
to a two-by-two 0.05°-aligned study grid, May 1–15 vegetation and May 11–15 rainfall.
It checks rainfall grid alignment rather than silently assigning another location.
The area-draft UI downloads an unprocessed research definition; it does not imply
arbitrary areas/dates have already been implemented. A new district/crop/window
requires data feasibility, baseline and season review before extending the adapter.

The builder selects at most three scene-cloud-ranked distinct acquisition times
per year, requiring a tile bounding box covering the study area. Scene cloudiness
only selects candidates; usable pixel fractions determine scientific acceptance.
All selected failed sources are recorded. Rasterio reads at approximately 20 m in
UTM zone 36N; reflectance is averaged and categorical masks use nearest neighbor.
Native 10 m red/NIR values are decoded using XML quantification and band offsets.
SCL vegetation/bare classes are retained with a one-grid-pixel invalid-area buffer.
WorldCover class 40 supplies a historical cropland denominator per unit.

For each year/unit, use median NDVI across accepted dates, not spatially invented
cloud-filled pixels. Compare target against median annual values from 2020–2023,
requiring at least three usable reference years. Rainfall is a separate five-day
estimate. Thresholds and freshness are demonstration settings, not agronomic risk
levels or confidence percentages. Short references and unequal observation counts
limit comparability. Missing NDVI does not become a crop assessment because a
rainfall signal exists.

The frozen JSON carries source IDs, unsigned URLs, acquisition dates, quality
counts, reflectance metadata/hash, processed-array hashes, failed source types,
retrieval time, configuration, code version and a content-derived brief ID.
Temporary signed asset URLs are not published in the evidence bundle.

## Temporal and scientific limits

This is present-day retrospective reconstruction, not historical operational
replay: CHIRPS v3 and some reprocessed imagery were not available in this form at
the 2024 cutoff. Acquisition dates and reference years precede the cutoff, but
provider availability at the time is not established. Do not claim a historical
alert or lead time. No verified field damage, maize location, planting date,
management event or reference field outcome has been supplied.

The historical broad cropland mask may include rotation, mixed fields or changed
land use. No parcel-level or crop-specific condition is inferred. The study box
is not a verified current district polygon. The overview SVG map remains a spatially referenced schematic. The added
[imagery/ML workbench](../ml/README.md) now supplies a dated raster inspector,
quality overlays and COG downloads. Neither view is a navigation tool. Continuous scheduled updates,
automatic arbitrary-AOI processing, authenticated hosting and AgriPortal API
integration are not implemented. Cached weeks do not update automatically.

## Costs and measurements

No paid imagery or hosting was purchased. The cached demo uses local compute and
storage. The observed partly cached scientific build took about 196 seconds;
that is not a production timing guarantee. `DEMO_RUN.json` summarizes the executed
run. Rainfall source files are regional rasters; transfer can dominate the first
run. Measure cold/warm downloaded bytes, CPU/memory, storage and analyst effort
before quoting a service. The observed local source/cache footprint was about
35.4 MB (not a measurement of total network transfer). Pricing assumptions and exclusions are in
[PILOT_PROPOSAL.md](PILOT_PROPOSAL.md), not presented as actual metered costs.

## Checks and remaining validation

```powershell
python -m unittest discover -s tests -v
node --check web/app.js
```

The scientific tests use synthetic fixtures explicitly. They cover independent
signals, cloud gaps, missing versus normal evidence, stale/future observations,
short/zero references, duplicate rejection, exports and escaped print content.
Feedback tests verify local persistence and cross-brief/demo-only validation.
Original Texas tests remain part of the regression suite.

Before a prospective pilot: confirm district/crop/season and local field capacity;
independently inspect masking/georegistration, current crop locations, matched
references and false/missed flags; agree the weekly editorial cutoff; freeze the
method on development data; sample unflagged areas; define useful findings and
follow-up intervals. Include coverage failures, nonvisits and uncertainty. Do not
translate software tests or reconstructed rainfall into a food-security outcome.

## Data attribution

- [Copernicus Sentinel data terms](https://dataspace.copernicus.eu/terms-and-conditions) and source asset legal-notice links in STAC records.
- [ESA WorldCover](https://esa-worldcover.org/en/data-access): 2021 v200 land cover, CC BY 4.0. Credit ESA WorldCover project / 2021 / European Space Agency; verify attribution for external materials.
- [CHIRPS](https://chc.ucsb.edu/data/chirps3): UCSB Climate Hazards Center CHIRPS v3, public-domain data; rainfall estimates are not field gauges or forecasts.
- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/docs/): discovery and source access; service conditions and source licences remain applicable.

Source products and classification uncertainty require review before operational
or commercial release. No customer dataset or farmer contact list was collected.
