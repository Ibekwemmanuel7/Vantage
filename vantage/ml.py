"""Versioned features and guarded ML experiments. Demonstration flags are never labels."""
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import math
from pathlib import Path
import statistics

import numpy as np

from .core import instant
from .imagery import FEATURES, stable_hash,atomic_text
from .area import units


def build_features(manifest, observations, rainfall):
    """One area/season sample, retaining excluded samples and their reasons."""
    groups = defaultdict(list)
    for row in observations:
        if row["dataset_id"] != manifest["dataset_id"]:
            raise ValueError("Dataset linkage mismatch")
        groups[(row["unit_id"],row["year"])].append(row)
    geometry_by_unit={u["id"]:u["geometry"] for u in units(manifest["recipe"]["config"])}
    slots=[(unit,year) for unit in sorted(geometry_by_unit) for year in manifest["reference_years"]+[manifest["target_year"]]]
    output=[]
    for unit,year in slots:
        rows=groups.get((unit,year),[])
        good=[r for r in rows if r["usable_fraction"] >= manifest["quality_policy"]["min_usable_fraction"]
              and r["valid_pixels"] >= manifest["quality_policy"]["min_valid_pixels"]
              and all(r[k] is not None and np.isfinite(r[k]) for k in FEATURES[:-1])]
        rain=[r for r in rainfall if r["unit_id"]==unit and r["year"]==year]
        reasons=[]
        if not rows:reasons.append("no_acquisition")
        if not good: reasons.append("insufficient_vegetation_coverage")
        if len(rain)!=1: reasons.append("missing_or_duplicate_rainfall")
        cutoff=instant(manifest["decision_cutoff"])
        if good and any(instant(r["acquired_at"])>cutoff for r in good): reasons.append("future_acquisition")
        if year==manifest["target_year"] and good and (cutoff-instant(max(r["acquired_at"] for r in good))).total_seconds()/86400>manifest["quality_policy"].get("freshness_days",14):
            reasons.append("stale_vegetation")
        if rain and instant(rain[0]["end"]+"T23:59:59Z")>cutoff: reasons.append("future_rainfall")
        values={key:statistics.median(r[key] for r in good) if good else None for key in FEATURES[:-1]}
        values["rainfall_mm"]=rain[0]["mm"] if len(rain)==1 else None
        west,south,east,north=manifest["bbox"]
        group=f'geoblock-{math.floor((west+east)/2)}-{math.floor((south+north)/2)}'
        output.append(dict(sample_id=stable_hash([manifest["dataset_id"],unit,year,"season-v1"])[:24],
            dataset_id=manifest["dataset_id"],profile_id=manifest["profile_id"],unit_id=unit,year=year,
            spatial_group=group,geometry=geometry_by_unit[unit],eligible=not reasons,exclusion_reasons=reasons,
            acquired_at=max(r["acquired_at"] for r in rows) if rows else None,
            accepted_dates=sorted(r["acquired_at"] for r in good),
            input_scene_ids=sorted(r["source_id"] for r in rows),
            accepted_scene_ids=sorted(r["source_id"] for r in good),
            usable_fraction=statistics.median(r["usable_fraction"] for r in good) if good else 0,
            reference_or_target="target" if year==manifest["target_year"] else "reference",
            n_dates=len(rows),n_accepted_dates=len(good),features=values))
    return output


