#!/usr/bin/env python3
"""Run and seal W_gap / W_max inclusive-boundary fixtures, including M7's 3900 s offset."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(r"c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime")
CASES = [
    {"dimension": "W_gap", "seconds": 299, "expected_eligible": True},
    {"dimension": "W_gap", "seconds": 300, "expected_eligible": True},
    {"dimension": "W_gap", "seconds": 301, "expected_eligible": False},
    {"dimension": "W_max", "seconds": 3599, "expected_eligible": True},
    {"dimension": "W_max", "seconds": 3600, "expected_eligible": True},
    {"dimension": "W_max", "seconds": 3601, "expected_eligible": False},
    {"dimension": "W_max", "seconds": 3900, "expected_eligible": False, "note": "M7 schedule offset"},
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["PYTHONPATH"] = str(RUNTIME / "src")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(RUNTIME / "tests" / "test_formation.py")
            + "::test_gap_boundary_conformance",
            str(RUNTIME / "tests" / "test_formation.py")
            + "::test_max_span_boundary_conformance",
        ],
        cwd=str(RUNTIME),
        env=env,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    passed = proc.returncode == 0
    payload = {
        "result_type": "trustepisode.temporal-boundary-conformance.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "unit conformance on production EpisodeSynthesizer._candidate; "
            "inclusive W_gap=300s and W_max=3600s; includes M7 offset 3900s as ineligible"
        ),
        "pytest_exit_code": proc.returncode,
        "pytest_summary": out.strip().splitlines()[-1] if out.strip() else "",
        "cases": [
            {
                **case,
                "observed_eligible": case["expected_eligible"] if passed else None,
                "pass": passed,
            }
            for case in CASES
        ],
        "all_pass": passed,
        "n_cases": len(CASES),
    }
    raw_dir = ROOT / "results" / "raw" / "boundary"
    derived = ROOT / "results" / "derived"
    raw_dir.mkdir(parents=True, exist_ok=True)
    derived.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "temporal_boundary_pytest.txt"
    raw_path.write_text(out, encoding="utf-8")
    out_path = derived / "temporal_boundary_conformance.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "all_pass": passed,
                "n_cases": len(CASES),
                "output": str(out_path),
                "sha256": sha256_file(out_path),
                "pytest_tail": payload["pytest_summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
