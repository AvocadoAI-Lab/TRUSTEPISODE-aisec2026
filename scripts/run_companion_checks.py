#!/usr/bin/env python3
"""Run every executable check promised by the portable companion README."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = (ROOT / "experiment_runtime" / "src").resolve()
COMMANDS = [
    [sys.executable, "artifacts/contracts/validate_contracts.py"],
    [sys.executable, "scripts/verify_runtime_origin.py"],
    [sys.executable, "-m", "pytest", "-q", "experiment_runtime/tests"],
    [sys.executable, "scripts/run_audit_conformance_a12.py"],
    [sys.executable, "scripts/run_taxonomy_ag.py"],
    [sys.executable, "scripts/run_audit_baselines_ab.py"],
    [sys.executable, "scripts/run_agent_boundary_conformance.py"],
    [sys.executable, "scripts/run_targeted_cards.py"],
    [sys.executable, "scripts/run_temporal_boundary_fixtures.py", "--check-only"],
    [sys.executable, "scripts/generate_tables.py"],
    [sys.executable, "scripts/verify_claims.py"],
]


def main() -> int:
    env = os.environ.copy()
    inherited = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(RUNTIME_SRC) + (
        os.pathsep + inherited if inherited else ""
    )
    checks = []
    for command in COMMANDS:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        item = {
            "command": command[1:],
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "").strip().splitlines()[-3:],
            "stderr_tail": (proc.stderr or "").strip().splitlines()[-3:],
            "ok": proc.returncode == 0,
        }
        checks.append(item)
        if not item["ok"]:
            break
    payload = {"all_pass": len(checks) == len(COMMANDS) and all(c["ok"] for c in checks), "checks": checks}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
