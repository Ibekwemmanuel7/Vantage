from datetime import datetime
import json
from pathlib import Path
import unittest
from vantage.recent_inventory import recent_window


class GapAcquisitionTests(unittest.TestCase):
    def test_cohorts_match_frozen_splits_and_budget(self):
        root=Path(__file__).resolve().parents[1]/"configs"
        for filename in ("gap_acquisition.json","gap_acquisition_june.json"):
            with self.subTest(plan=filename):
                plan=json.loads((root/filename).read_text())
                splits=json.loads((root/plan["split_plan"]).read_text())["splits"]
                config=json.loads((root/"uganda_archive.json").read_text())
                self.assertLessEqual(sum(c["scenes_per_location"] for c in plan["cohorts"]),plan["maximum_scenes_total"])
                for cohort in plan["cohorts"]:
                    location=next(l for l in config["locations"] if l["id"]==cohort["location_id"])
                    cutoff=datetime.fromisoformat(cohort["as_of"].replace("Z","+00:00"))
                    window=recent_window(config,location,cutoff,cohort["days"])
                    start=datetime.fromisoformat(window["interval"].split("/")[0])
                    self.assertIn(location["id"],splits[cohort["partition"]]["locations"])
                    self.assertIn(start.year,splits[cohort["partition"]]["years"])
