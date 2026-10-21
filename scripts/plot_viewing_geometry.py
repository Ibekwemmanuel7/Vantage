"""Show approximate local incidence and facet risks without claiming shadow-free crops."""

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
    base = ROOT / "outputs/africa/viewing"
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    report = json.loads((root / pointer["manifest"]).read_text())
    row = report["observations"][-1]
    with rasterio.open(root / row["assets"]["radar_angles"]["href"]) as ds:
        angles = ds.read()
    with rasterio.open(root / row["assets"]["radar_classes"]["href"]) as ds:
        classes = ds.read(1)
    crop_info = json.loads((ROOT / "docs/africa/KWEEN_RUN.json").read_text())
    crop_root = ROOT / "outputs/africa/kween" / crop_info["plan_sha256"][:20]
    with rasterio.open(crop_root / report["context"]["crop_asset"]) as ds:
        crop = ds.read(1).astype(bool)
    fig, axes = plt.subplots(
        2, 2, figsize=(13, 11), gridspec_kw={"height_ratios": [1.4, 1]}
    )
    image = axes[0, 0].imshow(angles[1], cmap="viridis", vmin=0, vmax=90)
    axes[0, 0].set_title("June 5 | approximate local incidence, whole box", fontsize=11)
    fig.colorbar(
        image,
        ax=axes[0, 0],
        fraction=0.045,
        pad=0.03,
        label="Angle to approximate surface normal (degrees)",
    )
    colors = ["#72777d", "#c1d1dc", "#cc884d", "#865f89", "#e3c469"]
    axes[0, 1].imshow(
        classes,
        cmap=ListedColormap(colors),
        norm=BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], 5),
    )
    axes[0, 1].set_title("June 5 | local facet risk classes, whole box", fontsize=11)
    labels = [
        "Unknown",
        "Locally unflagged; illumination unconfirmed",
        "Local range-reversal risk",
        "Back-facing facet risk",
        "Near-normal / grazing-angle guard",
    ]
    axes[0, 1].legend(
        handles=[
            Patch(facecolor=color, label=label) for color, label in zip(colors, labels)
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.015),
        frameon=False,
        fontsize=8,
    )
    for ax in axes[0]:
        ax.set_xticks([])
        ax.set_yticks([])
    valid = crop & np.isfinite(angles).all(axis=0)
    for band, color, label in [
        (0, "#456e8e", "Nominal ellipsoid incidence"),
        (1, "#855c7c", "Approximate local incidence"),
    ]:
        values = angles[band][valid]
        axes[1, 0].hist(
            values,
            bins=np.arange(10, 61),
            weights=np.full(len(values), 1 / len(values)),
            histtype="step",
            linewidth=1.5,
            color=color,
            label=label,
        )
    axes[1, 0].set(
        xlabel="Incidence (degrees; 1° bins)",
        ylabel="Fraction of historical-cropland analysis cells",
    )
    axes[1, 0].legend(frameon=False, fontsize=9)
    axes[1, 0].grid(axis="y", alpha=0.15)
    axes[1, 0].spines[["top", "right"]].set_visible(False)
    axes[1, 1].axis("off")
    table_rows = []
    for observation in report["observations"]:
        summary = observation["geometry_summary"]
        table_rows.append(
            [
                observation["acquired_at"][5:10],
                f"{100 * summary['locally_unflagged_crop_fraction']:.1f}%",
                f"{observation['annotation_check']['incidence_residual_max_degrees']:.4f}°",
            ]
        )
    table = axes[1, 1].table(
        cellText=table_rows,
        colLabels=["Date", "Crop cells locally unflagged", "Max annotation residual"],
        cellLoc="center",
        loc="upper center",
        colWidths=[0.15, 0.45, 0.4],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.8)
    axes[1, 1].text(
        0.02,
        0.46,
        "Annotation agreement checks internal consistency.\nIt is not measured real-world angle accuracy.\n\nDistant-terrain shadow: NOT CHECKED\nTrusted-processor agreement: NOT CHECKED\nIndependent field outcomes: 0",
        transform=axes[1, 1].transAxes,
        fontsize=10,
        va="top",
        linespacing=1.45,
    )
    fig.suptitle(
        "Ngenge | acquisition-specific local viewing geometry",
        x=0.09,
        ha="left",
        fontsize=16,
    )
    fig.subplots_adjust(
        left=0.09, right=0.97, top=0.90, bottom=0.21, hspace=0.6, wspace=0.4
    )
    fig.text(
        0.09,
        0.12,
        "Three SAFE-checksum-verified product annotations. No orbital or spatial extrapolation. 30m DSM normals; nearest transfer to radar grid.",
        fontsize=9,
    )
    fig.text(
        0.09,
        0.085,
        "Maps show the entire box. Local risks occur outside the historical crop mask. Analysis cells are correlated, not validation samples.",
        fontsize=9,
    )
    fig.text(
        0.09,
        0.05,
        "No complete illumination certification, crop-condition labels, optical gap filling or agricultural ranking. Run "
        + report["run_id"],
        fontsize=9,
    )
    path = base / "kween-viewing.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    main()
