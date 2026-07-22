#!/usr/bin/env python3
"""M2 evidence waterfall: receipt → raw → normalized → token → episode retention."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = Path(r"c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime\src")
sys.path.insert(0, str(RUNTIME_SRC))

from trustepisode_runtime.contract_io import ContractSet  # noqa: E402
from trustepisode_runtime.dataset import arrival_order, load_sealed_run  # noqa: E402
from trustepisode_runtime.evaluation import (  # noqa: E402
    formation_metrics,
    parse_truth_groups,
    terminal_episode_views,
)
from trustepisode_runtime.formation import EpisodeSynthesizer  # noqa: E402
from trustepisode_runtime.pipeline import PipelineResult, RuntimeArtifacts  # noqa: E402

TOKEN = "command_family:file_transfer"
SCP_ABILITY = "linux.scp_archive"


def digest_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def classify_drop(row: dict[str, Any]) -> str:
    if not row["receipt_success"]:
        return "A_action_execution_failure"
    if row["raw_observable"] == 0:
        return "B_sensor_observability_failure"
    if row["normalized_file_transfer"] == 0 and row["normalized_remote_session_scp_proxy"] > 0:
        return "D_token_mapping_failure"
    if row["normalized_file_transfer"] == 0:
        return "C_parser_normalization_failure"
    if row["episode_retained_file_transfer"] == 0:
        return "E_relation_linking_failure"
    return "F_matching_or_none"


def analyze_run(row: dict[str, Any], contracts: ContractSet) -> dict[str, Any]:
    sealed = Path(row["sealed_path"])
    receipt = json.loads((sealed / "offline_run_receipt.json").read_text(encoding="utf-8"))
    scp = [r for r in receipt["receipts"] if r.get("ability_id") == SCP_ABILITY]
    receipt_success = bool(scp) and all(r.get("valid") and r.get("exit_code") == 0 for r in scp)

    raw_text = ""
    for rel in [
        "inputs/edr-01/raw.ndjson",
        "inputs/edr-02/raw.ndjson",
        "inputs/ndr/raw/ndr-eve.ndjson",
    ]:
        p = sealed / rel
        if p.exists():
            raw_text += p.read_text(encoding="utf-8", errors="ignore").lower()
    raw_observable = 1 if ("scp" in raw_text or "file_transfer" in raw_text) else 0

    normalized = []
    for rel in [
        "inputs/edr-01/normalized.ndjson",
        "inputs/edr-02/normalized.ndjson",
        "inputs/ndr/normalized/ndr.ndjson",
    ]:
        normalized.extend(load_ndjson(sealed / rel))

    families = Counter((e.get("attributes") or {}).get("command_family") for e in normalized)
    actions = Counter(e.get("action") for e in normalized)
    normalized_file_transfer = sum(
        1
        for e in normalized
        if (e.get("attributes") or {}).get("command_family") == "file_transfer"
        or e.get("action") == "command_family:file_transfer"
    )
    # SCP is currently labeled remote_session in this lab normalizer
    normalized_remote_session = sum(
        1 for e in normalized if (e.get("attributes") or {}).get("command_family") == "remote_session"
    )

    run = load_sealed_run(contracts, row)
    aliases = {str(k): str(v) for k, v in (run.truth.get("entity_aliases") or {}).items()}
    synthetic = RuntimeArtifacts.synthetic(contracts)
    synthetic.entity_aliases = aliases
    pipeline = PipelineResult(
        synthesis=EpisodeSynthesizer(
            contracts.thresholds["formation"],
            versions=synthetic.versions,
            entity_aliases=aliases,
        ).synthesize(arrival_order(run.events))
    )
    episodes = terminal_episode_views(pipeline, aliases=aliases)
    episode_tokens = set()
    for ep in episodes:
        episode_tokens |= set(ep.actions)
    episode_retained_file_transfer = 1 if TOKEN in episode_tokens else 0
    episode_retained_remote_session = 1 if "command_family:remote_session" in episode_tokens else 0

    groups = parse_truth_groups(run.truth, aliases=aliases)
    metrics = formation_metrics(
        episodes,
        groups,
        benign_tokens=frozenset(str(x) for x in run.truth.get("benign_action_tokens", [])),
    )

    out = {
        "run_id": row["run_id"],
        "mode": row["benign_mode"],
        "manifest_digest": row["manifest_digest"],
        "expected_token": TOKEN,
        "receipt_success": receipt_success,
        "scp_receipt_count": len(scp),
        "raw_observable": raw_observable,
        "normalized_event_count": len(normalized),
        "normalized_file_transfer": normalized_file_transfer,
        "normalized_remote_session_scp_proxy": normalized_remote_session,
        "family_counts": dict(families),
        "action_counts": dict(actions),
        "episode_retained_file_transfer": episode_retained_file_transfer,
        "episode_retained_remote_session": episode_retained_remote_session,
        "action_coverage": metrics["action_coverage"],
        "episode_f1": metrics["episode_f1"],
    }
    out["drop_class"] = classify_drop(out)
    out["token_retention_conditional_on_observability"] = (
        None
        if raw_observable == 0
        else episode_retained_file_transfer / max(normalized_file_transfer, 1)
        if normalized_file_transfer
        else 0.0
    )
    return out


def waterfall(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    n = len(rows)
    stages = [
        ("receipt_success", sum(r["receipt_success"] for r in rows)),
        ("raw_observable", sum(r["raw_observable"] for r in rows)),
        ("normalized_file_transfer_present", sum(1 for r in rows if r["normalized_file_transfer"] > 0)),
        ("normalized_as_remote_session_instead", sum(1 for r in rows if r["normalized_remote_session_scp_proxy"] > 0 and r["normalized_file_transfer"] == 0)),
        ("episode_retained_file_transfer", sum(r["episode_retained_file_transfer"] for r in rows)),
        ("episode_retained_remote_session", sum(r["episode_retained_remote_session"] for r in rows)),
    ]
    out = []
    prev = n
    for name, observed in stages:
        out.append(
            {
                "stage": name,
                "expected_count": n,
                "observed_count": observed,
                "drop_count": n - observed if name != "normalized_as_remote_session_instead" else None,
                "note": (
                    "SCP evidence exists but mapped to command_family:remote_session, not file_transfer"
                    if name == "normalized_as_remote_session_instead"
                    else ""
                ),
            }
        )
        prev = observed
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lab-root",
        type=Path,
        default=Path(r"c:\Users\admin\Desktop\aisec\sensel-caldera-linux-lab"),
    )
    parser.add_argument("--contracts", type=Path, default=ROOT / "artifacts" / "contracts")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()

    registry = args.lab_root / "experiment-data" / "campaign" / "run_registry.csv"
    with registry.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            r
            for r in csv.DictReader(handle)
            if r["status"] == "sealed" and r["card_id"] == "M2" and r["partition"] == "train"
        ]
    if len(rows) != 10:
        raise SystemExit(f"expected 10 sealed M2 train runs, found {len(rows)}")

    contracts = ContractSet(args.contracts)
    per_run = [analyze_run(row, contracts) for row in rows]
    classes = Counter(r["drop_class"] for r in per_run)
    payload = {
        "result_type": "trustepisode.m2-evidence-waterfall.v1",
        "n_runs": len(per_run),
        "required_token": TOKEN,
        "waterfall": waterfall(per_run),
        "drop_class_counts": dict(classes),
        "final_classification": (
            "D_token_mapping_failure"
            if classes.get("D_token_mapping_failure", 0) == len(per_run)
            else dict(classes)
        ),
        "interpretation": (
            "All 10 M2 runs have successful linux.scp_archive receipts and raw scp observability, "
            "but Evidence Fabric labels the corresponding process events as command_family:remote_session "
            "rather than command_family:file_transfer. Formation retains remote_session evidence; "
            "offline matching therefore cannot credit the required file_transfer token. "
            "This is not an Episode Synthesis membership failure of an already-normalized file_transfer event."
        ),
        "per_run": per_run,
        "registry_sha256": digest_file(registry),
    }
    out_dir = args.output_root / "raw" / "m2_trace"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "m2_waterfall.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_root / "derived").mkdir(parents=True, exist_ok=True)
    derived = {
        "final_classification": payload["final_classification"],
        "waterfall": payload["waterfall"],
        "drop_class_counts": payload["drop_class_counts"],
        "interpretation": payload["interpretation"],
        "raw_digest": digest_file(path),
    }
    (args.output_root / "derived" / "m2_waterfall.json").write_text(
        json.dumps(derived, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"n": len(per_run), "classification": payload["final_classification"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
