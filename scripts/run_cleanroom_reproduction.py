#!/usr/bin/env python3
"""Clean-room reproduction: unpack companion ZIP into an isolated tree and re-verify."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = "TrustEpisode_reproducibility_companion_v1.zip"
CLEAN = ROOT / "tmp" / "cleanroom-aisec"
REPORT = ROOT / "CLEANROOM_REPRODUCTION_REPORT_AISEC_20260724.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path) -> dict:
    env = os.environ.copy()
    runtime_src = (cwd / "experiment_runtime" / "src").resolve()
    inherited = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(runtime_src) + (
        os.pathsep + inherited if inherited else ""
    )
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    return {
        "cmd": cmd,
        "cwd": ".",
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip().splitlines()[-5:],
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-5:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    zip_path = ROOT / ZIP_NAME
    side = ROOT / "TrustEpisode_reproducibility_companion_v1.sha256"
    if not zip_path.exists():
        raise SystemExit(f"missing companion zip: {zip_path}")
    digest = sha256_file(zip_path)
    side_text = side.read_text(encoding="utf-8").strip() if side.exists() else ""
    if side_text and digest not in side_text:
        raise SystemExit(f"sidecar digest mismatch: file={digest} sidecar={side_text}")

    if CLEAN.exists():
        shutil.rmtree(CLEAN)
    CLEAN.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(CLEAN)

    commands = [
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
    checks = [run(command, CLEAN) for command in commands]

    all_ok = all(c["ok"] for c in checks)
    payload = {
        "result_type": "trustepisode.cleanroom-reproduction.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "companion_zip": ZIP_NAME,
        "companion_sha256": digest,
        "cleanroom_root": "isolated extraction; local path omitted",
        "checks": checks,
        "all_pass": all_ok,
    }
    out_json = ROOT / "results" / "derived" / "cleanroom_reproduction.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Clean-room reproduction report (AISec revision)",
        "",
        f"- Generated (UTC): `{payload['generated_at']}`",
        f"- Companion ZIP: `{ZIP_NAME}`",
        f"- Companion SHA-256: `{digest}`",
        "- Clean-room root: isolated extraction (local path omitted)",
        f"- Overall: **{'PASS' if all_ok else 'FAIL'}**",
        "",
        "## Checks",
        "",
    ]
    for item in checks:
        status = "PASS" if item["ok"] else "FAIL"
        if len(item["cmd"]) > 2 and item["cmd"][1:3] == ["-m", "pytest"]:
            label = "experiment_runtime/tests"
        else:
            label = Path(item["cmd"][1]).name if len(item["cmd"]) > 1 else item["cmd"][0]
        lines.append(f"### `{label}` — {status} (exit {item['exit_code']})")
        lines.append("")
        if item["stdout_tail"]:
            lines.append("```")
            lines.extend(item["stdout_tail"])
            lines.append("```")
            lines.append("")
        if item["stderr_tail"] and not item["ok"]:
            lines.append("```")
            lines.extend(item["stderr_tail"])
            lines.append("```")
            lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "Every command above executed with the extracted archive as its working directory.",
            "The companion validates contracts and the imported runtime's extracted-archive origin;",
            "then runs all 38 packaged reference-runtime tests;",
            "re-executes A1--A12, A--G, AB0--AB3, AI0--AI7, T1--T8, and temporal boundary",
            "fixtures; regenerates tables; and checks sealed",
            "determinism, baseline, M2, supplemental, and local-model summaries.",
            "It byte-compares both frozen local-model raw/derived files without re-running Ollama.",
            "It does not re-execute live collection or cohort re-synthesis from omitted raw lab bundles.",
            "",
            f"Machine-readable: `results/derived/cleanroom_reproduction.json` (sha256 `{sha256_file(out_json)}`).",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"all_pass": all_ok, "report": str(REPORT), "json": str(out_json)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
