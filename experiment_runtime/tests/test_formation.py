from __future__ import annotations

from datetime import timedelta

import pytest

from conftest import event
from trustepisode_runtime.formation import EpisodeSynthesizer, Lineage


def test_revisable_lineage_is_checked_before_open_candidates(contracts, artifacts, base_time) -> None:
    first = event(
        "edr:first",
        source_family="EDR",
        source_instance="edr-target-01",
        event_time=base_time,
        ingest_time=base_time,
        subject="host:edr-target-01",
        object_="process:ssh",
        action="process.start.remote_session",
        dependency_group="root:first",
        attributes={"phase": "start", "command_family": "remote_session"},
    )
    unrelated = event(
        "edr:advance",
        source_family="EDR",
        source_instance="edr-target-02",
        event_time=base_time + timedelta(seconds=500),
        ingest_time=base_time + timedelta(seconds=500),
        subject="host:edr-target-02",
        object_="process:hostname",
        action="process.start.discovery",
        dependency_group="root:advance",
        attributes={"phase": "start", "command_family": "discovery"},
    )
    late_related = event(
        "ndr:late",
        source_family="NDR",
        source_instance="ndr-gateway-01",
        event_time=base_time + timedelta(seconds=100),
        ingest_time=base_time + timedelta(seconds=550),
        subject="ip:172.30.11.10",
        object_="ip:172.30.12.10",
        action="network.flow",
        dependency_group="ndr-flow:late",
        attributes={"app_protocol": "ssh", "destination_port": 22},
    )
    synthesizer = EpisodeSynthesizer(
        contracts.thresholds["formation"],
        versions=artifacts.versions,
        entity_aliases=artifacts.entity_aliases,
    )
    result = synthesizer.synthesize([first, unrelated, late_related], flush=False)
    late_revisions = [
        item for item in result.revisions if item["late_evidence_reason"] == "accepted_within_horizon"
    ]
    assert len(late_revisions) == 1
    assert set(late_revisions[0]["ordered_event_ids"]) == {"edr:first", "ndr:late"}
    assert not any(
        item["state"] == "open" and "ndr:late" in item["ordered_event_ids"]
        for item in result.revisions
    )


@pytest.mark.parametrize(
    ("seconds", "expected"),
    ((299, True), (300, True), (301, False)),
)
def test_gap_boundary_conformance(
    contracts, artifacts, base_time, seconds: int, expected: bool
) -> None:
    synthesizer = EpisodeSynthesizer(
        contracts.thresholds["formation"],
        versions=artifacts.versions,
    )
    first = event(
        "edr:gap-origin",
        source_family="EDR",
        source_instance="edr-target-01",
        event_time=base_time,
        ingest_time=base_time,
        subject="host:boundary",
        object_="process:boundary",
        action="process.start.discovery",
        dependency_group="root:boundary",
        attributes={},
    )
    candidate = event(
        f"ndr:gap-{seconds}",
        source_family="NDR",
        source_instance="ndr-gateway-01",
        event_time=base_time + timedelta(seconds=seconds),
        ingest_time=base_time + timedelta(seconds=seconds),
        subject="host:boundary",
        object_="ip:boundary",
        action="network.flow",
        dependency_group="root:boundary",
        attributes={},
    )
    synthesizer.events[first["event_id"]] = first
    lineage = Lineage(
        episode_id="ep:gap-boundary",
        event_ids={first["event_id"]},
        reason_by_event={},
        start_event_id=first["event_id"],
    )

    assert (synthesizer._candidate(candidate, lineage) is not None) is expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    (
        (3599, True),
        (3600, True),
        (3601, False),
        # M7 live schedule offset: same inclusive W_max=3600 s contract; beyond-span ineligible.
        (3900, False),
    ),
)
def test_max_span_boundary_conformance(
    contracts, artifacts, base_time, seconds: int, expected: bool
) -> None:
    synthesizer = EpisodeSynthesizer(
        contracts.thresholds["formation"],
        versions=artifacts.versions,
    )
    origin = event(
        "edr:span-origin",
        source_family="EDR",
        source_instance="edr-target-01",
        event_time=base_time,
        ingest_time=base_time,
        subject="host:boundary",
        object_="process:origin",
        action="process.start.discovery",
        dependency_group="root:boundary",
        attributes={},
    )
    bridge = event(
        "edr:span-bridge",
        source_family="EDR",
        source_instance="edr-target-01",
        event_time=base_time + timedelta(seconds=3301),
        ingest_time=base_time + timedelta(seconds=3301),
        subject="host:boundary",
        object_="process:bridge",
        action="process.start.discovery",
        dependency_group="root:boundary",
        attributes={},
    )
    candidate = event(
        f"ndr:span-{seconds}",
        source_family="NDR",
        source_instance="ndr-gateway-01",
        event_time=base_time + timedelta(seconds=seconds),
        ingest_time=base_time + timedelta(seconds=seconds),
        subject="host:boundary",
        object_="ip:boundary",
        action="network.flow",
        dependency_group="root:boundary",
        attributes={},
    )
    synthesizer.events.update(
        {origin["event_id"]: origin, bridge["event_id"]: bridge}
    )
    lineage = Lineage(
        episode_id="ep:span-boundary",
        event_ids={origin["event_id"], bridge["event_id"]},
        reason_by_event={},
        start_event_id=origin["event_id"],
    )

    assert (synthesizer._candidate(candidate, lineage) is not None) is expected
