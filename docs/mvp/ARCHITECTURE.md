# MVP architecture and data contract

Status: local executable prototype, 17 October 2026. Independent implementation;
no CropSight code or inherited validation. Portfolio: [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Forestry remains with Vepris. The user is an independent consultant serving
confirmed centre-pivot upland cotton in Hale and Floyd counties, Texas.
The sole supported decision is where to inspect first among fields due for scouting.

This document records the original Texas slice. The separate Uganda public-data
[imagery/ML workbench](../ml/README.md) now implements retrospective raster
processing and an exploratory fitted model; its results do not validate Texas.

## Executable slice

JSON input → validation → as-of evidence selection → quality/freshness gates →
same-field change comparison → ranked zone JSON + GeoJSON + responsive HTML →
dated inspection feedback in SQLite with an immutable copy of the brief.
Python standard library only; no remote service, account or image download.
Run one private local workspace per consultant. Tenant IDs prevent accidental
feedback linkage across briefs; they are not authentication or multi-tenant isolation.
Do not host these files publicly or load customer data into this demo without
access, consent, retention and backup arrangements.

## Version 1 import model

See `examples/synthetic.json` for a complete executable contract. Required keys
are validated at the processing boundary; missing required keys fail the CLI.

| Entity | Identity and required evidence |
|---|---|
| Dataset | schema_version `1`, tenant_id; one tenant per input |
| Field | unique id, boundary_version, consent_ref, WGS84 geometry, county/state, crop, irrigation, records_confirmed, planting_at, stage_eligible, due_for_scouting, management_context |
| Zone | unique id, field_id, WGS84 geometry contained by field |
| Observation | unique id, zone_id, boundary_version, acquired_at, processed_at, source_id, NDVI [-1,1], usable_fraction [0,1]; quality_method should document masking |
| Brief | schema/code version, tenant, as-of and processing time, frozen policy, ordered zone evidence, paired observations, scores, states and limitations |
| Feedback | local ID, tenant/zone, visited_at, useful_finding/no_finding/uncertain, finding, action, complete brief snapshot |

All timestamps require explicit timezone. Acquisition and processing must both
precede the decision cutoff; same-day duplicate acquisitions cannot create a
temporal pair. Boundary-version mismatch fails rather than silently mixing zones.
Coordinates use longitude/latitude. This first importer deliberately accepts only
simple axis-aligned rectangles without holes and checks containment. It does not
claim real-field polygon topology, county spatial validation, zone disjointness,
complete field coverage, or equal zone areas. Declared county and eligibility
require adviser confirmation. Real polygons need a GIS adapter and spatial QA.

## Evidence rule

Select latest observation with at least 80% usable zone coverage, falling back to
an older usable observation when a newer acquisition is cloudy. Age is measured
from acquisition, not processing: at most five elapsed days. Historical evidence
is retained when stale. Prior observation must be earlier and within 30 days.
Require three zones with the exact same acquisition pair in the same field.
Score = max(0, median zone NDVI change − zone NDVI change). A score of at least
0.10 marks `inspect`; otherwise `no_relative_flag`. Field visit order follows its
highest-scoring zone, with deterministic field/zone tie breaks. The full list is
shown so the consultant can apply visit capacity and existing plans.

These are development settings, not calibrated agronomic thresholds or
probabilities. Scores use NDVI units. Zone medians are unweighted; small zones,
edges and management differences can bias comparisons. A common field-wide
decline can be missed. No flag is not a healthy assessment. Missing, low-quality,
stale, insufficient-history and ineligible states never become satellite priorities.
The HTML map shows evidence states and full dated values, sources and management
context. It is schematic, not a navigation map. No persistence detector, crop-stage
normalization, weather interpretation or cause diagnosis is implemented.

## Practical production path

1. Recruit partner and establish consent, field/season IDs, planting and irrigation
   records, dated stage windows, scouting cadence and useful delivery cutoff.
2. Add topology-aware arbitrary Polygon/MultiPolygon import, overlap/edge checks,
   projected areas and boundary revisions; persist fields/seasons in a relational
   store with tenant authorization. Freeze zone versions before evaluation.
3. Add a licensed Sentinel-2 L2A adapter: record item/band/mask identifiers,
   resolution, cloud/shadow mask and buffer settings, NDVI aggregation method,
   usable pixel count/area and immutable raster checksums. Store rasters privately
   outside Git. Validate masks and georegistration against independent checks.
4. Add raster before/after views and trajectories, dated management/weather context,
   adviser review and mobile feedback entry. Keep inference and human conclusions
   separate. Add route/capacity selection without suppressing unavailable fields.
5. Add durable brief IDs, source/config revisions, migrations, audit and export,
   authenticated roles, backups and retention. Only then consider shared hosting.

In this original Texas engine, no live satellite, weather, soil, equipment or grower feed is connected. No model
has been trained, no real customer or Southern US performance established, and no
irrigation, yield, disease or water-saving claim is supported. This does not install
a runtime dependency into Lillie US; upstream pin changes follow a published,
reviewed product revision.
