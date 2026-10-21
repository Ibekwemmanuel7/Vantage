"""Local scientific preview of bounded sightlines; no field validation claim."""

# ruff: noqa: E402
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_uganda_demo as source  # noqa: F401
import rasterio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm


def main():
    base = ROOT / "outputs/africa/visibility"
    pointer = json.loads((base / "latest.json").read_text())
    root = base / pointer["directory"]
    report = json.loads((root / pointer["manifest"]).read_text())
    row = report["observations"][-1]
    with rasterio.open(root / report["assets"]["elevation"]["href"]) as ds:
        elevation = ds.read(1)
        bounds = ds.bounds
    with rasterio.open(root / row["assets"]["classes"]["href"]) as ds:
        classes = ds.read(1)
        target_bounds = ds.bounds
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), layout="constrained")
    image = axes[0].imshow(
        elevation,
        extent=[
            bounds.left / 1000,
            bounds.right / 1000,
            bounds.bottom / 1000,
            bounds.top / 1000,
        ],
        cmap="terrain",
    )
    axes[0].add_patch(
        plt.Rectangle(
            (target_bounds.left / 1000, target_bounds.bottom / 1000),
            (target_bounds.right - target_bounds.left) / 1000,
            (target_bounds.top - target_bounds.bottom) / 1000,
            fill=False,
            edgecolor="black",
        )
    )
    axes[0].set_title("Expanded 30 m surface model\nBlack box: sightline origins")
    fig.colorbar(image, ax=axes[0], label="DSM elevation (m)", shrink=0.7)
    cmap = ListedColormap(["#777777", "#7fcdbb", "#d73027", "#fec44f"])
    image = axes[1].imshow(
        classes,
        cmap=cmap,
        norm=BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], 4),
        extent=[
            target_bounds.left / 1000,
            target_bounds.right / 1000,
            target_bounds.bottom / 1000,
            target_bounds.top / 1000,
        ],
    )
    axes[1].set_title(
        "5 June 2023: sampled sightlines\n15 m–5 km toward sensor; 5 m guard"
    )
    bar = fig.colorbar(image, ax=axes[1], ticks=[0, 1, 2, 3], shrink=0.7)
    bar.ax.set_yticklabels(
        ["Unknown", "Clear within 5 km", "Obstruction risk", "Clearance guard"]
    )
    for ax in axes:
        ax.set_xlabel("UTM 36N easting (km)")
        ax.set_ylabel("Northing (km)")
    fig.suptitle(
        "Kween research locality proxy — bounded terrain check, not confirmed radar illumination\nHistorical crop mask is not a verified field boundary",
        fontsize=12,
    )
    fig.savefig(base / "kween-visibility.png", dpi=160)
    plt.close(fig)
    print(base / "kween-visibility.png")


if __name__ == "__main__":
    main()
