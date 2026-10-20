"""Prospective review sampling and paired capacity evaluation; no model fitting."""
import hashlib
import json
import math
import random
from datetime import datetime


def _date(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Dates require an explicit timezone")
    return result


def sampling_plan(units, capacity, seed=42):
    """Sample independently within flagged/unflagged strata, retaining gaps.

    Equal allocation is a research design, not an agronomic recommendation.
    Inclusion probabilities support later design-based analysis.
    """
    if type(capacity) is not int or capacity < 2:
        raise ValueError("Capacity must be an integer >= 2")
    ids = [u["unit_id"] for u in units]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate monitoring units")
    strata = {"flagged": [], "unflagged": []}
    excluded = []
    for u in units:
        if u["status"] == "unavailable":
            excluded.append(u["unit_id"])
        elif u["status"] in strata:
            strata[u["status"]].append(u["unit_id"])
        else:
            raise ValueError("Unknown sampling status")
    counts = {s: min(len(v), capacity // 2) for s, v in strata.items()}
    while sum(counts.values()) < capacity:
        available = [s for s in strata if counts[s] < len(strata[s])]
        if not available:
            break
        counts[available[0]] += 1
    selected = []
    for s, values in strata.items():
        # Stable under input ordering; independent pseudorandom stream per stratum.
        rng = random.Random(f"{seed}:{s}")
        for unit in sorted(rng.sample(sorted(values), counts[s])):
            selected.append(dict(unit_id=unit, stratum=s,
                                 inclusion_probability=counts[s] / len(values),
                                 outcome=None, reference_ref=None))
    warnings = [f"No {s} units: this cohort cannot compare flagged and unflagged outcomes"
                for s, values in strata.items() if not values]
    if not selected:
        warnings.append("No eligible units available for evidence-based sampling")
    return dict(schema_version="vantage-sampling-1", seed=seed, capacity=capacity,
                warnings=warnings,
                population_counts={s: len(v) for s, v in strata.items()},
                selected=selected, unavailable_units=sorted(excluded),
                limitation="Freeze before visits. Missing coverage is not a negative outcome. "
                           "Keep model scores hidden from outcome adjudicators where feasible.")


def evaluate_capacity(rows, capacity, seed=42, bootstrap_replicates=2000):
    """Paired model/baseline comparison on a fully verified frozen cohort.

    Partial outcome cohorts are rejected: precision at capacity cannot be
    estimated by silently treating unvisited units as negative. Scores must be
    frozen before outcomes and originate from held-out predictions.
    """
    if type(capacity) is not int or not 1 <= capacity <= len(rows):
        raise ValueError("Capacity must be between one and cohort size")
    if type(bootstrap_replicates) is not int or bootstrap_replicates < 100:
        raise ValueError("At least 100 bootstrap replicates required")
    ids = [r["sample_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate samples")
    for r in rows:
        if r.get("independently_verified") is not True or not r.get("reference_ref"):
            raise ValueError("Every cohort outcome requires independent verification and reference")
        if r.get("outcome") not in ("useful_finding", "no_useful_finding"):
            raise ValueError("Complete binary field outcomes required; no missing-outcome imputation")
        if r.get("held_out") is not True or not r.get("cohort_id") or not r.get("spatial_group"):
            raise ValueError("Held-out cohort and spatial group required")
        if not (_date(r["observed_at"]) >= _date(r["prediction_frozen_at"]) >= _date(r["acquired_at"])):
            raise ValueError("Prediction must follow acquisition and precede field outcome")
        for key in ("model_score", "baseline_score"):
            value = r.get(key)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError("Finite model and baseline scores required; higher means earlier visit")
    if len({r["cohort_id"] for r in rows}) != 1:
        raise ValueError("Evaluate one frozen decision cohort at a time")

    def precision(data, key, k):
        ordered = sorted(data, key=lambda r: (-r[key], r["sample_id"]))[:k]
        return sum(r["outcome"] == "useful_finding" for r in ordered) / k

    model = precision(rows, "model_score", capacity)
    baseline = precision(rows, "baseline_score", capacity)
    positives = sum(r["outcome"] == "useful_finding" for r in rows)
    groups = sorted({r["spatial_group"] for r in rows})
    interval = None
    # Three groups is a software gate, not assurance of adequate statistical power.
    if len(groups) >= 3:
        rng = random.Random(seed)
        grouped = {g: [r for r in rows if r["spatial_group"] == g] for g in groups}
        differences = []
        for _ in range(bootstrap_replicates):
            sample = [r for g in rng.choices(groups, k=len(groups)) for r in grouped[g]]
            k = min(capacity, len(sample))
            differences.append(precision(sample, "model_score", k) - precision(sample, "baseline_score", k))
        differences.sort()
        interval = [differences[int(.025 * (len(differences) - 1))],
                    differences[int(.975 * (len(differences) - 1))]]
    return dict(schema_version="vantage-capacity-evaluation-1", cohort_id=rows[0]["cohort_id"],
                cohort_size=len(rows), capacity=capacity, independent_spatial_groups=len(groups),
                model_precision_at_capacity=model, baseline_precision_at_capacity=baseline,
                precision_difference=model-baseline,
                model_recall_at_capacity=model*capacity/positives if positives else None,
                expected_random_precision=positives/len(rows),
                paired_cluster_bootstrap_95_interval=interval,
                bootstrap_seed=seed, bootstrap_replicates=bootstrap_replicates if interval else 0,
                cohort_sha256=hashlib.sha256(json.dumps(sorted(rows, key=lambda r:r["sample_id"]),
                    sort_keys=True, allow_nan=False).encode()).hexdigest(),
                limitation="Descriptive held-out comparison, not causal impact. Cluster intervals are exploratory; "
                           "few groups, repeated visits, unverified declarations or selection bias invalidate broad claims. "
                           "No interval with fewer than three groups. Full cohort outcomes required; "
                           "a stratified partial sampling plan cannot be evaluated by this complete-cohort estimator.")
