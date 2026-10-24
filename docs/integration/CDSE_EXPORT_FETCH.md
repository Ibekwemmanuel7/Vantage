# Local authenticated export fetch workflow

24 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

Implemented: credential-free dry run, fixed OAuth/provider endpoints, two exact
prepared requests, bounded response handling and verified local export storage.
Actual execution in this task was **dry run only**: two pending requests, no
credentials read, zero provider processing requests and zero independent
acquisitions evaluated. Live service compatibility remains untested.

## Run locally

```powershell
python scripts/fetch_lira_exports.py
$env:VANTAGE_CDSE_CLIENT_ID = "your-registered-oauth-client-id"
python scripts/fetch_lira_exports.py --execute
python scripts/prepare_lira_radar_comparison.py --exports outputs/private-lira-provider-exports
```

Create an OAuth client in the user's CDSE account following
[official authentication instructions](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html).
The secret is prompted through Python `getpass`, not accepted as a command-line
argument, read from other applications, searched in files or saved by this tool.
Do not paste secrets into chat or commit them. Use a terminal that supports hidden
input. Client credentials and bearer token remain in process memory only.

`--execute` can consume the account's processing quota. It submits at most the
two pending fixed requests, reusing one token. Authentication/process requests
disable redirects and have bounded timeouts. Processing POSTs are not retried
automatically, avoiding duplicate submissions after ambiguous failures. A timeout
does not prove processing did not occur; check provider usage before retrying.

The official [Sentinel-1 example](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process/Examples/S1GRD.html)
uses TAR responses for multiple outputs. This client accepts only uncompressed
TAR containing exactly regular files `default.tif` and `userdata.json`, with a
32 MiB response budget. Unknown paths, duplicates, links, extra files and missing
outputs are rejected; archive files are read as bytes rather than extracted.
Alternative content types/container layouts are not silently adapted.

## Integrity and partial failures

Prepared request hashes and regeneration by the exact-scene builder are checked
before authentication. Each staging directory must pass the existing strict
export reader: exact request, singleton SAFE inventory, service version,
three-band grid and consistent masks. Only then is it renamed to its final
`outputs/private-lira-provider-exports/0/` or `1/` folder. Receipts contain output
hashes and verification time, never credentials or HTTP response headers.

Existing final export folders must validate and are skipped without a processing
request. Incomplete/invalid folders fail rather than being overwritten. If the
second acquisition fails, a completed first export remains available for reuse.
Temporary staging cleanup is confined to the newly created local staging tree.
Raw provider error bodies, bearer tokens and exception messages are not printed.
The CLI records failure type; library HTTP errors contain status codes only.

Generated exports stay beneath the ignored `outputs/` directory. Authenticated
source access and a valid scene/grid response do not establish agricultural
accuracy or independent terrain truth. The comparison uses the same DEM family
and reports descriptive processor differences; no automatic promotion follows.

## Remaining dependencies

A registered OAuth client, user-supplied local secret, provider quota and actual
service-compatible outputs are still required. No real export, processor
agreement or radar-assisted model is claimed by mock tests or dry-run success.
Compatible training radar inputs, independent outcomes/calendars and untouched
evaluation remain missing; no optical values are filled or irrigation prescribed.

Verification: 100 focused tests passed. New mock tests cover OAuth redirect
rejection, sanitized errors, single-attempt processing, accepted TAR outputs and
rejection of path traversal, duplicates and incomplete archives. Existing raster
fixtures test exact scene/grid/mask ingestion. These are software checks, not
evidence that the real provider accepted a request.
