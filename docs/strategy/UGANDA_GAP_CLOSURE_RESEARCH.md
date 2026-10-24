# Uganda gap-closure research

Investigated 24 October 2026. Vantage within
[Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US). Uganda is the first pilot,
not the whole product. This is a source assessment, not dataset admission,
new agricultural validation, outreach or a deployed integration.

## Decision

Internet evidence can materially reduce our historical-data and contextual-data
gaps. It cannot by itself establish current farmer participation or prove that
Vantage improves scouting. The best next work is a **historical reference-data
audit plus regional calendar and rainfall context**, followed by a reproducible
event case. Do not start a new supervised model merely because a CSV is public.

## 1. Sources inspected as actual files

Bounded public downloads were inspected locally, not just found in search results.
Raw files and a detailed audit remain under ignored
`outputs/research/2026-10-24/`. The initial sandbox could not reach the sources;
the approved network-enabled read succeeded. No credentials were used.

| File inspection | Result | What remains open |
| --- | --- | --- |
| [Dalberg/Radiant Earth Uganda sample tile 019](https://source.coop/radiantearth/african-crops-uganda-01/ref_african_crops_uganda_01_tile_019.geojson) | 2 Polygon features; crop, yield and measurement-related columns present | Full dataset coverage, boundary accuracy, missing-value codes, yield protocol and reuse terms |
| [JRC subnational calendar archive](https://data.jrc.ec.europa.eu/dataset/jrc-10112-10003) | 44 Uganda crop/season rows across 9 distinct published zone names | Correct spatial join to the corresponding ASAP boundaries; field-specific confirmation |
| [One Acre Fund maize survey CSV](https://zenodo.org/records/11122388) | 14,773 rows overall; 109 Uganda rows, all 2020; published MD5 matched | Coordinate provenance and suitability for plot-level satellite joins |
| [GROW-Africa v2 metadata](https://zenodo.org/records/16544448) | Public record and CC-BY-4.0 identifier inspected | The 64.6 MB main database was not downloaded; Uganda-specific record counts and suitability remain unverified |

The Uganda tile's planting/harvest values are 1 January and 31 December 2017.
The [provider documentation](https://data.source.coop/radiantearth/african-crops-uganda-01/Uganda_Documentation.pdf)
explicitly says these are placeholders, not recorded dates. Its campaign and
crop-cut description make it promising historical evidence, but do not repair
the missing dates. The PDF was searchable through the web index; direct web PDF
parsing failed because the server labels it binary/octet-stream. Reuse terms for
this particular repository were not established in this review.

In the 109 Uganda maize-survey rows, yield, planting date and coordinates are
nonmissing; harvest date is missing in all 109. There are 106 distinct coordinate
pairs, with longitudes published to 2 or 3 decimal places. Dataset-wide methods
also describe some locations substituted by towns/districts. Published precision
does not prove field accuracy. CC-BY-4.0 was checked in the record API. These are
candidate retrospective yield references, not dated scouting outcomes.
[Source and methods](https://zenodo.org/records/11122388).

Selected file hashes for replay:

| File | SHA-256 |
| --- | --- |
| Uganda tile 019 | `e3f0ab7bd402b91b7baca1923fcdee2b4ebc598eb484b01ad96e0458c209a5f0` |
| JRC calendar ZIP | `f49b56942e00ec2927bb6b26212e07085a9d94f6779480e16251a6648b19dc73` |
| One Acre Fund CSV | `f305a3d3e48015bd877dc9df5c53b1715c61f940d58383d57d4dfb68c59c6ff0` |

## 2. What we can close or reduce

| Gap | Useful public source | Vantage action | Closure boundary |
| --- | --- | --- | --- |
| Historical field-shaped examples | Dalberg/Radiant Earth Uganda 2017 | Audit all records and permitted use, then match suitable historical imagery | Can support historical research; cannot create present-day customer consent |
| Regional crop-season context | JRC ASAP calendars | Import versioned regional priors with zone IDs, crop and dekad ranges | Can replace broad guesses; cannot mark a farmer's planting date confirmed |
| Retrospective yield references | One Acre Fund; GROW-Africa; World Bank MAPS research | Check provenance, location quality, dates, units and source overlap before pairing with imagery | May enable a separate yield benchmark; does not validate our scouting ranking |
| Rainfall history | CHIRPS v3 | Add versioned rainfall anomaly context with its native spatial scale and delivery latency | Does not measure plot irrigation need or prove the cause of NDVI change |
| Official weather information | Uganda DMS WIDS | Initially provide dated source links; verify API/reuse arrangements before automating | Public forecasts are accessible; no production ingestion contract was verified |
| Surface-water context | DE Africa WOfS | Evaluate dated water detections and observation availability around selected events | Surface-water evidence does not establish root-zone moisture or water allocation |
| Water-use context | FAO WaPOR v3 | Assess ET/productivity layers at their supported resolution | Modeled water-use context, not small-plot irrigation instructions |
| Soil context | ISRIC SoilGrids | Add clearly labeled modeled soil properties with uncertainty, if useful to the decision | Not current field soil tests or a fertilizer prescription |
| Radar processor agreement | ESA SNAP terrain flattening | Assess a pinned independent processing chain against equivalent source scenes/settings | Tool availability is not a completed comparison or independent ground truth |

The JRC calendar source uses dekad ranges and its own administrative/monitoring
IDs. The inspected Uganda rows include beans, maize and millet season labels;
they do not supply calendars for every Ugandan crop or zone. Preserve year
wraparound and do not attach a district by name alone. The catalogue provides
an acknowledgement-based reuse notice, subject to third-party rights.
[JRC catalogue](https://data.jrc.ec.europa.eu/dataset/jrc-10112-10003).

CHIRPS v3 provides 0.05-degree rainfall history from 1981, with separate preliminary
and final products. Its documentation gives different delivery schedules and
daily-disaggregation caveats. Keep the existing v2 reconstruction unchanged;
benchmark any v3 migration and freeze the rainfall baseline/version.
[CHC product documentation](https://www.chc.ucsb.edu/data/chirps3).

The official [Uganda DMS WIDS](https://wids.mwe.go.ug/) publishes daily, dekadal,
seasonal and alert information. Preserve issue time, validity and geographic
scope. No open API contract, redistribution licence or forecast skill for our
selected fields was verified in this investigation.

[DE Africa's product catalogue](https://docs.digitalearthafrica.org/en/latest/data_specs/index.html)
offers cropland, vegetation and water products. WOfS has a documented
[CC-BY-4.0 distribution](https://registry.opendata.aws/deafrica-wofs/).
Classified water, modeled cropland and vegetation composites remain products
with their own algorithms and missing-data limitations, not new field outcomes.

FAO documents [WaPOR v3 access without API credentials](https://www.fao.org/in-action/remote-sensing-for-water-productivity/wapor-data-access/en).
Its [resolution announcement](https://www.fao.org/land-water/news/detail/WaPOR-v3-data-now-available-in-the-new-portal/en)
lists global 300 m, regional 100 m and selected-area 20 m levels. Do not assume
20 m coverage for a Uganda farm; inspect the specific layer and date. These
scales limit direct use on small plots.

[SoilGrids](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs.html)
is a modeled 250 m product, with
[prediction quantiles and unit conversions](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html).
Field recommendations would require local measurements and agronomic review.
[SNAP's terrain-flattening documentation](https://step.esa.int/main/wp-content/help/versions/10.0.0/snap-toolboxes/eu.esa.microwavetbx.sar.op.sar.processing.ui/operators/TerrainFlatteningOp.html)
identifies another processor candidate; installing/running it and harmonizing
DEM, orbit, normalization, resolution and masks are still future work.

## 3. Historical events worth reproducing

| Candidate | Independent public description | Reproduction design | Honest result |
| --- | --- | --- | --- |
| Karamoja drought, 2023 | [NASA Earth Observatory, 23 October 2023](https://science.nasa.gov/earth/earth-observatory/karamoja-beset-with-drought-151969/) | Compare August vegetation with a declared seasonal baseline, inspect crop versus rangeland scope, and reconstruct rainfall context | Regional drought/vegetation reproduction; no invented damaged-field labels |
| West Nile/Lango/Acholi dryness, March-May 2024 | [FEWS NET May 2024 update](https://fews.net/east-africa/uganda/key-message-update/may-2024) | Predefine AOIs, match rainfall anomaly methods, assess optical availability and seasonal vegetation evolution | Independent published event reference; no claim of verified Vantage scouting benefit |
| Lake Victoria/Kyoga overflow, May 2024 | [FAO GIEWS October 2024 archived brief](https://www.fao.org/giews/countrybrief/country/UGA/pdf_archive/UGA_Archive.pdf) | Combine dated water/optical/radar observations, pre-event baseline, cropland context and quality masks | Candidate inundation exposure; no assumed field damage or yield loss |

The 2024 northern dryness is a strong first candidate because Lira research
already covers part of the relevant year and region. That is a workflow reuse
opportunity, not proof our study box suffered the reported losses. Karamoja 2023
offers a particularly clear public vegetation-anomaly reference, but must not
borrow the unrelated 2017 field labels as 2023 truth.

For each case freeze: event-source issue date, event window, AOIs and controls,
crop/land-cover assumptions, input availability, baseline years, quality rules,
and intended comparison. Keep retrospective processing distinct from information
that could actually have been available during the event. Do not measure agreement
against another product using the same satellite inputs and call that independent
ground validation.

## 4. Other useful sources and traps

- [GROW-Africa](https://zenodo.org/records/16544448) combines regional statistics,
  surveys and plot measurements. Preserve observation scale and original source
  IDs; a georeferenced regional total is not a field measurement. Check overlap
  with other collections before claiming independent test cohorts.
- [World Bank MAPS study description](https://www.worldbank.org/en/data/statistical-capacity-building/data-innovation-fund/measuring-crop-yields-from-space)
  documents Eastern Uganda research comparing different yield measurement
  methods. It supports study design; this investigation did not obtain a
  verified, precisely geolocated MAPS release ready for Vantage ingestion.
- [Uganda UNPS 2019-20](https://microdata.worldbank.org/index.php/catalog/3902)
  is an agricultural survey candidate, not a verified field-boundary source.
  Review access conditions, spatial disclosure treatment and measurement units.
  A generic search also surfaced catalogue 5639, which is Tanzania; it was
  excluded after checking the country on the actual catalogue page.
- [Africa-wide field labels](https://github.com/agroimpacts/lacunalabels/)
  are a delineation benchmark candidate. Its code's Apache licence is separate
  from imagery/label terms under the Planet NICFI participant agreement. No
  Uganda subset or unrestricted commercial redistribution was established here.
  Predicted field boundaries would still not establish ownership or current consent.
- [One Acre Fund MEL portal entry](https://data.harvestportal.org/en/dataset/oaf_mel)
  lists another multi-country release. It was not downloaded; do not confuse it
  with the specific audited 2016-2022 maize CSV or assume independent provenance.

## 5. Partner leads and market implication

These are relevant organizations to investigate, not partners we have contacted
or organizations that endorsed Vantage:

| Lead | Published relevance | What to ask through an authorized introduction |
| --- | --- | --- |
| IDEA / David | [Existing Uganda reports and AgriPortal](https://www.idea.ag/) | Which users and pilot districts, permissioned field records, report format, workflow and integration contract? |
| Makerere MaRCCI | [Published digital advisory project](https://rcci.mak.ac.ug/projects/) | Is a relevant team active and able to support field access, crop calendars and prospective evaluation? |
| NARO | [Agricultural discovery portal](https://databank.naro.go.ug/map.php) | Relevant zonal research team, agronomist review and data-sharing process? |
| NASA Harvest / Uganda monitoring community | [Published Uganda collection/training work](https://www.nasaharvest.org/news/a-hrefhttpsnasaharvestorgnewsharvest-partner-dr-catherine-nakalembe-leads-training-uganda-crop-and-livestock-conditionsharvest-partner-leads-training-on-uganda-data-collectiona) | Appropriate public protocols, dataset custodians and possible technical evaluation routes? |
| UBOS / agricultural survey community | [Official dataset catalogue](https://www.ubos.org/datasets-2/) | Permitted access, plot-location protection, objective measurement protocols and survey linkage? |

Published project/training pages may describe historical activities; current
availability requires confirmation. No messages were sent.

The [NASA Harvest crop-monitoring interface](https://harvest2market.nasaharvest.org/)
and [regional Crop Monitor](https://resilience.igad.int/tools_info_systems/crop-monitor/)
show existing overlap in broad monitoring. Vantage should test a narrower value
proposition: traceable field evidence, understandable uncertainty and a usable
scouting/feedback workflow inside a partner application. Public data access alone
is not a competitive advantage or evidence of customer demand.

## 6. Recommended execution order

1. **Reference-data audit:** inspect the complete Uganda 2017 collection and its
   terms; preserve placeholders as unknown; check geometry, labels, missing codes
   and measurement protocols. Separately assess the 109-row 2020 survey cohort.
2. **Regional context:** ingest a pinned JRC calendar snapshot and matching zone
   geometry; add source dates and labels that explicitly distinguish regional
   priors from confirmed field calendars. Keep the existing calendar approval
   gate; do not manufacture a partner confirmation.
3. **One reproducible event:** start with the 2024 northern dryness or Karamoja
   2023, with preregistered AOIs, seasonal baseline and controls. Produce maps
   showing actual coverage and source comparisons. No crop-loss attribution
   without appropriate outcome evidence.
4. **Context layer trial:** evaluate CHIRPS rainfall and official weather links;
   only then add water/soil layers if they improve the chosen user decision.
5. **Field validation partnership:** agree the field cohort, consent, calendars,
   independent finding rubric and prospective visits before scoring utility.

Acceptance is not the number of layers: it is correct source attribution,
temporal/geographic alignment, explicit missingness and an evidence trail that
supports the claimed decision. This search closes discovery/access uncertainty
for some sources; it does not complete their integration or validation. Vantage
still has zero independently verified prospective scouting outcomes, and no
new accuracy claim or trained model results from this research.
