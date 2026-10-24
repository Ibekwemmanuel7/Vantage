"""Package a checked local field-change report and bounded numeric map for browser review."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build_review(directory):
    import numpy as np
    import rasterio
    raw = (directory / "report.json").read_bytes()
    report = json.loads(raw.decode("utf-8-sig"))
    if report.get("schema_version") != "vantage-field-change-1" or report.get("field_priorities_available") is not False:
        raise ValueError("Observed research field-change report required")
    raster = report["change_raster"]
    if raster["path"] != "observed-change.tif":
        raise ValueError("Only the fixed packet raster filename is supported")
    path = directory / "observed-change.tif"
    if hashlib.sha256(path.read_bytes()).hexdigest() != raster["sha256"]:
        raise ValueError("Change raster checksum mismatch")
    with rasterio.open(path) as source:
        grid = report["after"]["grid"]
        if (source.count != 1 or source.width * source.height > 4_000_000
                or [source.width, source.height] != [grid["width"], grid["height"]]
                or list(source.transform) != grid["transform"] or source.crs.to_string() != grid["crs"]):
            raise ValueError("Raster differs from reported grid")
        tags = source.tags()
        for key, expected in (("before_acquired_at", report["before"]["acquired_at"]),
                              ("after_acquired_at", report["after"]["acquired_at"]),
                              ("decision_cutoff", report["decision_cutoff"])):
            if tags.get(key) != expected:
                raise ValueError("Raster acquisition/cutoff tag mismatch")
        values = source.read(1)
        valid = source.read_masks(1) != 0
        if not np.array_equal(valid, np.isfinite(values)) or np.any(np.abs(values[valid]) > 2):
            raise ValueError("Invalid masked NDVI difference")
        fields = report["fields"]
        if not 1 <= len(fields) <= 100:
            raise ValueError("Expected 1-100 field summaries")
        counts = [f["common_valid_pixels"] for f in fields if f["eligible_for_research_comparison"]]
        if not (max(counts, default=0) <= int(valid.sum()) <= sum(counts)):
            raise ValueError("Raster support conflicts with eligible field summaries")
        stride = max(1, int(np.ceil(max(source.width, source.height) / 1024)))
        sampled, mask = values[::stride, ::stride], valid[::stride, ::stride]
        encoded = np.full(sampled.shape, 32767, dtype="<i2")
        encoded[mask] = np.rint(sampled[mask] * 10000).astype("<i2")
        preview = dict(width=encoded.shape[1], height=encoded.shape[0], sample_stride=stride,
                       encoding="int16-le-ndvi1e4-nodata32767", values_base64=base64.b64encode(encoded.tobytes()).decode(),
                       crs=source.crs.to_string(), bounds=list(source.bounds),
                       note="Nearest sampled overview; small features may be omitted. Statistics retain full resolution.")
    return dict(schema_version="vantage-field-review-1", report=report, preview=preview,
                report_file_sha256=hashlib.sha256(raw).hexdigest(),
                limitation="Hash consistency is not independent authentication. Private browser review, no model or field recommendation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        from scripts.validate_field_evidence import private_output
        output = private_output(args.out)
        proj = Path(importlib.util.find_spec("rasterio").origin).parent / "proj_data"
        if proj.is_dir():
            os.environ["PROJ_DATA"] = os.environ["PROJ_LIB"] = str(proj)
        review = build_review(args.packet)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(review, stream, allow_nan=False)
            stream.write("\n")
        print(f"Saved private field review packet: {output}")
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        parser.exit(2, f"Field review failed: {exc}\n")


if __name__ == "__main__":
    main()
