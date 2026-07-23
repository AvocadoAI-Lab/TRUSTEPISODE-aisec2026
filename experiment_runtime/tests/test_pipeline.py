from __future__ import annotations

from datetime import timedelta
from copy import deepcopy
from types import SimpleNamespace

import pytest

from trustepisode_runtime.pipeline import ReferencePipeline, RuntimeArtifacts


def _support_for_u(
    *, health: str = "healthy", parser_valid: bool = True, reference_kind: str = "object"
):
    coverage = SimpleNamespace(
        health=health,
        parser_valid=parser_valid,
        references=[{"reference_kind": reference_kind}],
    )
    return SimpleNamespace(
        health_snapshot={"EDR": health, "NDR": health},
        family_coverage={"EDR": coverage, "NDR": coverage},
        decision={"kappa": "supported_global"},
    )


def _revision_for_u(*, state: str = "closed", late_reason=None):
    return {
        "state": state,
        "late_evidence_reason": late_reason,
        "ordered_event_ids": [],
    }


def test_runtime_preserves_support_semantics_when_descriptive_keys_are_absent(
    contracts,
) -> None:
    resolution = contracts.thresholds["detector_availability_resolution"]
    resolution.pop("coverage_selection_point", None)
    resolution.pop("covering_interval_cardinality", None)

    artifacts = RuntimeArtifacts.synthetic(contracts)

    assert artifacts.support_manifest_digest.startswith("sha256:")


def test_pipeline_produces_schema_valid_unique_terminal_outcomes(
    contracts, artifacts, sample_stream
) -> None:
    events, coverage = sample_stream
    pipeline = ReferencePipeline(contracts, artifacts, allow_synthetic=True)
    result = pipeline.run(events, coverage)
    assert result.synthesis.revisions
    assert len(result.outcomes) == len(result.synthesis.revisions)
    keys = {(item["episode_id"], item["revision"]) for item in result.outcomes}
    assert len(keys) == len(result.outcomes)
    for item in result.outcomes:
        contracts.validate_online(item)
    supported = [
        item
        for item in result.outcomes
        if item["object_type"] == "AuditRecord" and item["decision_eligible"]
    ]
    assert supported
    assert all(item["P"] is not None for item in supported)
    assert all(item["source_mask"] == {"EDR": 1, "NDR": 1} for item in supported)


def test_pipeline_is_byte_digest_deterministic(contracts, artifacts, sample_stream) -> None:
    events, coverage = sample_stream
    first = ReferencePipeline(contracts, artifacts, allow_synthetic=True).run(events, coverage)
    second = ReferencePipeline(contracts, artifacts, allow_synthetic=True).run(events, coverage)
    assert [item["canonical_digest"] for item in first.outcomes] == [
        item["canonical_digest"] for item in second.outcomes
    ]
    assert [item["membership_digest"] for item in first.synthesis.revisions] == [
        item["membership_digest"] for item in second.synthesis.revisions
    ]


def test_support_uses_event_end_not_future_close_watermark(
    contracts, artifacts, sample_stream, base_time
) -> None:
    events, coverage = sample_stream
    short_coverage = [
        {
            **item,
            "interval_end": (base_time + timedelta(seconds=60))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
        }
        for item in coverage
    ]
    result = ReferencePipeline(contracts, artifacts, allow_synthetic=True).run(
        events, short_coverage
    )
    assert all(item["object_type"] == "AuditRecord" for item in result.outcomes)


def test_pipeline_rejects_stale_runtime_versions(contracts, artifacts) -> None:
    stale = deepcopy(artifacts)
    stale.versions["support_policy"]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="VersionSet"):
        ReferencePipeline(contracts, stale, allow_synthetic=True)


@pytest.mark.parametrize(
    ("health", "parser_valid", "expected"),
    (
        ("unknown", True, "unknown"),
        ("healthy", False, "unavailable"),
        ("degraded", True, "degraded"),
        ("healthy", True, "complete"),
    ),
)
def test_table2_coverage_precedence(health, parser_valid, expected) -> None:
    value = ReferencePipeline._sufficiency(
        _revision_for_u(),
        _support_for_u(health=health, parser_valid=parser_valid),
        {},
    )
    assert value["coverage"] == expected


@pytest.mark.parametrize(
    ("reference_kind", "expected"), (("object", "complete"), ("sentinel", "missing"))
)
def test_table2_provenance_v1_states(reference_kind, expected) -> None:
    value = ReferencePipeline._sufficiency(
        _revision_for_u(),
        _support_for_u(reference_kind=reference_kind),
        {},
    )
    assert value["provenance"] == expected


@pytest.mark.parametrize(
    ("state", "late_reason", "expected"),
    (
        ("closed", "accepted_within_horizon", "late_accepted"),
        ("open", None, "revisable"),
        ("finalized", None, "revisable"),
        ("closed", None, "stable"),
    ),
)
def test_table2_lateness_precedence(state, late_reason, expected) -> None:
    value = ReferencePipeline._sufficiency(
        _revision_for_u(state=state, late_reason=late_reason),
        _support_for_u(),
        {},
    )
    assert value["lateness"] == expected


def test_table2_calibration_copies_scope_resolution() -> None:
    support = _support_for_u()
    support.decision["kappa"] = "out_of_support"
    value = ReferencePipeline._sufficiency(_revision_for_u(), support, {})
    assert value["calibration"] == "out_of_support"
