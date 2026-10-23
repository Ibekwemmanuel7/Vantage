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
