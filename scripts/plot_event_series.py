"""Plot actual observations, cloud gaps, freshness and all late-window comparisons."""

# ruff: noqa: E402
from datetime import timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source  # noqa: F401 -- matching PROJ database
from vantage.event_series import utc_time
import rasterio
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def main():
    base = ROOT / "outputs/africa/event-series"
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    report = json.loads((root / pointer["manifest"]).read_text())
    rows = report["observations"]
    late = [r for r in rows if r["acquired_at"][5:10] >= "05-21"]
    cols = max(1, len(late))
    fig = plt.figure(figsize=(14, 11))
    layout = fig.add_gridspec(3, cols, height_ratios=[1, 0.8, 1.3], hspace=0.65)
    spectral = fig.add_subplot(layout[0, :])
    coverage = fig.add_subplot(layout[1, :], sharex=spectral)
    as_of = utc_time(report["plan"]["as_of"])
    fresh_start = as_of - timedelta(days=report["plan"]["max_observation_age_days"])
    for ax in (spectral, coverage):
        ax.axvspan(fresh_start, as_of, color="#e8f0ea", zorder=0)
        ax.grid(axis="y", alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
    qualified = [
        r for r in rows if r["status"] == "processed" and r["coverage_qualified"]
    ]
    rejected = [r for r in rows if r not in qualified]
    spectral.scatter(
        [utc_time(r["acquired_at"]) for r in qualified],
        [r["observation"]["features"]["ndvi_b8a_median"] for r in qualified],
        color="#356b50",
        s=50,
        label="Coverage-qualified NDVI",
        zorder=3,
    )
    spectral.scatter(
        [utc_time(r["acquired_at"]) for r in rejected],
        [0.03] * len(rejected),
        color="#a94736",
        marker="x",
        transform=spectral.get_xaxis_transform(),
        label="Withheld: marker is not an NDVI value",
        zorder=3,
    )
    spectral.set(ylabel="Median NDVI (B8A/red)", ylim=(-0.05, 1))
    spectral.legend(
        loc="lower left", bbox_to_anchor=(0, 1.02), ncol=2, frameon=False, fontsize=9
    )
    spectral.set_title(
        "Actual observations only; no interpolation. Shading: seven-day research freshness window.",
        loc="left",
        fontsize=10,
        pad=40,
    )
    processed = [r for r in rows if r["status"] == "processed"]
    coverage.scatter(
        [utc_time(r["acquired_at"]) for r in processed],
        [r["observation"]["crop_usable_fraction"] for r in processed],
        color="#526e85",
        s=45,
        zorder=3,
    )
    coverage.axhline(0.6, color="#756c53", linestyle="--", linewidth=1)
    coverage.set(ylabel="Usable historical-cropland fraction", ylim=(-0.05, 1.05))
    coverage.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    coverage.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    coverage.text(
        0.99,
        0.63,
        "60% coverage threshold",
        ha="right",
        transform=coverage.get_yaxis_transform(),
        fontsize=9,
    )
    parent_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    parent_root = ROOT / "outputs/africa/kween" / parent_info["plan_sha256"][:20]
    with rasterio.open(parent_root / report["context"]["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("#d4d7db")
    image = None
    for col, row in enumerate(late):
        ax = fig.add_subplot(layout[2, col])
        comparison = row["comparison"]
        ax.set_facecolor("#d4d7db")
        if comparison and comparison["status"] == "research_comparison_available":
            with rasterio.open(root / comparison["asset"]) as ds:
                delta = ds.read(1)
            image = ax.imshow(delta, cmap=cmap, vmin=-0.4, vmax=0.4)
            label = f"Median delta {comparison['median_delta']:+.3f}\n{comparison['comparable_crop_fraction']:.0%} comparable cropland"
        else:
            label = "WITHHELD\nInsufficient comparable coverage"
        ax.imshow(np.where(crop, np.nan, 1), cmap="gray", vmin=0, vmax=1)
        freshness = (
            "within age window" if row["within_freshness_window"] else "STALE at cutoff"
        )
        ax.set_title(
            f"{row['acquired_at'][:10]} | {freshness}\nAge {row['age_at_cutoff_days']:.1f} days",
            fontsize=9,
        )
        ax.set_xlabel(label, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle(
        "Ngenge | denser Kween event follow-up, May 1–June 5, 2023",
        x=0.08,
        ha="left",
        fontsize=16,
    )
    fig.subplots_adjust(left=0.08, right=0.97, top=0.85, bottom=0.24)
    if image is not None:
        bar = fig.colorbar(
            image, cax=fig.add_axes([0.25, 0.155, 0.5, 0.014]), orientation="horizontal"
        )
        bar.set_label(
            "NDVI: observed value minus 2019–2022 calendar-window median", fontsize=9
        )
    fig.text(
        0.08,
        0.10,
        "Gray maps: missing/withheld historical cropland. White: outside historical cropland. Shared map scale; no crop-damage labels.",
        fontsize=9,
    )
    fig.text(
        0.08,
        0.07,
        "Observation medians can cover different pixels. Proxy boundary and crop stages unconfirmed. Freshness does not establish agricultural validity.",
        fontsize=9,
    )
    fig.text(
        0.08,
        0.04,
        "Exploratory follow-up, no model training, historical delivery claim or causal attribution. Run "
        + report["run_id"],
        fontsize=9,
    )
    path = base / "kween-temporal.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    main()
