# Kween acquisition-specific local viewing geometry

Independent Vantage research within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda remains the priority; Texas is deferred and forestry stays with Vepris.
No CropSight code or validation is inherited.

This increment moves beyond the [direction-independent slope proxy](KWEEN_TERRAIN.md)
to annotation-derived viewing directions and local surface-facet checks. It is
an approximate geometry research slice, **not a complete layover/shadow solution,
validated geocoder or illumination certificate**. It does not alter provider RTC
values, refresh optical evidence, diagnose crop condition or enter scouting rankings.

## Verified source annotations

The source GRD items are resolved through the original RTC `derived_from` links.
In these three items, the catalog asset named `schema-product-vv` points into
**`annotation/rfi/`**, rather than to the manifest-identified product annotation.
The resolver follows the SAFE manifest's `s1Level1ProductSchema` references instead.
Original SAFE filenames return 404 under the host's normalized storage layout;
the single measurement-stem mapping is accepted **only when the product XML byte
size and MD5 match the original SAFE manifest**. SHA256 hashes pin all archived
items, SAFE manifests and annotation files. No guessed geometry or RFI-derived
angles are substituted. This is a finding for these archived items, not a claim
that every catalog product has the same issue.

Each verified VV annotation supplies **210 geolocation points and 16 Earth-fixed
orbital position/velocity states**. Check mission, IW/GRD mode, polarization,
absolute orbit and acquisition interval before using it. VV annotation geometry
is used as an approximation for the paired VV/VH observations; independent
polarization-specific geometry differences have not been evaluated.

