"""Export the fixed public historical snapshot for partner contract discussion."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vantage.partner_bundle import build_bundle, render_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/partner-example")
    args = parser.parse_args()
    snapshot = json.loads((ROOT / "web/data/scouting.json").read_text(encoding="utf-8"))
    bundle = build_bundle(snapshot)
    report = render_report(bundle)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "evidence.json").write_text(json.dumps(bundle, indent=2, allow_nan=False), encoding="utf-8")
    (args.out / "report.html").write_text(report, encoding="utf-8")
    print(f"Historical partner example: {args.out.resolve()} ({bundle['quality']['state']}; priorities withheld)")


if __name__ == "__main__":
    main()