def labels_template(rows):
    fields=["sample_id","dataset_id","unit_id","year","spatial_group","split","outcome",
            "label_kind","independently_verified","observed_at","reference_ref","sampling_method"]
    stream=io.StringIO(newline="")
    writer=csv.DictWriter(stream,fieldnames=fields,extrasaction="ignore",lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({**r,"split":"","outcome":"","label_kind":"","independently_verified":"false"})
    return stream.getvalue()


def publish_label_template(rows,local_path,public_path):
    """Never overwrite annotations or publish an independently filled label file."""
    blank=labels_template(rows)
    local_path=Path(local_path)
    preserve=False
    if local_path.exists():
        with local_path.open(encoding="utf-8-sig",newline="") as stream:
            existing=list(csv.DictReader(stream))
        preserve=any(any(r.get(k,"").strip() for k in ("outcome","split","label_kind","observed_at","reference_ref","sampling_method"))
                     or r.get("independently_verified","").lower() not in ("","false") for r in existing)
    if not preserve:atomic_text(local_path,blank)
    atomic_text(public_path,blank)
    return "Existing annotations preserved; public template is newly generated and blank" if preserve else "Blank independent-label template generated"


def feature_matrix(rows):
    array=np.array([[r["features"][key] for key in FEATURES] for r in rows],dtype=float)
    if array.ndim!=2 or array.shape[1]!=len(FEATURES) or not np.isfinite(array).all():
        raise ValueError("Complete finite feature rows are required; quality gaps cannot be imputed")
    return array


def novelty_experiment(rows,target_year,seed=42):
    from sklearn.ensemble import IsolationForest
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import RobustScaler
    train=[r for r in rows if r["eligible"] and r["year"]<target_year]
    test=[r for r in rows if r["eligible"] and r["year"]==target_year]
    report=dict(schema_version="ml-experiment-1",model="RobustScaler + IsolationForest",mode="exploratory_unsupervised",
         seed=seed,features=FEATURES,training_samples=len(train),target_samples=len(test),
         training_years=sorted({r["year"] for r in train}),target_year=target_year,
         independent_spatial_groups=len({r["spatial_group"] for r in train}),
         dataset_ids=sorted({r["dataset_id"] for r in rows}),ground_truth_labels=0,
         accuracy=None,precision=None,recall=None,
         limitation="Small correlated retrospective dataset. Novelty is not confirmed crop damage or useful-finding probability. No independent spatial or field validation.",
         predictions=[])
    if len(train)<8 or len({r["year"] for r in train})<3:
        report.update(status="insufficient_training_data",model_trained=False)
        return report,None
    model=make_pipeline(RobustScaler(),IsolationForest(n_estimators=256,max_samples="auto",contamination="auto",random_state=seed,n_jobs=1))
    x=feature_matrix(train)
    model.fit(x)
    median=np.median(x,axis=0)
    spread=np.percentile(x,75,axis=0)-np.percentile(x,25,axis=0)
    spread=np.where(spread>1e-8,spread,1.)
    for r in rows:
        if r["year"]!=target_year: continue
        p=dict(sample_id=r["sample_id"],unit_id=r["unit_id"],status="unavailable",
               reasons=r["exclusion_reasons"],decision_score=None,feature_context=[])
        if r["eligible"]:
            vector=feature_matrix([r])
            score=float(model.decision_function(vector)[0])
            distances=np.abs((vector[0]-median)/spread)
            p.update(status="novelty_candidate" if score<0 else "within_reference_envelope",decision_score=score,
                 reasons=["Uncalibrated Isolation Forest decision boundary; research review only."],
                 feature_context=[dict(feature=FEATURES[i],observed=float(vector[0,i]),training_median=float(median[i]),
                     interpretation="Descriptive feature difference, not causal attribution") for i in np.argsort(-distances)[:3]])
        report["predictions"].append(p)
    report.update(status="trained_exploratory_only",model_trained=True,
        native_boundary="scikit-learn contamination=auto (decision_function < 0); not an agronomic threshold",
        preprocessing_fit="Earlier-year training rows only; target-year values never used in fit")
    return report,model


def validate_labels(rows,labels):
    """Return admissible independent outcomes and explicit release-gate failures."""
    index={r["sample_id"]:r for r in rows}
    accepted=[]; errors=[]; seen=set()
    for label in labels:
        if not label.get("outcome","").strip(): continue
        sid=label.get("sample_id")
        if sid not in index or sid in seen:
            errors.append("Unknown or duplicate labeled sample");continue
        seen.add(sid)
        row=index[sid]
        if label.get("dataset_id")!=row["dataset_id"]:
            errors.append("Label dataset mismatch");continue
        if not row["eligible"]:
            errors.append("A quality-excluded sample cannot become a training example");continue
        if label.get("outcome") not in ("useful_finding","no_useful_finding") or label.get("split") not in ("train","validation","test"):
            errors.append("Unsupported independent outcome or split");continue
        if label.get("label_kind")!="field_visit" or label.get("independently_verified","").lower()!="true" or not label.get("reference_ref","").strip():
            errors.append("Independent field-visit verification required; demo/weak labels are not accepted");continue
        if label.get("sampling_method") not in ("flagged","presampled_unflagged","routine"):
            errors.append("Field-check sampling method is required");continue
        try:
            observed=instant(label["observed_at"])
            latest=instant(row["acquired_at"])
            if not latest<=observed<=latest+timedelta(days=21) or observed>datetime.now(timezone.utc):
                raise ValueError()
        except (KeyError,ValueError):
            errors.append("Independent finding must be dated within the 21-day research follow-up window");continue
        accepted.append((row,label))
    partitions={split:[(r,l) for r,l in accepted if l["split"]==split] for split in ("train","validation","test")}
    minimum={"train":20,"validation":10,"test":10}
    for split,pairs in partitions.items():
        if len(pairs)<minimum[split]: errors.append(f"{split} requires at least {minimum[split]} independently labeled usable samples (engineering gate, not a power calculation)")
        if len({l["outcome"] for _,l in pairs})<2: errors.append(f"{split} requires both outcome classes")
        if split=="train" and pairs and min(Counter(l["outcome"] for _,l in pairs).get(c,0) for c in ("useful_finding","no_useful_finding"))<5:
            errors.append("Training requires at least five verified examples in each outcome class (engineering gate)")
        if split in ("validation","test") and pairs and not any(l["sampling_method"] in ("presampled_unflagged","routine") for _,l in pairs):
            errors.append(f"{split} needs independent comparison checks, not only inspected flags")
    groups={s:{r["spatial_group"] for r,_ in pairs} for s,pairs in partitions.items()}
    if len(groups["train"])<3: errors.append("At least three training spatial groups are required")
    for a,b in (("train","validation"),("train","test"),("validation","test")):
        if groups[a]&groups[b]: errors.append(f"Spatial group leakage between {a} and {b}")
    if all(partitions.values()):
        if max(r["year"] for r,_ in partitions["train"])>=min(r["year"] for r,_ in partitions["validation"]) or max(r["year"] for r,_ in partitions["validation"])>=min(r["year"] for r,_ in partitions["test"]):
            errors.append("Strict earlier-train, later-validation, latest-test chronology required")
        # Add geographic separation, independent of label-provided group names.
        def bbox(r):
            pts=r["geometry"]["coordinates"][0]
            return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)
        for a,b in (("train","validation"),("train","test"),("validation","test")):
            close=False
            for ra,_ in partitions[a]:
                aa=bbox(ra)
                for rb,_ in partitions[b]:
                    bb=bbox(rb)
                    if bbox_distance_m(aa,bb)<10000: close=True
            if close: errors.append(f"Overlapping or neighboring geometry across {a}/{b}; research buffer is 10 km")
    return partitions,sorted(set(errors))


