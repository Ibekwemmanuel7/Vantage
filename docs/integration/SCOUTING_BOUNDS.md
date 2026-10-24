# Scouting ranking bounds with incomplete field evidence

Vantage can now calculate exact bounds on useful-finding precision at the frozen
visit capacity and on the paired difference between its declared ranking and the
baseline ranking. This is an offline, private research analysis. Real independent
field outcomes remain **zero**; no agricultural performance result is reported.

The [field visit protocol](FIELD_VISIT_PROTOCOL.md) selects only a stratified
sample of the available cohort. Its returned visits cannot be used directly by
the existing complete-cohort evaluator. This bounds calculation instead retains
every unresolved binary outcome as unknown. It requires no random-sampling
assumption, imputation or weighting to bound the fixed cohort's ranked outcomes.
It does not estimate average performance, generalize to other seasons, or supply
a confidence interval. Its validity is conditional on truthful known outcomes,
fixed rankings and the declared cohort/rubric.

## Independent adjudication declarations

Start with `configs/scouting_adjudication_template.json`, copied into
`outputs/private`. Fill `cohort_id`, `protocol_sha256` and `rubric_ref` from the
frozen protocol. Each object in `records` requires:

| Field | Meaning |
| --- | --- |
| `unit_id`, `record_id` | Exact selected visit and single ready intake record |
| `decision` | `confirmed` for use; all other decisions remain unresolved |
| `outcome` | `useful_finding` or `no_useful_finding`, agreeing with the reviewed intake |
| `adjudicator_ref` | Pseudonymous adjudicator, distinct from observer and intake reviewer |
| `reference_ref` | Private audit record supporting the adjudication |
| `independence_confirmed` | JSON true following an actual independence review |
| `adjudicated_at` | Explicit timezone timestamp at/after intake review and no later than analysis |

A different identifier and true declaration do **not** prove independence,
qualifications, consent, source truth or blinding. References are not fetched or
authenticated. The software reports how many declarations it used and explicitly
reports zero independently authenticated outcomes. Human study governance must
audit original evidence and training exclusion before interpreting results.

Unready visits, public reports, uncertain findings, duplicates, mismatched IDs,
missing references and invalid temporal order remain unknown. A conflicting
adjudication cannot silently overwrite the intake. Resolve disagreements in a
traceable review process with a new version of the private intake, retaining the
originals and explanation. Do not discard unfavorable visits or relabel to
improve the comparison.

```powershell
python scripts/compare_scouting_bounds.py outputs/private/round-001/protocol.json outputs/private/returned-visits.json outputs/private/adjudications.json --out outputs/private/round-001/bounds.json
```

The empty template can represent no adjudications after its protocol references
are filled. It supplies no invented labels. The output includes input file
SHA-256 hashes, validation time, unresolved and visit-state counts, adjudication
blockers, ranked unit IDs, marginal precision bounds and paired difference bounds.
It stays beneath ignored `outputs/private`, and existing reports are never
overwritten. It contains private identifiers; do not publish it in the dashboard.

## How to read the bounds

Both rankings use the same available cohort and capacity `k`, capped at its size.
Higher frozen scores rank first; score ties break by unit ID. Unavailable units
stay counted separately and are excluded from both rankings. These bounds say
nothing about unavailable fields, their crop condition or the value of inspecting
them. Sampling and comparison are research designs, not operational visit advice.

For a ranked set containing `p` declared known positives and `u` unresolved
outcomes, precision is bounded by `p/k` and `(p+u)/k`. Thus, if nothing is known,
the range is `[0, 1]`; it is not zero precision.

The paired difference uses the **same** possible outcome for a unit in both
rankings. Shared units therefore cancel. Let `d` be the known positives in
model-only units minus those in baseline-only units. Let `u_model` and
`u_baseline` be their unresolved counts. The exact paired difference range is
`[(d-u_baseline)/k, (d+u_model)/k]`. Simply subtracting the two marginal ranges
can overstate uncertainty by ignoring the shared units.

For identical ranked sets the difference is exactly zero even if every finding
is unknown. This proves only equivalence of these two visit sets; it supplies no
evidence that either set detects useful findings. A range spanning zero cannot
establish which ranking is better. Even a positive conditional lower bound
would not prove independent verification, service readiness, yield benefit or
causal impact. No automatic promotion threshold is implemented.

## Status and remaining work

Synthetic tests compare bounds to exhaustive binary completions for disjoint,
overlapping and identical rankings, check provenance/temporal rejection, and
exercise the private CLI and overwrite protection. They are software checks,
not farmer observations. No trained model, label export, statistical confidence
interval, dashboard change or sampling-weighted performance estimator is added.

The remaining dependencies are actual consented boundaries, confirmed crop and
season context, prospectively frozen predictions and a useful-finding rubric,
independent field findings/adjudication, and an agreed study design with enough
independent farms and seasons. Uganda remains the first pilot within Vantage.
No imagery-only cause diagnosis or irrigation prescription is produced.

Verification on 24 October 2026: **34 tests passed** across scouting bounds,
field protocols, intake, capacity evaluation and seasonal checks. CLI help and
`git diff --check` passed. CLI tests used temporary synthetic private records;
no real field outcome or performance report was created.
