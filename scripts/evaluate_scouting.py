"""Offline private cohort evaluation. Does not publish outcomes to the web desk."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vantage.evaluation import evaluate_capacity, sampling_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["plan", "evaluate"])
    parser.add_argument("input", type=Path, help="JSON array; see docs/africa/EVALUATION.md")
    parser.add_argument("--capacity", type=int, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    web = Path(__file__).resolve().parents[1] / "web"
    if args.out.resolve().is_relative_to(web.resolve()):
        parser.error("Outcome reports must stay outside the public web directory")
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    result = (sampling_plan if args.mode == "plan" else evaluate_capacity)(rows, args.capacity, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects frozen plans and reports from accidental replacement.
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Saved {args.mode}: {args.out}")


if __name__ == "__main__":
    main()
