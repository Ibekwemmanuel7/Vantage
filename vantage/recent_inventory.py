"""Recent catalog metadata is acquisition availability, not crop condition."""
from datetime import datetime, timedelta, timezone
from vantage.archive import summarize_window, windows


def recent_window(config, location, cutoff, days):
    if cutoff.tzinfo is None or cutoff.utcoffset() != timedelta(0):
        raise ValueError("UTC cutoff required")
    if type(days) is not int or not 1 <= days <= 31:
        raise ValueError("Lookback must be 1-31 days")
    # Reuse the existing bounded Uganda geometry validation, without changing
    # the historical archive's completed-year eligibility rules.
    list(windows({**config, "locations": [location], "years": [2024], "months": [1]}))
    start = cutoff - timedelta(days=days)
    return dict(location_id=location["id"], bbox=location["bbox"],
                interval=start.isoformat()+"/"+cutoff.isoformat())


def summarize_recent(window, response, config, retrieved_at):
    start, end = [datetime.fromisoformat(v.replace("Z", "+00:00"))
                  for v in window["interval"].split("/")]
    for item in response["features"]:
        if item.get("collection") != config["collection"]:
            raise ValueError("Unexpected collection")
        acquired = datetime.fromisoformat(item["properties"]["datetime"].replace("Z", "+00:00"))
        if acquired.tzinfo is None or not start <= acquired <= end:
            raise ValueError("Acquisition outside requested interval")
    summary = summarize_window(window, response, config)
    latest = max((x["acquired_at"] for x in summary["candidates"]),
                 key=lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")), default=None)
    age = ((end - datetime.fromisoformat(latest.replace("Z", "+00:00"))).total_seconds() / 86400
           if latest else None)
    return dict(**summary, retrieved_at=retrieved_at,
                latest_catalog_acquisition=latest, acquisition_age_days=age,
                usable_observation_status="not_assessed",
                field_priorities_available=False,
                mode="recent_catalog_inventory_not_crop_monitoring",
                first_known_historical_availability=None)
