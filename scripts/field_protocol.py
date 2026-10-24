"""Freeze private research visit packets or reconcile returned scouting intake."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_field_evidence import private_output
from vantage.field_protocol import collection_form, freeze_protocol, reconcile_intake


def _read(path):
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("input", type=Path)
    freeze.add_argument("--out-dir", type=Path, required=True, help="New directory beneath outputs/private")
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("protocol", type=Path)
    reconcile.add_argument("intake", type=Path)
    reconcile.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "freeze":
            directory = private_output(args.out_dir)
            spec, source_hash = _read(args.input)
            protocol = freeze_protocol(spec)
            form = collection_form(protocol)
            protocol["input_sha256"] = source_hash
            directory.mkdir(parents=True, exist_ok=False)
            for name, content in (("protocol.json", protocol), ("collection.json", form)):
                with (directory / name).open("x", encoding="utf-8") as stream:
                    json.dump(content, stream, indent=2, allow_nan=False)
                    stream.write("\n")
            print(f"Saved private protocol and score-hidden collection form: {directory}")
        else:
            output = private_output(args.out)
            protocol, protocol_hash = _read(args.protocol)
            intake, intake_hash = _read(args.intake)
            result = reconcile_intake(protocol, intake)
            result.update(protocol_file_sha256=protocol_hash, intake_file_sha256=intake_hash)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, allow_nan=False)
                stream.write("\n")
            print(f"Visit states: {result['state_counts']}. No labels admitted.")
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        parser.exit(2, f"Field protocol failed: {exc}\n")


if __name__ == "__main__":
    main()
