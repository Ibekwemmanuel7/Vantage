"""Keep optical quality and radar numerical context distinct in one research figure."""

# ruff: noqa: E402
from datetime import timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source  # noqa: F401 -- matching PROJ database
from vantage.event_series import utc_time
import numpy as np
import rasterio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def main():
    base = ROOT / "outputs/africa/radar-pixels"
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    report = json.loads((root / pointer["manifest"]).read_text())
    optical = json.loads((ROOT / "docs/africa/KWEEN_TEMPORAL_RUN.json").read_text())
    fig = plt.figure(figsize=(13, 11))
    layout = fig.add_gridspec(3, 2, height_ratios=[0.6, 0.8, 1.4], hspace=0.7)
    timing = fig.add_subplot(layout[0, :])
    features = fig.add_subplot(layout[1, :], sharex=timing)
    cutoff = utc_time(report["plan"]["as_of"])
    for ax in (timing, features):
        ax.axvspan(cutoff - timedelta(days=7), cutoff, color="#eef1f2", zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", alpha=0.12)
    for good, marker, color, label in [
        (True, "o", "#3e7155", "Optical coverage qualified"),
        (False, "x", "#a34737", "Optical withheld"),
    ]:
        rows = [r for r in optical["observations"] if r["coverage_qualified"] == good]
        timing.scatter(
            [utc_time(r["acquired_at"]) for r in rows],
            [1] * len(rows),
            marker=marker,
            color=color,
            s=45,
            label=label,
        )
    rows = [r for r in report["observations"] if r["status"] == "processed"]
    dates = [utc_time(r["acquired_at"]) for r in rows]
    timing.scatter(
        dates,
        [0] * len(rows),
        marker="^",
        s=60,
        color="#456e8e",
        label="Radar numeric support; terrain QA unverified",
    )
    timing.set(
        yticks=[0, 1],
        yticklabels=["Radar context", "Optical"],
        ylim=(-0.5, 1.5),
    )
    timing.legend(
        loc="lower left", bbox_to_anchor=(0, 1.03), ncol=3, frameon=False, fontsize=8
    )
    for key, color, marker, label in [
        ("vv_db_median", "#456e8e", "o", "VV"),
        ("vh_db_median", "#855c7c", "s", "VH"),
    ]:
        features.scatter(
            dates,
            [r["evidence"]["features"][key] for r in rows],
            color=color,
            marker=marker,
            s=48,
            label=label,
        )
    features.set_ylabel("Median gamma0 backscatter (dB)")
    features.legend(frameon=False, ncol=2, loc="upper left", fontsize=9)
    features.grid(axis="y", alpha=0.15)
    features.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    features.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    timing.set_title(
        "Same platform, relative orbit 130, ascending, IW, VV/VH. Points only; no interpolation or sensor fusion.",
        loc="left",
        fontsize=10,
        pad=36,
    )
    latest = report["changes"][-1]
    with rasterio.open(root / latest["asset"]["href"]) as ds:
        delta = ds.read()
    parent_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    parent_root = ROOT / "outputs/africa/kween" / parent_info["plan_sha256"][:20]
    with rasterio.open(parent_root / report["context"]["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad("#d4d7db")
    for index, band in enumerate(("VV", "VH")):
        ax = fig.add_subplot(layout[2, index])
        image = ax.imshow(delta[index], cmap=cmap, vmin=-6, vmax=6)
        ax.imshow(np.where(crop, np.nan, 1), cmap="gray", vmin=0, vmax=1)
        median = latest[band.lower() + "_median_delta_db"]
        ax.set_title(
            f"{band}: June 5 minus May 24\nMedian per-pixel change {median:+.2f} dB",
            fontsize=11,
        )
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle(
        "Ngenge | radar context during optical coverage gaps",
        x=0.09,
        ha="left",
        fontsize=16,
    )
    fig.subplots_adjust(left=0.09, right=0.97, top=0.85, bottom=0.23)
    bar = fig.colorbar(
        image,
        cax=fig.add_axes([0.27, 0.155, 0.5, 0.014]),
        orientation="horizontal",
        extend="both",
    )
    bar.set_label(
        "Backscatter change (dB); display clipped to ±6 dB, numerical values retained",
        fontsize=9,
    )
    fig.text(
        0.09,
        0.105,
        "June 5 UTC: optical acquisition 07:46; radar acquisition 15:57. Afternoon radar cannot enter the morning comparison.",
        fontsize=9,
    )
    fig.text(
        0.09,
        0.075,
        "Historical-cropland proxy only. No independent terrain QA, crop calendars, field outcomes, soil-moisture retrieval or crop-damage labels.",
        fontsize=9,
    )
    fig.text(
        0.09,
        0.045,
        "Optical evidence remains stale. Radar is separate numerical context; no causal attribution or model training. Run "
        + report["run_id"],
        fontsize=8,
    )
    path = base / "kween-radar.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    main()
