# Public-source evidence program

20 October 2026. The owner has no Uganda field partner and authorized public
internet research. No one was contacted. This program uses public reports,
farmer accounts, research repositories and open datasets as evidence leads.

## Results of the first search pass

The [nine-reference registry](../../examples/uganda-public-evidence.json) records
source URL, origin group, review scope, publication/event timing, geographic
precision, reported crop, permitted analytical role and unresolved matches.
The [machine assessment](PUBLIC_EVIDENCE_REVIEW.json) retains all blockers.
It contains no downloaded article images, private social content or invented
field coordinates. Titles/snippets are not treated as reviewed original text.

| Source | What was actually found | Role now |
| --- | --- | --- |
| [Uganda Radio Network, 6 June 2023](https://ugandaradionetwork.net/story/prolonged-dry-spell-drying-up-crops-in-kween) | Farmer accounts of drying maize/beans near flowering in named Kween localities | Strong historical-event lead; exact fields and observation dates unverified |
| [Daily Monitor, 3 October 2024](https://www.monitor.co.ug/uganda/news/national/dry-spell-casts-shadow-of-poverty-and-hunger-4784504) | Withering crops described across districts; caption locates affected maize in a Kasese town; Iganga only broadly mentioned | September/October case candidate; not evidence for an Iganga March–July pixel |
| [FEWS NET, May–September 2024](https://fews.net/east-africa/uganda/key-message-update/may-2024) | Regional dry conditions and crop effects in West Nile, Lango and Acholi, explicitly using CHIRPS | Regional context; shared rainfall input means no independent precipitation validation |
| [Kyambogo University dissertation abstract, November 2024](https://kyuspace.kyu.ac.ug/items/c5faf93f-1ea3-4b6a-b6a4-5cdcbb29488a) | Identifies secondary district maize records for 2013–2022 | Historical data lead; underlying tables/methods not audited; no 2023/24 field outcomes |
| [CropLife farmer account](https://croplife.org/campaigns/maize-from-uganda/) | Farmer testimony about inadequate rainfall, without a verified event date/farm match | Market-discovery context |
| [Voice of Lango, 1 December 2024](https://www.radiocomnetu.org/voiceoflango/2024/12/01/1523/) | Positive hybrid-maize experience, changed management and expected harvest figures in a named Lira locality | Counterexample/management-confounder lead; not a verified measured yield or negative control |
| [NARO June 2024 bulletin, p.6](https://naro.go.ug/wp-content/uploads/2024/08/NARL-bulletin-June-2024.pdf) | Banana training event on 17 May 2024 in a named Lira village | Original dated institutional reference; not maize or a crop-condition outcome |
| [Public Reddit discussion](https://www.reddit.com/r/Uganda/comments/1gjmzwc/) | Indexed farming discussion; full page retrieval failed | Discovery only; no verified observed outcome |
| [UG Reports July 2024 lead](https://ugreports.co.ug/masindi-agago-farmers-count-losses-over-prolonged-dry-spell/) | Search index reports crop-loss accounts; full page retrieval failed | Discovery only; date and original reporting unverified |

Public social-post searches did not produce a verified, precisely matched farmer
post in this pass. Do not represent the newspaper interviews as farmer-authored
Facebook posts. No inaccessible page was bypassed or login performed.

## How public reports become useful

An event case can compare dated regional imagery with what an independent
report describes at the same geographic and temporal scale. Distinguish this
consistency check from proving cause, detection accuracy or useful findings per
scouting visit. A district reference cannot label every parcel in that district.
Absence of a post does not mean healthy crops. Several websites copying one
report are one origin, not multiple corroborations.

For each promoted case, freeze the event window, public administrative boundary
or explicitly uncertain area, source claim and matched comparison area before
examining model scores. Retain contrasting cases, cloudy coverage and failures.
The best candidate outside the current cohort is the Kween June 2023 field
report; it needs a separately documented AOI and imagery reconstruction. The
Kasese September/October 2024 report similarly needs a matching temporal window.
Neither has been reproduced or validated merely by adding the registry.

For supervised scouting labels, the new offline assessment requires a verified
field spatial match and day-specific observation, crop identity, independent
field evidence, an explicitly adjudicated useful/no-useful finding, sampling
design, origin/verification references and a completed reuse review. It checks
declarations, not truth. No automatic import into `train_baseline.py` exists.
All nine current records fail one or more requirements; **zero supervised
labels were admitted**. That describes this pass, not an impossibility of using
online field evidence. Public facts can still inform hypotheses and cases.

The full suite passes **71 tests**, including public-source independence,
publication/observation-date separation, shared-origin counting and synthetic
audited-declaration tests. Synthetic passing references are test fixtures,
not added to the real registry or counted as agricultural evidence. Checks
also cover ten-day slot selection and rejection of desk-only calendars.

```powershell
python scripts/review_public_evidence.py
```

## Open reference datasets checked

Also inspected two small pinned [WorldCereal 2023/2024 Africa archives](https://zenodo.org/records/17288873).
Publisher MD5 checksums matched. Their nested collection names and workbook
metadata identify Morocco, not a Uganda reference cohort; no Uganda training
sample was admitted. This does not prove that Uganda data are absent from all
WorldCereal releases, global bundles or the live Reference Data Module. See
[inspection records](REFERENCE_ARCHIVES.json). Per-collection methods and licences
still require review before any training or redistribution.

[WorldCereal RDM](https://worldcereal.github.io/worldcereal-documentation/rdm/explore.html)
provides public reference discovery. Crop-type labels can help establish crop
identity; they are not scouting outcomes. [GROW-Africa v1](https://zenodo.org/records/14961637)
is another promising lead spanning mixed regional, survey and crop-cut scales.
Only its public record was reviewed here; the database was not downloaded or
matched to Uganda fields. [CIMMYT historical maize trials](https://hdl.handle.net/11529/10548190)
include Uganda in geographic coverage but collection dates 1999–2007 predate
Sentinel-2; they do not validate the current 2023/24 imagery cohort.

```powershell
python scripts/inspect_reference_archives.py --allow-downloads
# Check cached archives without network:
python scripts/inspect_reference_archives.py
```

No source establishes Vantage accuracy, irrigation recommendations, yield
benefits or a commercial partnership. Keep forestry with Vepris and retain
the [Lillie US backlink](https://github.com/Ibekwemmanuel7/Lillie_US).
