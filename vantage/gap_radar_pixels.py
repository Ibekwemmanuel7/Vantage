"""Provider raster metadata checks and whole-box numeric summaries."""
import numpy as np
from vantage.radar_values import decibels


def fixed_track_candidates(candidates,plan):
    if type(plan["max_passes"]) is not int or not 1<=plan["max_passes"]<=3:
        raise ValueError("Fixed budget of one to three passes required")
    selected=[r for r in candidates if r["track_id"]==plan["track_id"]]
    if not 1<=len(selected)<=plan["max_passes"]:
        raise ValueError("Fixed track cohort exceeds budget or is empty")
    if len({r["item_id"] for r in selected})!=len(selected):raise ValueError("Duplicate radar identity")
    return sorted(selected,key=lambda r:r["acquired_at"])


def validate_asset(asset):
    bands=asset.get("raster:bands",[])
    if len(bands)!=1 or bands[0].get("nodata")!=-32768 or bands[0].get("data_type")!="float32":
        raise ValueError("Unsupported RTC raster band contract")
    if bands[0].get("scale",1)!=1 or bands[0].get("offset",0)!=0:
        raise ValueError("Unimplemented RTC scale/offset")
    if "gamma naught" not in asset.get("description","").lower():
        raise ValueError("Expected provider gamma-naught metadata")


def whole_box_summary(power,support,minimum_support=.8):
    if power.ndim!=3 or power.shape[0]!=2 or power.shape!=support.shape:
        raise ValueError("Exactly aligned VV/VH power and support required")
    if not 0<minimum_support<=1:raise ValueError("Invalid support threshold")
    valid=np.isfinite(power).all(axis=0)&(power>0).all(axis=0)&(support>=minimum_support).all(axis=0)
    db=decibels(np.where(valid[None,...],power,np.nan))
    return dict(analysis_pixels=int(valid.size),numeric_pixels=int(valid.sum()),
        numeric_fraction=float(valid.mean()),
        vv_db_median=float(np.median(db[0][valid])) if valid.any() else None,
        vh_db_median=float(np.median(db[1][valid])) if valid.any() else None,
        terrain_screen_verified=False,usable_agricultural_evidence=False,
        spatial_scope="Whole optical study grid, not crop-masked or confirmed fields")


def slope_screen_summary(classes,numeric_mask):
    if classes.shape!=numeric_mask.shape or numeric_mask.dtype.kind!="b" or not np.isin(classes,[0,1,2]).all():
        raise ValueError("Aligned slope classes and Boolean numerical support required")
    counts={name:int((classes==value).sum()) for value,name in [(0,"unknown"),(1,"lower_slope"),(2,"elevated_slope")]}
    return dict(whole_box_pixels=int(classes.size),class_counts=counts,
        numeric_pixels_before=int(numeric_mask.sum()),
        numeric_lower_slope_pixels=int((numeric_mask & (classes==1)).sum()),
        terrain_screen_verified=False,radar_illumination_confirmed=False,
        usable_agricultural_evidence=False)
