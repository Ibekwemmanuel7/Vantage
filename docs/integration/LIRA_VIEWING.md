# Lira acquisition-specific local viewing geometry

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/check_lira_viewing.py --online
python scripts/check_lira_viewing.py
```

The first permits only the required source-item, SAFE-manifest and annotation
reads for the fixed two-pass cohort. Offline replay checks cached byte identities
and reproduced both geometry arrays. No new radar raster acquisition is required.
`configs/lira_gap_viewing.json` fixes the cohort, 0.25-degree incidence consistency
tolerance and 5–85-degree local-incidence guards before annotation inspection.

## Verified source chain

Follow each RTC item's actual `derived_from` link to its authoritative Planetary
Computer GRD item, then its SAFE manifest. Select the manifest-referenced VV
product annotation, excluding calibration/RFI references. If the original SAFE
filename is not available, accept only the documented measurement-stem storage
mapping when byte size and MD5 agree with the SAFE reference. Cached replay repeats
these checks. The checksum establishes consistency with the fetched manifest,
not independent authenticity certification or trusted-processor agreement.

Product parsing checks platform, GRD/IW/VV identity, absolute orbit, acquisition
time containment, Earth-fixed orbit states and geolocation support. Orbit positions
use cubic Hermite interpolation without extrapolation. Viewing vectors are
interpolated only inside supported annotation geometry. Independent DSM gradients
and metric grid-axis orientation supply approximate local facet normals.
This reuses the previously tested viewing mathematics, not Kween validation.

## Actual findings

Both 4 and 16 June 2024 annotations contain 210 geolocation points and 17 orbit
states. Maximum annotation-versus-orbit incidence discrepancy is approximately
0.004413 degrees, within the fixed tolerance; no orbit extrapolation occurred.

| Whole-box local risk class | 4 June | 16 June |
| --- | ---: | ---: |
| Unknown | 0 | 0 |
| Locally unflagged | 307,450 | 307,450 |
| Local range-reversal risk | 1 | 1 |
| Back-facing facet risk | 0 | 0 |
| Incidence-guard risk | 17 | 17 |

Denominator is 307,468 whole-box analysis pixels, not confirmed crop fields.
Mapped nominal incidence ranges are approximately 37.88–38.69 degrees; approximate
local incidence spans about 1.69–70.73 degrees. These are local estimates, not
surveyed or independently validated acquisition geometry. VV annotation supports
approximate viewing geometry for this dual-polarization research cohort.

Report: `outputs/africa/gap-viewing/82fd966dcc318d43362f/report.json`.
It retains source radar/terrain report identities, original source/manifest/
annotation filenames and hashes, SAFE reference size/MD5, derived artifact hashes,
track identity and implementation hashes. Generated XML and arrays remain outside
Git; access tokens are never written to this report. Provider errors expose only
their type. Failed acquisition/validation does not become an unflagged result.

## Remaining gate

`nonlocal_shadow_checked=false`, `radar_illumination_confirmed=false` and
`usable_agricultural_evidence=false` remain explicit. Local predicates cannot
establish nonlocal shadow or full layover, validate source radiometry, remove
speckle or certify the provider RTC processor. DSM surface/height approximations
and source delivery-time uncertainty persist. Passing local checks must not
refresh optical observation dates or turn estimates into measured NDVI.

Next: bounded nonlocal visibility screening using a larger independent elevation
window, then independent processor checks and compatible training inputs before
radar-assisted modeling. No crop diagnosis, yield estimate, irrigation instruction
or operational field priority is enabled. Crop calendars, independent field
outcomes and an untouched final evaluation remain missing; forestry stays with
Vepris and no CropSight validation transfers.

Verification: 76 focused tests passed, including annotation tampering/type checks,
orbit/geometry analytical cases, terrain, native-raster and cloud-gap regressions.
