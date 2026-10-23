"""Causal persistence benchmark on withheld clear pixels; no operational infill."""
from datetime import datetime
import numpy as np


def evaluate_persistence(series, max_age_days=7):
    if not 0 < max_age_days <= 31:
        raise ValueError("Bounded positive gap age required")
    ordered = sorted(series, key=lambda r:r["acquired_at"])
    if not ordered:
        return []
    shape = ordered[0]["ndvi"].shape
    prediction = np.full(shape,np.nan)
    source_time = np.full(shape,np.nan)
    seen = set()
    results = []
    for row in ordered:
        stamp = datetime.fromisoformat(row["acquired_at"].replace("Z","+00:00"))
        if stamp.tzinfo is None or stamp in seen or row["ndvi"].shape != shape:
            raise ValueError("Unique timezone-aware dates on an identical grid required")
        seen.add(stamp)
        now = stamp.timestamp()/86400
        target = row["ndvi"]
        clear = np.isfinite(target)
        scored = clear & np.isfinite(prediction) & ((now-source_time) <= max_age_days)
        errors = prediction[scored]-target[scored]
        results.append(dict(acquired_at=row["acquired_at"], clear_target_pixels=int(clear.sum()),
            evaluated_pixels=int(scored.sum()),
            mae=float(np.mean(np.abs(errors))) if errors.size else None,
            bias=float(np.mean(errors)) if errors.size else None,
            max_source_age_days=max_age_days,
            interpretation="Withheld clear-pixel persistence test, not accuracy beneath actual clouds"))
        # Update only after scoring, preventing same-date target leakage.
        prediction[clear] = target[clear]
        source_time[clear] = now
    return results


def evaluate_masked_persistence(series, max_age_days=7):
    """Transfer the previous acquisition's rejection footprint onto clear targets.

    Mask donors and prediction sources must precede targets. Rejected pixels can
    represent cloud, shadow or other quality exclusions; this is not cloud truth.
    """
    if not 0 < max_age_days <= 31:
        raise ValueError("Bounded positive gap age required")
    def stamp(row):
        value = datetime.fromisoformat(row["acquired_at"].replace("Z", "+00:00"))
        if value.tzinfo is None:
            raise ValueError("Timezone-aware acquisition required")
        return value
    ordered = sorted(series,key=stamp)
    if not ordered:
        return []
    shape = ordered[0]["ndvi"].shape
    prediction = np.full(shape,np.nan)
    source_time = np.full(shape,np.nan)
    previous = None
    seen = set()
    results = []
    for row in ordered:
        date = stamp(row)
        if date in seen or row["ndvi"].shape != shape:
            raise ValueError("Unique dates and identical grids required")
        seen.add(date)
        now = date.timestamp()/86400
        target = row["ndvi"]
        clear = np.isfinite(target)
        hidden = clear & ~np.isfinite(previous["ndvi"]) if previous is not None else np.zeros(shape,dtype=bool)
        scored = hidden & np.isfinite(prediction) & ((now-source_time) <= max_age_days)
        errors = prediction[scored]-target[scored]
        n = int(hidden.sum())
        results.append(dict(acquired_at=row["acquired_at"],
            mask_source_acquisition=previous["acquired_at"] if previous else None,
            hidden_clear_target_pixels=n, predicted_pixels=int(scored.sum()),
            prediction_coverage=float(scored.sum()/n) if n else None,
            mae=float(np.abs(errors).mean()) if errors.size else None,
            bias=float(errors.mean()) if errors.size else None,
            p90_absolute_error=float(np.percentile(np.abs(errors),90)) if errors.size else None,
            large_error_fraction=float((np.abs(errors)>.1).mean()) if errors.size else None,
            max_source_age_days=max_age_days,
            status="evaluated" if errors.size else "withheld_no_supported_predictions"))
        # Simulated hidden values cannot refresh prediction history.
        observed = clear & ~hidden
        prediction[observed] = target[observed]
        source_time[observed] = now
        previous = row
    return results
