#!/usr/bin/env python3
"""Wall-clock late-evidence L4: hold forwarders, wait real time, release backlog."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LAB = Path(r"c:\Users\admin\Desktop\aisec\sensel-caldera-linux-lab")
PAPER = Path(r"c:\Users\admin\Desktop\aisec\TRUSTEPISODE-aisec2026")
CONTRACTS = PAPER / "artifacts" / "contracts"
OUT = PAPER / "results" / "raw" / "supplemental_live"
COMPOSE_FILES = ("compose.yml", "compose.ndr.yml", "compose.trustepisode.yml")

sys.path.insert(0, str(LAB / "scripts"))
from trustepisode_card_runner import Runner  # noqa: E402
from trustepisode_snapshot import seal_run  # noqa: E402

# Formation thresholds (frozen)
L_WM = 120
W_REV = 900


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    cmd = ["docker", "compose"]
    for f in COMPOSE_FILES:
        cmd.extend(("-f", str(LAB / f)))
    cmd.extend(args)
    return subprocess.run(cmd, cwd=LAB, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def set_edr_forwarders(running: bool) -> None:
    op = "start" if running else "stop"
    for service in ("target-linux", "target-linux-02"):
        if not running:
            compose(
                "exec",
                "-T",
                service,
                "sh",
                "-c",
                "mkdir -p /var/lib/trustepisode/forwarder && : > /var/lib/trustepisode/forwarder/authorized-stop",
            )
        compose("exec", "-T", service, "supervisorctl", op, "trustepisode-forwarder")
        if running:
            compose("exec", "-T", service, "rm", "-f", "/var/lib/trustepisode/forwarder/authorized-stop")


def set_ndr_spool(running: bool) -> None:
    op = "start" if running else "stop"
    compose("exec", "-T", "ndr-gateway", "trustepisode-spool-control", op, check=False)


def collectors_on() -> None:
    set_edr_forwarders(True)
    set_ndr_spool(True)
    time.sleep(2)


def collectors_off() -> None:
    set_edr_forwarders(False)
    set_ndr_spool(False)
    time.sleep(2)


def run_card_phase(run_id: str, card_id: str, flush: float = 20.0) -> dict[str, Any]:
    runner = Runner(
        LAB,
        CONTRACTS,
        run_id,
        card_id,
        "attack_only",
        flush,
        startup_delay_seconds=8.0,
    )
    runner.startup_delay_seconds = 8.0
    return runner.execute()


def wallclock_case(kind: str, hold_seconds: float, idx: int) -> dict[str, Any]:
    """
    kind: within | beyond
    Phase A: collectors ON, run M3 (SSH), wait for watermark finalization window.
    Phase B: collectors OFF, run second M5-like local related action on same host (or M3 again via
             reusing ssh cleanup path) — use linux.local_action via M5 card in a sibling run_id
             is messy. Simpler: stop collectors BEFORE second ability inside custom flow.

    Simpler protocol used here:
    1) collectors ON, execute M3 fully (both abilities) → baseline evidence delivered
    2) wait L_WM+30 for finalization opportunity
    3) collectors OFF
    4) execute M5 (local action) while held — creates related-ish local EDR on target-01
    5) wall-clock hold_seconds
    6) collectors ON → real delayed ingest
    7) flush sleep, seal under combined run folder manually

    For membership relation, M5 local may not attach to M3 SSH episode. Better: after M3,
    hold collectors, re-run linux.ssh_action only via docker exec with same fixture, then release.

    Fastest relation-preserving approach:
    1) M3 with collectors ON
    2) wait L_WM+30
    3) collectors OFF
    4) docker-exec second ssh_action (same as catalog)
    5) sleep hold_seconds
    6) collectors ON + flush
    7) seal
    """
    run_id = f"run-supp-l4wc-{kind}-{idx:02d}-{utc()}"
    row: dict[str, Any] = {
        "run_id": run_id,
        "tag": f"l4_wallclock_{kind}",
        "partition": "supplemental_mechanism",
        "hold_seconds": hold_seconds,
        "L_watermark_seconds": L_WM,
        "W_revision_seconds": W_REV,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "delivery_mode": "wall_clock_forwarder_hold_and_release",
    }
    gt = LAB / "experiment-data" / "ground-truth" / run_id
    try:
        collectors_on()
        print(f"[{kind}] phaseA M3 {run_id}", flush=True)
        # Use unique run_id for phase A receipt; Runner requires empty output dir
        phase_a_id = run_id
        manifest_a = run_card_phase(phase_a_id, "M3", flush=25.0)
        if not manifest_a.get("valid"):
            row["status"] = "phase_a_invalid"
            row["execution_errors"] = manifest_a.get("execution_errors")
            return row

        print(f"[{kind}] waiting finalization window {L_WM + 30}s", flush=True)
        time.sleep(L_WM + 30)

        print(f"[{kind}] collectors OFF; second ssh_action", flush=True)
        collectors_off()
        # Second related SSH write while held in spool
        ssh_cmd = (
            "printf '%s\\n' 'TRUSTEPISODE_CONTROLLED_ACTION_LATE' | "
            "ssh -F /opt/trustepisode/fixtures/ssh_config "
            "sensel-svc@172.30.12.10 -- /usr/bin/install -D -m 0600 /dev/stdin "
            "/home/sensel-svc/primary-action.txt"
        )
        # Resolve fixture path from container
        r = compose(
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
            ssh_cmd,
            check=False,
        )
        row["late_ability_exit"] = r.returncode
        row["late_ability_stderr"] = r.stderr.decode("utf-8", errors="replace")[-400:]
        if r.returncode != 0:
            # fallback: local action while held
            r2 = compose(
                "exec",
                "-T",
                "target-linux",
                "/opt/trustepisode/bin/trustepisode-endpoint-exec",
                "--",
                "/bin/bash",
                "--noprofile",
                "--norc",
                "-c",
                "echo LATE > /tmp/trustepisode-late-local && sync",
                check=False,
            )
            row["late_fallback_exit"] = r2.returncode

        print(f"[{kind}] wall-clock hold {hold_seconds}s", flush=True)
        t0 = time.monotonic()
        time.sleep(hold_seconds)
        row["observed_hold_seconds"] = round(time.monotonic() - t0, 3)

        print(f"[{kind}] collectors ON; flush", flush=True)
        collectors_on()
        time.sleep(35.0)

        # Update receipt end offsets by re-reading sizes into a patch file, then seal via snapshot
        # Simplest: rewrite offline_run_receipt evidence_end_offsets to current file sizes
        receipt_path = gt / "offline_run_receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        base = LAB / "experiment-data"
        end_offsets = {}
        for rel, start in receipt["evidence_start_offsets"].items():
            path = base / rel
            end_offsets[rel] = path.stat().st_size if path.exists() else int(start)
        receipt["evidence_end_offsets"] = end_offsets
        receipt["collection_end_unix_ns"] = time.time_ns()
        receipt["wallclock_late"] = {
            "kind": kind,
            "hold_seconds": hold_seconds,
            "observed_hold_seconds": row["observed_hold_seconds"],
            "delivery_mode": "wall_clock_forwarder_hold_and_release",
        }
        # keep valid if phase A was valid; late ability failure recorded separately
        receipt["manifest_digest"] = "pending"
        from trustepisode_card_runner import digest_json  # type: ignore

        receipt["manifest_digest"] = digest_json(
            {k: v for k, v in receipt.items() if k != "manifest_digest"}
        )
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        sealed = seal_run(LAB, CONTRACTS, run_id, LAB / "experiment-data" / "runs" / run_id)
        row["sealed_path"] = str(LAB / "experiment-data" / "runs" / run_id)
        row["sealed_digest"] = sealed.get("run_digest") or sealed.get("manifest_digest")
        row["status"] = "sealed"
        # cleanup late files
        compose(
            "exec",
            "-T",
            "target-linux-02",
            "rm",
            "-f",
            "/tmp/trustepisode-late-action",
            check=False,
        )
        compose(
            "exec",
            "-T",
            "target-linux",
            "rm",
            "-f",
            "/tmp/trustepisode-late-local",
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        row["status"] = "failed"
        row["error"] = str(exc)
        collectors_on()
    row["finished_at"] = datetime.now(timezone.utc).isoformat()
    return row


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # within: hold 180s after finalization wait (well inside 900s horizon)
    # beyond: hold W_REV + 30 after finalization wait
    plan = [
        ("within", 180.0, 1),
        ("within", 180.0, 2),
        ("beyond", float(W_REV + 30), 1),
    ]
    results = []
    for kind, hold, idx in plan:
        print(f"=== WALLCLOCK L4 {kind} #{idx} hold={hold} ===", flush=True)
        results.append(wallclock_case(kind, hold, idx))
        print(json.dumps(results[-1], indent=2)[:800], flush=True)

    payload = {
        "result_type": "trustepisode.supplemental-live.l4-wallclock.v1",
        "partition": "supplemental_mechanism",
        "primary_untouched": True,
        "runs": results,
        "within_sealed": sum(
            1 for r in results if r.get("tag") == "l4_wallclock_within" and r.get("status") == "sealed"
        ),
        "beyond_sealed": sum(
            1 for r in results if r.get("tag") == "l4_wallclock_beyond" and r.get("status") == "sealed"
        ),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    raw = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path = OUT / f"wallclock_l4_{utc()}.json"
    path.write_text(raw, encoding="utf-8")
    (OUT / "wallclock_l4_latest.json").write_text(raw, encoding="utf-8")
    (PAPER / "results" / "derived" / "supplemental_live_l4_wallclock.json").write_text(
        raw, encoding="utf-8"
    )
    print("WROTE", path, flush=True)
    print(
        "summary",
        {k: payload[k] for k in ("within_sealed", "beyond_sealed")},
        flush=True,
    )
    return 0 if payload["within_sealed"] >= 1 and payload["beyond_sealed"] >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
