"""Validate private field records; write an exclusive metadata-only report."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vantage.field_evidence import validate_intake


def private_output(path):
    resolved = path.resolve()
    if not resolved.is_relative_to((ROOT / "outputs" / "private").resolve()):
        raise ValueError("Report must be beneath outputs/private")
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = private_output(args.out)
        raw = args.input.read_bytes()
        result = validate_intake(json.loads(raw.decode("utf-8-sig")))
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Intake failed: {exc}\n")
    print(f"Validated {result['record_count']} records; {result['ready_for_manual_review_count']} ready for manual review. No labels admitted.")


if __name__ == "__main__":
    main()
