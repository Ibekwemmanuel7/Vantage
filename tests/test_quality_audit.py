import unittest
import numpy as np
from vantage.quality_audit import audit_quality


class QualityAuditTests(unittest.TestCase):
    def test_all_cloud_class_is_accounted_for(self):
        a = np.full((5,5), 2000)
        result = audit_quality({"B04":a,"B08":a}, np.full((5,5),9), 10000, {"B04":0,"B08":0})
        self.assertEqual(result["ordered_exclusive_rejections"]["scl_class_rejected"], 25)
        self.assertEqual(result["accepted_pixels"], 0)
        self.assertTrue(result["accounting_complete"])

    def test_cloud_buffer_and_numeric_failure_are_separate(self):
        a = np.full((5,5),2000)
        scl = np.full((5,5),4)
        scl[2,2] = 9
        red = a.copy()
        red[0,0] = 0
        result = audit_quality({"B04":red,"B08":a}, scl, 10000, {"B04":0,"B08":0})
        reasons = result["ordered_exclusive_rejections"]
        self.assertEqual(reasons["scl_class_rejected"],1)
        self.assertEqual(reasons["scl_buffer_rejected"],4)
        self.assertEqual(reasons["source_red_or_nir_nodata"],1)
        self.assertEqual(result["accepted_pixels"],19)
        self.assertTrue(result["accounting_complete"])

    def test_reflectance_offset_failure_not_called_cloud(self):
        a = np.full((3,3),500)
        result = audit_quality({"B04":a,"B08":a}, np.full((3,3),4),10000,{"B04":-1000,"B08":-1000})
        self.assertEqual(result["ordered_exclusive_rejections"]["invalid_physical_reflectance"],9)
        self.assertEqual(result["ordered_exclusive_rejections"]["scl_class_rejected"],0)
