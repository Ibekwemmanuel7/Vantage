"""Freeze disjoint geographic/year partitions and audit reconstruction inputs."""
from datetime import datetime
import hashlib
import json


def split_inventory(plan, scenes):
    splits = plan["splits"]
    if set(splits) != {"train", "validation", "test"}:
        raise ValueError("Train, validation and test partitions required")
    names = sorted(splits)
    for i,name in enumerate(names):
        if not splits[name]["locations"] or not splits[name]["years"]:
            raise ValueError("Nonempty location and year partitions required")
        for other in names[i+1:]:
            if set(splits[name]["locations"]) & set(splits[other]["locations"]):
                raise ValueError("Location overlap across splits")
            if set(splits[name]["years"]) & set(splits[other]["years"]):
                raise ValueError("Year overlap across splits")
    minimum = plan["minimum_distinct_dates_per_cohort"]
    if type(minimum) is not int or minimum < 3:
        raise ValueError("At least three distinct dates per cohort required")
    assigned = {name:[] for name in splits}
    excluded = []
    seen = set()
    for scene in scenes:
        identity = (scene["location_id"],scene["acquired_at"])
        if identity in seen:
            raise ValueError("Duplicate acquisition in a location")
        seen.add(identity)
        stamp = datetime.fromisoformat(scene["acquired_at"].replace("Z","+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Timezone-aware scene timestamp required")
        destination = next((name for name,part in splits.items()
                            if scene["location_id"] in part["locations"] and stamp.year in part["years"]),None)
        if destination:
            assigned[destination].append(scene)
        else:
            excluded.append(scene["scene_id"])
    blockers=[]
    for name,part in splits.items():
        for location in part["locations"]:
            for year in part["years"]:
                cohort=[s for s in assigned[name] if s["location_id"]==location
                        and datetime.fromisoformat(s["acquired_at"].replace("Z","+00:00")).year==year]
                usable=sum(s["valid_pixels"]>0 for s in cohort)
                if usable < minimum:
                    blockers.append(f"{name}:{location}:{year}:insufficient_nonempty_dates:{usable}/{minimum}")
    payload=dict(schema_version="gap-dataset-manifest-1",plan=plan,splits=assigned,
                 excluded_scene_ids=excluded,blockers=blockers,
                 training_data_gate_passed=not blockers,
                 model_trained=False,untouched_final_test=False,
                 limitation="Date counts alone do not establish usable causal pairs, mask diversity or agricultural validity")
    payload["manifest_id"]=hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return payload
