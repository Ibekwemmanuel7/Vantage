"""Private conditional ranking bounds; unresolved visits stay unknown."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.field_protocol import _read
from scripts.validate_field_evidence import private_output
from vantage.scouting_bounds import compare_scouting_bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("intake", type=Path)
    parser.add_argument("adjudications", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = private_output(args.out)
        protocol, protocol_hash = _read(args.protocol)
        intake, intake_hash = _read(args.intake)
        adjudications, adjudication_hash = _read(args.adjudications)
        result = compare_scouting_bounds(protocol, intake, adjudications)
        result["source_file_sha256"] = dict(protocol=protocol_hash, intake=intake_hash, adjudications=adjudication_hash)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        parser.exit(2, f"Scouting comparison failed: {exc}\n")
    print(f"Conditional paired precision bounds: {result['paired_precision_difference_bounds']}; not a confidence interval.")


if __name__ == "__main__":
    main()
