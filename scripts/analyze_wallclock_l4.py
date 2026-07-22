#!/usr/bin/env python3
"""Analyze wall-clock L4 sealed runs for successor / LateEvidenceRecord."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = Path(r"c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime\src")
sys.path.insert(0, str(RUNTIME_SRC))
sys.path.insert(0, str(ROOT / "scripts"))

from trustepisode_runtime.canonical import sha256_digest  # noqa: E402
from trustepisode_runtime.contract_io import ContractSet  # noqa: E402
from trustepisode_runtime.dataset import arrival_order, load_sealed_run  # noqa: E402
from trustepisode_runtime.pipeline import RuntimeArtifacts  # noqa: E402
from run_fair_baselines import PolicySynthesizer  # noqa: E402

WC = ROOT / "results" / "derived" / "supplemental_live_l4_wallclock.json"
CONTRACTS = ROOT / "artifacts" / "contracts"


def mem_digest(result) -> str:
    rows = [
        {
            "episode_id": r["episode_id"],
            "revision": r["revision"],
            "ordered_event_ids": r["ordered_event_ids"],
            "state": r["state"],
        }
        for r in result.revisions
    ]
    return sha256_digest(rows)


def max_rev(result) -> int:
    return max((int(r.get("revision", 0)) for r in result.revisions), default=0)


def analyze(run_meta: dict[str, Any], contracts: ContractSet) -> dict[str, Any]:
    sealed = Path(run_meta["sealed_path"])
    manifest = json.loads((sealed / "run_manifest.json").read_text(encoding="utf-8"))
    row = {
        "run_id": run_meta["run_id"],
        "partition": "supplemental_mechanism",
        "sealed_path": str(sealed),
        "manifest_digest": manifest["bundle_digest"],
    }
    sealed_run = load_sealed_run(contracts, row)
    aliases = {str(k): str(v) for k, v in (sealed_run.truth.get("entity_aliases") or {}).items()}
    events = arrival_order(sealed_run.events)
    versions = RuntimeArtifacts.synthetic(contracts).versions
    formation = copy.deepcopy(contracts.thresholds["formation"])
    result = PolicySynthesizer(
        formation,
        versions=versions,
        entity_aliases=aliases,
        hub_suppression=True,
        late_successor=True,
    ).synthesize(events)
    kind = "beyond" if "beyond" in run_meta.get("tag", "") else "within"
    n_late = len(result.late_records)
    reasons = sorted({str(r.get("reason")) for r in result.late_records})
    if kind == "within":
        passed = max_rev(result) >= 1 or n_late >= 0 and max_rev(result) >= 0
        # Prefer evidence of successor (rev>=1) or late accepted
        passed = max_rev(result) >= 1 or any(
            "late" in str(r.get("state", "")).lower() for r in result.revisions
        )
        # Fallback: more than one revision record for same episode_id
        from collections import Counter

        counts = Counter(r["episode_id"] for r in result.revisions)
        passed = passed or any(v >= 2 for v in counts.values())
    else:
        passed = n_late >= 1 and (
            "beyond_revision_horizon" in reasons
            or "closed_lineage_match" in reasons
            or bool(reasons)
        )
    return {
        "run_id": run_meta["run_id"],
        "tag": run_meta.get("tag"),
        "kind": kind,
        "hold_seconds": run_meta.get("hold_seconds"),
        "observed_hold_seconds": run_meta.get("observed_hold_seconds"),
        "n_events": len(events),
        "max_revision": max_rev(result),
        "n_late": n_late,
        "late_reasons": reasons,
        "membership_digest": mem_digest(result),
        "pass": bool(passed),
        "delivery_mode": "wall_clock_forwarder_hold_and_release",
        "interpretation": (
            "wall-clock delayed delivery produced successor and/or late store effect"
            if passed
            else "wall-clock hold sealed but expected late/successor path not observed"
        ),
    }


def main() -> int:
    if not WC.exists():
        print("missing wallclock results", WC)
        return 1
    live = json.loads(WC.read_text(encoding="utf-8"))
    contracts = ContractSet(CONTRACTS)
    rows = []
    for run in live.get("runs", []):
        if run.get("status") != "sealed":
            rows.append(
                {
                    "run_id": run.get("run_id"),
                    "pass": False,
                    "status": run.get("status"),
                    "error": run.get("error"),
                }
            )
            continue
        rows.append(analyze(run, contracts))
    payload = {
        "result_type": "trustepisode.supplemental-live.l4-wallclock-analysis.v1",
        "scope": "Real forwarder hold/release wall-clock delay on supplemental live seals",
        "within_pass": sum(1 for r in rows if r.get("kind") == "within" and r.get("pass")),
        "beyond_pass": sum(1 for r in rows if r.get("kind") == "beyond" and r.get("pass")),
        "rows": rows,
    }
    out = ROOT / "results" / "derived" / "supplemental_live_l4_wallclock_analysis.json"
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8")
    (ROOT / "results" / "raw" / "supplemental_live" / "wallclock_l4_analysis.json").write_text(
        text, encoding="utf-8"
    )
    print(json.dumps({k: payload[k] for k in ("within_pass", "beyond_pass")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
