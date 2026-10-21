"""Verify prepared requests and exactly replay pending or exported comparisons."""

# ruff: noqa: E402
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_radar_series import manifest, require
from vantage.imagery import sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path)
    args = parser.parse_args()
    base = ROOT / "outputs/africa/processor-benchmark"
    root, path, report = manifest(base)
    checksum = sha256_file(path)
    for row in report["observations"]:
        require(
            sha256_file(root / f"{row['index']}-request.json") == row["request_sha256"],
            "Prepared request differs",
        )
    command = [sys.executable, str(ROOT / "scripts/compare_radar_processor.py")]
    if args.exports is not None:
        command.extend(["--exports", str(args.exports.resolve())])
    subprocess.run(command, cwd=ROOT, check=True)
    new_root, new_path, _ = manifest(base)
    require(
        root == new_root and path == new_path and sha256_file(path) == checksum,
        "Comparison replay differs",
    )
    summary = json.loads(
        (ROOT / "docs/africa/KWEEN_PROCESSOR_BENCHMARK_RUN.json").read_text()
    )
    require(summary["manifest_sha256"] == checksum, "Published status differs")
    print(
        "Verified",
        len(report["observations"]),
        "requests and exact replay; status:",
        report["status"],
    )


if __name__ == "__main__":
    main()
