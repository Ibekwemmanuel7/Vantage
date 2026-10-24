# Provisional spatial joins to regional calendars

Vantage now links polygon study areas or declared private fields to a pinned
Uganda ASAP monitoring-zone snapshot. It exposes regional crop-season context
without confirming crop identity, farmer consent or field planting dates.

## Source investigation and compatibility

The [ASAP download documentation](https://agricultural-production-hotspots.ec.europa.eu/download.php)
describes adapted/simplified monitoring geometries, a public WFS endpoint and
ID-based joins. It explicitly cautions that these geometries are for broad-scale
visualization and may not preserve original topology. They are not surveyed
farm boundaries. The current system's units have also evolved; matching an ID
does not prove its geometry stayed unchanged historically.

A bounded download attempt stopped at its 80 MB limit. A subsequent HEAD request
showed the global `gaul1_asap_v06.zip` archive is 259,139,373 bytes; the full
archive was not obtained. We instead inspected WFS capabilities and feature
schema, then requested only `public:warning_crop` geometries for `asap0_id=209`
in EPSG:4326. The complete response contains **13 Uganda monitoring zones** and
is **37,907 bytes**, archived locally at:

`outputs/research/2026-10-24/uganda-wfs-zones.geojson`

Its SHA-256 is
`2583008495f10162ae9c5be5e03faf128e25d731dc1c0b761c8776da764347cd`.
The exact request and expected count are pinned in
`configs/uganda_regional_zones.json`. The inspected response has valid polygon
geometries and includes all nine zone IDs used by our pinned calendar archive.
The extra zones need not have crop calendars. This establishes ID coverage for
this pair of snapshots, not complete historical version equivalence or legal
administrative membership.

Provider warning values are discarded. They are not imported as Vantage alerts,
independent findings, model outcomes or diagnoses. Provider attribution and
underlying rights must be preserved; a public endpoint does not replace rights
review for any intended redistribution.

## Actual study-box results

The completed cached replay is:

`outputs/private/uganda-study-regional-context-v2.json`

| Existing research unit | Matched source zone | Source ID |
| --- | --- | --- |
| Iganga study box | South Eastern | 9988 |
| Lira study box | Mid Northen | 9985 |
| Kasese study box | W. Highlands | 9981 |

Labels are preserved as published, including abbreviations/spelling. The three
units remain analyst study boxes, not registered farms. No farmer calendar was
confirmed and no dashboard recommendation was enabled.

## Replay and private fields

Dependencies are in `requirements-field.txt`. The join is offline and requires
the cached sources. On another computer obtain the pinned WFS response and
calendar archive from their configuration URLs, then verify hashes; a current
WFS response can change, so it may require a separately reviewed source version.
Never disable the source checks to make a changed response pass.

```powershell
python scripts/join_regional_context.py --zones outputs/research/2026-10-24/uganda-wfs-zones.geojson --calendar-archive outputs/research/2026-10-24/jrc_calendars.source --study-config configs/uganda_archive.json --year 2024 --out outputs/private/uganda-study-regional-context-replay.json
```

For declared fields, replace `--study-config ...` with
`--fields outputs/private/fields.geojson`, following the
[field-boundary contract](FIELD_PIXELS.md). The CLI requires exactly one mode.
Field declarations and referenced consent still require independent review.
No private field file was supplied in this increment.

The output must resolve beneath ignored `outputs/private`. Existing reports are
never overwritten. Source files, configuration, unit file and implementation
hashes are retained. Default source configurations are pinned; alternate reviewed
versions can be supplied with `--source-config` and `--calendar-config`.

## Join rules

1. Require a complete WFS response with explicit WGS84 CRS and Uganda IDs;
   reject truncated responses or unexpected countries.
2. Require valid Polygon/MultiPolygon geometry, unique source zone IDs and
   coverage of every source calendar zone ID. No silent geometry repair.
3. Require the **whole unit polygon** to fit inside exactly one source zone.
   Do not assign from a centroid, nearest zone or majority area.
4. Withhold conflicting overlaps, cross-zone units, uncovered areas and unknown
   projected geometry/distance.
5. Apply a **1,000 m border guard** using projected metre distances. Near-border
   units remain unresolved. This engineering guard is not a measured positional
   accuracy bound; even interior assignments remain provisional.
6. Attach only calendar rows with the matched source ID. A zone without calendar
   rows stays explicitly without calendar context. No neighboring crop/season
   is substituted.

The year argument instantiates recurring windows using the existing regional
calendar rules. It does not prove actual sowing/harvesting in that year. All
available regional crop/season labels are retained; the join does not identify
which crop a field actually contains or choose its season. A field still needs
its own confirmed crop/calendar evidence.

## Status and remaining work

This closes the basic source-ID/spatial-context link for the three research
boxes, with conservative software checks. It does not certify the spatial
accuracy of the source or enable a farmer service. Dashboard presentation,
reviewed field records, positional uncertainty evaluation and independent
agricultural outcomes remain pending. No model, irrigation prescription,
imagery-only cause diagnosis or CropSight validation is added. Forestry remains
with Vepris; Uganda remains a pilot within Vantage.

Verification on 24 October 2026: **26 tests passed** across zone joins, regional
calendars, seasonal contracts and field pixels. Synthetic checks cover interior,
near-border, cross-zone, overlapping, missing-calendar and incompatible-source
cases, WFS completeness/country/CRS checks, warning-value exclusion, private
output and overwrite refusal. The pinned real sources replayed successfully
for all three study boxes. `git diff --check` passed. No private farm record,
new model or agricultural accuracy result was produced.
