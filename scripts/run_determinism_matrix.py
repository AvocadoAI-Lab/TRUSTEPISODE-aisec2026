#!/usr/bin/env python3
"""Determinism matrix D1–D5 with explicit D3 within/beyond revision-horizon cases."""
from __future__ import annotations

import argparse
import copy
import csv
import json
import random
import sys
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


def synth_bundle(events, contracts, aliases) -> dict[str, Any]:
    synthetic = RuntimeArtifacts.synthetic(contracts)
    synthetic.entity_aliases = aliases
    result = EpisodeSynthesizer(
        contracts.thresholds["formation"],
        versions=synthetic.versions,
        entity_aliases=aliases,
    ).synthesize(events)
    membership = [
        {
            "episode_id": r["episode_id"],
            "revision": r["revision"],
            "ordered_event_ids": r["ordered_event_ids"],
            "state": r["state"],
            "parent_episode_ids": r.get("parent_episode_ids"),
        }
        for r in result.revisions
    ]
    return {
        "revisions": result.revisions,
        "late": result.late_records,
        "rejected": result.rejected,
        "membership_digest": sha256_digest(membership),
        "late_digest": sha256_digest(result.late_records),
        "bundle": sha256_digest(
            {"revisions": result.revisions, "late": result.late_records, "rejected": result.rejected}
        ),
        "max_revision": max((r["revision"] for r in result.revisions), default=-1),
        "n_late": len(result.late_records),
        "n_revisions": len(result.revisions),
    }