def bbox_distance_m(a,b):
    """Regional bounding-box separation on a mean-radius sphere, in meters.

    Bounding boxes conservatively enclose the study polygons. This screening
    buffer is not a parcel survey or a replacement for full spatial cohort QA.
    """
    if a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]:return 0.
    def haversine(p,q):
        x1,y1,x2,y2=map(math.radians,(*p,*q))
        value=math.sin((y2-y1)/2)**2+math.cos(y1)*math.cos(y2)*math.sin((x2-x1)/2)**2
        return 2*6371008.8*math.asin(math.sqrt(min(1.,value)))
    distances=[]
    for first,second in ((a,b),(b,a)):
        for x in (first[0],first[2]):
            for y in (first[1],first[3]):
                q=(min(second[2],max(second[0],x)),min(second[3],max(second[1],y)))
                distances.append(haversine((x,y),q))
    return min(distances)


def supervised_experiment(rows,labels,seed=42):
    partitions,errors=validate_labels(rows,labels)
    report=dict(schema_version="ml-experiment-1",mode="supervised_research",features=FEATURES,seed=seed,
        admitted_label_counts={s:len(p) for s,p in partitions.items()},status="insufficient_independent_labels",
        model_trained=False,gates=errors,
        limitation="Minimum counts and buffers are engineering gates, not statistical validation. Retrospective results do not establish prospective scouting value.")
    if errors:return report,None
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import RobustScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score,balanced_accuracy_score,f1_score,precision_score,recall_score,roc_auc_score
    xs={s:feature_matrix([r for r,_ in pairs]) for s,pairs in partitions.items()}
    ys={s:np.array([int(l["outcome"]=="useful_finding") for _,l in pairs]) for s,pairs in partitions.items()}
    model=make_pipeline(RobustScaler(),LogisticRegression(class_weight="balanced",random_state=seed,max_iter=2000))
    model.fit(xs["train"],ys["train"])
    val=model.predict_proba(xs["validation"])[:,1]
    thresholds=np.arange(.1,.91,.05)
    threshold=float(max(thresholds,key=lambda t:(f1_score(ys["validation"],val>=t,zero_division=0),-abs(t-.5))))
    score=model.predict_proba(xs["test"])[:,1]
    prediction=score>=threshold
    report.update(status="trained_research_only",model_trained=True,model="RobustScaler + class-weighted LogisticRegression",
         validation_selected_threshold=threshold,test_samples=len(score),
         test_metrics=dict(average_precision=float(average_precision_score(ys["test"],score)),
             roc_auc=float(roc_auc_score(ys["test"],score)),balanced_accuracy=float(balanced_accuracy_score(ys["test"],prediction)),
             precision=float(precision_score(ys["test"],prediction,zero_division=0)),recall=float(recall_score(ys["test"],prediction,zero_division=0)),
             prevalence_baseline_average_precision=float(ys["test"].mean())),
         confidence_intervals=None,uncertainty="Cluster-aware uncertainty and prospective evaluation remain required",
         probabilities_calibrated=False,
         split_ids={s:[r["sample_id"] for r,_ in pairs] for s,pairs in partitions.items()})
    return report,model
