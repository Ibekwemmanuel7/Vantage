# Africa development architecture

20 October 2026. Active priority authorized by the owner: Uganda first; Texas
deferred. Part of [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Independent of CropSight; forestry remains with Vepris. No IDEA engagement is
implied. Africa is an expansion direction, not one interchangeable market.

## Product contract

Proposed user: extension analyst/coordinator. Proposed buyer: program or
agricultural-intelligence leadership; budget and willingness to pay unknown.
Decision: which areas to investigate in the next weekly round, with dated
evidence and questions for local experts. Start with partner-confirmed Uganda
monitoring boundaries and a locally confirmed crop calendar. The present
historical WorldCover cropland mask does not establish current maize location.
Do not prescribe irrigation or infer cause from imagery alone.

## Architecture and implementation boundary

Keep the existing modular pipeline: archived source metadata -> physical
reflectance and quality masks -> immutable COG/STAC dataset -> seasonal features
-> independent evidence queue and research model bench. Implemented locally.
Current rasters are retrospective May 2024, not a live satellite feed.

Later increments on 20 October 2026 added a separate three-location research
archive spanning May/November 2022–2024, now 18 six-band observations with
historical-cropland context and coverage inspection in the local desk. The
original weekly brief remains the May 2024 reconstruction. Neither is a live
feed or independently validated crop service. See [current context and QA](CROP_CONTEXT.md).

Added now: deterministic flagged/unflagged visit sampling with explicit
inclusion probabilities; private complete-cohort model/baseline evaluation at
fixed visit capacity; descriptive paired spatial-cluster uncertainty intervals;
missing-outcome and chronology rejection. These are offline research tools,
not integrated field collection, proof of independence or a validated model.

Next increments, in order:

1. Confirm an initial district/subset, seasons, extension team and boundary/crop
   references. Define useful finding and inspection capacity before enrollment.
   Add consented, access-controlled visit collection with independent
   adjudication. Existing SQLite demo feedback cannot become ground truth.
2. Add multi-season, multi-area optical archives with actual publication/arrival
   times. Preserve quality gaps; compare matched crop stages, not just dates.
   Separate present-day reconstruction from historical operational replay.
3. Benchmark simple seasonal NDVI/rainfall rules, robust tabular models and the
   existing novelty baseline on the same frozen cohorts. Test a geospatial
   encoder only with its exact bands, preprocessing, licensed pinned weights,
   and held-out regions/seasons. Evaluate performance per location and season,
   cloud coverage, field scale and delivery latency; report abstentions.
4. Add Sentinel-1 only with orbit/polarization, calibration, terrain correction,
   speckle and temporal-comparability contracts. Radar is not automatic ground
   truth or an interchangeable optical replacement. No radar ingestion exists.
5. Deploy modular API/workers with PostGIS and private object storage, tenant
   authorization, audit events, signed raster access, backups and monitoring.
   The loopback server remains a demonstration server, not public hosting.

## Evidence gates

Engineering: reproducible versioned inputs, masks, source links, unit tests and
failure states. Already partly implemented; not agronomic validation.

Scientific: independent reference outcomes, frozen development/validation/test
regions and seasons, predeclared baseline and endpoint, clustered uncertainty,
negative controls and failure analysis. Require improvement at real inspection
capacity; choose acceptable effect and sample size with the partner and a power
analysis. Three clusters in software is not an adequate-power guarantee.

Operational: prospective delivery before visits; measured missed findings,
useful findings per visit and preparation time; human review and abstention.
Commercial: confirmed buyer, consent, repeat use and willingness to pay. No gate
above has been satisfied merely by implementing this roadmap.

## Current research informing model selection

NASA's [Prithvi EO 2.0 technical report](https://ntrs.nasa.gov/citations/20240015391)
describes a temporal geospatial foundation model; its published benchmarks do
not validate Vantage. The [publisher's model card](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-100M-TL)
specifies HLS 30m blue, green, red, narrow NIR and two SWIR bands. Current
Sentinel-2 RGB/B08 products do not satisfy that contract. NASA's
[HLS access documentation](https://hls.gsfc.nasa.gov/data-access-and-tools/)
describes COG distribution and Earthdata access. No Earthdata credentials,
weights, HLS adapter or foundation-model training are added in this increment.

Research on [smallholder boundary mapping](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2021.744863/full)
documents resolution/field-scale and label challenges. This supports a cautious
area-level pilot design; it does not validate the current Uganda study box.
State-of-the-art performance remains a benchmark objective, not product status.
