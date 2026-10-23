"""Validate product annotation bytes against their authoritative SAFE reference."""
import hashlib
import xml.etree.ElementTree as ET


def verify_annotation(raw,reference):
    if len(raw)!=reference["size"] or hashlib.md5(raw).hexdigest()!=reference["md5"]:
        raise ValueError("Product annotation differs from SAFE size/checksum")
    if ET.fromstring(raw).tag.split("}")[-1]!="product":
        raise ValueError("Expected product annotation XML")
    return hashlib.sha256(raw).hexdigest()
