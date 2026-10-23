import copy
import json
from pathlib import Path
import unittest
from vantage.gap_dataset import split_inventory


class GapDatasetTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((Path(__file__).resolve().parents[1]/"configs/gap_benchmark_split.json").read_text())

    def test_overlap_rejected_even_without_scenes(self):
        for key,value in [("locations",["iganga-study"]),("years",[2023])]:
            plan=copy.deepcopy(self.plan)
            plan["splits"]["test"][key]=value
            with self.assertRaises(ValueError):split_inventory(plan,[])

    def test_empty_training_blocks_and_content_identity_is_stable(self):
        result=split_inventory(self.plan,[])
        self.assertFalse(result["training_data_gate_passed"])
        self.assertEqual(len(result["blockers"]),3)
        self.assertEqual(result,split_inventory(self.plan,[]))

    def test_partition_assignment_duplicate_and_nonempty_date_gate(self):
        scenes=[]
        for name,part in self.plan["splits"].items():
            for day in range(1,4):
                scenes.append(dict(location_id=part["locations"][0],scene_id=f"{name}-{day}",
                    acquired_at=f'{part["years"][0]}-05-{day:02}T00:00:00Z',valid_pixels=10))
        self.assertTrue(split_inventory(self.plan,scenes)["training_data_gate_passed"])
        scenes[0]["valid_pixels"]=0
        self.assertFalse(split_inventory(self.plan,scenes)["training_data_gate_passed"])
        with self.assertRaises(ValueError):split_inventory(self.plan,scenes+[scenes[0]])
