# Independent Lira surface-slope proxy

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/screen_lira_terrain.py --online
python scripts/screen_lira_terrain.py
```

The first permits a bounded independent elevation acquisition; the second
replays archived catalog and native elevation data without network reads.
Actual offline replay reproduced the classes and maximum-slope arrays.

The fixed `configs/lira_gap_terrain.json` uses Copernicus DEM GLO-30,
EPSG:32636 derivatives at 30 m, 180 m padding, 0.999 native support and
5/10/15-degree sensitivity thresholds. The primary rule is 10 degrees; no
threshold is selected using observed radar differences. Source tile:
`Copernicus_DSM_COG_10_N02_00_E032_00_DEM`, archived from the public Planetary
Computer `cop-dem-glo-30` collection. Source catalog and native clip hashes are
retained in the report; collection attribution and redistribution terms must be
reviewed for any external distribution. Generated data remain outside Git.

The implementation reuses the existing independent terrain recipe: finite
metric gradients, complete derivative neighborhoods and maximum slope over 3x3
cells. Unknown support stays unknown. Slope is mapped by nearest neighbor to
the exact radar/optical grid. This does not create higher-resolution elevation
information. Copernicus DSM includes vegetation/structures; it is not surveyed
bare earth or a verified contemporaneous 2024 surface.

## Actual whole-box results

| Maximum neighborhood slope threshold | Lower-slope pixels | Elevated-slope pixels | Unknown |
| --- | ---: | ---: | ---: |
| 5 degrees | 291,749 | 15,719 | 0 |
| 10 degrees, primary | 305,219 | 2,249 | 0 |
| 15 degrees | 306,075 | 1,393 | 0 |

The primary rule excludes 0.73% of 307,468 analysis pixels. Both radar passes
have identical numerical-support counts, so 305,219 numerical pixels remain
inside the lower-slope proxy for each. These are whole-box denominators, not
confirmed crop or field areas. Source radar arrays and exact grids are verified
before reporting sensitivity counts. No backscatter differences are used to
choose the terrain rule, and no crop condition is assigned.

Report: `outputs/africa/gap-terrain/35b6e4f23a945db5119a/report.json`.
It retains parent report, catalog, elevation, artifact and implementation hashes.
The primary source elevation window and derived NPZ classes remain local.

## Interpretation and next gate

This proxy measures surface-slope sensitivity only. It does not establish local
incidence, acquisition-specific layover, distant-terrain shadow, radiometric
noise quality or trusted-processor agreement. `terrain_screen_verified=false`,
`radar_illumination_confirmed=false` and `usable_agricultural_evidence=false`
remain explicit. Kween viewing-geometry work does not validate Lira automatically.

Next: verified acquisition annotations and orbit/viewing geometry for the two
Lira passes, followed by local illumination and bounded nonlocal visibility
checks. No radar-assisted model is trained, optical pixels filled, crop diagnosis
made or irrigation prescribed. Confirmed crop calendars, independent field
outcomes and an untouched final evaluation remain missing. Forestry stays with
Vepris; no CropSight validation transfers.

Verification: 66 focused tests passed, including analytical slope surfaces,
unknown-neighborhood propagation, threshold sensitivity, numerical-support
denominators, cached linear-domain radar averaging and cloud-gap regressions.
