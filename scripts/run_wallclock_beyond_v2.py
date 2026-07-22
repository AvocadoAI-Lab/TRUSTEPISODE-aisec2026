#!/usr/bin/env python3
"""Corrected wall-clock beyond-horizon: quiet wait past revision deadline, then related SSH."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(r"c:\Users\admin\Desktop\aisec\sensel-caldera-linux-lab")
PAPER = Path(r"c:\Users\admin\Desktop\aisec\TRUSTEPISODE-aisec2026")
CONTRACTS = PAPER / "artifacts" / "contracts"
COMPOSE_FILES = ("compose.yml", "compose.ndr.yml", "compose.trustepisode.yml")
L_WM, W_REV = 120, 900
WAIT = L_WM + W_REV + 60

sys.path.insert(0, str(LAB / "scripts"))
from trustepisode_card_runner import Runner, digest_json  # noqa: E402
from trustepisode_snapshot import seal_run  # noqa: E402


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    cmd = ["docker", "compose"]
    for f in COMPOSE_FILES:
        cmd.extend(("-f", str(LAB / f)))
    cmd.extend(args)
    return subprocess.run(cmd, cwd=LAB, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def set_edr(on: bool) -> None:
    op = "start" if on else "stop"
    for service in ("target-linux", "target-linux-02"):
        if not on:
            compose(
                "exec",
                "-T",
                service,
                "sh",
                "-c",
                "mkdir -p /var/lib/trustepisode/forwarder && : > /var/lib/trustepisode/forwarder/authorized-stop",
            )
        compose("exec", "-T", service, "supervisorctl", op, "trustepisode-forwarder")
        if on:
            compose("exec", "-T", service, "rm", "-f", "/var/lib/trustepisode/forwarder/authorized-stop")


def set_ndr(on: bool) -> None:
    compose(
        "exec",
        "-T",
        "ndr-gateway",
        "trustepisode-spool-control",
        "start" if on else "stop",
        check=False,
    )


def main() -> int:
    run_id = "run-supp-l4wc-beyond-v2-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print("run", run_id, flush=True)
    set_edr(True)
    set_ndr(True)
    time.sleep(2)
    runner = Runner(LAB, CONTRACTS, run_id, "M3", "attack_only", 25.0, startup_delay_seconds=8.0)
    runner.startup_delay_seconds = 8.0
    manifest = runner.execute()
    print("phaseA valid", manifest.get("valid"), flush=True)
    if not manifest.get("valid"):
        return 1

    print(f"collectors OFF; quiet wait {WAIT}s", flush=True)
    set_edr(False)
    set_ndr(False)
    time.sleep(2)
    t0 = time.monotonic()
    time.sleep(WAIT)
    print("waited", round(time.monotonic() - t0, 1), flush=True)

    ssh = (
        "printf '%s\\n' 'TRUSTEPISODE_LATE_BEYOND' | "
        "ssh -F /opt/trustepisode/fixtures/ssh_config "
        "sensel-svc@172.30.12.10 -- /usr/bin/install -D -m 0600 /dev/stdin "
        "/home/sensel-svc/primary-action.txt"
    )
    rc = compose(
        "exec",
        "-T",
        "target-linux",
        "/opt/trustepisode/bin/trustepisode-endpoint-exec",
        "--",
        "/bin/bash",
        "--noprofile",
        "--norc",
        "-euo",
        "pipefail",
        "-c",
        ssh,
        check=False,
    )
    print("late ssh exit", rc.returncode, flush=True)
    print("collectors ON; flush", flush=True)
    set_edr(True)
    set_ndr(True)
    time.sleep(40)

    gt = LAB / "experiment-data" / "ground-truth" / run_id
    receipt = json.loads((gt / "offline_run_receipt.json").read_text(encoding="utf-8"))
    base = LAB / "experiment-data"
    receipt["evidence_end_offsets"] = {
        rel: (base / rel).stat().st_size if (base / rel).exists() else int(start)
        for rel, start in receipt["evidence_start_offsets"].items()
    }
    receipt["collection_end_unix_ns"] = time.time_ns()
    receipt["wallclock_late"] = {
        "kind": "beyond_v2",
        "wait_before_late_action_seconds": WAIT,
        "delivery_mode": "wall_clock_quiet_wait_then_related_action",
    }
    receipt["manifest_digest"] = digest_json(
        {k: v for k, v in receipt.items() if k != "manifest_digest"}
    )
    (gt / "offline_run_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    seal_run(LAB, CONTRACTS, run_id, LAB / "experiment-data" / "runs" / run_id)
    row = {
        "run_id": run_id,
        "tag": "l4_wallclock_beyond_v2",
        "status": "sealed",
        "sealed_path": str(LAB / "experiment-data" / "runs" / run_id),
        "wait_before_late_action_seconds": WAIT,
        "late_ability_exit": rc.returncode,
        "delivery_mode": "wall_clock_quiet_wait_then_related_action",
        "hold_seconds": WAIT,
        "observed_hold_seconds": WAIT,
    }
    wc_path = PAPER / "results" / "derived" / "supplemental_live_l4_wallclock.json"
    wc = json.loads(wc_path.read_text(encoding="utf-8"))
    wc.setdefault("runs", []).append(row)
    wc["beyond_sealed"] = sum(
        1 for x in wc["runs"] if "beyond" in x.get("tag", "") and x.get("status") == "sealed"
    )
    text = json.dumps(wc, indent=2, ensure_ascii=False) + "\n"
    wc_path.write_text(text, encoding="utf-8")
    (PAPER / "results" / "raw" / "supplemental_live" / "wallclock_l4_latest.json").write_text(
        text, encoding="utf-8"
    )
    print("SEALED", json.dumps(row), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
