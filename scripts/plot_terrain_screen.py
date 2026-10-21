"""Visualize the fixed surface-slope proxy and sensitivity, without SAR validity claims."""

# ruff: noqa: E402
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source  # noqa: F401 -- matching PROJ database
import numpy as np
import rasterio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch


def main():
    base = ROOT / "outputs/africa/terrain"
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    report = json.loads((root / pointer["manifest"]).read_text())
    parent_info = json.loads(
        (ROOT / "docs/africa/KWEEN_RADAR_PIXELS_RUN.json").read_text()
    )
    parent_root = ROOT / "outputs/africa/radar-pixels" / parent_info["plan_sha256"][:20]
    parent = json.loads(
        (parent_root / (report["plan"]["parent_radar_run_id"] + ".json")).read_text()
    )
    crop_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    crop_root = ROOT / "outputs/africa/kween" / crop_info["plan_sha256"][:20]
    with rasterio.open(crop_root / report["context"]["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    with rasterio.open(
        root / report["terrain_assets"]["radar_grid_slope"]["href"]
    ) as ds:
        slope = ds.read(1)
    with rasterio.open(root / report["terrain_assets"]["proxy_classes"]["href"]) as ds:
        classes = ds.read()
    thresholds = report["plan"]["sensitivity_max_slope_degrees"]
    primary = thresholds.index(report["plan"]["primary_max_slope_degrees"])
    fig, axes = plt.subplots(
        2, 2, figsize=(12.5, 11), gridspec_kw={"height_ratios": [1.4, 1]}
    )
    image = axes[0, 0].imshow(slope, cmap="cividis", vmin=0, vmax=20)
    fig.colorbar(
        image,
        ax=axes[0, 0],
        fraction=0.045,
        pad=0.03,
        label="Maximum neighborhood surface slope (degrees)",
        extend="max",
    )
    axes[0, 0].set_title("30m surface-slope proxy on the radar grid", fontsize=11)
    values = np.where(crop, classes[primary], 3)
    colors = ["#696f75", "#b5c7bf", "#c78146", "#ffffff"]
    axes[0, 1].imshow(
        values,
        cmap=ListedColormap(colors),
        norm=BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], 4),
    )
    axes[0, 1].set_title("Primary 10° proxy over historical cropland", fontsize=11)
    axes[0, 1].legend(
        handles=[
            Patch(facecolor=colors[1], label="Lower slope; illumination unconfirmed"),
            Patch(
                facecolor=colors[2], label="Elevated slope; excluded from sensitivity"
            ),
            Patch(facecolor=colors[0], label="Unknown"),
            Patch(
                facecolor=colors[3],
                edgecolor="#aaaaaa",
                label="Outside historical cropland",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        frameon=False,
        fontsize=8,
    )
    for ax in axes[0]:
        ax.set_xticks([])
        ax.set_yticks([])
    fractions = [
        r["proxy_summary"]["retained_crop_fraction"] for r in report["sensitivity"]
    ]
    axes[1, 0].bar(
        [str(t) + "°" for t in thresholds],
        fractions,
        color="#b5c7bf",
        label="Retained lower-slope proxy",
    )
    axes[1, 0].bar(
        [str(t) + "°" for t in thresholds],
        [1 - f for f in fractions],
        bottom=fractions,
        color="#c78146",
        label="Excluded / unknown",
    )
    for i, fraction in enumerate(fractions):
        axes[1, 0].text(i, 0.5, f"{fraction:.2%}\nretained", ha="center", fontsize=10)
    axes[1, 0].set(
        ylabel="Fraction of original historical cropland",
        ylim=(0, 1.04),
        xlabel="Fixed maximum-slope threshold (10° is primary)",
    )
    axes[1, 0].legend(
        loc="lower left", bbox_to_anchor=(0, 1.02), frameon=False, fontsize=8
    )
    colors_by_band = {"vv": "#456e8e", "vh": "#855c7c"}
    for band in ("vv", "vh"):
        key = band + "_median_delta_db"
        color = colors_by_band[band]
        delta = [r["changes"][-1][key] for r in report["sensitivity"]]
        axes[1, 1].scatter(
            thresholds, delta, color=color, s=55, label=band.upper() + " after proxy"
        )
        axes[1, 1].axhline(
            parent["changes"][-1][key],
            color=color,
            linestyle="--",
            linewidth=1,
            label=band.upper() + " original",
        )
    axes[1, 1].set(
        xticks=thresholds,
        xlabel="Fixed threshold (degrees)",
        ylabel="Median per-pixel backscatter change (dB)",
    )
    axes[1, 1].set_title("June 5 minus May 24: descriptive sensitivity", fontsize=11)
    axes[1, 1].legend(frameon=False, ncol=2, fontsize=8)
    for ax in axes[1]:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.15)
    fig.suptitle(
        "Ngenge | independent surface-slope risk proxy", x=0.09, ha="left", fontsize=16
    )
    fig.subplots_adjust(
        left=0.09, right=0.97, top=0.90, bottom=0.20, hspace=0.53, wspace=0.42
    )
    fig.text(
        0.09,
        0.12,
        "Surface model includes vegetation and structures. Derivatives use a 30m grid; nearest-neighbor transfer creates no finer terrain detail.",
        fontsize=9,
    )
    fig.text(
        0.09,
        0.085,
        "No threshold tuning, verified radar illumination, local-incidence / layover / shadow certification, crop labels or optical gap filling.",
        fontsize=9,
    )
    fig.text(
        0.09,
        0.05,
        "Radar remains ineligible for agricultural ranking. Optical evidence remains stale. Run "
        + report["run_id"],
        fontsize=9,
    )
    path = base / "kween-terrain.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    main()
