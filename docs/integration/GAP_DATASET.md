# Frozen cloud-gap research dataset partitions

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

```powershell
python scripts/prepare_gap_dataset.py --sequence outputs/africa/recent/a013b10c8db819241036/pixels/sequence-observations.json
```

The script verifies artifact hashes, array/mask agreement and pixel counts, then
assigns acquisitions using `configs/gap_benchmark_split.json`. Multiple compatible
sequence reports can be supplied to `--sequence`. Outputs are ignored generated
manifests under `outputs/ml/cloud-gaps/<content-id>/manifest.json`. The content
identity includes the plan and source records; a different manifest must not
overwrite an existing frozen artifact. This prepares metadata, not model tensors.

Partitions are deliberately disjoint in both geography and year:

| Partition | Location | Calendar year |
| --- | --- | --- |
| Training | Iganga study box | 2023 |
| Validation | Lira study box | 2024 |
| Development test | Kasese study box | 2026 |

Overlapping locations or years, duplicate location/acquisition timestamps and
naive timestamps are rejected. Each designated cohort needs at least three
nonempty dates to pass this minimum inventory gate. Passing is necessary but not
sufficient for training: exact grids, causal overlap within seven days, mask
diversity and sufficient independent examples still need checking at sample
construction. Calendar years are research partitions, not confirmed crop seasons.

Actual current run: train 0, validation 0, development test 6 assigned scenes.
The missing historical cohorts produce explicit blockers and
`training_data_gate_passed=false`. Other 2026 Iganga/Lira observations are excluded
by the frozen plan rather than silently reassigned. Existing historical data
elsewhere in the repository have not been silently adapted or counted as these
compatible sequence inputs. Successful manifest generation does not imply that
training is authorized by the gate; no trainer is implemented in this release.

The 2026 scenes and baseline errors were already inspected during development.
Consequently Kasese 2026 is not an untouched final test. An independent future
cohort must be frozen before final performance claims. Location/year separation
also confounds those two sources of change; it does not isolate either effect.

Next acquisition: bounded multi-date Iganga 2023 and Lira 2024 sequences using
the same numerical recipe, followed by sample construction and comparison of
uncertainty-aware candidates against persistence and abstention. No crop calendar,
field outcome, diagnosis, yield forecast or operational infill is supplied.
