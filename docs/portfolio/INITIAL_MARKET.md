# Vantage initial market definition

Version 0.1, 17 October 2026. Product recommendation for a first Southern US pilot; customer demand and performance remain to be validated.

## Product decision

Vantage will initially help an independent crop consultant decide **which irrigated cotton fields and within-field zones to inspect on the next scheduled scouting round**. The first operating region is **Hale and Floyd counties in the Texas High Plains**. Farmers are the beneficiaries and management decision makers; the consultant is the proposed first contracting customer and daily user.

This is a proposed initial market, not an identified or contacted customer. Vantage is a new product and does not inherit CropSight's code or validation claims.

## Customer

Recruit one independent agronomy or crop-consulting firm serving several cotton growers in the two counties. The firm must be able to supply consented field boundaries, planting and management records, irrigation-system information, and dated scouting observations. Its owner or lead consultant must have authority to agree a paid pilot and evaluate the service.

For the first pilot, seek three to five participating growers and approximately 20-40 irrigated cotton fields. These are proposed operational limits for a manageable pilot, not an estimate of regional customer size or a statistical power calculation.

The consultant is a plausible first buyer because one relationship can aggregate fields, supply agronomic interpretation and connect an observed anomaly to a useful inspection. Whether the consultant prefers to pay, resell the service or introduce growers as direct buyers must be established in discovery. Do not assume the economic buyer and end user are the same person.

## Crop and management system

Start with upland cotton in confirmed centre-pivot-irrigated fields. Grower-confirmed crop and irrigation records establish eligibility; automatic crop classification is not required for the first product.

Compare zones within the same field and through time, accounting for planting date, crop stage, soil/background effects and management. Intentional deficit irrigation, crop-stage differences, field edges, hail, pests, disease and nutrient problems can resemble irrigation-related stress. An anomaly is a reason to investigate, not an irrigation diagnosis.

The first decision window runs from sufficient canopy development for useful observation through the reproductive period, with start and stop dates set by the partner's observed crop stage. Exclude crop establishment and intentional late-season senescence until they have separate validated rules.

## Geography

Use Hale and Floyd counties as a bounded recruitment and validation region. USDA's Texas agricultural statistics include cotton production records for both counties. The region and county selection are a commercial and operational recommendation, not a measured ranking of the best market or proof of customer demand. [1]

Texas A&M AgriLife maintains High Plains cotton irrigation resources addressing pivot systems, soil-water monitoring, evapotranspiration and limited-irrigation strategies. Its irrigation-timing guidance describes the management choices growers face when water is limited. These support the relevance of the problem; they do not validate a Vantage model or a commercial water-saving claim. [2][3]

Expand geographically only after repeatable field value and observation availability have been demonstrated. A partner with excellent ground truth in a nearby county may justify a documented AOI revision before the pilot is frozen.

## Supported decision and action

The consultant's question is: **Of the fields already due for scouting, where should I look first, and which zones merit an additional check?**

Vantage supplies a ranked exception list and zone maps. The consultant combines these with crop stage, irrigation history, weather, soil observations and experience to decide where to visit. Only after a field check does the grower or adviser decide whether to inspect equipment, measure soil moisture, investigate pests or nutrients, change management, or take no action.

Example: a persistent area in an irrigated field develops differently from its own prior trajectory and comparable managed areas. Vantage marks the zone, shows the observation dates and quality, and asks for a field check. It does not declare a clogged nozzle, insufficient irrigation or a required water depth.

## First deliverable

Provide one weekly scouting brief, refreshed when a suitable new observation materially changes the evidence. Each brief contains:

- A reviewed list of fields and zones to prioritise within the consultant's available visit capacity.
- Before-and-after imagery and a simple crop-condition trajectory.
- The evidence for the flag, relevant management context, alternative explanations and confidence limitations.
- Acquisition time, usable coverage, processing time and explicit missing or stale data status.
- A mobile-friendly field map with a place to record inspection findings and the action taken.

Start with a report and straightforward map view. A complex dashboard is not an initial acceptance requirement.

