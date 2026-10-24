# Uganda field evidence and scouting benchmark

Implemented offline research tools; no real field results. Keep outcomes outside
`web/`. The CLI rejects output under `web/` and refuses overwriting reports.
Inputs and declarations remain the operator's responsibility; this is not a
tamper-proof registry or authorization system.

## Freeze the visit design before outcomes

Prepare a JSON array of `unit_id` and `status` (`flagged`, `unflagged`,
`unavailable`). Status must come from a frozen, dated evidence run; do not
interpret missing data as unflagged. Retain unavailable units for a separate
data-gap review; this sampler does not inspect them or assess their outcomes.

```powershell
python scripts/evaluate_scouting.py plan private/units.json --capacity 10 --seed 42 --out outputs/private/visit-plan.json
```

The plan samples without replacement within strata, approximately equal
allocation, retaining exact inclusion probabilities. The seed and sorted IDs
make it independent of input ordering. If one stratum is small, unused slots
transfer to the other. Empty strata remain visible. This is a pilot research
allocation, not a statistically powered design or the final production queue.
Freeze cohort membership, source dataset/run IDs, cutoff, capacity, baseline,
crop/season eligibility and useful-finding rubric in an access-controlled
protocol before visits. The present sampler does not store that registry.

## Complete-cohort comparison

The evaluator requires outcomes for **every** unit in a frozen cohort. A
partially visited stratified sample is not compatible with this estimator.
Do not filter to completed visits and claim full-cohort precision. Future
partial-sample analysis requires design-based weighting and uncertainty.

The [conditional scouting ranking bounds](../integration/SCOUTING_BOUNDS.md)
now provide a separate exact range calculation for incomplete outcomes. These
are finite-cohort identification bounds, not a weighted sampling estimator,
confidence interval or independently validated agricultural performance result.

Each JSON record requires:

| Key | Meaning |
| --- | --- |
| sample_id, cohort_id | Unique observation unit and common frozen decision round |
| spatial_group | Independently defined geographic cluster, not arbitrary ID |
| acquired_at | Latest input observation timestamp, timezone required |
| prediction_frozen_at | Timestamp after inputs and before outcome observation |
| observed_at | Independent visit timestamp, timezone required |
| held_out | JSON true; verified by study governance, not self-certifying |
| independently_verified | JSON true following independent adjudication |
| reference_ref | Private traceable field evidence reference |
| outcome | useful_finding or no_useful_finding under frozen rubric |
| model_score, baseline_score | Finite priority values, higher means earlier inspection |

```powershell
python scripts/evaluate_scouting.py evaluate private/complete-cohort.json --capacity 10 --out outputs/private/evaluation.json
```

Outputs: paired precision at fixed capacity, difference, recall where positives
exist, expected random precision, cohort hash and exploratory paired cluster
bootstrap 95% percentile interval. Both methods use exactly the same cohort and
capacity. Equal scores break by sample ID. No interval below three geographic
groups. Cluster resampling uses the same draw for both methods and recomputes
rankings; capacity is capped at resampled population size for small draws.
This can be unstable with few or uneven clusters; it is not confirmatory
inference. Repeated rounds and overlapping geography require a richer design.

The evaluator checks types, completeness and timestamp ordering, but cannot
prove label truth, immutable historical predictions, training exclusion or
actual publication-time availability. Preserve audited source/arrival records
and independent study governance. No minimum performance pass is invented.

## Validation recorded for this increment

Synthetic unit tests cover known paired rankings, deterministic cluster
resampling, missing outcomes, future predictions, invalid scores, unverified
labels, single-group uncertainty withholding, sampling controls/probabilities
and duplicate units. Synthetic test results are not product performance.
The existing Uganda archive still has zero independent field labels; therefore
no real capacity benchmark or supervised agricultural result is reported.

Verification on 20 October 2026: full regression suite **41 passed**; CLI help
and `git diff --check` passed. The first sandboxed suite attempt was blocked
on loopback sockets and temporary SQLite access; the approved unrestricted
rerun passed. No browser changes were made in this increment.

Running the sampler against the existing novelty report produced
`outputs/africa/sampling-feasibility.json`: one flagged unit (IG-11), zero
unflagged units and three unavailable units. The tool explicitly warns that
this archive cannot compare flagged versus unflagged outcomes. This is a
historical feasibility check, not a current field visit plan or crop finding.
