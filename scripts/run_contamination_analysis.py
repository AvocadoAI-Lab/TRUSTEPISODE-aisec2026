#!/usr/bin/env python3
"""Contamination trade-off analysis from fair baseline per-run results."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path(__file__).resolve().parents[1] / "results")
    args = parser.parse_args()
    per_run = json.loads((args.results / "raw" / "fair_baselines" / "per_run.json").read_text(encoding="utf-8"))
    builders = sorted({r["builder"] for r in per_run})
    summary = {}
    for b in builders:
        rows = [r for r in per_run if r["builder"] == b]
        conc = [r for r in rows if r["mode"] == "concurrent_benign"]
        summary[b] = {
            "overall_contamination_mean": statistics.fmean(
                [r["contamination"] for r in rows if r["contamination"] is not None]
            ),
            "concurrent_contamination_mean": statistics.fmean(
                [r["contamination"] for r in conc if r["contamination"] is not None]
            ),
            "concurrent_coverage_mean": statistics.fmean(
                [r["action_coverage"] for r in conc if r["action_coverage"] is not None]
            ),
            "attack_only_contamination_mean": statistics.fmean(
                [
                    r["contamination"]
                    for r in rows
                    if r["mode"] == "attack_only" and r["contamination"] is not None
                ]
            ),
        }
    # Pareto points: coverage vs contamination for concurrent mode
    pareto = []
    for b in builders:
        conc = [r for r in per_run if r["builder"] == b and r["mode"] == "concurrent_benign"]
        pareto.append(
            {
                "builder": b,
                "mean_coverage": statistics.fmean([r["action_coverage"] for r in conc]),
                "mean_contamination": statistics.fmean([r["contamination"] for r in conc]),
            }
        )
    payload = {
        "result_type": "trustepisode.contamination-tradeoff.v1",
        "summary_by_builder": summary,
        "concurrent_pareto": pareto,
        "interpretation": (
            "On the sealed concurrent-benign subset, EB1_SLIDING_TIME through EB4_TRUSTEPISODE "
            "share identical mean contamination. Relative to legacy EB0_FIXED_BIN_300s, "
            "completeness improves while mean contamination remains the same at the overall "
            "macro level. Sliding entity does not reduce contamination versus sliding time on "
            "this cohort. TrustEpisode therefore shows a completeness gain versus fixed bins "
            "without a contamination improvement versus fair sliding baselines."
        ),
    }
    out = args.results / "derived" / "contamination_tradeoff.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(pareto, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
