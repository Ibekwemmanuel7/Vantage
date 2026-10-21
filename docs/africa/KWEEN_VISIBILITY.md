# Kween: bounded terrain sightlines

Vantage agriculture research within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda is active; Texas is deferred. Forestry remains with Vepris.

Implemented: acquisition-specific sampled terrain sightlines for the pinned
[local viewing geometry](KWEEN_VIEWING.md) cohort, not a validated SAR shadow processor.
This is a local CLI research artifact, not a new dashboard panel or operational
scouting release. No CropSight code or validation is inherited.

The policy in `configs/kween_2023_visibility.json` was frozen before inspecting
the expanded elevation window. This retrospective extension is exploratory;
the parent case and its local terrain results were already known.

## Method and outputs

The existing Copernicus GLO-30 source tile is read across a larger window and
reprojected to a 30 m UTM 36N grid with 5,070 m extra padding on each side.
Missing native elevations or incomplete interpolation support stay missing.
The target remains the parent 384 × 381 grid, preserving comparisons.
Source tile identity, raw clip checksum, catalog checksum, parent manifest,
code hashes and software versions are recorded in the run manifest.

Each verified Sentinel-1 VV annotation supplies an interpolated Earth-fixed
ground-to-sensor direction. Projected grid-axis orientation and physical scale
convert that direction to horizontal travel and vertical rise. A bilinear DSM
surface is sampled toward the sensor at 15 m intervals, with an explicit final
5,000 m sample: 334 samples per origin. The flat tangent relative-height ray is
compared with the DSM; the minimum sampled clearance and its distance are saved.

Classes are unknown, clear within the tested distance, obstruction risk and
clearance guard. A clearance below −5 m flags an obstruction risk. Complete
support and minimum clearance above +5 m are required to pass. Complete support
within the ±5 m guard is ambiguous. Any missing sample otherwise prevents a pass;
an observed obstruction remains flagged even if other samples are missing.
The 5 m guard is an engineering policy, not measured DSM accuracy.

Ten COGs are produced: one expanded DSM and, per acquisition, native metrics,
native classes and classes mapped to the parent 20 m radar grid. The mapping
uses nearest neighbor, not additional physical resolution. The historical
WorldCover crop mask is a denominator, not verified field geometry.

## Observed result

Run `05151b97dd8fef9ee29b5670` checked 12 May, 24 May and 5 June 2023.
For each pass all 146,304 native origins passed the bounded sampled test.
All 105,091 historical cropland pixels mapped to that passing class;
none mapped to unknown, obstruction risk or the clearance guard.
Zero detections here do not establish detector sensitivity. Synthetic ridge,
missing-height, boundary, direction and near-touch tests exercise those branches.
The machine-readable record is [KWEEN_VISIBILITY_RUN.json](KWEEN_VISIBILITY_RUN.json).

The optical status remains `stale_research_context`. Confirmed radar
illumination, verified complete terrain screening and agronomic eligibility
remain false. There are zero independent field labels and no newly trained model.
This slice does not change radar intensity, impute optical observations, infer
crop damage or diagnose a cause. It does not prescribe irrigation.

## Reproduction and validation

With the preceding pinned viewing and terrain artifacts present and the geo
dependencies installed:

```powershell
python scripts/build_visibility.py --allow-downloads --write-summary
python scripts/verify_visibility.py
python scripts/plot_visibility.py
python -m unittest discover -s tests -q
```

Downloading is explicit. Cached runs need no network. The verifier checks frozen
policy and science-code hashes, raw clip and COG checksums, and exactly replays
all ten COG arrays, grid contracts and manifest identity offline. Generated
rasters, XML, caches and figures stay outside Git; a fresh clone still needs
the preceding local artifacts. Compact committed summaries alone cannot recreate
their original acquisition timestamps or byte-identical manifests.

## Remaining limits and next evaluation

Sampling excludes the first 15 m and everything beyond 5 km. A bilinear 30 m
surface and finite sampling can miss narrow or subcell ridges. This approximation
omits Earth curvature, atmospheric refraction and spatial geoid variation; it
uses a surface model rather than confirmed bare-earth terrain. These omissions
and a policy guard do not provide calibrated error bounds. It does not solve
nonlocal layover or full Range-Doppler geometry. Local facet checks remain
separate and must not be replaced by this result.

Next compare difficult terrain cases against an independent processor's shadow
and local-incidence products, with aligned DEM, acquisition, grid and nodata
policies, before deciding whether a terrain gate is operationally justified.
For example, the primary [Copernicus Sentinel-1 GRD documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html)
describes separate local incidence and shadow-mask outputs; no agreement with
those products has been measured here. Do not treat this test as equivalent.
Agricultural validation still needs broader seasonal/location cohorts,
confirmed crop calendars, field boundaries and independent dated outcomes.
Public reports remain event leads, not automatically field labels.