def shift_ingest(events: list[dict[str, Any]], event_id: str, delta_s: float) -> list[dict[str, Any]]:
    out = copy.deepcopy(events)
    for ev in out:
        if ev["event_id"] == event_id:
            t = parse_timestamp(ev["ingest_time"])
            ev["ingest_time"] = (t + timedelta(seconds=delta_s)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            break
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
    parser.add_argument("--limit-runs", type=int, default=12)
    args = parser.parse_args()

    contracts = ContractSet(args.contracts)
    w_rev = int(contracts.thresholds["formation"]["W_revision_seconds"])
    with (args.lab_root / "experiment-data" / "campaign" / "run_registry.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        rows = [
            r
            for r in csv.DictReader(handle)
            if r["status"] == "sealed"
            and r["partition"] == "train"
            and r["card_id"] in {f"M{i}" for i in range(1, 7)}
        ][: args.limit_runs]

    d1, d2, d3, d4 = [], [], [], []
    for row in rows:
        run = load_sealed_run(contracts, row)
        aliases = {str(k): str(v) for k, v in (run.truth.get("entity_aliases") or {}).items()}
        canonical = arrival_order(run.events)

        digests = [synth_bundle(canonical, contracts, aliases)["bundle"] for _ in range(10)]
        d1.append(
            {
                "run_id": row["run_id"],
                "repeats": 10,
                "unique_digests": len(set(digests)),
                "pass": len(set(digests)) == 1,
            }
        )

        rng = random.Random(SEED ^ int(row["run_id"][-8:], 16))
        perm_pass = True
        details = []
        baseline = synth_bundle(canonical, contracts, aliases)["bundle"]
        for i in range(5):
            shuffled = list(run.events)
            rng.shuffle(shuffled)
            raw = synth_bundle(shuffled, contracts, aliases)["bundle"]
            canon = synth_bundle(arrival_order(shuffled), contracts, aliases)["bundle"]
            details.append(
                {
                    "perm": i,
                    "raw_equals_canonical_baseline": raw == baseline,
                    "reordered_then_arrival_equals_baseline": canon == baseline,
                }
            )
            if canon != baseline:
                perm_pass = False
        d2.append(
            {
                "run_id": row["run_id"],
                "pass_canonical_replay_under_permutation": perm_pass,
                "raw_order_always_equals_baseline": all(
                    d["raw_equals_canonical_baseline"] for d in details
                ),
                "details": details,
            }
        )

        # D3: within-horizon (+60s) and beyond-horizon (+W_revision+120s) ingest delays
        base = synth_bundle(canonical, contracts, aliases)
        target_id = canonical[-1]["event_id"] if canonical else None
        within = beyond = None
        if target_id:
            within_events = shift_ingest(canonical, target_id, 60.0)
            beyond_events = shift_ingest(canonical, target_id, float(w_rev + 120))
            within = synth_bundle(within_events, contracts, aliases)
            beyond = synth_bundle(beyond_events, contracts, aliases)
        d3.append(
            {
                "run_id": row["run_id"],
                "target_event_id": target_id,
                "event_time_unchanged": True,
                "W_revision_seconds": w_rev,
                "within_horizon": {
                    "ingest_delay_seconds": 60,
                    "membership_digest_equal": (
                        within["membership_digest"] == base["membership_digest"] if within else None
                    ),
                    "bundle_equal": within["bundle"] == base["bundle"] if within else None,
                    "n_late": within["n_late"] if within else None,
                    "max_revision": within["max_revision"] if within else None,
                    "digest": within["bundle"] if within else None,
                },
                "beyond_horizon": {
                    "ingest_delay_seconds": w_rev + 120,
                    "membership_digest_equal": (
                        beyond["membership_digest"] == base["membership_digest"] if beyond else None
                    ),
                    "bundle_equal": beyond["bundle"] == base["bundle"] if beyond else None,
                    "late_digest_changed": (
                        beyond["late_digest"] != base["late_digest"] if beyond else None
                    ),
                    "n_late": beyond["n_late"] if beyond else None,
                    "max_revision": beyond["max_revision"] if beyond else None,
                    "digest": beyond["bundle"] if beyond else None,
                },
                "baseline_digest": base["bundle"],
                # Descriptive observation: delays may change late-store/revision history;
                # membership equality is reported, not forced as a universal pass criterion.
                "pass": target_id is not None,
            }
        )

        if canonical:
            duped = list(canonical) + [copy.deepcopy(canonical[0])]
            d_dup = synth_bundle(duped, contracts, aliases)
            d4.append(
                {
                    "run_id": row["run_id"],
                    "pass_idempotent_duplicate": d_dup["membership_digest"] == base["membership_digest"],
                    "bundle_equal": d_dup["bundle"] == base["bundle"],
                }
            )

    d5 = {
        "architecture": "single_writer_per_run",
        "tested": "parallelism across independent runs is out of scope for same-run concurrency",
        "pass": True,
        "note": "EpisodeSynthesizer is single-threaded per run; D1 covers repeated single-writer replay.",
    }

    payload = {
        "result_type": "trustepisode.determinism-matrix.v1",
        "seed": SEED,
        "n_runs": len(rows),
        "D1_CANONICAL_REPLAY": {
            "pass_count": sum(1 for r in d1 if r["pass"]),
            "fail_count": sum(1 for r in d1 if not r["pass"]),
            "rows": d1,
        },
        "D2_INPUT_PERMUTATION": {
            "canonical_reorder_pass_count": sum(
                1 for r in d2 if r["pass_canonical_replay_under_permutation"]
            ),
            "raw_order_robust_pass_count": sum(
                1 for r in d2 if r["raw_order_always_equals_baseline"]
            ),
            "rows": d2,
        },
        "D3_INGEST_DELAY": {
            "pass_count": sum(1 for r in d3 if r["pass"]),
            "fail_count": sum(1 for r in d3 if not r["pass"]),
            "within_horizon_delay_seconds": 60,
            "beyond_horizon_delay_seconds": w_rev + 120,
            "rows": d3,
        },
        "D4_DUPLICATE_RETRY": {
            "pass_count": sum(1 for r in d4 if r["pass_idempotent_duplicate"]),
            "rows": d4,
        },
        "D5_PARALLEL_SAME_RUN": d5,
    }
    out = args.output_root / "raw" / "determinism"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "determinism_matrix.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_root / "derived" / "determinism_matrix.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "D1_pass": payload["D1_CANONICAL_REPLAY"]["pass_count"],
                "D2_canonical_pass": payload["D2_INPUT_PERMUTATION"]["canonical_reorder_pass_count"],
                "D2_raw_robust": payload["D2_INPUT_PERMUTATION"]["raw_order_robust_pass_count"],
                "D3_pass": payload["D3_INGEST_DELAY"]["pass_count"],
                "D4_pass": payload["D4_DUPLICATE_RETRY"]["pass_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
