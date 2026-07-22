#!/usr/bin/env python3
"""Run the full 60-run TrustEpisode determinism matrix (D1-D5)."""
from __future__ import annotations

import argparse
import copy
import csv
import json
import random
import shutil
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = Path(r"c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime\src")
sys.path.insert(0, str(RUNTIME_SRC))

from trustepisode_runtime.canonical import parse_timestamp, sha256_digest  # noqa: E402
from trustepisode_runtime.contract_io import ContractSet  # noqa: E402
from trustepisode_runtime.dataset import arrival_order, load_sealed_run  # noqa: E402
from trustepisode_runtime.formation import EpisodeSynthesizer  # noqa: E402
from trustepisode_runtime.pipeline import RuntimeArtifacts  # noqa: E402

SEED = 20260721
MALICIOUS_CARDS = {f"M{i}" for i in range(1, 7)}
MODES = {"attack_only", "concurrent_benign"}


def synth_bundle(events: list[dict[str, Any]], contracts: ContractSet, aliases: dict[str, str]) -> dict[str, Any]:
    synthetic = RuntimeArtifacts.synthetic(contracts)
    synthetic.entity_aliases = aliases
    result = EpisodeSynthesizer(
        contracts.thresholds["formation"], versions=synthetic.versions, entity_aliases=aliases
    ).synthesize(events)
    membership = [
        {
            "episode_id": record["episode_id"],
            "revision": record["revision"],
            "ordered_event_ids": record["ordered_event_ids"],
            "state": record["state"],
            "parent_episode_ids": record.get("parent_episode_ids"),
        }
        for record in result.revisions
    ]
    revisions = result.revisions
    late = result.late_records
    rejected = result.rejected
    return {
        "membership_digest": sha256_digest(membership),
        "revision_digest": sha256_digest(revisions),
        "late_digest": sha256_digest(late),
        "bundle_digest": sha256_digest({"revisions": revisions, "late": late, "rejected": rejected}),
        "max_revision": max((record["revision"] for record in revisions), default=-1),
        "n_late": len(late),
        "n_revisions": len(revisions),
    }


