# Historical cloud-gap cohort acquisition

23 October 2026. Vantage within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).

The fixed `configs/gap_acquisition.json` adds May research windows for the
designated Iganga 2023 training and Lira 2024 validation cohorts. These are not
confirmed crop seasons. The existing inventory now supports `--location` to
restrict acquisition to one existing bounded box. Other market profiles and the
historical dashboard remain unchanged.

```powershell
python scripts/acquire_gap_cohorts.py
python scripts/acquire_gap_cohorts.py --online
```

The default prints commands without executing network or raster reads.
`--online` executes the fixed catalog/pixel plan sequentially, stopping on any
failed command. Catalog responses are archived/replayed, and existing numerical
arrays must agree before reuse. Maximum budget is twelve scenes, with at most
six latest eligible distinct acquisitions per box; no cloud-ranked fallback.

Actual results:

| Partition | Location/window | Catalog items | Distinct scenes processed | Coverage-qualified scenes |
| --- | --- | ---: | ---: | ---: |
| Training | Iganga, May 2023 | 8 | 5 | 2 |
| Validation | Lira, May 2024 | 6 | 6 | 2 |

All eleven processing attempts succeeded. Iganga's eight catalog items include
alternate versions/acquisitions that do not yield eight eligible distinct dates.
Latest qualifying Iganga observation is 24 May (7.67 days old at 1 June cutoff);
Lira is 28 May (3.67 days old). Coverage is whole-box, not confirmed cropland.

Combine these sequences with the existing recent series:

```powershell
python scripts/prepare_gap_dataset.py --sequence outputs/africa/recent/c990c8c23060aea1302a/pixels/sequence-observations.json outputs/africa/recent/ef95be98f85b606e9313/pixels/sequence-observations.json outputs/africa/recent/a013b10c8db819241036/pixels/sequence-observations.json
```

Actual frozen manifest `8df8e140fc0355075da5` assigns train 5, validation 6,
development test 6. The minimum nonempty-date inventory gate now passes with no
inventory blockers, superseding the earlier recent-only failed-gate run. It does
not establish causal training-pair sufficiency, reliable ground truth under
clouds, independent agricultural performance or operational historical delivery.
Generated imagery, arrays and manifests remain outside Git.

Next: construct causal masked samples, measure supported pair counts and compare
a bounded learned baseline with persistence. The already inspected development
test remains unsuitable for an untouched final performance claim. Crop identity,
planting calendars, field outcomes and independent future evaluation remain absent.
