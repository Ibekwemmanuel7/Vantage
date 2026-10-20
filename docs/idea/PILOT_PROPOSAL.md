# Proposed pilot: weekly agricultural evidence for extension review

Discussion draft, 20 October 2026. Prospective IDEA opportunity only; not a quote,
contract, approved partnership or promise of outcomes. Do not circulate as an
IDEA-branded or IDEA-endorsed document.

## Problem and value hypothesis

An analyst must turn regional information into a practical weekly investigation
list. Vantage proposes dated vegetation and rainfall evidence, explicit gaps and
field questions that qualified experts can accept, reject or amend. The hypothesis
is more useful checks and less evidence-preparation time. Public IDEA reporting
suggests a weekly format fit; demand and procurement remain unverified. See
[assessment and primary sources](ASSESSMENT.md).

## Bounded proposed scope

One confirmed Uganda district, initially a partner-selected agricultural subset;
maize-oriented extension workflow without crop-specific conclusions until locations
and seasons are supported. Proposed duration: two weeks of setup followed by six
weekly review cycles. These are planning assumptions; revise after data access
and partner capacity are known. No national monitoring commitment.

| Responsibility | Proposed Vantage work | Partner confirmation/input required |
|---|---|---|
| Scope | Prepare area geometry, source inventory and limitations | District, crop, program priority and permitted monitoring area |
| Evidence | Satellite/rainfall processing, source lineage, quality gates | Local crop/season context and review of baseline assumptions |
| Weekly delivery | Review queue, printable brief, CSV, GeoJSON, frozen version | Editorial cutoff, preferred template, named expert reviewer |
| Field checks | Record findings, uncertainties and follow-ups | Authorized extension staff, safe access, sampled checks and consent |
| Evaluation | Coverage, turnaround, misleading/confirmed flags and time | Baseline workflow, useful-finding definition and review records |
| Data handling | Minimal operational records and agreed retention | Rights to any private input and approval of any public case study |

No access to IDEA systems or farmer database is assumed. Start with file delivery;
evaluate an API only after the system owner confirms its purpose and contract.
Live hosting requires authentication, backups, role controls, monitoring and a
separate deployment decision. The current loopback prototype is unsuitable for
multi-user hosting or private operational data.

## Outputs and exclusions

Each cycle: a reviewed priority list with coordinates/scale, source dates,
freshness, usable coverage, historical reference, reason for inclusion, unknowns
and a field question; downloadable observations/GeoJSON; feedback record.
Maintain separate vegetation and rainfall states. A partial rainfall-based flag
must not be presented as a measured crop anomaly.

Exclude imagery-only diagnosis, pesticides/fertilizer/irrigation prescriptions,
yield or financial-loss estimates, emergency warnings, market forecasts,
insurance decisions and promised food-security improvements. Experts retain
agronomic interpretation. Forestry remains outside Vantage.

## Success measures and decision gates

Before revealing priorities, record the analyst's intended checks. Agree useful
finding, confirmation categories, follow-up interval and review capacity before
evaluation. Inspect a presampled subset of unflagged areas as well as flagged
ones. Log no visits, unavailable evidence and unresolved findings.

Measure useful confirmed findings per completed check, misleading flags, findings
in sampled unflagged areas, analyst preparation/review time, report turnaround,
usable/fresh area-week coverage, active usage and repeat-payment interest. Retain
area/week clustering and report denominators and uncertainty. Decide acceptance
thresholds after development-only variability estimates, before prospective
testing. Insufficient observations or field labels means insufficient evidence.

## Pricing hypotheses and cost model

No IDEA budget or accepted price is known. Use a fixed setup fee plus a capped
weekly service fee initially. Compute actual labor, downloaded bytes, storage,
processing time and review effort before issuing a quote.

Illustrative planning model, USD (assumptions, not observed operating costs):

| Cost component | Proposed assumption | Eight-week envelope |
|---|---|---|
| Setup labor | 8–16 hours at $50–100/hour | $400–1,600 |
| Six weekly preparation/review cycles | 1–2 hours/cycle at $50–100/hour | $300–1,200 |
| Hosting, processing, storage and transfer | $5–25/week over eight weeks | $40–200 |
| Total before field logistics, tax and contingency | Above assumptions | $740–3,000 |

Public data access currently has no invoiced imagery purchase; that does not
eliminate compute, network, licensing review, support or human analyst cost.
Field staff/travel/translation and partner review time need separate agreement.
Commercial imagery, custom integration and expanded AOIs are separately scoped.

Price-testing examples: $1,000 setup plus $250/week for six cycles ($2,500 total),
or $1,500 plus $400/week ($3,900 total). These are negotiation hypotheses; the
lower bundle may lose money at the higher cost assumptions. Require a costed
scope and contingency before quoting. No payment or agreement is implied.

## Required next confirmations

Establish the contact's role and intended organization, program decision-maker,
budget owner, district and crop priority, editorial deadline, field-check capacity,
data rights, minimum useful scale and whether satellite evidence adds value to
existing tools. Proceed only with a concrete jointly agreed pilot scope.
