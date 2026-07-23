from __future__ import annotations

from trustepisode_runtime.group_calibration import (
    balanced_fold_assignment,
    evaluate_group_candidate,
)


def candidate_rows(run_count: int = 10) -> list[dict]:
    rows = []
    for run_index in range(run_count):
        for label in (0, 1):
            for index in range(5):
                rows.append(
                    {
                        "run_id": f"run-{run_index:02d}",
                        "revision_id": f"rev-{run_index:02d}-{label}-{index}",
                        "z": -2.0 if label == 0 else 2.0,
                        "label": label,
                    }
                )
    return rows


def test_balanced_group_folds_are_deterministic_and_nonempty() -> None:
    rows = candidate_rows()
    first = balanced_fold_assignment("group-a", rows, fold_count=5, seed=20260710)
    second = balanced_fold_assignment("group-a", list(reversed(rows)), fold_count=5, seed=20260710)
    assert first == second
    assert {item["fold"] for item in first} == set(range(5))
    assert len({item["run_id"] for item in first}) == 10


def test_group_gate_falls_back_when_minimum_cohort_is_not_met(
    contracts, artifacts
) -> None:
    calibrator, gate = evaluate_group_candidate(
        "group-small",
        candidate_rows(run_count=2),
        artifacts.global_calibrator,
        contracts.thresholds["calibration_group_gate"],
    )
    assert calibrator is None
    assert gate["gate_decision"] == "fallback_supported_global"
    assert gate["reason"] == "minimum_cohort_not_met"
