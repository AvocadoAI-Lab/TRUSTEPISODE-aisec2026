from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from typing import Any

import numpy as np

from .canonical import sha256_digest, utf8_key
from .scoring import AffineCalibrator, fit_affine_calibrator


def evaluate_group_candidate(
    group_key: str,
    rows: list[dict[str, Any]],
    global_calibrator: AffineCalibrator,
    policy: dict[str, Any],
) -> tuple[AffineCalibrator | None, dict[str, Any]]:
    parsed = [
        {
            "run_id": str(item["run_id"]),
            "revision_id": str(item["revision_id"]),
            "z": float(item["z"]),
            "label": int(item["label"]),
        }
        for item in rows
    ]
    if any(item["label"] not in {0, 1} or not math.isfinite(item["z"]) for item in parsed):
        raise ValueError("invalid group calibration candidate row")
    positive = sum(item["label"] == 1 for item in parsed)
    negative = sum(item["label"] == 0 for item in parsed)
    run_ids = sorted({item["run_id"] for item in parsed}, key=utf8_key)
    prerequisites = {
        "positive_revisions": positive,
        "negative_revisions": negative,
        "independent_runs": len(run_ids),
        "minimum_positive_revisions": int(policy["minimum_positive_revisions"]),
        "minimum_negative_revisions": int(policy["minimum_negative_revisions"]),
        "minimum_independent_runs": int(policy["minimum_independent_runs"]),
    }
    if (
        positive < prerequisites["minimum_positive_revisions"]
        or negative < prerequisites["minimum_negative_revisions"]
        or len(run_ids) < prerequisites["minimum_independent_runs"]
    ):
        artifact = {
            "artifact_type": "trustepisode.group-calibration-gate.v1",
            "group_key": group_key,
            "gate_decision": "fallback_supported_global",
            "reason": "minimum_cohort_not_met",
            "prerequisites": prerequisites,
        }
        artifact["artifact_digest"] = sha256_digest(artifact)
        return None, artifact

    fold_count = int(policy["run_level_folds"])
    assignments = balanced_fold_assignment(
        group_key,
        parsed,
        fold_count=fold_count,
        seed=int(policy["fold_assignment_seed"]),
    )
    fold_by_run = {item["run_id"]: item["fold"] for item in assignments}
    fold_metrics = []
    losses_by_run: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for fold in range(fold_count):
        training = [item for item in parsed if fold_by_run[item["run_id"]] != fold]
        held_out = [item for item in parsed if fold_by_run[item["run_id"]] == fold]
        if not training or not held_out:
            raise ValueError("balanced group fold is empty")
        calibrator, _artifact = fit_affine_calibrator(
            [(item["revision_id"], item["z"], item["label"]) for item in training]
        )
        brier_deltas = []
        nll_deltas = []
        for item in held_out:
            global_probability = global_calibrator.probability(item["z"])
            group_probability = calibrator.probability(item["z"])
            global_brier = (global_probability - item["label"]) ** 2
            group_brier = (group_probability - item["label"]) ** 2
            global_nll = binary_nll(item["label"], global_probability)
            group_nll = binary_nll(item["label"], group_probability)
            delta_brier = global_brier - group_brier
            delta_nll = global_nll - group_nll
            brier_deltas.append(delta_brier)
            nll_deltas.append(delta_nll)
            losses_by_run[item["run_id"]].append((delta_brier, delta_nll))
        fold_metrics.append(
            {
                "fold": fold,
                "held_out_runs": sorted(
                    {item["run_id"] for item in held_out}, key=utf8_key
                ),
                "held_out_revisions": len(held_out),
                "delta_Brier": float(np.mean(brier_deltas)),
                "delta_NLL": float(np.mean(nll_deltas)),
            }
        )

    all_brier = [value[0] for values in losses_by_run.values() for value in values]
    all_nll = [value[1] for values in losses_by_run.values() for value in values]
    repetitions = 2000
    bootstrap_seed = int(policy["fold_assignment_seed"])
    lower_brier, upper_brier = cluster_bootstrap_interval(
        losses_by_run, index=0, repetitions=repetitions, seed=bootstrap_seed
    )
    lower_nll, upper_nll = cluster_bootstrap_interval(
        losses_by_run, index=1, repetitions=repetitions, seed=bootstrap_seed + 1
    )
    mean_brier = float(np.mean(all_brier))
    mean_nll = float(np.mean(all_nll))
    enabled = (
        mean_brier >= float(policy["minimum_mean_brier_improvement"])
        and mean_nll >= float(policy["minimum_mean_nll_improvement"])
        and lower_brier > 0.0
        and lower_nll > 0.0
        and all(item["delta_Brier"] >= 0.0 and item["delta_NLL"] >= 0.0 for item in fold_metrics)
    )
    artifact = {
        "artifact_type": "trustepisode.group-calibration-gate.v1",
        "group_key": group_key,
        "gate_decision": "enabled" if enabled else "fallback_supported_global",
        "reason": "all_gate_predicates_pass" if enabled else "improvement_gate_not_met",
        "prerequisites": prerequisites,
        "fold_assignments": assignments,
        "fold_assignment_digest": sha256_digest(assignments),
        "fold_metrics": fold_metrics,
        "mean_delta_Brier": mean_brier,
        "mean_delta_NLL": mean_nll,
        "delta_Brier_interval_95": [lower_brier, upper_brier],
        "delta_NLL_interval_95": [lower_nll, upper_nll],
        "cluster_bootstrap_repetitions": repetitions,
        "cluster_bootstrap_seed": bootstrap_seed,
    }
    artifact["artifact_digest"] = sha256_digest(artifact)
    if not enabled:
        return None, artifact
    final, final_artifact = fit_affine_calibrator(
        [(item["revision_id"], item["z"], item["label"]) for item in parsed]
    )
    artifact["final_refit_artifact_digest"] = final_artifact["artifact_digest"]
    artifact["artifact_digest"] = sha256_digest(
        {key: value for key, value in artifact.items() if key != "artifact_digest"}
    )
    return final, {**artifact, "final_refit": final_artifact}


