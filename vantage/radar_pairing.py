"""Causal metadata pairing is distinct from verified radar feature eligibility."""
from vantage.event_series import utc_time


def causal_pairs(optical,radar,max_age_days=7):
    if not 0<max_age_days<=7:raise ValueError("Fixed positive at-most-seven-day lag required")
    if len({r["track_id"] for r in radar})>1:raise ValueError("Exactly one radar track per pairing cohort")
    if len({r["item_id"] for r in radar})!=len(radar):raise ValueError("Duplicate radar pass")
    pairs=[]
    for observation in optical:
        when=utc_time(observation["acquired_at"])
        prior=[r for r in radar if utc_time(r["acquired_at"])<=when]
        latest=max(prior,key=lambda r:utc_time(r["acquired_at"]),default=None)
        age=(when-utc_time(latest["acquired_at"])).total_seconds()/86400 if latest else None
        supported=latest is not None and age<=max_age_days
        pairs.append(dict(optical_scene_id=observation["scene_id"],optical_acquired_at=observation["acquired_at"],
            prior_radar_item_id=latest["item_id"] if latest else None,lag_days=age,
            within_age_limit=supported,selected_radar_item_id=latest["item_id"] if supported else None,
            status="research_pair_only" if supported else "withheld_no_recent_prior_radar",
            usable_for_agricultural_model=False))
    return pairs
