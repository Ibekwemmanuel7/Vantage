# Historical cropland context and coverage desk

20 October 2026. Active Uganda research within
[Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US); no inherited CropSight
validation. Forestry remains with Vepris. No partner approval is implied.

## Implemented

The six-band archive now contains all 18 frozen acquisitions across three study
boxes and May/November 2022–2024. Earlier access failures were recovered with
short-lived container tokens, cached in memory with expiry checks and bounded
network retries. All physical input recipes remain versioned. The original
partial dataset remains recoverable rather than being silently modified.

The historical-context adapter archives the public WorldCover catalog search,
selects the 2021 v200 map covering each box, and samples categorical classes by
nearest neighbour onto the exact spectral grid. A two-band COG records class-40
historical cropland and known land-cover classification separately. Unknown
classes are not assumed to be confirmed non-cropland. This nearest-neighbour
classification is not subpixel cropland fraction or a precise area estimate.

For each dated acquisition, intersect six-band common validity with the
historical crop mask. Report whole-box coverage, historical-crop denominator,
valid historical-crop count and coverage separately. Produce numerical
reflectance/NDVI-B8A/NDMI summaries only when at least 100 pixels and 60%
historical-crop coverage pass. These thresholds are uncalibrated development
rules. Withhold summaries below the threshold rather than interpreting a tiny
clear subset as representative crop conditions.

Every record remains `current_crop_confirmed=false`,
`crop_stage_confirmed=false` and `agronomic_review_eligible=false`. Coverage
sufficient for research does not make a record actionable agricultural advice.
The historical map does not establish present cultivation, maize location,
planting date or field boundaries. The 2021 map's publication/retrieval dates
also prevent calling this a contemporary 2022 early-warning replay.

## Run and replay

```powershell
python scripts/prepare_multispectral.py --allow-downloads
python scripts/build_crop_context.py --allow-downloads
# Cached operation, no network:
python scripts/prepare_multispectral.py
python scripts/build_crop_context.py
```

Context files are under `outputs/africa/crop-context/`, with input hashes,
source links, masks and a versioned result. The public research-only report is
`web/data/research-readiness.json`; it contains no field outcomes, credentials
or signed URLs. The [compact run record](CROP_CONTEXT_RUN.json) records actual
coverage and replay checks. No new model or performance score is published.

WorldCover attribution: © ESA WorldCover project 2021 / Contains modified
Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.
WorldCover 2021 v200: [Zanaga et al., 2022](https://doi.org/10.5281/zenodo.7254221),
CC BY 4.0. [Official access and usage documentation](https://esa-worldcover.org/en/data-access).

## Browser desk

Start the loopback server, refresh the Uganda profile and scroll to **Where the
research evidence is usable**. Select a study box to inspect dates and coverage.
The existing weekly brief is still the separate Iganga May 2024 reconstruction;
this newer archive does not silently rerank its worklist. Texas hides this
Uganda research panel. JSON download preserves the explicit limitations.

Desktop and 390px mobile checks covered all three study-box selections, visible
unavailable summaries, profile separation, no document horizontal overflow and
no console errors. The coverage table itself scrolls horizontally on small
screens. These are focused checks, not a complete accessibility/browser audit.
An isolated missing-JSON fixture also verified the unavailable message, hidden
stale-data body and working retry state. Its expected HTTP 404 is separate from
the normal desk's error-free console check.
Screenshots: `outputs/africa/research-desktop.png` and `research-mobile.png`.
The temporary QA server used port 8937; the user's port 8917 was not stopped.

## Remaining dependencies

Confirmed current crop/field references, planting calendars, a denser seasonal
series, contemporaneous archived independent field outcomes and future
prospective visits remain needed. HLS-compatible inputs and a pinned licensed
model adapter are still required for a fair Prithvi benchmark. Do not use
historical land cover or an imagery anomaly as an independent damage label.
