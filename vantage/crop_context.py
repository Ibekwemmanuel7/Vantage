"""Historical land-cover context, never current crop truth or a field diagnosis."""
import numpy as np
from .multispectral import spectral_features

KNOWN_CLASSES=(10,20,30,40,50,60,70,80,90,95,100)


def landcover_masks(classes):
    if classes.ndim!=2:
        raise ValueError("Two-dimensional categorical land-cover grid required")
    known=np.isin(classes,KNOWN_CLASSES)
    return (classes==40)&known,known


def crop_evidence(cube,common_valid,classes,min_fraction=.6,min_pixels=100):
    if not 0<=min_fraction<=1 or type(min_pixels) is not int or min_pixels<1:
        raise ValueError("Invalid research coverage policy")
    if cube.shape!=(6,*classes.shape) or common_valid.shape!=classes.shape:
        raise ValueError("Exact aligned six-band and land-cover grids required")
    if not np.array_equal(np.isfinite(cube).all(axis=0),common_valid):
        raise ValueError("Common validity must match finite measurements")
    crop,known=landcover_masks(classes)
    valid=crop&common_valid
    count=int(crop.sum());usable=int(valid.sum())
    fraction=usable/count if count else None
    reasons=[]
    if not count:reasons.append("no_historical_cropland_pixels")
    if usable<min_pixels:reasons.append("insufficient_valid_historical_cropland_pixels")
    if fraction is not None and fraction<min_fraction:reasons.append("insufficient_historical_cropland_coverage")
    return dict(historical_cropland_pixels=count,valid_historical_cropland_pixels=usable,
        known_landcover_pixels=int(known.sum()),total_pixels=int(classes.size),
        historical_cropland_fraction=count/int(classes.size),crop_usable_fraction=fraction,
        evidence_status="insufficient_coverage" if reasons else "sufficient_coverage_for_research",
        exclusion_reasons=reasons,features=spectral_features(cube,valid) if not reasons else None,
        current_crop_confirmed=False,crop_stage_confirmed=False,agronomic_review_eligible=False,
        interpretation="Historical 2021 mapped cropland only. Crop identity, current cultivation and field outcomes unconfirmed.")
