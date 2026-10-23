"""Small causal residual-regression benchmark; no operational reconstruction."""
from datetime import datetime
import numpy as np


def causal_samples(series, max_age_days=7, transferred_masks=True, isolated_gaps=False):
    if not 0 < max_age_days <= 31:
        raise ValueError("Bounded positive source age required")
    ordered=sorted(series,key=lambda r:datetime.fromisoformat(r["acquired_at"].replace("Z","+00:00")))
    if not ordered:return []
    shape=ordered[0]["ndvi"].shape
    last=np.full(shape,np.nan)
    times=np.full(shape,np.nan)
    previous=None
    seen=set()
    samples=[]
    for row in ordered:
        stamp=datetime.fromisoformat(row["acquired_at"].replace("Z","+00:00"))
        if stamp.tzinfo is None or stamp in seen or row["ndvi"].shape!=shape:
            raise ValueError("Unique dated observations on identical grids required")
        seen.add(stamp)
        now=stamp.timestamp()/86400
        target=row["ndvi"]
        clear=np.isfinite(target)
        hidden=(clear & ~np.isfinite(previous) if previous is not None else np.zeros(shape,dtype=bool)) if transferred_masks else clear
        ages=now-times
        eligible=hidden & np.isfinite(last) & (ages>0) & (ages<=max_age_days)
        x=last[eligible]
        age=ages[eligible]/7
        features=np.column_stack([np.ones(x.size),x,age,x*age,x*x])
        samples.append(dict(acquired_at=row["acquired_at"],features=features,
            target=target[eligible].astype(float),persistence=x,
            hidden_pixels=int(hidden.sum()),
            unsupported_no_prior=int((hidden & ~np.isfinite(last)).sum()),
            unsupported_expired_prior=int((hidden & np.isfinite(last) & (ages>max_age_days)).sum()),
            source_age_days=ages[eligible],
            protocol="isolated_transferred_gap" if isolated_gaps else (
                "sequential_transferred_gaps" if transferred_masks else "clear_transitions")))
        # In isolated experiments each target is a separate intervention. The
        # next experiment can use this date's original observations as history,
        # but this target is never used to predict itself.
        observed=clear if isolated_gaps or not transferred_masks else clear & ~hidden
        last[observed]=target[observed]
        times[observed]=now
        previous=target
    return samples


def fit_residual(samples, per_date_limit=10000):
    matrices=[]
    residuals=[]
    for sample in samples:
        n=len(sample["target"])
        if not n:continue
        indices=np.random.default_rng(20261023).choice(n,min(n,per_date_limit),replace=False)
        matrices.append(sample["features"][indices])
        residuals.append((sample["target"]-sample["persistence"])[indices])
    if not matrices:raise ValueError("No causal training samples")
    x=np.concatenate(matrices)
    y=np.concatenate(residuals)
    # Fixed regularization, selected before validation/test inspection.
    coefficients=np.linalg.solve(x.T@x+np.eye(x.shape[1]),x.T@y)
    return dict(coefficients=coefficients.tolist(),training_samples=len(y),
                training_target_dates=len(matrices),ridge_penalty=1,
                features=["intercept","prior_ndvi","age_div_7","prior_ndvi_times_age","prior_ndvi_squared"])


def score_samples(samples, model):
    results=[]
    coefficients=np.asarray(model["coefficients"])
    for sample in samples:
        target=sample["target"]
        n=len(target)
        prediction=np.clip(sample["persistence"]+sample["features"]@coefficients,-1,1)
        def metrics(values):
            error=values-target
            return dict(mae=float(np.abs(error).mean()) if n else None,
                        bias=float(error.mean()) if n else None,
                        p90_absolute_error=float(np.percentile(np.abs(error),90)) if n else None)
        results.append(dict(acquired_at=sample["acquired_at"],hidden_pixels=sample["hidden_pixels"],
            predicted_pixels=n,prediction_coverage=n/sample["hidden_pixels"] if sample["hidden_pixels"] else None,
            unsupported_no_prior=sample.get("unsupported_no_prior",0),
            unsupported_expired_prior=sample.get("unsupported_expired_prior",0),
            source_age_median_days=float(np.median(sample["source_age_days"])) if n else None,
            learned=metrics(prediction),persistence=metrics(sample["persistence"])))
    total=sum(r["predicted_pixels"] for r in results)
    hidden=sum(r["hidden_pixels"] for r in results)
    return dict(dates=results,predicted_pixel_date_pairs=total,hidden_pixel_date_pairs=hidden,
        unsupported_no_prior=sum(r["unsupported_no_prior"] for r in results),
        unsupported_expired_prior=sum(r["unsupported_expired_prior"] for r in results),
        prediction_coverage=total/hidden if hidden else None,
        learned_mae=sum(r["learned"]["mae"]*r["predicted_pixels"] for r in results if r["predicted_pixels"])/total if total else None,
        persistence_mae=sum(r["persistence"]["mae"]*r["predicted_pixels"] for r in results if r["predicted_pixels"])/total if total else None)
