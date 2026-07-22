#!/usr/bin/env python3
"""Generate simple formation comparison figure from sealed result JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"matplotlib required: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path(__file__).resolve().parents[1] / "results")
    args = parser.parse_args()
    data = json.loads(
        (args.results / "derived" / "formation_baselines_ablations.json").read_text(encoding="utf-8")
    )
    names = []
    f1 = []
    exact = []
    for item in data["builders"]:
        if not item["builder"].startswith(("EB", "ABL_no_hub")):
            continue
        if item["builder"].startswith("ABL") and item["builder"] != "ABL_no_hub_guard":
            continue
        names.append(item["builder"].replace("_", "\n"))
        f1.append(item["overall"]["episode_f1"]["mean"])
        exact.append(item["overall"]["exact_complete_recovery"]["mean"])
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    x = range(len(names))
    ax.bar([i - 0.18 for i in x], f1, width=0.36, label="Episode F1")
    ax.bar([i + 0.18 for i in x], exact, width=0.36, label="Exact-complete")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, fontsize=7)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.legend(frameon=False)
    ax.set_title("Formation baselines on sealed M1--M7 cohort (n=70)")
    out = args.results / "figures"
    out.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out / "formation_baselines.pdf")
    fig.savefig(out / "formation_baselines.png", dpi=160)
    print(json.dumps({"wrote": [str(out / "formation_baselines.pdf")]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
