#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sub_files = [
        root / "main.tex",
        root / "sections/intro.tex",
        root / "sections/related.tex",
        root / "sections/arch.tex",
        root / "sections/exps.tex",
        root / "sections/conc.tex",
        root / "sections/appendix_submission.tex",
        *sorted((root / "results/tables").glob("*.tex")),
    ]
    sub = "\n".join(p.read_text(encoding="utf-8") for p in sub_files)
    labels = set(re.findall(r"\\label\{([^}]+)\}", sub))
    refs: set[str] = set()
    for match in re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", sub):
        for part in match.split(","):
            refs.add(part.strip())
    missing = sorted(refs - labels)
    forbidden = [
        "demonstrates robustness",
        "validates calibration",
        "production-ready",
        "supports deployment generalization",
    ]
    hits = [phrase for phrase in forbidden if phrase.lower() in sub.lower()]
    data = json.loads(
        (root / "results/derived/formation_baselines_ablations.json").read_text(encoding="utf-8")
    )
    eb3_builder = next(item for item in data["builders"] if item["builder"] == "EB3_trustepisode")
    eb3 = eb3_builder["overall"]
    replay = json.loads(
        (root / "results/derived/formation_replay_equality.json").read_text(encoding="utf-8")
    )
    cohort_runs = data["cohort"]["malicious_runs"]
    action_coverage = eb3["action_coverage"]
    result_title = (root / "main.tex").read_text(encoding="utf-8")
    title_ok = "Auditable Evidence Contracts for AI-Assisted EDR/NDR Investigation" in result_title
    data_consistency = {
        "eb3_run_count_matches_cohort": eb3_builder["malicious_runs"] == cohort_runs,
        "action_coverage_defined_for_cohort": action_coverage["defined"] == cohort_runs,
        "action_coverage_is_probability": 0.0 <= action_coverage["mean"] <= 1.0,
        "replay_run_count_matches_cohort": (
            replay["byte_equal_pass_count"] + replay["byte_equal_fail_count"] == cohort_runs
        ),
        "replay_has_no_byte_mismatch": replay["byte_equal_fail_count"] == 0,
    }
    report = {
        "missing_refs_submission": missing,
        "forbidden_hits": hits,
        "title_ok": title_ok,
        "table6_removed": "entity-public-comparison" not in sub,
        "macros_file_exists": (root / "results/tables/result_macros.tex").exists(),
        "cohort_runs": cohort_runs,
        "eb3_action_coverage_mean": action_coverage["mean"],
        "data_consistency": data_consistency,
    }
    print(json.dumps(report, indent=2))
    report_checks = [
        title_ok,
        report["table6_removed"],
        report["macros_file_exists"],
        *data_consistency.values(),
    ]
    return 1 if missing or hits or not all(report_checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
