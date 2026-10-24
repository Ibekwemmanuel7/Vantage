# Versioned Uganda regional crop calendars

Vantage now imports the JRC ASAP subnational calendar archive as regional context.
This implements the first context-data follow-up from the
[public-source investigation](../strategy/UGANDA_GAP_CLOSURE_RESEARCH.md).
It does not confirm farmer planting dates, crop identity, a forecast or a
scouting recommendation. Uganda is the first active pilot within Vantage.

## Source and actual import

Source: European Commission, Joint Research Centre; Dimou, Maria,
[Crop calendar dataset compatible with satellite-derived land surface phenology](https://data.jrc.ec.europa.eu/dataset/jrc-10112-10003).
The catalogue describes national/subnational planting, growth and harvest dekad
windows and an acknowledgement-based reuse notice subject to third-party rights.
Retain that attribution and consult the catalogue for complete terms.

The inspected ZIP is pinned in `configs/uganda_regional_calendar.json` with
SHA-256 `f49b56942e00ec2927bb6b26212e07085a9d94f6779480e16251a6648b19dc73`.
This local copy was observed on 24 October 2026. It is not evidence of what
calendar file was operationally available during a past event.

The completed local import produced:

`outputs/africa/regional-calendars/uganda-2024-context-v1.json`

It contains **44 Uganda crop/season contexts across nine source zone IDs**.
The year 2024 is a chosen planting anchor for historical research, not the year
of independently recorded planting. Field calendars confirmed: **0**.

## Replay

The importer uses Python's standard library and does not access the network.
Use the already inspected archive from the research step:

```powershell
python scripts/import_regional_calendars.py --archive outputs/research/2026-10-24/jrc_calendars.source --year 2024 --out outputs/africa/regional-calendars/uganda-2024-context-replay.json
```

If the cache is missing on another computer, obtain the
[public source ZIP](https://mars.jrc.ec.europa.eu/asap/files/crop_calendar_gaul1.zip)
and pass its saved path as `--archive`. No credentials are needed for that
public source. A changed archive is rejected; review and version a changed
source contract instead of silently disabling checksum checks.

Outputs must stay beneath ignored `outputs/`; files are exclusively created,
so reruns require a new output name. The report includes the source contract,
configuration/implementation hashes, creation time, source IDs/labels, original
dekad markers, instantiated date windows and limitations. Generated context files
are not copied into the public dashboard or committed as farmer evidence.

## Date interpretation

There are 36 dekads per year: each month has days 1-10, 11-20 and 21-month-end.
Conversion respects leap years and actual month lengths. The source uses:

| Phase | Source boundaries |
| --- | --- |
| Planting | `sos_s` through `sos_e` |
| Growing | `sos_e` through `eos_s` |
| Harvesting | `eos_s` through `eos_e` |

Each phase is represented from its first dekad's first day through its last
dekad's last day. Adjacent phases therefore overlap at their transition dekad;
these are uncertain seasonal windows, not mutually exclusive daily growth stages.
When successive markers decrease, the later marker moves into the next year.
An implausible full-year/multiple-wrap season is rejected for manual review.

For example, a source window with markers 24, 29, 1, 3 anchored in 2024 has
planting 21 August-20 October 2024, growing 11 October 2024-10 January 2025 and
harvest 1-31 January 2025. This explains the conversion; it is not an instruction
for a particular farmer or proof those dates describe their crop.

## Geography and field confirmation gates

Source IDs and published crop/season labels are retained. Labels with punctuation
or spelling peculiarities are not silently rewritten. The helper
`vantage.regional_calendar.select_context` requires an exact source zone ID and
crop/season label; unknown or ambiguous matches return unavailable.

The calendar catalogue instructs joining `asap1_id` to its corresponding ASAP
zone geometry. That spatial layer has **not** been imported or matched to our
fields/districts in this increment. No district-to-zone crosswalk or field
membership is inferred from region names. Published Uganda coverage does not
include every crop/season/zone; missing entries must remain unavailable.

Every context explicitly has `confirmation_kind=regional_prior`,
`field_calendar_confirmed=false`, `crop_identity_confirmed=false` and
`field_priorities_available=false`. Tests verify that a regional context fails
the existing independent `calendar_readiness` gate. A field calendar still
requires dated field/partner evidence, crop identity, permission and review under
the separate seasonal contract. No new training or evaluation label is admitted.

## Remaining work

The next integration step is a version-matched zone geometry and reviewed spatial
join, followed by clearly labeled calendar context in reports. Field confirmation
must stay separate. Prospective evaluation still needs consented boundaries,
actual crops/calendars and independent findings. This increment adds neither a
dashboard layer nor a new model, and makes no disease, yield or irrigation claim.

Verification on 24 October 2026: **25 tests passed** across the regional calendar,
seasonal, field intake and frozen field protocol modules. Tests cover source
schema/duplicates, exact lookup, invalid dekads, cross-year/leap-year conversion,
field-confirmation rejection, CLI source hashes and overwrite refusal. The real
cached source imported successfully: 44 rows, nine zones and 16 cross-year
contexts at the 2024 planting anchor. `git diff --check` passed. No agricultural
accuracy or current field-calendar claim is made.
