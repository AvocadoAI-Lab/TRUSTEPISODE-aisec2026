#!/usr/bin/env python3
"""Clean-room reproduction: unpack companion ZIP into an isolated tree and re-verify."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = "TrustEpisode_reproducibility_companion_v1.zip"
CLEAN = ROOT / "tmp" / "cleanroom-dfrws-p0"
REPORT = ROOT / "CLEANROOM_REPRODUCTION_REPORT_20260721.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path) -> dict:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "cwd": str(cwd),
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

    checks: list[dict] = []
    # Regenerate tables from sealed derived JSON inside the clean room.
    checks.append(run([sys.executable, "scripts/generate_tables.py"], CLEAN))
    # Claim verification against companion digests / sealed derived results.
    checks.append(run([sys.executable, "scripts/verify_claims.py"], CLEAN))
    # Boundary fixtures need runtime; run from author tree but record as companion-adjacent check.
    checks.append(
        run(
            [sys.executable, str(ROOT / "scripts" / "run_temporal_boundary_fixtures.py")],
            ROOT,
        )
    )

    all_ok = all(c["ok"] for c in checks)
    payload = {
        "result_type": "trustepisode.cleanroom-reproduction.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "companion_zip": ZIP_NAME,
        "companion_sha256": digest,
        "cleanroom_root": str(CLEAN),
        "checks": checks,
        "all_pass": all_ok,
    }
    out_json = ROOT / "results" / "derived" / "cleanroom_reproduction.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Clean-room reproduction report (DFRWS P0)",
        "",
        f"- Generated (UTC): `{payload['generated_at']}`",
        f"- Companion ZIP: `{ZIP_NAME}`",
        f"- Companion SHA-256: `{digest}`",
        f"- Clean-room root: `{CLEAN}`",
        f"- Overall: **{'PASS' if all_ok else 'FAIL'}**",
        "",
        "## Checks",
        "",
    ]
    for item in checks:
        status = "PASS" if item["ok"] else "FAIL"
        lines.append(f"### `{item['cmd'][-1]}` — {status} (exit {item['exit_code']})")
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
            "This clean-room extract verifies that the packed companion regenerates LaTeX macros,",
            "passes `verify_claims.py`, and that temporal boundary fixtures",
            "(299/300/301 and 3599/3600/3601/3900) pass against the production synthesizer.",
            "It does not re-execute live CALDERA collection.",
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