## Observation and freshness policy

Use Sentinel-2 optical observations as an initial vegetation-monitoring source, combined with weather and grower records. ESA describes a nominal five-day constellation revisit and 10 m resolution for its finest bands; this does not mean every band is 10 m or that a clear usable image arrives every five days. [4]

Do not promise daily field observation or fault alerts. Use the next scheduled scouting round as the decision cadence. A proposed initial rule is that a field needs a usable observation no older than five days to receive an actionable satellite-based priority; older evidence is displayed as historical context. The pilot must test whether this rule provides enough timely coverage. The exact limit is a planning choice to freeze with the adviser before evaluation, not an established agronomic threshold.

Missing, cloudy or stale observations are not healthy-field assessments. Existing scouting continues when imagery cannot support a judgement. If public imagery cannot meet the agreed freshness requirement, evaluate the cost and permitted use of commercial observations or change the product cadence before making a service commitment.

## Pilot and evidence

Prepare historical feasibility work before a prospective 2027 growing-season pilot. Run a proposed eight-to-ten-week prospective window determined by eligible crop stages and partner capacity.

Compare the consultant's existing scouting process with the same process supported by Vantage. Record the intended visit list before revealing Vantage's priorities. Predefine the unit of analysis, useful-finding criteria and follow-up interval. Repeated observations from one field are correlated; they cannot be counted as independent farms.

Inspect a preselected sample of unflagged zones as well as flagged zones. Otherwise, precision might be observable but missed problems would remain invisible. Keep uncertain causes and fields lacking timely observations in the evaluation record.

Measure actionable field-confirmed findings per visit, missed actionable problems in the comparison sample, consultant time, false-alarm burden, proportion of field-weeks with fresh usable evidence, and whether a recommendation changed an inspection decision. Record cost per field-week and willingness to pay for continuation.

Do not select a numerical accuracy threshold before defining the field outcome and obtaining development-only estimates of variability and event frequency. Freeze thresholds and analysis before prospective evaluation. Insufficient confirmed cases or timely observations must produce an insufficient-evidence result rather than a success claim.

A technical anomaly detector is insufficient for commercial success. Continue only if the adviser finds the output useful, the delivery cost can support the tested price, and a budget owner agrees repeat work. No percentage water saving or yield gain is promised; causal attribution would require an appropriately designed management-outcome study.

## Initial scope boundaries

The first release is scouting support. It does not prescribe irrigation depth or pump operation, diagnose disease or contamination, forecast field-level yield, determine crop-insurance payouts, or provide an emergency warning system. These are potential later products with distinct validation requirements.

Related services can later include drought and storm-loss documentation, irrigation-water accounting with appropriate reference measurements, additional crops and adviser portfolio reporting. Expansion is contingent on a paying workflow and new validation rather than a shared satellite feed alone.

## Positioning

**Vantage helps Texas High Plains cotton advisers prioritise field visits using satellite-observed crop changes, weather and grower records.**

The initial economic hypothesis is better use of scouting time and earlier investigation of observable problems. The first interviews must test whether this is valuable enough to buy and what existing tools already provide.

## Sources

Researched 17 October 2026. Sources establish the crop, regional context and sensor capabilities; buyer choice, pilot sizes, product cadence and freshness rules are proposed Vantage design decisions.

1. USDA NASS, [2024 Texas Agricultural Statistics, including county cotton records for 2022-2023](https://data.nass.usda.gov/Statistics_by_State/Texas/Publications/Annual_Statistical_Bulletin/tx-bulletin-2024-web-updated.pdf). Historical crop records are not a 2026 market-size estimate.
2. Texas A&M AgriLife, [Cotton irrigation resources](https://cotton.tamu.edu/irrigation/).
3. Texas A&M AgriLife Extension, [Irrigation timing during drought for corn cotton and sorghum](https://agrilifeextension.tamu.edu/asset-external/irrigation-timing-during-drought-corn-cotton-and-sorghum-furrow-systems/).
4. ESA, [Sentinel 2 mission characteristics](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2).
