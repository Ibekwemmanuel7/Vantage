# GROW-Africa Uganda reference audit

Investigated 2 November 2026 for Vantage's crop-condition and yield programme.
Vantage remains within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
This increment adds a reproducible source audit, not a new fitted model.

## Source and scope

[GROW-Africa v2](https://zenodo.org/records/16544448), by Geyman and colleagues,
combines multiple measurement methods and spatial supports. Its record API
identified CC-BY-4.0. The [primary methods paper](https://www.nature.com/articles/s41597-025-05257-5)
explains survey geospatial anonymization and warns against directly matching
those points to high-resolution imagery. Source-family overlap also matters:
some data originate from One Acre Fund, as did our preceding survey benchmark.

The public 64,638,070-byte ZIP and 9,538-byte readme were downloaded. Both matched
the provider's published MD5 checksums; Vantage also pins SHA-256. The actual ZIP
contains four XLSX workbooks, despite the readme describing CSVs. We read them
without modifying or executing workbook content. No GADM boundaries were acquired
or redistributed. Raw workbooks and aggregate working reports remain outside Git.

## Actual inventory

All 535,844 source rows were inspected. There are **39,859 Uganda rows**, with
different observation supports that must remain separate:

| Source table | Uganda rows | Maize rows | Maize primary yield numerically valid |
| --- | ---: | ---: | ---: |
| LSMS crop cuts | 0 | 0 | 0 |
| Regional statistics | 9,687 | 909 | 487 |
| Other point sources | 300 | 244 | 244 |
| LSMS farmer surveys | 29,872 | 6,290 | 6,101 |

“Numerically valid” means finite and nonnegative in the primary yield column.
It does not establish correct units, measurement accuracy, independence or model
admission. Alternative GPS-area and second-production yield columns are counted
separately; missing primary yields are not silently filled with another variant.

The maize survey records span agricultural end years 2005, 2010, 2011, 2012,
2014, 2016, 2018 and 2019. The three Sentinel-2-era end-year cohorts contain 1,000,
89 and 545 maize rows respectively, before filtering for yield, coordinates,
units, season and original-survey conditions. End-year labels do not establish
planting dates or a common growing season.

All Uganda survey rows have reported spatial precision greater than 1 km;
17,437 rows across all crops have finite global-range coordinates. Coordinate
availability does not override displacement or prove a field location. These
records might support a separately designed cluster/coarse-scale analysis after
review, not immediate field-pixel training.

All 244 Uganda maize point rows use source `OneAcre_survey`, harvest year 2020
and reported precision 0.03 km. They are not a new multi-season reference set.
Overlap with the earlier 109-row release is unresolved, so they must not be
concatenated and treated as independent observations. The fine precision field
also requires checking against the original release's coordinate provenance.

The strict date audit recognizes ISO strings and typed Excel dates. Spot checks
of the maize point workbook instead found unformatted numeric planting-date
serials and missing harvest dates. Numeric date conventions are deliberately
unresolved, not replaced with January 1 or an assumed Excel/MATLAB conversion.
“Zero parseable dates” is not a claim that all underlying planting dates are absent.

Regional statistics are area-level references. The dedicated LSMS crop-cut
workbook contributes no Uganda rows in this release. None of these tables
supplies an independently assessed, dated crop-problem cohort for our satellite
scouting task. **New training labels admitted: zero.**

## Implemented audit

- Pinned source/configuration and implementation checksums, including a guard
  against implementation changes during the audit.
- Read-only streaming through the four expected XLSX workbooks, with bounded
  ZIP sizes, workbook expansion and row counts. No raw records are exported.
- Counts by table, crop, source, year, maize cohort and reported precision.
- Separate primary/alternative yield availability and strict date availability.
- Repeated source/year/crop coordinate groups flagged without deduplicating them
  into an assumed farmer identity.
- Explicit false field-join permission and zero label-admission counts.

Fifteen selected tests passed across the source audit, survey audit and existing
yield benchmark safeguards. They cover zeros versus missing data, country
separation, precision/date handling, yield variants and retained repeated points.
The aggregate run is pinned in `GROW_UGANDA_REFERENCE_RUN.json`; its implementation
hashes were checked against the final files. These are software/source checks,
not agricultural accuracy or farmer consent verification.

## Replay

Use an environment with `requirements-reference.txt` installed. The executed
audit used the bundled workspace Python with openpyxl 3.1.5. It did not install
packages or alter source workbooks.

```powershell
python scripts/audit_grow_reference.py outputs/research/2026-11-02/GROW-Africa-Database.zip --out outputs/private/grow-uganda-reference-v3.json
python -m unittest tests.test_grow_reference tests.test_yield_research tests.test_survey_audit
```

Use a new report filename. The exact pinned `readme.txt` must be adjacent to the
ZIP. A new checkout does not include the raw source archive. Download the matching
version from the cited record and verify the configuration hashes before replay.

## What this changes for ML

We now have a verified multi-year survey inventory, but not a qualified new
field-level satellite cohort. The next admission work is to resolve original
Uganda survey season/unit definitions, coordinate-displacement treatment and
source overlap. For a coarse-scale experiment, declare the spatial support and
aggregation method before choosing imagery or evaluation splits.

For a field-level yield model, continue seeking precisely bounded, permissioned
multi-season harvest/crop-cut records. For crop problems, seek independently
assessed positive and negative dated findings. Do not convert these aggregated
survey yields into disease labels, use current satellite scenes for historical
records, or silently promote the existing weak yield benchmark.
