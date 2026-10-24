# Frozen field visit protocol

Vantage's offline research workflow now connects a declared satellite decision
cohort to a stratified visit plan and returned scouting intake. This implements
collection logistics and linkage checks, not independent verification, a live
scouting recommendation, a training dataset or a performance claim. Uganda is the
first pilot; the contract is market-independent. Real independent outcomes: **0**.

## Prepare and freeze before field visits

Copy `configs/field_protocol_template.json` into `outputs/private` and complete
the fields below. The supplied template is intentionally empty and is rejected
by the freeze command until a real, eligible cohort is supplied. No demonstration
farm or satellite score is fabricated.

| Protocol field | Required meaning |
| --- | --- |
| `cohort_id` | Unique decision round identifier |
| `prediction_frozen_at` | Explicit timezone timestamp after all inputs became available and strictly before field observations |
| `rubric_ref` | Private versioned useful-finding rubric, agreed before visits |
| `held_out_protocol_ref` | Private protocol documenting training exclusion and geographic/season separation |
| `capacity`, `seed` | Integer visit slots (at least two) and deterministic sampling seed |
| `units` | Nonempty declared monitoring-unit array, with unique `unit_id` values |

Each unit must contain exactly these fields:

| Unit fields | Required meaning |
| --- | --- |
| `unit_id`, `field_id` | Stable unit and field identifiers; a zone may have its own unit ID and boundary reference |
| `boundary_ref`, `boundary_version` | Exact private field/zone boundary reference and version used in this round |
| `season_id`, `crop` | Declared season and crop |
| `spatial_group` | Geographic analysis cluster defined independently of findings |
| `source_run_ref` | Frozen evidence-run reference, including input and quality lineage |
| `acquired_at`, `available_at` | Explicit timezone timestamps; acquisition <= operational input availability <= prediction freeze |
| `status` | `flagged`, `unflagged` or `unavailable`; inadequate quality/staleness must remain unavailable |
| `model_score`, `baseline_score` | Finite priorities, higher means earlier visit; both null for unavailable units |

The tool checks temporal ordering and declarations. It does not fetch or verify
references, reprocess imagery, calculate priorities, or establish whether data
were historically available. The operator must preserve source receipt logs,
boundaries, quality/staleness decisions, model/baseline versions and the actual
versioned rubric. Do not convert our study-box radar measurements into confirmed
farm evidence. Quality thresholds and crop eligibility belong to the frozen
evidence run, rather than being invented by this collection tool.

```powershell
python scripts/field_protocol.py freeze outputs/private/cohort-input.json --out-dir outputs/private/round-001
```

This exclusively creates a new private directory containing:

- `protocol.json`: normalized declared cohort, content hash, exact input-file
  hash, creation time, sampled units, inclusion probabilities and unavailable units.
- `collection.json`: the selected field links, rubric reference and blank intake
  fields, sorted by ID. Scores, baseline ranks, strata and probabilities are omitted
  to reduce outcome ascertainment bias. This is not a validated blinding procedure.

The existing sampler allocates approximately equal slots to flagged/unflagged
strata, transfers spare slots and samples without replacement. Unavailable units
remain in the private protocol but are not visited by this design. A separate
data-gap investigation is necessary; findings on unavailable units cannot be
inferred. Full protocol access reveals selection information; distribute the
collection form and rubric only to field observers when feasible.

## Collect and reconcile

Keep the frozen protocol unchanged. Copy the collection form for visits and
complete its fields according to the [intake contract](FIELD_EVIDENCE_INTAKE.md).
Use one scouting record per selected unit. Remove uncompleted blank records
from the returned copy to represent missing visits; retained incomplete forms
are explicitly withheld. Resolve corrections through a documented adjudication
process, not by choosing whichever duplicate finding favors the model.

```powershell
python scripts/field_protocol.py reconcile outputs/private/round-001/protocol.json outputs/private/returned-visits.json --out outputs/private/round-001/reconciliation.json
```

Reconciliation verifies the protocol hash and reproducible selection, cohort/hash/
rubric linkage, exact field/zone boundary and season/crop linkage, intake checks
and that observation follows prediction freeze. Every selected unit remains
visible as `missing`, `withheld` or `ready_for_adjudication`. Duplicate visits,
unmatched records, public leads, uncertain findings and boundary changes cannot
silently become accepted outcomes. Reports retain source file checksums and
record indices for private audit, without copying finding text or outcomes.

All outputs stay under ignored `outputs/private`; existing packets/reports are
never overwritten. Local hashes detect inconsistent content, but an operator
can rewrite a document and recompute its hash. This is not a trusted timestamp,
signed custody chain, encrypted store or multi-user authorization service. If
packet writing is interrupted, treat that directory as incomplete and use a new
directory after investigating; no resume or partial-packet admission is supplied.

## Evaluation boundary and next data dependencies

Readiness is for **manual adjudication**, not an independently verified outcome.
Training and evaluation eligibility remain false, even if every visit is complete.
The stratified sample must not be sent to the existing complete-cohort capacity
estimator; design-based weighting and uncertainty analysis are not implemented.
See the [evaluation protocol](../africa/EVALUATION.md).

An [exact ranking-bounds analysis](SCOUTING_BOUNDS.md) is now available for
incomplete outcomes, conditional on linked adjudication declarations. It is not
a sampling-weighted estimator or an independently validated performance result.

Before an agricultural performance study we still need consented, versioned field
boundaries; locally confirmed crops/calendars; a useful-finding rubric; genuinely
pre-visit predictions; independent field observations and adjudication; and a
pre-agreed analysis/power plan. Internet reports can identify leads, not substitute
for those field outcomes. No imagery-only cause diagnosis, irrigation instruction
or model promotion is enabled. Forestry stays with Vepris; Vantage does not
inherit CropSight validation.

Synthetic tests exercise linkage, score-hidden forms, temporal leakage rejection,
stratified selection, missing/duplicate/foreign records, mutation detection,
private output enforcement and overwrite refusal. These tests are software
checks, not agricultural validation.

Verification on 24 October 2026: **26 tests passed** across the field protocol,
field intake, capacity evaluation and seasonal modules. CLI help and
`git diff --check` passed. The CLI integration uses synthetic fixtures in a
temporary private directory; no real farm visit packet or new field outcome
was created. No dashboard changes or new model training occurred.
