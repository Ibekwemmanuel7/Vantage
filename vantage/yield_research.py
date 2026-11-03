"""Isolated retrospective survey benchmark; never admits operational field labels."""
import csv
import hashlib
import io
from collections import Counter
import numpy as np
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ['elev','twi','soil_rzpawhc','soil_clay','soil_pH','soil_orgC','soil_ECEC']


def load_cohort(raw, plan):
    if len(raw)>10_000_000 or hashlib.sha256(raw).hexdigest()!=plan['source_sha256']:
        raise ValueError('Pinned bounded source required')
    if plan['features']!=FEATURES or plan['target']!='yield_kg_ha':
        raise ValueError('Only static feature allowlist and declared yield target supported')
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if not set(FEATURES+['iso','country','lon','lat','year','disease','pest','striga','water_excess','yield_kg_ha']).issubset(reader.fieldnames or []):
        raise ValueError('Required survey columns missing')
    cohort=[]
    for index,row in enumerate(reader):
        if index>=100_000 or None in row or any(v is None for v in row.values()): raise ValueError('Malformed or oversized table')
        if row['iso']!='UGA' and row['country'].casefold()!='uganda': continue
        if row['iso']!='UGA' or row['country'].casefold()!='uganda' or row['year']!='2020': raise ValueError('Cohort identity changed')
        x=[float(row[k]) if row[k].strip() else np.nan for k in FEATURES]
        y=float(row['yield_kg_ha']);xy=[float(row['lon']),float(row['lat'])]
        if not np.isfinite(y) or y<0 or not np.isfinite(xy).all() or not (29<=xy[0]<=36 and -2<=xy[1]<=5) or np.isinf(x).any():
            raise ValueError('Invalid yield, coordinates or features')
        cohort.append(dict(source_row=index,x=x,y=y,xy=xy,labels={k:row[k] for k in ('disease','pest','striga','water_excess')}))
    if len(cohort)!=109: raise ValueError('Expected pinned 109-row Uganda cohort')
    return cohort


def buffered_splits(xy, folds=5, cell=.1, buffer_km=5, minimum=30):
    xy=np.asarray(xy,dtype=float)
    if xy.ndim!=2 or xy.shape[1]!=2 or not np.isfinite(xy).all() or folds<2 or cell<=0 or buffer_km<0 or minimum<2:
        raise ValueError('Valid bounded split parameters required')
    groups=np.array([f'{a}:{b}' for a,b in np.floor(xy/cell).astype(int)])
    if len(set(groups))<folds: raise ValueError('Insufficient geographic groups')
    lon,lat=np.deg2rad(xy).T
    result=[]
    for train,test in GroupKFold(n_splits=folds).split(xy,groups=groups):
        delta_lat=lat[train,None]-lat[test][None,:];delta_lon=lon[train,None]-lon[test][None,:]
        a=np.sin(delta_lat/2)**2+np.cos(lat[train,None])*np.cos(lat[test][None,:])*np.sin(delta_lon/2)**2
        distances=6371.0088*2*np.arcsin(np.sqrt(np.clip(a,0,1)))
        keep=distances.min(axis=1)>=buffer_km
        selected=train[keep]
        if len(selected)<minimum: raise ValueError('Buffer leaves too few training rows; no silent fold skipping')
        result.append((selected,test,dict(train_rows=len(selected),test_rows=len(test),buffer_removed=int((~keep).sum()),
                                        minimum_reported_coordinate_distance_km=float(distances[keep].min()),
                                        disjoint_group_ids=not bool(set(groups[selected])&set(groups[test])))))
    return result


def metrics(y,pred):
    return dict(mae_kg_ha=float(mean_absolute_error(y,pred)),rmse_kg_ha=float(np.sqrt(mean_squared_error(y,pred))),
                bias_kg_ha=float(np.mean(pred-y)),r2=float(r2_score(y,pred)) if len(y)>1 and np.var(y)>0 else None)


def experiment(cohort,plan):
    x=np.array([r['x'] for r in cohort]);y=np.array([r['y'] for r in cohort]);xy=np.array([r['xy'] for r in cohort])
    candidates={
        'median':DummyRegressor(strategy='median'),
        'ridge':make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(**plan['models']['ridge'])),
        'random_forest':make_pipeline(SimpleImputer(strategy='median'),RandomForestRegressor(**plan['models']['random_forest'],random_state=plan['random_seed'],n_jobs=1))}
    splits=buffered_splits(xy,plan['folds'],plan['group_cell_degrees'],plan['buffer_km'],plan['minimum_training_rows'])
    predictions={name:np.full(len(y),np.nan) for name in candidates};fold_reports=[]
    for number,(train,test,details) in enumerate(splits):
        scores={}
        for name,candidate in candidates.items():
            fitted=clone(candidate).fit(x[train],y[train]);p=fitted.predict(x[test])
            predictions[name][test]=p;scores[name]=metrics(y[test],p)
        fold_reports.append(dict(fold=number,**details,metrics=scores,
                                 split_sha256=hashlib.sha256(np.array([*train,-1,*test],dtype='<i8').tobytes()).hexdigest()))
    if any(not np.isfinite(p).all() for p in predictions.values()): raise ValueError('Every cohort row must receive held-out predictions')
    pooled={name:metrics(y,p) for name,p in predictions.items()}
    labels={k:dict(Counter(r['labels'][k] or '(missing)' for r in cohort)) for k in ('disease','pest','striga','water_excess')}
    return dict(schema_version='vantage-yield-research-1',task=plan['task'],rows=len(y),features=FEATURES,
                metrics=pooled,folds=fold_reports,label_audit=labels,
                baseline_beaten={name:pooled[name]['mae_kg_ha']<pooled['median']['mae_kg_ha'] for name in ('ridge','random_forest')},
                crop_problem_classifier_fitted=False,satellite_model_fitted=False,forecast_validated=False,
                operational_promotion_allowed=False,independent_prospective_scouting_outcomes=0,
                interpretation='Exploratory cross-validation on reported proxy coordinates, not independent farms or years. Static-context association only; no satellite inputs, causal diagnosis, operational forecast or field-label admission.'), predictions
