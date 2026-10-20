"""Explicit temporal slots and independent crop-calendar evidence contracts."""
import calendar
from datetime import date, datetime, timezone


def dekad_slots(plan):
    if not plan["years"] or not plan["months"] or len(set(plan["years"]))!=len(plan["years"]) or len(set(plan["months"]))!=len(plan["months"]):
        raise ValueError("Nonempty unique years and months required")
    for year in sorted(plan["years"]):
        if type(year) is not int or not 2017<=year<=2025:raise ValueError("Completed historical year required")
        for month in sorted(plan["months"]):
            last=calendar.monthrange(year,month)[1]
            for index,(start,end) in enumerate(((1,10),(11,20),(21,last)),1):
                yield dict(slot_id=f'{plan["location_id"]}-{year}-{month:02}-D{index}',
                    location_id=plan["location_id"],year=year,month=month,dekad=index,
                    start=f"{year}-{month:02}-{start:02}",end=f"{year}-{month:02}-{end:02}")


def slot_candidates(slot,items,bbox):
    w,s,e,n=bbox
    accepted=[]
    for item in items:
        stamp=item["properties"]["datetime"]
        day=date.fromisoformat(stamp[:10])
        if not date.fromisoformat(slot["start"])<=day<=date.fromisoformat(slot["end"]):continue
        a,b,c,d=item["bbox"][:4]
        if not (a<=w and b<=s and c>=e and d>=n):continue
        if not all(k in item["assets"] for k in ("B02","B03","B04","B8A","B11","B12","SCL","product-metadata")):continue
        accepted.append(item)
    accepted.sort(key=lambda i:(i["properties"].get("eo:cloud_cover") if i["properties"].get("eo:cloud_cover") is not None else 101,
                                i["properties"]["datetime"],i["id"]))
    # Do not count alternate processing/tile versions of a datatake as extra visits.
    seen=set();unique=[]
    for item in accepted:
        if item["properties"]["datetime"] not in seen:
            unique.append(item);seen.add(item["properties"]["datetime"])
    return unique


def calendar_readiness(record,location_id,year):
    blockers=[]
    if not record:return dict(confirmed=False,blockers=["no_independent_crop_calendar_record"])
    if record.get("location_id")!=location_id or record.get("year")!=year:blockers.append("location_or_year_mismatch")
    if not record.get("crop") or record.get("crop_identity_confirmed") is not True:blockers.append("crop_identity_unconfirmed")
    if record.get("confirmation_kind") not in ("dated_field_record","partner_agronomist"):blockers.append("independent_confirmation_required")
    if not record.get("source_ref") or not record.get("reviewer_ref"):blockers.append("missing_traceable_reference")
    if record.get("permission_status")!="approved":blockers.append("permission_unconfirmed")
    try:
        planting=date.fromisoformat(record["planting_date"]);harvest=date.fromisoformat(record["harvest_date"])
        reviewed=datetime.fromisoformat(record["reviewed_at"].replace("Z","+00:00"))
        if planting.year!=year or harvest<planting or (harvest-planting).days>366:raise ValueError()
        if reviewed.tzinfo is None or reviewed>datetime.now(timezone.utc):raise ValueError()
        if reviewed.date()<planting:raise ValueError()
    except (KeyError,TypeError,ValueError):blockers.append("missing_or_invalid_dated_calendar_evidence")
    return dict(confirmed=not blockers,blockers=blockers,
                limitation="Declared references require independent audit; regional desk calendars do not confirm field planting dates. Calendar confirmation alone is not a field outcome label.")
