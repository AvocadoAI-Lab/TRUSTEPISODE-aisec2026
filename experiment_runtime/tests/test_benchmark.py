from __future__ import annotations

from trustepisode_runtime.benchmark import run_benchmark


def test_benchmark_measures_determinism_and_cost(
    contracts, artifacts, sample_stream
) -> None:
    events, coverage = sample_stream
    value = run_benchmark(
        contracts,
        artifacts,
        events,
        coverage,
        worker_counts=[1, 2],
        measured_repetitions=1,
        allow_synthetic=True,
    )
    assert value["formal"] is False
    assert [item["worker_count"] for item in value["rows"]] == [1, 2]
    assert all(item["canonical_hash_equal"] for item in value["rows"])
    assert all(item["events_per_second"] > 0 for item in value["rows"])
    assert all(item["p50_ms"] is not None for item in value["rows"])


def test_full_worker_matrix_with_synthetic_artifacts_is_not_formal(
    contracts, artifacts, sample_stream
) -> None:
    events, coverage = sample_stream
    value = run_benchmark(
        contracts,
        artifacts,
        events,
        coverage,
        worker_counts=[1, 2, 4, 8],
        measured_repetitions=5,
        allow_synthetic=True,
    )
    assert value["formal_configuration"] is True
    assert value["artifact_status"] == "synthetic_test_only"
    assert value["formal"] is False
