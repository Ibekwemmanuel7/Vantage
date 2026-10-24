# Lira independent comparison contract and causal radar pairing

24 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/prepare_lira_radar_comparison.py
python scripts/prepare_lira_radar_comparison.py --exports outputs/private-lira-provider-exports
```

The first prepares exact requests and the research pairing table locally. The
second ingests independently obtained exports; it does not send requests, obtain
credentials or invoke a paid/provider service. No credentials or export directory
was supplied in the actual run, so zero acquisitions were independently compared.

Actual output directory:
`outputs/africa/lira-comparison/0dbeacd5e45ecbf430b7/` contains `0-request.json`,
`1-request.json` and `report.json`. Source visibility/viewing/radar/optical report
hashes, array hashes and grids are checked. Derived outputs remain ignored.

## Provider contract

Requests reuse the strict comparison builder for the two exact SAFE products:

- `S1A_IW_GRDH_1SDV_20240604T160548_20240604T160613_054176_0696A8_C7B8`
- `S1A_IW_GRDH_1SDV_20240616T160548_20240616T160613_054351_069CB6_1E1B`

The intended endpoint is `https://sh.dataspace.copernicus.eu/process/v1`.
Requests use orthorectification, terrain gamma0, COPERNICUS_30 and the exact
parent grid. Output bands are local incidence angle, provider shadowMask and
dataMask. Actual service execution/compatibility is not tested by preparation.
The provider documents these bands and their processing requirements in
[Sentinel-1 GRD documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html).
Authenticated service access is described in
[Copernicus authentication documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html).

For each `0/` and `1/` private export subdirectory, supply the exact submitted
request as `request.json`, output `default.tif` and actual provider `userdata.json`.
The reader rejects changed requests, different grids, mixed/wrong SAFE scene
inventories, absent service version and inconsistent masks. Exports are not
silently reprojected. A rerun cannot replace a report with fewer evaluated exports.

Comparison is descriptive incidence difference and directional shadow
co-occurrence. Provider shadowMask means in/near radar shadow under its scattering
area rule; it is not equivalent to Vantage's finite sampled obstruction class.
This Lira cohort has no obstruction-positive sightlines, so it cannot establish
sensitivity to actual shadow. A comparison does not automatically certify
illumination or agricultural accuracy.
Both workflows use the Copernicus DEM family, so this is a processor comparison,
not independent terrain ground truth or independent field validation.

## Actual causal research pairs

Only the processed ascending relative-orbit-029 passes are eligible; descending
catalog matches are excluded. Radar must precede/equal the exact optical time and
be no more than seven days old. Scene delivery availability remains unknown.

| Optical date | Prior radar date | Lag, days | Clear optical targets inside radar research screen | Missing optical pixels inside screen |
| --- | --- | ---: | ---: | ---: |
| 7 June 2024 | 4 June | 2.66 | 140,824 | 166,626 |
| 17 June 2024 | 16 June | 0.66 | 211,024 | 96,426 |
| 22 June 2024 | 16 June | 5.66 | 292,532 | 14,918 |

The research screen intersects numerical radar support, locally unflagged
facets and bounded-clear sightlines: 307,450 whole-box pixels for each paired
date. It does not apply the separate 10-degree slope proxy. Clear targets are
potential supervised reconstruction references; missing pixels have no optical
ground truth and must not become labels. These are correlated pixel-date counts,
not independent farms or achieved reconstruction coverage.

2 June has no earlier processed radar pass. 12 June's nearest is 7.66 days old
and 27 June's is 10.66 days old; both are withheld. The earlier 8/9 Lira catalog
coverage-gap result combined two orbit directions and two windows; it must not be
confused with the stricter two-pass fixed-track sample's three matched dates.

All pairs retain `usable_for_agricultural_model=false`. Independent geometry
exports, radiometric/processor suitability, a compatible training radar cohort,
uncertainty evaluation, confirmed crop calendars and independent field outcomes
remain dependencies. No optical values are filled, radar-assisted model trained,
crop cause diagnosed or irrigation prescribed. Forestry remains with Vepris.

Verification: 97 focused tests passed, including exact export scene/grid/mask
fixtures, future-radar rejection, expired-pair withholding and prior geometry,
terrain, raster and cloud-gap regression checks. Prepared provider requests were
not submitted during these tests; synthetic export fixtures are software tests.
