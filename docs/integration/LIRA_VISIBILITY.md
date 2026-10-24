# Lira bounded nonlocal terrain visibility

24 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/check_lira_visibility.py --online
python scripts/check_lira_visibility.py
```

The first permits a bounded expanded read of the same independent Copernicus
DSM source. The second replays the cached elevation and verified annotation
inputs without requesting tokens. On the actual acquisition run, a public token
request first failed with HTTP 504; a retry succeeded. Failure supplied no clear
visibility result. The CLI reports only exception type to avoid exposing signed
provider URLs. Offline replay reproduced derived arrays.

## Fixed method

`configs/lira_gap_visibility.json` fixes a 5,000 m search, 15 m sampling, 5 m
engineering clearance guard and 169-cell padding on the 30 m derivative grid,
for the two existing Lira passes. The padded grid adds 5,070 m on each side.
Source report/code/annotation identities and exact target CRS/transform/shape
are checked before results are combined. Source and derived artifact hashes
remain in the report. No radar values or outcomes select the policy.

The existing tested sightline algorithm samples bilinear DSM heights toward the
sensor along acquisition-specific directions, using projected metric basis
orientation and relative-height flat-tangent rays. Every required sample must
have supported elevation to pass. An observed obstruction takes precedence over
missing farther-away heights. Classes remain unknown, clear within tested
distance, obstruction risk and clearance guard. Neither missing heights nor
failed source reads can become clear terrain. No interpolation across missing
elevation support is allowed.

The finite search begins at 15 m, includes 5 km, and uses 334 samples per ray.
It omits curvature, refraction, geoid variation, subcell terrain and anything
beyond the fixed horizon. The 5 m guard is not calibrated DSM uncertainty.
Elevation remains a surface model rather than independently surveyed bare earth.

## Actual results

| Whole-box visibility class | 4 June 2024 | 16 June 2024 |
| --- | ---: | ---: |
| Unknown | 0 | 0 |
| Clear within sampled 5 km | 307,468 | 307,468 |
| Obstruction risk | 0 | 0 |
| Clearance guard | 0 | 0 |

Intersecting bounded-clear pixels with the previous local geometry classes
leaves 307,450 locally unflagged pixels per pass. The 18 prior local risk flags
remain excluded from that intersection. This is not an intersection with the
separate primary 10-degree slope proxy and is not an agricultural eligibility
decision. All counts refer to whole-box analysis pixels, not confirmed crop area.

Report: `outputs/africa/gap-visibility/727b09efd2cac9dbfae2/report.json`.
Derived NPZ artifacts retain classes, sampled clearance, minimum-clearance
distance and support fractions on the derivative grid. Mapped classes and grids
are recorded separately. Replays compare arrays instead of silently overwriting
earlier results; generated elevation/radar/annotation artifacts stay outside Git.

## Remaining interpretation gate

`bounded_nonlocal_visibility_checked=true` means this bounded approximation ran.
`radar_illumination_confirmed=false` and `usable_agricultural_evidence=false`
remain explicit. It is not a full shadow/layover solution, correction of provider
RTC values or independent processor validation. Passing does not establish crop
condition, measured NDVI beneath clouds or the cause of backscatter changes.

Next: independent processor comparison and quality-screened causal radar/optical
pair construction, with compatible training inputs and untouched evaluation.
No radar-assisted model is trained or optical values imputed. Confirmed crop
identity/calendars and independent field outcomes remain absent; forestry stays
with Vepris and no CropSight validation transfers.

Verification: 84 focused tests passed, including analytical ridge, missing-height,
opposite-direction and boundary sightline fixtures, orbit/annotation checks,
terrain, numerical radar and cloud-gap regressions.
