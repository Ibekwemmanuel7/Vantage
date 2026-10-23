# Recent numerical vegetation observations

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/process_recent_pixels.py --inventory outputs/africa/recent/a013b10c8db819241036/inventory.json --online
```

Requires `requirements-geo.txt` and the preceding recent inventory archives.
Processes one latest eligible scene per box, at most three scenes. Eligibility
requires full catalog bounding-box containment and the baseline assets. Selection
uses acquisition time rather than lowest scene cloud. There is no fallback to
older images and no temporal interpolation. No dashboard data is overwritten.

Reuses the existing archive numerical recipe: 20 m analysis grid, B04/B08
physical reflectance using product quantification and band offsets, SCL classes
4/5 accepted with a one-pixel rejection buffer, nonzero source values and valid
reflectance/NDVI checks. NDVI and valid masks are saved as georeferenced internal
NPZ caches, not COG exports or foundation-model inputs. Raw raster reads are
cached by the existing source adapter. Signed access tokens stay out of reports.

Source catalog archive checksums and acquisition identities are checked before
processing. Reports retain source inventory, artifact and metadata checksums,
acquisition dates, valid/total pixel counts and processing time. Quality uses an
explicit 70% whole-box coverage threshold and seven-day freshness rule for
research only. These thresholds are not locally validated agricultural rules.

Actual run at the 23 October 2026 00:00 UTC cutoff:

| Study box | Latest acquisition | Accepted pixels / analysis pixels |
| --- | --- | --- |
| Iganga | 20 October 2026 | 0 / 308,021 |
| Lira | 20 October 2026 | 0 / 307,468 |
| Kasese | 20 October 2026 | 0 / 309,132 |

All three processing jobs succeeded but all observations have insufficient
coverage under the mask recipe. No NDVI median is available. Zero accepted
pixels does not mean no vegetation, crop failure or a diagnosed cloud cause;
it means the combined quality rules rejected the available values. Detailed
mask attribution remains a useful next diagnostic. No crop health claim follows.

Reports are under the inventory directory in `pixels/observations.json`.
Errors record types only, because provider exceptions can contain signed URLs.
Repeated runs reuse source caches and verify existing derived arrays rather than
silently changing them. The summary is regenerated; generated data stays out of Git.

Whole-box coverage is not current cropland or field coverage. Confirmed crops,
planting dates, independent field outcomes and a multi-date usable sequence are
still absent. Radar does not substitute for NDVI. Yield prediction, nutrient or
disease diagnosis and irrigation prescription remain unavailable.

Verification: 23 tests passed across recent selection/quality, catalog inventory,
existing imagery/ML numerical checks and historical partner bundle behavior.
