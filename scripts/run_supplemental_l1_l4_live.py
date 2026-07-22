#!/usr/bin/env python3
"""Fast supplemental L1+L4 live cohort (separate from primary M1-M6)."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LAB = Path(r"c:\Users\admin\Desktop\aisec\sensel-caldera-linux-lab")
PAPER = Path(r"c:\Users\admin\Desktop\aisec\TRUSTEPISODE-aisec2026")
CONTRACTS = PAPER / "artifacts" / "contracts"
OUT = PAPER / "results" / "raw" / "supplemental_live"
sys.path.insert(0, str(LAB / "scripts"))

from trustepisode_card_runner import Runner  # noqa: E402
from trustepisode_snapshot import seal_run  # noqa: E402


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_one(card_id: str, tag: str, idx: int, flush: float = 25.0) -> dict[str, Any]:
    run_id = f"run-supp-{tag}-{idx:02d}-{utc()}"
    # shorten startup delay by subclassing
    class FastRunner(Runner):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.startup_delay_seconds = 10.0

    row: dict[str, Any] = {
        "run_id": run_id,
        "card_id": card_id,
        "tag": tag,
        "partition": "supplemental_mechanism",
        "mode": "attack_only",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        runner = FastRunner(
            LAB,
            CONTRACTS,
            run_id,
            card_id,
            "attack_only",
            flush,
            startup_delay_seconds=10.0,
        )
        # Force short startup even if ctor ignored kw in older signature
        runner.startup_delay_seconds = 10.0
        manifest = runner.execute()
        row["receipt_valid"] = bool(manifest.get("valid"))
        row["receipt_digest"] = manifest.get("manifest_digest")
        row["execution_errors"] = manifest.get("execution_errors", [])
        if not manifest.get("valid"):
            row["status"] = "invalid_receipt"
            return row
        sealed = seal_run(LAB, CONTRACTS, run_id, LAB / "experiment-data" / "runs" / run_id)
        row["sealed_path"] = str(LAB / "experiment-data" / "runs" / run_id)
        row["sealed_digest"] = sealed.get("run_digest") or sealed.get("manifest_digest")
        row["status"] = "sealed"
    except Exception as exc:  # noqa: BLE001 — record and continue
        row["status"] = "failed"
        row["error"] = str(exc)
    row["finished_at"] = datetime.now(timezone.utc).isoformat()
    return row


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    plan = {
        "protocol": "PROTOCOL_L1_L4_FAST.md",
        "partition": "supplemental_mechanism",
        "primary_untouched": True,
        "targets": {"L1": ("M3", 3), "L4": ("M5", 3)},
        "note": "L1 uses M3 SSH cross-host abilities; L4 uses M5 short local; late inject offline",
    }
    results: list[dict[str, Any]] = []
    # L1 first (session-oriented)
    for i in range(1, 4):
        print(f"=== L1 run {i}/3 ===", flush=True)
        results.append(run_one("M3", "l1", i))
        print(json.dumps(results[-1], indent=2), flush=True)
    # L4 bases
    for i in range(1, 4):
        print(f"=== L4 base run {i}/3 ===", flush=True)
        results.append(run_one("M5", "l4", i))
        print(json.dumps(results[-1], indent=2), flush=True)

    payload = {
        "result_type": "trustepisode.supplemental-live.l1-l4.v1",
        "plan": plan,
        "runs": results,
        "l1_sealed": sum(1 for r in results if r.get("tag") == "l1" and r.get("status") == "sealed"),
        "l4_sealed": sum(1 for r in results if r.get("tag") == "l4" and r.get("status") == "sealed"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    raw = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    out_path = OUT / f"live_runs_{utc()}.json"
    out_path.write_text(raw, encoding="utf-8")
    (OUT / "live_runs_latest.json").write_text(raw, encoding="utf-8")
    (PAPER / "results" / "derived" / "supplemental_live_l1_l4.json").write_text(raw, encoding="utf-8")
    print("WROTE", out_path)
    print("summary", {k: payload[k] for k in ("l1_sealed", "l4_sealed")})
    return 0 if payload["l1_sealed"] >= 1 and payload["l4_sealed"] >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
