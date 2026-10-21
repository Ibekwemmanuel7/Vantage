"""Render the executed case, retaining withheld maps and native rainfall context."""
# ruff: noqa: E402

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Establish the rasterio wheel's matching projection database before opening COGs.
from scripts import build_uganda_demo as source  # noqa: F401 -- initializes matching PROJ database
import rasterio
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    base = ROOT / "outputs/africa/kween"
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    report = json.loads((root / pointer["manifest"]).read_text())
    fig, axes = plt.subplots(3, 3, figsize=(14, 11))
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("#d4d7db")
    image = None
    for row, area in enumerate(report["plan"]["areas"]):
        context = report["contexts"][area["id"]]
        with rasterio.open(root / context["crop_asset"]) as ds:
            crop = ds.read(1).astype(bool)
        for col, epoch in enumerate(report["plan"]["epochs"]):
            ax = axes[row, col]
            result = next(
                r
                for r in report["comparisons"]
                if r["area_id"] == area["id"] and r["epoch"] == epoch["id"]
            )
            ax.set_facecolor("#d4d7db")
            if result["status"] == "research_comparison_available":
                with rasterio.open(root / result["asset"]) as ds:
                    delta = ds.read(1)
                image = ax.imshow(delta, cmap=cmap, vmin=-0.4, vmax=0.4)
                ax.imshow(np.where(crop, np.nan, 1), cmap="gray", vmin=0, vmax=1)
                subtitle = (
                    f"Median delta {result['median_delta']:+.3f}; "
                    f"{result['comparable_crop_fraction']:.0%} comparable\n"
                    f"{result['lower_than_reference_fraction']:.1%} below all refs and -0.10"
                )
            else:
                ax.imshow(np.where(crop, np.nan, 1), cmap="gray", vmin=0, vmax=1)
                subtitle = "WITHHELD\nInsufficient coverage / reference years"
            date = (result["target_acquired_at"] or "no acquisition")[:10]
            ax.set_title(
                f"{area['id']} | {epoch['id']}\n{date}; eligible refs: {len(result['reference_years'])}",
                fontsize=10,
            )
            ax.set_xlabel(subtitle, fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        ax = axes[row, 2]
        rain = report["rainfall"][area["id"]]["summary"]
        if rain["status"] == "available":
            years = report["plan"]["reference_years"] + [report["plan"]["target_year"]]
            totals = [rain["totals_mm"][str(y)] for y in years]
            ax.bar([str(y) for y in years], totals, color=["#a9b5c0"] * 4 + ["#426d81"])
            ax.axhline(
                rain["reference_median_mm"],
                color="#6c654e",
                linestyle="--",
                linewidth=1,
            )
            ratio = rain["ratio_to_reference_median"]
            text = (
                f"2023 / reference median: {ratio:.2f}"
                if ratio is not None
                else "Reference median is zero; ratio unavailable"
            )
            ax.set_title(f"March–May rainfall | {area['id']}\n{text}", fontsize=10)
        else:
            ax.text(
                0.5, 0.5, "Rainfall unavailable", ha="center", transform=ax.transAxes
            )
        ax.set_ylabel("Rainfall total (mm)", fontsize=9)
        ax.grid(axis="y", alpha=0.15)
    fig.suptitle(
        "Kween 2023 | retrospective public-event research case",
        x=0.06,
        ha="left",
        fontsize=17,
    )
    fig.subplots_adjust(
        left=0.06, right=0.97, top=0.89, bottom=0.23, hspace=0.65, wspace=0.35
    )
    if image is not None:
        bar = fig.colorbar(
            image,
            cax=fig.add_axes([0.21, 0.145, 0.58, 0.015]),
            orientation="horizontal",
        )
        bar.set_label("NDVI (B8A/red): 2023 minus earlier-year median", fontsize=9)
    fig.text(
        0.06,
        0.095,
        "Gray: unavailable or withheld historical cropland. White: outside WorldCover 2021 cropland. Maps share a fixed scale.",
        fontsize=9,
    )
    fig.text(
        0.06,
        0.065,
        "Native CHIRPS cell means; four earlier years are a short reference, not climatology. Overlapping locality proxies are correlated.",
        fontsize=9,
    )
    fig.text(
        0.06,
        0.035,
        "No verified crop calendars or independent field outcomes. No cause, damage, model accuracy or historical alert claim. Run "
        + report["run_id"],
        fontsize=8,
    )
    out = base / "kween-case.png"
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