The [Sentinel-1 geocoding guide](https://sentinels.copernicus.eu/documents/247904/1653442/Guide-to-Sentinel-1-Geocoding.pdf)
describes Earth-fixed coordinates, product orbit states and full Range-Doppler
geocoding. [Copernicus processing documentation](https://sentiwiki.copernicus.eu/web/s1-processing)
also describes state-vector interpolation and geolocation. The implementation
below is our explicitly approximate method; those documents do not validate it.

## Fixed method

The [frozen plan](../../configs/kween_2023_viewing.json) pins the original radar
and terrain runs. This is an exploratory follow-up, not a blinded test or
independent event-validation cohort.

1. Interpolate annotated Earth-fixed orbit positions with cubic Hermite splines
   using their velocities. Reject extrapolation beyond the state-vector interval.
2. Convert annotated geographic coordinates/heights using WGS84 and construct
   normalized ground-to-sensor vectors at the geolocation points. Compare their
   nominal incidence to the annotated angles; reject disagreement above the
   fixed 0.25° engineering guard.
3. Linearly interpolate the Earth-fixed viewing vectors inside the annotation
   grid's convex hull, then normalize them. Outside support stays unknown.
4. Use supported derivatives of the pinned 30m DSM to construct approximate
   surface normals. Transform physical grid-axis directions into Earth-fixed
   coordinates, accounting for grid orientation, row direction and metric scale.
   Orthometric DSM gradients are not claimed to be exact ellipsoidal gradients.
5. Compute the angle between the approximate surface normal and viewing vector.
   Flag local range-order reversal from the sensor-facing range gradient, a
   back-facing facet where the normal points away from the sensor, and the fixed
   local-incidence guard outside 5–85°. These guards are not calibrated crop rules.
6. Transfer native geometry/classes to the original radar grid with nearest
   neighbor and recompute numerical comparisons using locally unflagged support.
   Preserve the original historical-cropland denominator and 60%/100-pixel gates.

Class codes are **0 unknown, 1 locally unflagged, 2 local range-reversal risk,
3 back-facing facet risk, 4 near-normal/grazing incidence guard**. Class 1 does
not mean terrain-correct, shadow-free or agriculturally eligible. A range reversal
can occur even when the computed local-incidence angle is acute; the implementation
tests that predicate separately rather than relying only on an angle threshold.

## Actual findings

Run `43d8ea585a445e8c941e5788` generated **12 geometry COGs and two filtered-change
COGs**. The orbit-derived angles agree with the annotated incidence values within
approximately **0.0032°** at the annotation points. That is an internal consistency
check using related source metadata, **not measured real-world angular accuracy**.
It does not quantify interpolation error between points or validate DSM normals.

| Acquisition | Nominal incidence over historical cropland | Approximate local incidence | Crop cells locally unflagged |
|---|---:|---:|---:|
| May 12 | 33.61–34.45° | 18.75–49.32° | 100% |
| May 24 | 33.60–34.44° | 18.74–49.32° | 100% |
| June 5 | 33.60–34.45° | 18.74–49.32° | 100% |

Local risk flags occur on surrounding slopes, outside the historical crop mask.
None of the original **105,091 historical-cropland analysis cells** are flagged
or unsupported by these local predicates in this box. They remain correlated
measurements with unconfirmed current crop identity, not healthy-field labels.

Consequently, these local filters leave the original cropland numerical changes
unchanged: June 5 minus May 24 has median VV change **-1.628 dB** and VH change
**-1.110 dB**. This neither validates crop stress nor establishes that terrain
effects are absent. The earlier 10° slope proxy and these local geometric
predicates measure different things; neither is selected based on its retention.

## Reproduce and verify

Use the existing geographic dependencies and optional reporting dependencies.
The pinned RTC catalog, numerical radar and terrain archives must exist locally.
Large artifacts are excluded from Git; compact summaries alone cannot recover an
exact frozen run on a fresh checkout. The first command can download the required
source metadata after the pinned catalog is available; geometry processing uses
the cached annotations and parent numerical rasters.

```powershell
python scripts/acquire_viewing_annotations.py --allow-downloads
python scripts/build_viewing_geometry.py --write-summary
python scripts/verify_viewing_geometry.py
python scripts/plot_viewing_geometry.py
# Cached replay: neither command permits downloads.
python scripts/acquire_viewing_annotations.py
python scripts/build_viewing_geometry.py
python -m unittest discover -s tests -v
```

The [executed run record](KWEEN_VIEWING_RUN.json) is tracked. Raw annotations,
manifests, inputs and rasters remain under `outputs/africa/viewing/`. The visually
inspected figure is `outputs/africa/viewing/kween-viewing.png`. No live service or
new dashboard panel is added by this numerical slice.

Verification checks source metadata hashes, SAFE product references, product
byte sizes/MD5, parent grids/radar inputs and the frozen choices. It reconstructs
the viewing vectors, normals, angles, classes, counts and numerical comparisons,
then verifies all **14 COG arrays**, layouts and band/grid contracts. Cached replay
preserved both input bytes and the final manifest, whose SHA256 is
`3bb1780f1c409afe78dd469f72f6b5792efce8c77457d9762309e05ca3a072aa`.

The **112-test regression suite passed**, including WGS84 reference coordinates,
velocity-aware interpolation, prohibited orbital/spatial extrapolation, rotated
grid bases, row direction, unit-vector contracts, unknown support, synthetic
range reversal/back-facing cases, product identity/frame checks and manifest
reference selection. Increment lint checks passed. No model is trained and no
new agricultural accuracy claim is reported.

## Remaining gate

Keep `local_geometry_checks_applied=true`, `nonlocal_shadow_checked=false`,
`terrain_screen_verified=false`, `radar_illumination_confirmed=false` and
`agronomic_review_eligible=false`. Optical evidence remains stale.

A locally visible facet can still be occluded by **distant terrain**, and local
range reversal is not a complete accounting of overlapping radar returns.
This slice does not ray-trace surrounding terrain, solve full Range-Doppler
geometry, reconcile all height-datum/processor differences or compare its masks
against an independent trusted processor. The next step requires adequate
surrounding terrain and bounded line-of-sight tests with explicit unknown support,
followed by processor comparison. Confirmed field/crop calendars, independent
dated outcomes and held-out regions/seasons remain necessary before radar can be
evaluated for scouting priorities. No irrigation or cause diagnosis follows from
these imagery measurements.
