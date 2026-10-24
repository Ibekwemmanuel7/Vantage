"""Native-grid rainfall context and common-support optical differences."""
import numpy as np


def rainfall_comparison(months, target_year, baseline_years):
    """Require every month and cell; missing rain is never zero-filled."""
    if target_year in baseline_years or len(set(baseline_years)) != len(baseline_years) or len(baseline_years) < 30:
        raise ValueError('At least 30 distinct baseline years excluding target required')
    expected = {(year, month) for year in [*baseline_years, target_year] for month in (3, 4, 5)}
    if set(months) != expected:
        raise ValueError('Complete exact March-May cohort required')
    for values in months.values():
        array = np.asarray(values, dtype=float)
        if array.shape != (2, 2) or not np.isfinite(array).all() or (array < 0).any():
            raise ValueError('Four finite nonnegative native rainfall cells required')
    totals = {year:sum(np.asarray(months[year, m], dtype=float) for m in (3, 4, 5))
              for year in [*baseline_years, target_year]}
    baseline = np.stack([totals[y] for y in baseline_years]).mean(axis=0)
    target = totals[target_year]
    # Native cells occupy equal longitude width but slightly different area by latitude.
    weights = np.repeat(np.cos(np.deg2rad([2.275, 2.225]))[:, None], 2, axis=1)
    mean = lambda a: float(np.average(a, weights=weights))
    average = mean(baseline)
    difference = target-baseline
    return dict(target_mam_mm=mean(target), baseline_mam_mean_mm=average,
                departure_mm=mean(difference), departure_percent=100*mean(difference)/average if average else None,
                baseline_year_count=len(baseline_years),
                baseline_annual_totals_mm={str(y):mean(totals[y]) for y in baseline_years},
                target_cells_mm=target.tolist(), baseline_cells_mm=baseline.tolist(),
                departure_cells_mm=difference.tolist(),
                scope='Four native 0.05-degree cells; area-weighted study-box context, not field rainfall',
                interpretation='Retrospective CHIRPS v3 difference, not replication of the FEWS NET source-product version or independent rain-gauge validation')


def optical_difference(before, before_valid, after, after_valid, minimum=.7):
    before, after = np.asarray(before), np.asarray(after)
    before_valid, after_valid = np.asarray(before_valid), np.asarray(after_valid)
    if (before.ndim != 2 or before.shape != after.shape or before_valid.shape != before.shape
            or after_valid.shape != after.shape or before_valid.dtype != bool or after_valid.dtype != bool
            or not before.size or before.size > 4_000_000 or not 0 < minimum <= 1):
        raise ValueError('Aligned bounded arrays and boolean quality masks required')
    for values, valid in ((before,before_valid), (after,after_valid)):
        if not np.array_equal(valid, np.isfinite(values)) or np.any(np.abs(values[valid]) > 1):
            raise ValueError('NDVI finite support must exactly match quality mask')
    common = before_valid & after_valid
    difference = np.where(common, after-before, np.nan).astype('float32')
    count = int(common.sum())
    qualified = count >= 9 and count/before.size >= minimum
    return difference, dict(common_pixels=count, total_pixels=int(before.size),
                            common_fraction=count/before.size, coverage_qualified=qualified,
                            median_ndvi_difference=float(np.median(difference[common])) if qualified else None,
                            interpretation='Single-date interannual difference on identical observed pixels, not a climatological anomaly, crop-health diagnosis or loss estimate')
