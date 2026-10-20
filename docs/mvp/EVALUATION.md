# Evaluation and release gates

This plan operationalizes [INITIAL_MARKET](../portfolio/INITIAL_MARKET.md).
No prospective evaluation has run. Synthetic tests establish software behavior only.

## Historical feasibility before the 2027 pilot

Obtain consented boundaries, zone versions, planting dates, pivot confirmation,
crop-stage windows, management events and independently dated scouting findings.
Sample Hale and Floyd field-weeks across clear/cloudy periods, field sizes and
management systems. Archive actual acquisition AND availability/processing times
so replay cannot use observations unavailable at the decision cutoff. Review
usable coverage and masks manually on a prespecified sample. Measure fresh usable
field-week coverage using all eligible due field-weeks as denominator; also report
zone coverage, stale duration and exclusions. Preserve cloudy and missing weeks.

Use development-only seasons/fields to choose coverage, age, baseline gap, zone
sizes and score thresholds. Avoid adjacent-zone and repeated-field leakage.
Freeze code, boundaries, input lineage, policy and outcome rubric before holdout
replay or prospective evaluation. No numerical accuracy target is asserted yet.

## Prospective consultant workflow

Proposed cohort: one consultant, 3–5 growers, 20–40 fields; 8–10 eligible weeks.
This is operational scope, not a power calculation. Before revealing each brief,
record baseline planned visits, order, available capacity and expected time.
Save the presented brief and the revised order. Prespecify a field-check interval
with the adviser. Independently select unflagged zones for inspection alongside
flagged zones; never substitute available flags for the control sample. Log
nonvisits and reasons, unavailable evidence, uncertain findings and late checks.

The primary analysis unit is the field-week scouting decision. Zone visits are
nested in fields and fields in growers; report counts and cluster-aware uncertainty
instead of treating pixels or repeated visits as independent farms. Have the
adviser define `useful_finding` before evaluation: a field-confirmed finding that
justifies an additional investigation or documented management review. Separate
observation from suspected cause; uncertain evidence is not counted as confirmed.
Blind outcome review to flag status where practical. Consider randomized or
counterbalanced brief exposure when feasible; simple before/after differences
cannot establish causal improvement.

| Measure | Required denominator / record |
|---|---|
| Confirmed useful findings per visit | completed visits, flagged and comparison separately |
| False-alarm burden | inspected flags with no useful finding; report uncertain separately |
| Missed findings | confirmed useful findings in presampled unflagged inspections; account for sampling probabilities |
| Availability | all eligible field-weeks, including missing/cloudy/stale |
| Changed inspection decision | paired baseline and revised visit plans |
| Adviser time and cost | preparation, review, travel/check time, imagery/compute and support per field-week |
| Commercial continuation | tested price, budget owner, willingness to pay and repeat agreement |

Publish cohort counts, missingness, follow-up compliance and uncertainty with
every metric. Insufficient confirmed events, control checks or fresh evidence
means **insufficient evidence**, not successful validation. Continue routine
scouting when imagery is unavailable. Agree quantitative go/no-go criteria only
after development estimates and freeze them before the prospective window.
No irrigation prescriptions or imagery-only diagnosis; forestry belongs to Vepris.

## Current automated checks

`python -m unittest discover -s tests -v` covers known synthetic relative changes,
stale/missing/low-quality evidence, future processing exclusion, eligibility,
insufficient history, boundary and duplicate rejection, and feedback linkage and
snapshot persistence. CLI smoke checks generate JSON, GeoJSON and HTML and append
feedback. These do not test real sensor masking, agronomy or commercial value.
