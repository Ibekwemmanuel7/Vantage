# Independent processor comparison: implementation and pending inputs

Vantage agriculture research within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda remains active; Texas is deferred and forestry stays with Vepris.

The request preparation, strict export ingestion, descriptive comparison and
offline replay verifier are implemented. **No independent processor exports have
been acquired or compared.** The recorded status is `awaiting_provider_exports`,
zero evaluated acquisitions and null metrics. The request payloads have not been
tested against the live service. This is a CLI research workflow, not a new
dashboard panel, radar certification or agricultural model evaluation.

## Why this candidate

The primary [Copernicus Sentinel-1 GRD documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html)
documents local incidence angles and an in/near-shadow flag when radiometric
terrain correction is enabled. Its shadow definition uses scattering area and
source-pixel proximity. That is not equivalent to Vantage's sampled, bounded
5 km obstruction search. Differences are therefore descriptive co-occurrence,
not false-positive/false-negative rates against truth. Provider output is a
comparison candidate, not independently observed ground truth.

The service requires an authenticated account and OAuth client as described in
the [official authentication instructions](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html).
No relevant client credentials are configured in this environment. Account
creation, a network acquisition client and a live request have not been performed.
Credentials must remain local and must never be pasted into Git or this report.

## Frozen comparison contract

`configs/kween_2023_processor_benchmark.json` pins the existing three viewing and
bounded-sightline acquisitions. Preparation freezes the policy before inspecting
any provider results. The Kween parent results are already known, so this is an
exploratory comparison, not a blind test or a new agricultural validation cohort.

Each generated request uses the exact parent EPSG:32636 20 m radar grid, the
source acquisition interval, IW/DV ascending high-resolution GRD, nearest-neighbor
resampling, orthorectification, terrain gamma0, `COPERNICUS_30` and terrain
oversampling 2. The three float32 bands are local incidence, shadow mask and
data mask. Metadata requests preserve the scene inventory and service version.
ORBIT evaluation returns nodata if it sees anything other than one sample.

The Process API supports the new `/process/v1` endpoint format according to the
[March 2026 provider announcement](https://dataspace.copernicus.eu/news/2026-3-9-api-path-structure-updates-sentinel-hub-services).
Scene metadata varies by collection and mosaicking method; the provider's
[metadata guide](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Evalscript/resources/metadata_sh_docs.html)
describes exporting the actual metadata. If required identity/version information
is absent in a live response, ingestion fails. Do not manufacture missing metadata
or relax identity checks simply to get a comparison result.

Choosing the same named DEM family does not prove equal source tile revisions,
vertical datum treatment, resampling, orbit handling or internal processing.
`exact_provider_dem_realization_verified` remains false. Shared Sentinel-1 inputs
and a shared DEM family also prevent treating the processors as independent
agricultural evidence sources.

## Running it

With the preceding pinned Kween local artifacts available:

```powershell
python scripts/compare_radar_processor.py --write-summary
python scripts/verify_processor_benchmark.py
```

This prepares three credential-free request JSON files under
`outputs/africa/processor-benchmark/206317b4fcc9df7197c5/` and a hashed run manifest.
It makes no network call and consumes no provider processing quota.
The committed [status record](KWEEN_PROCESSOR_BENCHMARK_RUN.json) distinguishes
request preparation from evaluated exports.

Once an authenticated provider run is available, save its extracted files in
local directories `outputs/africa/provider-exports/0/`, `1/` and `2/`. Each must
contain:

- `request.json`: the exact submitted prepared request, unchanged.
- `default.tif`: the three-band output raster in the requested order.
- `userdata.json`: the actual exported scene inventory and input metadata.

Then run:

```powershell
python scripts/compare_radar_processor.py --exports outputs/africa/provider-exports --write-summary
python scripts/verify_processor_benchmark.py --exports outputs/africa/provider-exports
```

Keep raw responses and exports locally for audit. Their checksums and selected
identity/version fields enter the manifest; raw files stay outside Git. Export
provenance is an operator-supplied audit trail, not a cryptographic attestation
that a remote service produced the files. Synthetic fixtures only test code.

## Checks and interpretation

Ingestion rejects any grid shift, different CRS, missing band, changed request,
mixed or missing product identity, missing service version, or conflicting
raster/data masks. Actual metadata must identify exactly the pinned complete
SAFE product, including its checksum suffix; merely matching date or orbit is
insufficient. It never silently resamples a comparison raster. Invalid angle,
shadow or data-mask encodings fail before metrics are calculated.

The full locality and historical WorldCover crop mask are reported separately.
Each includes region size, provider availability, comparable angle count and
comparable sightline count. Angle summaries give signed median difference,
mean absolute difference and 95th-percentile absolute difference in degrees.
Unknown local angles do not enter them. Shadow tables separately count bounded
clear/obstruction risk versus provider unflagged/near-shadow; Vantage unknown and
clearance-guard cells are excluded and counted explicitly. Empty comparisons
produce null angle metrics and an unavailable status, never perfect agreement.
Rerunning without prior exports cannot silently replace an evaluated comparison
with a smaller export cohort. Exact replay needs the same original exports.

The existing Kween sightline maps contain zero obstruction positives. They
cannot establish sensitivity even if both processors agree everywhere. Before
any release gate, freeze additional acquisition/location cases with challenging
terrain, report all planned cases including missing data, and audit DEM and
processor differences. Do not tune thresholds on this comparison and call the
same cases independent validation.

Synthetic tests exercise metric arithmetic, absent support, unknown/guard
exclusion, invalid masks, exact scene identity, changed requests and shifted
georeferenced rasters. They do not establish live API compatibility or provider
agreement. Optical evidence remains stale; independent field outcomes, confirmed
crop calendars and real field boundaries remain outstanding. No imagery-only
cause diagnosis, irrigation prescription or trained-model accuracy is reported.
