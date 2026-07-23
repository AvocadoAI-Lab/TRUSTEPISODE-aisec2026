from __future__ import annotations

import os
import platform
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import numpy as np
import psutil

from . import __version__
from .canonical import canonical_bytes, sha256_digest
from .contract_io import ContractSet
from .pipeline import ReferencePipeline, RuntimeArtifacts


@dataclass
class TaskMeasurement:
    elapsed_seconds: float
    outcome_latency_ms: list[float]
    outcome_digests: list[str]
    outcome_count: int
    failure_count: int
    canonical_outcome_bytes: int


def run_benchmark(
    contracts: ContractSet,
    artifacts: RuntimeArtifacts,
    events: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    *,
    worker_counts: list[int] | tuple[int, ...] = (1, 2, 4, 8),
    measured_repetitions: int = 5,
    allow_synthetic: bool = False,
) -> dict[str, Any]:
    if not events:
        raise ValueError("RT6 benchmark requires at least one event")
    if measured_repetitions <= 0:
        raise ValueError("measured_repetitions must be positive")
    hardware = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "memory_bytes": psutil.virtual_memory().total,
    }
    software = {
        "runtime_version": __version__,
        "python": platform.python_version(),
        "contract_schema_digest": sha256_digest(contracts.schema),
        "threshold_digest": sha256_digest(contracts.thresholds),
        "artifact_manifest_digest": artifacts.versions["manifest"]["digest"],
    }
    hardware_digest = sha256_digest(hardware)
    software_digest = sha256_digest(software)
    rows = []
    canonical_event_bytes = sum(len(canonical_bytes(item)) for item in events)

    for worker_count in worker_counts:
        if worker_count <= 0:
            raise ValueError("worker counts must be positive")
        _run_batch(
            worker_count,
            contracts,
            artifacts,
            events,
            coverage,
            allow_synthetic=allow_synthetic,
            sample_rss=False,
        )
        repeats = [
            _run_batch(
                worker_count,
                contracts,
                artifacts,
                events,
                coverage,
                allow_synthetic=allow_synthetic,
                sample_rss=True,
            )
            for _ in range(measured_repetitions)
        ]
        tasks = [task for repeat in repeats for task in repeat["tasks"]]
        latencies = [value for task in tasks for value in task.outcome_latency_ms]
        digest_sequences = [task.outcome_digests for task in tasks]
        reference = digest_sequences[0] if digest_sequences else []
        total_events = len(events) * worker_count * measured_repetitions
        total_wall_seconds = sum(float(item["wall_seconds"]) for item in repeats)
        total_outcomes = sum(task.outcome_count for task in tasks)
        total_failures = sum(task.failure_count for task in tasks)
        canonical_outcome_bytes = sum(task.canonical_outcome_bytes for task in tasks)
        rows.append(
            {
                "worker_count": worker_count,
                "hardware_manifest_digest": hardware_digest,
                "software_manifest_digest": software_digest,
                "measured_repetitions": measured_repetitions,
                "canonical_hash_equal": all(item == reference for item in digest_sequences),
                "events_per_second": total_events / total_wall_seconds,
                "p50_ms": percentile(latencies, 50),
                "p95_ms": percentile(latencies, 95),
                "p99_ms": percentile(latencies, 99),
                "peak_rss_mb": max(float(item["peak_rss_bytes"]) for item in repeats)
                / (1024 * 1024),
                "canonical_bytes_per_event": canonical_event_bytes / len(events),
                "canonical_bytes_per_outcome": (
                    canonical_outcome_bytes / total_outcomes if total_outcomes else None
                ),
                "replay_seconds": statistics.mean(
                    float(item["wall_seconds"]) for item in repeats
                ),
                "failure_fraction": (
                    total_failures / total_outcomes if total_outcomes else None
                ),
                "repeat_wall_seconds": [float(item["wall_seconds"]) for item in repeats],
            }
        )
    formal_configuration = (
        list(worker_counts) == [1, 2, 4, 8] and measured_repetitions == 5
    )
    formal = (
        formal_configuration
        and artifacts.status == "fitted"
        and not allow_synthetic
    )
    return {
        "registry": "RT6",
        "formal": formal,
        "formal_configuration": formal_configuration,
        "artifact_status": artifacts.status,
        "allow_synthetic": allow_synthetic,
        "hardware_manifest": hardware,
        "software_manifest": software,
        "rows": rows,
    }


def _run_batch(
    worker_count: int,
    contracts: ContractSet,
    artifacts: RuntimeArtifacts,
    events: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    *,
    allow_synthetic: bool,
    sample_rss: bool,
) -> dict[str, Any]:
    process = psutil.Process()
    stop = threading.Event()
    rss_values = [process.memory_info().rss]

    def sample() -> None:
        while not stop.wait(0.1):
            rss_values.append(process.memory_info().rss)

    sampler = threading.Thread(target=sample, daemon=True)
    if sample_rss:
        sampler.start()
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            tasks = list(
                executor.map(
                    lambda _index: _measure_task(
                        contracts,
                        artifacts,
                        events,
                        coverage,
                        allow_synthetic=allow_synthetic,
                    ),
                    range(worker_count),
                )
            )
    finally:
        stop.set()
        if sample_rss:
            sampler.join()
        rss_values.append(process.memory_info().rss)
    return {
        "wall_seconds": time.perf_counter() - started,
        "peak_rss_bytes": max(rss_values),
        "tasks": tasks,
    }


def _measure_task(
    contracts: ContractSet,
    artifacts: RuntimeArtifacts,
    events: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    *,
    allow_synthetic: bool,
) -> TaskMeasurement:
    started = time.perf_counter()
    result = ReferencePipeline(
        contracts, artifacts, allow_synthetic=allow_synthetic
    ).run(events, coverage)
    return TaskMeasurement(
        elapsed_seconds=time.perf_counter() - started,
        outcome_latency_ms=result.outcome_latency_ms,
        outcome_digests=[item["canonical_digest"] for item in result.outcomes],
        outcome_count=len(result.outcomes),
        failure_count=sum(
            item["object_type"] == "AssemblyFailureRecord" for item in result.outcomes
        ),
        canonical_outcome_bytes=sum(len(canonical_bytes(item)) for item in result.outcomes),
    )


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float64), quantile))
