#!/usr/bin/env python3
"""Optional scorer evaluation — fail-closed when sealed labels are insufficient."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "results" / "raw" / "scorer"
    out.mkdir(parents=True, exist_ok=True)
    status = {
        "executed": False,
        "scheme": "B_design_only",
        "reason": (
            "Insufficient sealed calibration/locked labels for leakage-free run-level "
            "held-out ranking; group gate 50/50/10 unmet. No AUPRC/AUROC reported."
        ),
        "models_not_fitted": ["ML0_RULE_SCORE", "ML1_D_ONLY", "ML2_D_PLUS_C", "ML3_UNCONSTRAINED"],
        "claim": "Scorer/calibrator remain design interfaces only in this submission.",
    }
    (out / "STATUS.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
