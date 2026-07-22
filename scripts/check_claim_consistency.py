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
    eb3 = next(item for item in data["builders"] if item["builder"] == "EB3_trustepisode")["overall"]
    replay = json.loads(
        (root / "results/derived/formation_replay_equality.json").read_text(encoding="utf-8")
    )
    assert abs(eb3["action_coverage"]["mean"] - 0.9583333333333334) < 1e-9 or abs(
        eb3["action_coverage"]["mean"] - 0.958
    ) < 1e-3
    assert replay["byte_equal_fail_count"] == 0
    report = {
        "missing_refs_submission": missing,
        "forbidden_hits": hits,
        "title_ok": "Deterministic and Replayable Contract" in (root / "main.tex").read_text(
            encoding="utf-8"
        ),
        "table6_removed": "entity-public-comparison" not in sub,
        "macros_file_exists": (root / "results/tables/result_macros.tex").exists(),
    }
    print(json.dumps(report, indent=2))
    return 1 if missing or hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
