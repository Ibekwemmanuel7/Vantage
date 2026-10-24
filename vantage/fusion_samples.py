"""Radar-only features and separately masked observed optical references."""
import numpy as np
from vantage.radar_values import decibels

FEATURES=["vv_db","vh_db","vh_minus_vv_db","approximate_local_incidence_degrees","radar_age_days"]
UNITS=["dB","dB","dB","degrees","days"]


def make_sample(power,support,local_angles,local_classes,visibility_classes,slope_classes,
                ndvi,optical_valid,radar_age_days,minimum_support=.8):
    if not np.isfinite(radar_age_days) or not 0<=radar_age_days<=7:
        raise ValueError("Causal radar age must be 0-7 days")
    if not 0<minimum_support<=1:raise ValueError("Invalid native support threshold")
    shape=ndvi.shape
    if ndvi.ndim!=2 or power.shape!=(2,)+shape or support.shape!=power.shape or local_angles.shape!=(3,)+shape:
        raise ValueError("Exactly aligned radar/angle/optical arrays required")
    if any(a.shape!=shape for a in [local_classes,visibility_classes,slope_classes,optical_valid]):
        raise ValueError("Mask shape differs")
    if optical_valid.dtype.kind!="b" or not np.array_equal(optical_valid,np.isfinite(ndvi)):
        raise ValueError("Observed optical mask must equal finite NDVI support")
    if not np.isin(local_classes,range(5)).all() or not np.isin(visibility_classes,range(4)).all() or not np.isin(slope_classes,range(3)).all():
        raise ValueError("Unrecognized quality classes")
    if ((ndvi[optical_valid]<-1)|(ndvi[optical_valid]>1)).any():raise ValueError("Invalid observed NDVI")
    angle=local_angles[1]
    valid=(np.isfinite(power)&(power>0)&np.isfinite(support)&(support>=minimum_support)).all(axis=0)
    valid&=(local_classes==1)&(visibility_classes==1)&(slope_classes==1)&np.isfinite(angle)&(angle>=5)&(angle<=85)
    db=decibels(power)
    features=np.stack([db[0],db[1],db[1]-db[0],angle,np.full(shape,radar_age_days,dtype="float32")]).astype("float32")
    valid&=np.isfinite(features).all(axis=0)&(support<=1).all(axis=0)
    features[:,~valid]=np.nan
    target_valid=valid&optical_valid
    return dict(features=features,feature_valid=valid,
        target_ndvi=np.where(target_valid,ndvi,np.nan).astype("float32"),target_valid=target_valid,
        observed_optical_valid=optical_valid.copy(),gap_candidate=valid&~optical_valid,
        local_quality_classes=local_classes.copy(),visibility_classes=visibility_classes.copy(),
        slope_proxy_classes=slope_classes.copy(),radar_native_support=support.astype("float32"))
