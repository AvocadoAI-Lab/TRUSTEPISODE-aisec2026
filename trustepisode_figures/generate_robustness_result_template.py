#!/usr/bin/env python3
"""Generate the illustrative camera-ready template used by Figure 4."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap


ROOT = Path(__file__).resolve().parent
PDF = ROOT / "pdf" / "fig10_adversarial_robustness_template.pdf"
SVG = ROOT / "svg" / "fig10_adversarial_robustness_template.svg"
PNG = ROOT / "png" / "fig10_adversarial_robustness_template.png"


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.0,
            "axes.titlesize": 7.5,
            "axes.labelsize": 7.0,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "legend.fontsize": 6.2,
            "axes.linewidth": 0.65,
            "lines.linewidth": 1.25,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    blue = "#0072B2"
    orange = "#D55E00"
    green = "#009E73"
    gray = "#6B7280"

    fig = plt.figure(figsize=(7.08, 2.32), constrained_layout=False)
    grid = fig.add_gridspec(
        1,
        3,
        width_ratios=(1.02, 1.20, 1.08),
        left=0.055,
        right=0.995,
        bottom=0.23,
        top=0.84,
        wspace=0.38,
    )

    # (a) Dose-response: report normalized retention so heterogeneous operators
    # can share a camera-ready summary axis. Replace with paired run estimates.
    ax = fig.add_subplot(grid[0, 0])
    dose = np.arange(4)
    series = [
        ("Action cov.", np.array([1.00, 0.95, 0.86, 0.73]), blue, "o", "-"),
        ("Episode F1", np.array([1.00, 0.91, 0.77, 0.59]), orange, "s", "--"),
        ("Eligibility", np.array([1.00, 0.98, 0.92, 0.82]), green, "^", "-."),
    ]
    for idx, (label, values, color, marker, linestyle) in enumerate(series):
        half_width = np.array([0.0, 0.025, 0.04, 0.055]) + idx * 0.003
        ax.fill_between(
            dose,
            values - half_width,
            values + half_width,
            color=color,
            alpha=0.12,
            linewidth=0,
        )
        ax.plot(
            dose,
            values,
            label=label,
            color=color,
            marker=marker,
            linestyle=linestyle,
            markersize=3.2,
            markerfacecolor="white",
            markeredgewidth=0.8,
        )
    ax.axhline(1.0, color="0.45", linewidth=0.65, linestyle=":")
    ax.set_xticks(dose, ["Base", "Low", "Med.", "High"])
    ax.set_ylim(0.48, 1.04)
    ax.set_yticks([0.5, 0.7, 0.9, 1.0])
    ax.set_ylabel("Retention vs. base")
    ax.set_xlabel("Registered perturbation dose")
    ax.set_title("(a) Paired dose-response", fontweight="bold", pad=4)
    ax.grid(axis="y", color="0.88", linewidth=0.55)
    ax.legend(frameon=False, loc="lower left", handlelength=2.0, borderaxespad=0.2)

    # (b) Fraction of runs that move to a worse state on each Table 2 axis.
    ax = fig.add_subplot(grid[0, 1])
    transition_pct = np.array(
        [
            [4, 11, 2, 1, 3, 0, 86],
            [1, 8, 5, 4, 14, 9, 13],
            [0, 13, 64, 46, 57, 8, 71],
            [1, 3, 2, 4, 19, 27, 7],
            [9, 26, 3, 2, 8, 1, 92],
        ]
    )
    cmap = LinearSegmentedColormap.from_list("trustepisode_blue", ["#F3F6F8", blue])
    image = ax.imshow(transition_pct, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    xlabels = ["Drop", "Gap", "Delay", "Reord.", "Clock", "Dup.", "Outage"]
    ylabels = ["coverage", "provenance", "lateness", "contradiction", "calibration"]
    ax.set_xticks(np.arange(len(xlabels)), xlabels, rotation=38, ha="right")
    ax.set_yticks(np.arange(len(ylabels)), ylabels)
    for row in range(transition_pct.shape[0]):
        for col in range(transition_pct.shape[1]):
            value = transition_pct[row, col]
            text_color = "white" if value >= 55 else "#111827"
            ax.text(col, row, f"{value}", ha="center", va="center", fontsize=5.4, color=text_color)
    ax.set_title("(b) Runs with worse $U$ state (%)", fontweight="bold", pad=4)
    cbar = fig.colorbar(image, ax=ax, fraction=0.038, pad=0.025)
    cbar.set_ticks([0, 50, 100])
    cbar.ax.tick_params(labelsize=5.7, length=2)
    for spine in ax.spines.values():
        spine.set_linewidth(0.55)

    # (c) Compact time-to-event summary. The final paper should use KM curves
    # in the supplement when censoring is material.
    ax = fig.add_subplot(grid[0, 2])
    labels = ["EDR / 120 s", "EDR / 600 s", "NDR / 120 s", "NDR / 600 s"]
    y = np.arange(len(labels))[::-1]
    detected = np.array([31, 35, 44, 48])
    detected_lo = np.array([25, 28, 35, 39])
    detected_hi = np.array([39, 43, 54, 59])
    stable = np.array([168, 706, 208, 752])
    stable_lo = np.array([142, 632, 176, 680])
    stable_hi = np.array([201, 812, 251, 891])
    ax.errorbar(
        detected,
        y + 0.11,
        xerr=np.vstack([detected - detected_lo, detected_hi - detected]),
        fmt="o",
        markersize=3.5,
        color=blue,
        markerfacecolor="white",
        capsize=2,
        label="Health detected",
    )
    ax.errorbar(
        stable,
        y - 0.11,
        xerr=np.vstack([stable - stable_lo, stable_hi - stable]),
        fmt="s",
        markersize=3.4,
        color=orange,
        markerfacecolor="white",
        capsize=2,
        label="Stable recovery",
    )
    ax.set_xscale("log")
    ax.set_xlim(20, 1200)
    ax.set_xticks([30, 60, 120, 300, 600, 900], ["30", "60", "120", "300", "600", "900"])
    ax.set_yticks(y, labels)
    ax.set_xlabel("Seconds (log scale)")
    ax.set_title("(c) Physical-outage timing", fontweight="bold", pad=4)
    ax.grid(axis="x", color="0.88", linewidth=0.55)
    ax.legend(
        frameon=False,
        loc="center",
        bbox_to_anchor=(0.62, 0.50),
        ncol=1,
        borderaxespad=0,
        columnspacing=0.8,
        handlelength=1.4,
    )

    for axis in fig.axes:
        if axis is not cbar.ax:
            axis.tick_params(width=0.55, length=2.3)
            axis.spines["top"].set_visible(False)
            axis.spines["right"].set_visible(False)

    fig.text(
        0.5,
        0.94,
        "ILLUSTRATIVE DATA - CAMERA-READY LAYOUT TARGET - REPLACE BEFORE SUBMISSION",
        ha="center",
        va="center",
        fontsize=6.4,
        fontweight="bold",
        color=gray,
    )

    for path in (PDF, SVG, PNG):
        path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF, bbox_inches="tight")
    fig.savefig(SVG, bbox_inches="tight")
    fig.savefig(PNG, dpi=300, bbox_inches="tight")
    # Matplotlib writes path-data lines with trailing spaces. Normalize them so
    # the generated SVG passes repository whitespace checks.
    svg_text = SVG.read_text(encoding="utf-8")
    SVG.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )
    plt.close(fig)


if __name__ == "__main__":
    main()