def balanced_fold_assignment(
    group_key: str,
    rows: list[dict[str, Any]],
    *,
    fold_count: int,
    seed: int,
) -> list[dict[str, Any]]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for item in rows:
        counts[item["run_id"]][int(item["label"])] += 1
    if len(counts) < fold_count:
        raise ValueError("fewer runs than group calibration folds")

    def seeded_hash(run_id: str) -> bytes:
        return hashlib.sha256(
            str(seed).encode("ascii")
            + b"\x1f"
            + group_key.encode("utf-8")
            + b"\x1f"
            + run_id.encode("utf-8")
        ).digest()

    ordered_runs = sorted(
        counts,
        key=lambda run_id: (
            -(counts[run_id][0] + counts[run_id][1]),
            seeded_hash(run_id),
            utf8_key(run_id),
        ),
    )
    positive_total = sum(value[1] for value in counts.values())
    negative_total = sum(value[0] for value in counts.values())
    run_total = len(counts)
    fold_positive = [0] * fold_count
    fold_negative = [0] * fold_count
    fold_runs = [0] * fold_count
    assignments = []
    for run_id in ordered_runs:
        negative, positive = counts[run_id]
        candidates = []
        for fold in range(fold_count):
            p_load = (fold_positive[fold] + positive) / positive_total
            n_load = (fold_negative[fold] + negative) / negative_total
            r_load = (fold_runs[fold] + 1) / run_total
            candidates.append((max(p_load, n_load, r_load), p_load + n_load + r_load, fold))
        fold = min(candidates)[2]
        fold_positive[fold] += positive
        fold_negative[fold] += negative
        fold_runs[fold] += 1
        assignments.append(
            {
                "group_key": group_key,
                "run_id": run_id,
                "positive_count": positive,
                "negative_count": negative,
                "fold": fold,
            }
        )
    if any(value == 0 for value in fold_runs):
        raise ValueError("balanced fold assignment produced an empty fold")
    return assignments


def cluster_bootstrap_interval(
    losses_by_run: dict[str, list[tuple[float, float]]],
    *,
    index: int,
    repetitions: int,
    seed: int,
) -> tuple[float, float]:
    run_ids = sorted(losses_by_run, key=utf8_key)
    generator = np.random.default_rng(seed)
    values = np.empty(repetitions, dtype=np.float64)
    for repetition in range(repetitions):
        selected = generator.integers(0, len(run_ids), size=len(run_ids))
        observations = [
            value[index]
            for selected_index in selected
            for value in losses_by_run[run_ids[int(selected_index)]]
        ]
        values[repetition] = float(np.mean(observations))
    lower, upper = np.percentile(values, [2.5, 97.5])
    return float(lower), float(upper)


def binary_nll(label: int, probability: float) -> float:
    clipped = min(max(probability, 1e-15), 1.0 - 1e-15)
    return -(label * math.log(clipped) + (1 - label) * math.log(1.0 - clipped))
