# Uganda historical survey reference audit

Vantage now has an offline, aggregate-only audit of the pinned One Acre Fund
maize-survey CSV inspected during the public-source investigation. This closes
the repeatability gap for the initial Uganda subset inspection, not the field
validation gap. No model is trained and no survey rows become scouting labels.

Source: [published dataset and methods](https://zenodo.org/records/11122388).
The earlier research checked its CC-BY-4.0 metadata; consult the source methods
and attribution before any downstream use. Raw records remain outside Git.

## Replay

```powershell
python scripts/audit_uganda_survey.py outputs/research/2026-10-24/one_acre_csv.source --out outputs/private/uganda-survey-audit-v1.json
python -m unittest tests.test_survey_audit
```

Use a new output filename for another run. The CLI checks the exact downloaded
CSV SHA-256 before parsing, permits reports only beneath `outputs/private`, and
refuses to overwrite an existing report. It uses only the Python standard library.
Inputs are bounded to 10 MB and 100,000 rows. Reports include the source and
implementation hashes, aggregate quality counts and explicit ineligibility flags.
No coordinates, individual yields or row-level records are exported.

## Actual result, 24 October 2026

| Check | Result |
| --- | --- |
| Source rows | 14,773 |
| Uganda rows | 109; all 2020, first season |
| Parseable planting dates | 109; none mismatched the declared year |
| Missing harvest dates | 109 |
| Finite, nonnegative reported yields | 109; numerical validity is not measurement verification |
| Coordinates within global WGS84 ranges | 109; not confirmation of plot location |
| Distinct coordinate pairs | 106 |
| Repeated coordinate groups | 3; 3 additional rows at repeated coordinates |
| Exact duplicate rows | 0 |
| Published longitude decimal places | 13 rows with 2; 96 with 3 |

Counter keys for defects are present only when nonzero. Repeated coordinates
are not deduplicated: several observations can share a rounded or substituted
location. Decimal places describe representation, not a positional error bound.

## Remaining admission requirements

Confirm original coordinate provenance, plot geometry, crop/yield measurement
protocol, harvest timing, and spatial disclosure treatment before field-level
imagery pairing. Trace source overlap before creating independent test splits.
Repeated points, nearby observations and shared seasons need explicit grouping
in a future benchmark protocol; this audit does not create those splits.

Even a suitable historical yield benchmark would evaluate a different task from
prospective scouting priority. Independent dated field outcomes are still zero.
Training and scouting-validation eligibility remain false in every audit report.
