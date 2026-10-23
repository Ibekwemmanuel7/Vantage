# Sentinel-1 availability at optical gaps

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/inventory_gap_radar.py --sequence outputs/africa/recent/c990c8c23060aea1302a/pixels/sequence-observations.json outputs/africa/recent/954abd0883653516f0d5/pixels/sequence-observations.json outputs/africa/recent/ef95be98f85b606e9313/pixels/sequence-observations.json outputs/africa/recent/e285b40bbdfb86b1cc40/pixels/sequence-observations.json --online
```

Omit `--online` to replay archived searches. Queries are limited to five
single-location sequence windows, at most 62 days and 100 catalog items per
window. Pagination is rejected; failed searches are not empty-coverage results.
Optical inventory hashes are verified. Source sequence, catalog and code hashes
are retained in ignored `outputs/africa/gap-radar/<plan-id>/report.json` artifacts.
Public-facing candidate summaries omit asset URLs.

Source: [Planetary Computer STAC](https://planetarycomputer.microsoft.com/api/stac/v1),
`sentinel-1-rtc`. This run downloads metadata only, without tokens or radar
rasters. Collection terms and raster access still need review before processing.

The existing radar metadata contract requires actual footprint containment,
IW VV/VH assets and complete platform/orbit identities. Duplicate slices from
one platform/pass are removed; tracks remain separate. Queries begin seven days
before the first optical acquisition and end at the last optical timestamp.
Matches must precede or equal the optical timestamp and be at most seven days old.

Both clear optical dates (potential future training pairs) and coverage-gap dates
are matched. A coverage-gap date means whole-box coverage below the research
threshold, not missing pixel counts or simulated gap targets. Per-track matches
are combined as unique optical dates, not summed as independent successes.

## Actual results

| Window | Eligible radar passes | Optical dates matched / total | Coverage-gap dates matched / total |
| --- | ---: | --- | --- |
| Iganga May 2023 | 2 | 2 / 5 | 0 / 3 |
| Iganga June 2023 | 3 | 4 / 6 | 2 / 3 |
| Lira May 2024 | 4 | 5 / 6 | 3 / 4 |
| Lira June 2024 | 5 | 6 / 6 | 5 / 5 |

Iganga uses Sentinel-1A ascending relative orbit 028. Lira includes ascending
029 and descending 123; their combined time coverage is not one comparable
backscatter series. Lira's 8/9 matched coverage-gap dates make it a useful next
pixel-quality study. Search intervals overlap, so summed window pass counts
are not necessarily unique passes. Offline replay reproduced the counts.

Every match retains `measured_radar_coverage=null` and
`usable_radar_evidence=false`. Geometric/time matches do not establish usable
VV/VH values, radiometric units, noise quality, terrain illumination or historical
delivery availability. No radar pixels were processed for these new cohorts;
Kween radar work does not transfer validation. Kasese 2026 is not queried here.

Next: bounded VV/VH extraction on exact optical grids for a fixed Lira track,
source metadata/units/nodata checks, repeat-pass consistency and independent
terrain screening. Only then construct compatible radar-assisted samples.
No measured NDVI beneath clouds, crop diagnosis, soil-moisture retrieval, yield
prediction or irrigation prescription is provided. Confirmed crop calendars
and independent field outcomes remain absent. Forestry stays with Vepris.
