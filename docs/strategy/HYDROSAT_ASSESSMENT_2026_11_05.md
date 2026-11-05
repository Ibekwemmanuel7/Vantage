# Hydrosat / IrriWatch: supplier assessment

Research checked 5 November 2026. Public-source technical and procurement
assessment, not a quote, contract interpretation or Vantage validation claim.
Vantage is the agriculture product within [Lillie US](https://github.com/Ibekwemmanuel7/Lillie_US).
Uganda is the first pilot; forestry remains with Vepris.

## Recommendation

Evaluate Hydrosat as an optional supplier. Keep the public-data workflow as the
baseline and require a bounded area trial plus a written commercial offer before
making Hydrosat-dependent commitments. No account, order, trial activation,
data purchase, API connection or supplier outreach was performed in this assessment.

## Two different procurement routes

| Route | Publicly documented capability | What remains unverified |
| --- | --- | --- |
| IrriWatch analytics | Advisor advertises daily 10 m crop/water analytics combining satellite, soil and weather context | Uganda field suitability, observation/model flags, endpoint contract, validation and commercial reporting rights |
| Discovery imagery | STAC API uses bearer authentication and COG imagery; full downloads require ordered data | AOI inventory, native bands/grid, calibration, actual access terms, recurring cost and processing effort |

Sources: [IrriWatch](https://hydrosat.com/solutions/),
[Discovery API documentation](https://satdocs.hydrosat.com/data-discovery-platform/stac-api-documentation.md).
An imagery API is not necessarily the API for derived IrriWatch field analytics.
Do not assume the same entitlement, price or integration effort.

## Resolution and freshness

The technology page distinguishes current VZ sensors (30 m VNIR, 70 m LWIR)
from a future Osiris design (10 m visible, 25 m thermal). These are not equivalent
to a derived product's 10 m output grid. The Academy explains that cloudy-period
daily results can be estimated with a soil-water-balance model until a new
usable satellite observation arrives. Therefore an update date must not replace
the last observed acquisition date.

Sources: [sensor technology](https://hydrosat.com/satellite-technology/),
[cloud-gap explanation](https://irriwatch.academy.hydrosat.com/srs-hs-satellites).

A 70 m square occupies 0.49 ha before accounting for the sensor response,
geolocation and field-edge mixing. This arithmetic is not a minimum useful field
size or proof of smallholder suitability. Benchmark actual field geometry,
intercropping, valid interior support and spatial uncertainty. Resampling cannot
create independently observed detail. Do not promise cloud-penetrating thermal
observations or daily fresh imagery.

## Commercial access and licensing questions

Discovery advertises catalog/monitoring subscriptions, single-image purchases
and a trial up to three months on selected AOIs. No numerical tariff was found
on the reviewed official pages; trial eligibility and commercial-use rights are
not confirmed. Source: [Discovery access options](https://hydrosat.com/discovery-platform/).

The published imagery licence distinguishes internal evaluation from commercial
use. Section 3.3 allows certain non-government value-added products subject to
the agreement, order form and possible extra charges. Other provisions restrict
data publication, redistribution and third-party API access. Government customers
have additional express-authorisation requirements. This does not establish
permission for a particular report, tile service, AI pipeline or downstream user.

Source: [Satellite Imagery License Agreement, sections 3.1–3.3](https://hydrosat.com/wp-content/uploads/2025/03/License.docx.pdf).

The addendum assigns prices to the order form and describes supplier use of
customer data for service delivery and internal research, including aggregated
anonymised publication. Confirm acceptable handling of sensitive farm geometry,
retention, subprocessors, training use and deletion before supplying private inputs.
Source: [Commercial Terms Addendum, sections 4 and 7](https://hydrosat.com/wp-content/uploads/2025/03/Commercial-Terms-Addendum.docx.pdf).
Ask for the current contract pack applicable to the chosen product; the public
imagery agreement must not be assumed to govern every IrriWatch offering.

## Request for an itemised written offer

1. Confirm actual coverage and usable acquisitions for the supplied Uganda AOI
   and dates; distinguish archive, new collections and future plans.
2. Quote imagery and derived analytics separately. State minimum billable area,
   annual/monthly minimum, minimum term, per-field/AOI/user/API charges, currency,
   tax, setup, support, egress, trial conditions and renewal changes.
3. Explain native support, effective resolution and uncertainty for small and
   intercropped fields. Provide observation dates, modelled/imputed flags,
   quality masks, valid support, timestamps, units and validation evidence.
4. Specify API schema, authentication, rate limits, webhooks/file alternatives,
   historical backfill, retries and deletion/version behaviour. No secrets in browsers.
5. Confirm rights for paid HTML/PDF reports, derived statistics, embedded raster
   tiles, offline downloads, model training, end users, government recipients,
   subcontracted AI processing and retention after termination.
6. Confirm customer-data processing purposes, permitted hosting regions,
   retention/deletion, third-party transfers and restrictions on supplier training.
7. Request a capped evaluation with no automatic paid conversion. Agree which
   evaluation outputs may be shown to a partner before sharing them.

## Public-data baseline

Copernicus Sentinel data are available on a free, full and open basis under
their own legal notice. Data-access services retain quotas and separate terms;
other portal content and third-party datasets do not inherit Sentinel rights.
Compute, storage, analyst review, service access and delivery still cost money.
Sources: [CDSE terms](https://dataspace.copernicus.eu/terms-and-conditions),
[Sentinel data notice](https://cds.climate.copernicus.eu/licences/ec-sentinel).

Compare options on the same AOI and dates using usable observed coverage,
latency, withheld/modelled fraction, field support, reviewer time, permitted
delivery and total incremental cost. Thermal analytics must demonstrate added
decision value rather than being assumed superior to a simple optical baseline.

## Vantage implementation boundary

Historical imagery, local field review and report export exist. Hydrosat data
ingestion and a partner API do not. Crop-problem diagnosis and operational yield
forecasting remain unvalidated. Current exploratory ML results do not justify
agricultural accuracy, water-saving, yield-increase or financial-return claims.