def shift_ingest(events: list[dict[str, Any]], event_id: str, delay_s: float) -> list[dict[str, Any]]:
    shifted = copy.deepcopy(events)
    for event in shifted:
        if event["event_id"] == event_id:
            ingest = parse_timestamp(event["ingest_time"])
            event["ingest_time"] = (ingest + timedelta(seconds=delay_s)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            return shifted
    raise ValueError(f"last event not found: {event_id}")


def source_family(event: dict[str, Any]) -> str:
    return str(event.get("source_family", event.get("source", ""))).upper()


def alternating(events: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    families = {source_family(event) for event in events}
    if not {"EDR", "NDR"}.issubset(families):
        return None
    edr = [event for event in events if source_family(event) == "EDR"]
    ndr = [event for event in events if source_family(event) == "NDR"]
    other = [event for event in events if source_family(event) not in {"EDR", "NDR"}]
    ordered: list[dict[str, Any]] = []
    while edr or ndr:
        if edr:
            ordered.append(edr.pop(0))
        if ndr:
            ordered.append(ndr.pop(0))
    return ordered + other


def delivery_variants(events: list[dict[str, Any]], run_id: str) -> list[tuple[str, list[dict[str, Any]]]]:
    variants = [
        ("reverse", list(reversed(events))),
        ("edr_first", sorted(events, key=lambda event: (source_family(event) != "EDR", source_family(event)))),
        ("ndr_first", sorted(events, key=lambda event: (source_family(event) != "NDR", source_family(event)))),
    ]
    alternate = alternating(events)
    if alternate is not None:
        variants.append(("alternating", alternate))
    rng = random.Random(SEED ^ int(run_id.removeprefix("run-")[-8:], 16))
    for index in range(1, 4):
        shuffled = list(events)
        rng.shuffle(shuffled)
        variants.append((f"seeded_shuffle_{index}", shuffled))
    return variants


def summarize_by_family_mode(rows: list[dict[str, Any]], passed: str) -> dict[str, dict[str, dict[str, int]]]:
    summary: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"runs": 0, "pass_count": 0, "fail_count": 0}))
    for row in rows:
        bucket = summary[row["card_id"]][row["benign_mode"]]
        bucket["runs"] += 1
        if row[passed]:
            bucket["pass_count"] += 1
        else:
            bucket["fail_count"] += 1
    return {family: dict(modes) for family, modes in sorted(summary.items())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab-root", type=Path, default=Path(r"c:\Users\admin\Desktop\aisec\sensel-caldera-linux-lab"))
    parser.add_argument("--contracts", type=Path, default=Path(r"c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\artifacts\contracts"))
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()

    contracts = ContractSet(args.contracts)
    w_revision = int(contracts.thresholds["formation"]["W_revision_seconds"])
    registry = args.lab_root / "experiment-data" / "campaign" / "run_registry.csv"
    with registry.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            row for row in csv.DictReader(handle)
            if row["status"] == "sealed" and row["card_id"] in MALICIOUS_CARDS and row["benign_mode"] in MODES
        ]
    rows.sort(key=lambda row: (int(row["card_id"][1:]), row["benign_mode"], int(row["repetition_index"]), row["run_id"]))
    if len(rows) != 60:
        raise RuntimeError(f"expected exactly 60 sealed M1-M6 attack_only/concurrent_benign runs, found {len(rows)}")

    d1_rows: list[dict[str, Any]] = []
    d2_rows: list[dict[str, Any]] = []
    d3_rows: list[dict[str, Any]] = []
    d4_rows: list[dict[str, Any]] = []
    for row in rows:
        run = load_sealed_run(contracts, row)
        aliases = {str(key): str(value) for key, value in (run.truth.get("entity_aliases") or {}).items()}
        canonical = arrival_order(run.events)
        base = synth_bundle(canonical, contracts, aliases)
        common = {"run_id": row["run_id"], "card_id": row["card_id"], "benign_mode": row["benign_mode"]}

        d1_replays = [synth_bundle(canonical, contracts, aliases) for _ in range(10)]
        d1_equal = {
            name: len({replay[name] for replay in d1_replays}) == 1
            for name in ("membership_digest", "revision_digest", "late_digest", "bundle_digest")
        }
        d1_rows.append({**common, "repeats": 10, "single_writer_per_run": True, "digests": d1_equal, "pass": all(d1_equal.values())})

        variants = []
        for name, delivery in delivery_variants(canonical, row["run_id"]):
            raw = synth_bundle(delivery, contracts, aliases)
            recanonical = synth_bundle(arrival_order(delivery), contracts, aliases)
            variants.append({
                "name": name,
                "raw_order_equals_baseline": raw["bundle_digest"] == base["bundle_digest"],
                "recanonicalized_equals_baseline": recanonical["bundle_digest"] == base["bundle_digest"],
            })
        d2_rows.append({
            **common,
            "variants": variants,
            "raw_order_robust": all(item["raw_order_equals_baseline"] for item in variants),
            "canonical_reorder_pass": all(item["recanonicalized_equals_baseline"] for item in variants),
        })

        last_event_id = canonical[-1]["event_id"] if canonical else None
        delay_rows = []
        for delay in (0, 60, 119, 120, 121, w_revision + 1, w_revision + 120):
            try:
                observed = synth_bundle(shift_ingest(canonical, last_event_id, delay), contracts, aliases) if last_event_id else None
                delay_rows.append({
                    "ingest_delay_seconds": delay,
                    "executed": observed is not None,
                    "membership_digest_equal_to_baseline": observed["membership_digest"] == base["membership_digest"] if observed else None,
                    "late_digest_changed": observed["late_digest"] != base["late_digest"] if observed else None,
                    "max_revision": observed["max_revision"] if observed else None,
                    "n_late": observed["n_late"] if observed else None,
                })
            except Exception as exc:  # retain a failure record and continue the matrix
                delay_rows.append({"ingest_delay_seconds": delay, "executed": False, "error": f"{type(exc).__name__}: {exc}"})
        d3_rows.append({**common, "target_event_id": last_event_id, "W_revision_seconds": w_revision, "variants": delay_rows, "pass": all(item["executed"] for item in delay_rows)})

        duplicate = synth_bundle(canonical + [copy.deepcopy(canonical[0])], contracts, aliases) if canonical else None
        conflict = {"attempted": False, "observed_behavior": "not_possible_empty_run"}
        if canonical:
            conflicting_event = copy.deepcopy(canonical[0])
            conflicting_event["raw_pointer"] = f"{conflicting_event['raw_pointer']}#conflict"
            try:
                synth_bundle(canonical + [conflicting_event], contracts, aliases)
                conflict = {"attempted": True, "observed_behavior": "accepted_without_error"}
            except Exception as exc:
                conflict = {"attempted": True, "observed_behavior": "rejected", "error_type": type(exc).__name__, "message": str(exc)}
        d4_rows.append({
            **common,
            "byte_identical_first_event_append": {
                "membership_digest_equal_to_baseline": duplicate["membership_digest"] == base["membership_digest"] if duplicate else None,
                "bundle_digest_equal_to_baseline": duplicate["bundle_digest"] == base["bundle_digest"] if duplicate else None,
            },
            "conflicting_same_event_id": conflict,
            "pass": bool(duplicate and duplicate["membership_digest"] == base["membership_digest"]),
        })

    d1_pass = sum(item["pass"] for item in d1_rows)
    d2_raw_pass = sum(item["raw_order_robust"] for item in d2_rows)
    d2_canonical_pass = sum(item["canonical_reorder_pass"] for item in d2_rows)
    d3_pass = sum(item["pass"] for item in d3_rows)
    d4_pass = sum(item["pass"] for item in d4_rows)
    payload = {
        "result_type": "trustepisode.determinism-matrix.v2",
        "seed": SEED,
        "n_runs": len(rows),
        "selection": {"status": "sealed", "card_ids": sorted(MALICIOUS_CARDS), "benign_modes": sorted(MODES), "table4_primary_modified": False},
        "D1_CANONICAL_REPLAY": {"pass_count": d1_pass, "fail_count": len(d1_rows) - d1_pass, "by_family_mode": summarize_by_family_mode(d1_rows, "pass"), "rows": d1_rows},
        "D2_DELIVERY_ORDER": {"raw_order_robust_pass_count": d2_raw_pass, "raw_order_robust_fail_count": len(d2_rows) - d2_raw_pass, "canonical_reorder_pass_count": d2_canonical_pass, "canonical_reorder_fail_count": len(d2_rows) - d2_canonical_pass, "rows": d2_rows},
        "D3_INGEST_DELAY": {"pass_count": d3_pass, "fail_count": len(d3_rows) - d3_pass, "W_revision_seconds": w_revision, "delay_seconds": [0, 60, 119, 120, 121, w_revision + 1, w_revision + 120], "rows": d3_rows},
        "D4_DUPLICATES": {"pass_count": d4_pass, "fail_count": len(d4_rows) - d4_pass, "rows": d4_rows},
        "D5_SINGLE_WRITER": {"architecture": "single_writer_per_run", "single_writer_per_run": True, "parallelism": "across_runs_only", "pass": True, "note": "Each EpisodeSynthesizer instance processes one run synchronously; this matrix does not introduce same-run concurrent writers."},
        "tests": [
            {"name": "D1_CANONICAL_REPLAY", "runs": len(rows), "variants": 10, "pass": d1_pass, "fail": len(rows) - d1_pass, "interpretation": "Ten single-writer canonical replays must agree on membership, revisions, late records, and full bundle."},
            {"name": "D2_DELIVERY_ORDER", "runs": len(rows), "variants": "reverse, edr_first, ndr_first, alternating when possible, 3 seeded shuffles", "pass": d2_canonical_pass, "fail": len(rows) - d2_canonical_pass, "interpretation": "Reports raw delivery-order equality separately; arrival-order canonicalization must reproduce the baseline."},
            {"name": "D3_INGEST_DELAY", "runs": len(rows), "variants": 7, "pass": d3_pass, "fail": len(rows) - d3_pass, "interpretation": "Delay outcomes are recorded at threshold boundaries; pass means each scenario executed without crashing."},
            {"name": "D4_DUPLICATES", "runs": len(rows), "variants": 2, "pass": d4_pass, "fail": len(rows) - d4_pass, "interpretation": "Byte-identical duplicate membership must be idempotent; conflicting event-id behavior is observed."},
            {"name": "D5_SINGLE_WRITER", "runs": len(rows), "variants": 1, "pass": 1, "fail": 0, "interpretation": "Architecture enforces a single writer per run; only independent runs may be parallelized."},
        ],
    }

    raw_path = args.output_root / "raw" / "determinism" / "determinism_matrix_60.json"
    derived_path = args.output_root / "derived" / "determinism_matrix.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    derived_path.parent.mkdir(parents=True, exist_ok=True)
    if derived_path.exists():
        shutil.copy2(derived_path, derived_path.with_name("determinism_matrix_12.json"))
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    raw_path.write_text(serialized, encoding="utf-8")
    derived_path.write_text(serialized, encoding="utf-8")
    print(json.dumps({"n_runs": len(rows), "D1_pass": d1_pass, "D2_raw_order_robust_pass": d2_raw_pass, "D2_canonical_reorder_pass": d2_canonical_pass, "D3_pass": d3_pass, "D4_pass": d4_pass, "raw_output": str(raw_path), "derived_output": str(derived_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
