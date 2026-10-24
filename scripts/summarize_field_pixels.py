"""Offline private field summaries from an existing observed NDVI NPZ artifact."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("boundaries", type=Path)
    parser.add_argument("pixels", type=Path)
    parser.add_argument("--pixels-sha256", required=True, help="Expected hash from the archived pixel report")
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--acquired-at", required=True)
    parser.add_argument("--available-at", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        from scripts.validate_field_evidence import private_output
        output = private_output(args.out)
        # Use the installed rasterio wheel's own PROJ database in this CLI process.
        proj = Path(importlib.util.find_spec("rasterio").origin).parent / "proj_data"
        if proj.is_dir():
            os.environ["PROJ_DATA"] = os.environ["PROJ_LIB"] = str(proj)
        import numpy as np
        from vantage.field_pixels import summarize_fields
        raw = args.boundaries.read_bytes()
        pixel_hash = hashlib.sha256(args.pixels.read_bytes()).hexdigest()
        if pixel_hash != args.pixels_sha256:
            raise ValueError("Pixel artifact checksum mismatch")
        with np.load(args.pixels, allow_pickle=False) as arrays:
            result = summarize_fields(json.loads(raw.decode("utf-8-sig")), arrays["ndvi"], arrays["valid"],
                                      arrays["transform"], str(arrays["crs"]), acquired_at=args.acquired_at,
                                      available_at=args.available_at, cutoff=args.cutoff, source_ref=args.source_ref)
        result["input_sha256"] = dict(boundaries=hashlib.sha256(raw).hexdigest(), pixels=pixel_hash)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print(f"Summarized {len(result['fields'])} declared fields; no field priorities generated.")
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        parser.exit(2, f"Field summary failed: {exc}\n")


if __name__ == "__main__":
    main()
