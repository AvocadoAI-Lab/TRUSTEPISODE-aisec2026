#!/usr/bin/env python3
"""Camera-ready 3-panel figure in the oldmain Fig.4 layout, filled with sealed real data only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap


def mean_sd(block: dict) -> tuple[float, float]:
    return float(block["mean"]), float(block["sample_sd"] or 0.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "results",
    )
    parser.add_argument(
        "--table4",
        type=Path,
        default=Path(
            r"c:\Users\admin\Desktop\aisec\sensel-caldera-linux-lab\experiment-data"
            r"\final-results-amended\table4_amended_results.json"
        ),
    )
    args = parser.parse_args()

    derived = args.results / "derived"
    baselines = json.loads((derived / "formation_baselines_ablations.json").read_text(encoding="utf-8"))
    sens = json.loads((derived / "matching_sensitivity.json").read_text(encoding="utf-8"))
    table4 = json.loads(args.table4.read_text(encoding="utf-8"))

    by_builder = {item["builder"]: item["overall"] for item in baselines["builders"]}
    m2 = baselines["m2_analysis"]

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

    fig = plt.figure(figsize=(7.08, 2.32), constrained_layout=False)
    grid = fig.add_gridspec(
        1,
        3,
        width_ratios=(1.05, 1.15, 1.05),
        left=0.055,
        right=0.995,
        bottom=0.23,
        top=0.84,
        wspace=0.40,
    )

    # (a) Builder comparison — same visual language as oldmain dose-response panel.
    ax = fig.add_subplot(grid[0, 0])
    builders = ["EB1_time_window", "EB2_time_entity", "EB3_trustepisode"]
    labels_x = ["EB1\ntime", "EB2\ntime+ent.", "EB3\nTrustEp."]
    x = np.arange(len(builders))
    series = [
        ("Action cov.", "action_coverage", blue, "o", "-"),
        ("Episode F1", "episode_f1", orange, "s", "--"),
        ("Exact-complete", "exact_complete_recovery", green, "^", "-."),
    ]
    for name, key, color, marker, ls in series:
        means = []
        sds = []
        for b in builders:
            m, s = mean_sd(by_builder[b][key])
            means.append(m)
            sds.append(s)
        means_a = np.array(means)
        sds_a = np.array(sds)
        ax.fill_between(x, means_a - sds_a, means_a + sds_a, color=color, alpha=0.12, linewidth=0)
        ax.plot(
            x,
            means_a,
            label=name,
            color=color,
            marker=marker,
            linestyle=ls,
            markersize=3.2,
            markerfacecolor="white",
            markeredgewidth=0.8,
        )
    ax.set_xticks(x, labels_x)
    ax.set_ylim(-0.05, 1.08)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("Rate (mean ± sample SD)")
    ax.set_xlabel("Label-blind builder")
    ax.set_title("(a) Formation baselines (n=60)", fontweight="bold", pad=4)
    ax.grid(axis="y", color="0.88", linewidth=0.55)
    ax.legend(frameon=False, loc="lower left", handlelength=2.0, borderaxespad=0.2)

    # (b) Family × metric heatmap from amended Table 4 / exact-complete.
    ax = fig.add_subplot(grid[0, 1])
    families = [f"M{i}" for i in range(1, 7)]
    # rows: coverage (both modes pooled via offline EB3 cells), exact-complete,
    # concurrent contamination, attack-only contamination
    # Build from per-run EB3 rows for exact-complete; Table4 for coverage/contam.
    per_run = json.loads((args.results / "raw" / "formation_baselines_per_run.json").read_text(encoding="utf-8"))
    eb3_runs = [r for r in per_run if r["builder"] == "EB3_trustepisode"]

    def family_mean(card: str, key: str, mode: str | None = None) -> float:
        rows = [r for r in eb3_runs if r["card_id"] == card and (mode is None or r["mode"] == mode)]
        vals = [float(r[key]) for r in rows if r[key] is not None]
        return float(np.mean(vals)) if vals else float("nan")

    matrix = np.array(
        [
            [family_mean(f, "action_coverage") for f in families],
            [family_mean(f, "exact_complete_recovery") for f in families],
            [family_mean(f, "contamination", "concurrent_benign") for f in families],
            [family_mean(f, "episode_f1") for f in families],
        ]
    )
    cmap = LinearSegmentedColormap.from_list(
        "te_blue", ["#ffffff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"]
    )
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
    ax.set_xticks(np.arange(len(families)), families)
    ax.set_yticks(
        np.arange(4),
        ["coverage", "exact-comp.", "contam.\n(conc.)", "episode F1"],
    )
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix[i, j]
            ax.text(
                j,
                i,
                f"{val:.2f}",
                ha="center",
                va="center",
                fontsize=5.8,
                color="white" if val >= 0.55 else "black",
            )
    ax.set_title("(b) Family means under EB3", fontweight="bold", pad=4)
    ax.set_xlabel("Attack family")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=5.5)
    cbar.set_label("Rate", fontsize=6.0)

    # (c) M2 token recovery + matching sensitivity anchors (real sealed data).
    ax = fig.add_subplot(grid[0, 2])
    tokens = list(m2["per_token_recovery_rate"].items())
    # Short display names
    ylabels = []
    means = []
    for token, block in tokens:
        short = token.replace("command_family:", "").replace("network.", "net.")
        ylabels.append(short)
        means.append(float(block["mean"]))
    # Append sensitivity anchors as extra rows
    jac = next(c for c in sens["configs"] if c["label"] == "jaccard_0.75")
    ylabels.extend(["match F1\n(primary)", "match F1\n(Jacc.0.75)"])
    means.extend([float(sens["configs"][0]["episode_f1"]["mean"]), float(jac["episode_f1"]["mean"])])
    y = np.arange(len(ylabels))[::-1]
    colors = [blue] * len(tokens) + [orange, green]
    ax.hlines(y, 0, means, color="0.82", linewidth=0.9)
    for yi, mean, color in zip(y, means, colors):
        ax.plot(
            mean,
            yi,
            marker="o",
            markersize=4.0,
            color=color,
            markerfacecolor="white",
            markeredgewidth=0.9,
        )
    ax.set_yticks(y, ylabels)
    ax.set_xlim(-0.05, 1.08)
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("Rate")
    ax.set_title("(c) M2 tokens & match sens.", fontweight="bold", pad=4)
    ax.grid(axis="x", color="0.88", linewidth=0.55)
    ax.text(
        0.02,
        -0.22,
        "Blue: M2 token recovery (n=10). Orange/green: matching sensitivity F1 (n=60).",
        transform=ax.transAxes,
        fontsize=5.2,
        color="0.35",
        clip_on=False,
    )

    fig.suptitle(
        "SEALED FORMATION RESULTS — n=60 malicious runs (amended M1–M6 cohort)",
        fontsize=6.4,
        color="0.25",
        y=0.98,
    )

    out = args.results / "figures"
    out.mkdir(parents=True, exist_ok=True)
    pdf = out / "fig_formation_real_threepanel.pdf"
    png = out / "fig_formation_real_threepanel.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=220)
    # also publish into trustepisode_figures for LaTeX graphicspath convenience
    pub = Path(__file__).resolve().parents[1] / "trustepisode_figures" / "pdf"
    pub.mkdir(parents=True, exist_ok=True)
    fig.savefig(pub / "fig_formation_real_threepanel.pdf")
    fig.savefig(
        Path(__file__).resolve().parents[1] / "trustepisode_figures" / "png" / "fig_formation_real_threepanel.png",
        dpi=220,
    )
    print(json.dumps({"wrote": [str(pdf), str(png)], "source": "sealed_real_only"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
