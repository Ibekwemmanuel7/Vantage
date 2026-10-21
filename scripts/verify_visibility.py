"""Verify checksums then exactly replay all bounded sightline COGs offline."""

# ruff: noqa: E402
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_radar_series import manifest, require
from vantage.imagery import sha256_file


def main():
    base = ROOT / "outputs/africa/visibility"
    root, path, report = manifest(base)
    before = sha256_file(path)
    require(
        sha256_file(root / report["elevation_lineage"]["cache"])
        == report["elevation_lineage"]["sha256"],
        "Native DSM differs",
    )
    assets = list(report["assets"].values())
    for row in report["observations"]:
        assets.extend(row["assets"].values())
        require(
            sum(row["historical_crop_counts"].values())
            == report["historical_crop_pixels"],
            "Crop denominator differs",
        )
    for asset in assets:
        require(sha256_file(root / asset["href"]) == asset["sha256"], "COG differs")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_visibility.py")],
        cwd=ROOT,
        check=True,
    )
    after_root, after_path, _ = manifest(base)
    require(
        root == after_root and path == after_path and sha256_file(path) == before,
        "Offline replay differs",
    )
    summary = json.loads((ROOT / "docs/africa/KWEEN_VISIBILITY_RUN.json").read_text())
    require(
        summary["manifest_sha256"] == before and summary["run_id"] == report["run_id"],
        "Published summary differs",
    )
    print(
        f"Verified {len(report['observations'])} acquisitions, {len(assets)} COGs and exact offline replay"
    )


if __name__ == "__main__":
    main()
