import hashlib
import unittest
from vantage.safe_annotations import verify_annotation


class SafeAnnotationTests(unittest.TestCase):
    def test_bytes_must_match_size_checksum_and_product_type(self):
        raw=b"<product/>"
        reference=dict(size=len(raw),md5=hashlib.md5(raw).hexdigest())
        self.assertEqual(verify_annotation(raw,reference),hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):verify_annotation(raw+b" ",reference)
        with self.assertRaises(ValueError):verify_annotation(b"<changed/>",reference)
        raw=b"<notProduct/>"
        with self.assertRaises(ValueError):verify_annotation(raw,dict(size=len(raw),md5=hashlib.md5(raw).hexdigest()))
