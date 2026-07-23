from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trustepisode_runtime.canonical import sha256_digest, timestamp
from trustepisode_runtime.contract_io import ContractSet
from trustepisode_runtime.pipeline import RuntimeArtifacts


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def contracts() -> ContractSet:
    return ContractSet(ROOT / "artifacts" / "contracts")


@pytest.fixture
def base_time() -> datetime:
    return datetime(2026, 7, 12, 12, 0, 0, tzinfo=timezone.utc)


def raw_pointer(prefix: str, event_id: str) -> dict:
    digest = sha256_digest({"prefix": prefix, "event_id": event_id})
    return {
        "object_id": f"{prefix}:{event_id}",
        "content_digest": digest,
        "locator": f"fixture:{event_id}",
        "storage_schema_version": "fixture.raw.v1",
    }


def event(
    event_id: str,
    *,
    source_family: str,
    source_instance: str,
    event_time: datetime,
    ingest_time: datetime,
    subject: str,
    object_: str,
    action: str,
    dependency_group: str,
    attributes: dict,
) -> dict:
    return {
        "object_type": "NormalizedEvent",
        "schema_version": "trustepisode.online.v1",
        "event_id": event_id,
        "event_time": timestamp(event_time),
        "ingest_time": timestamp(ingest_time),
        "source_family": source_family,
        "source_instance": source_instance,
        "subject": subject,
        "object": object_,
        "action": action,
        "raw_pointer": raw_pointer(source_family.lower(), event_id.replace(":", "-")),
        "dependency_group": dependency_group,
        "parser_version": f"fixture.{source_family.lower()}.v1",
        "attributes": attributes,
    }


def coverage(family: str, instance: str, start: datetime, end: datetime, **overrides) -> dict:
    value = {
        "object_type": "SourceCoverage",
        "schema_version": "trustepisode.online.v1",
        "source_family": family,
        "source_instance": instance,
        "interval_start": timestamp(start),
        "interval_end": timestamp(end),
        "expected": True,
        "health": "healthy",
        "parser_valid": True,
        "observed_lag_seconds": 0.0,
        "heartbeat_period_seconds": 30,
        "missed_heartbeat_count": 0,
        "transport_live": True,
        "reason_code": "ok",
        "monitor_version": "fixture.monitor.v1",
        "policy_version": "trustepisode.source-health.v1",
    }
    value.update(overrides)
    return value


@pytest.fixture
def sample_stream(base_time: datetime):
    events = [
        event(
            "edr:e1",
            source_family="EDR",
            source_instance="edr-target-01",
            event_time=base_time,
            ingest_time=base_time + timedelta(seconds=1),
            subject="host:edr-target-01",
            object_="process:ssh",
            action="process.start.remote_session",
            dependency_group="edr-process:root-1",
            attributes={
                "phase": "start",
                "pid": 100,
                "ppid": 10,
                "executable": "ssh",
                "command_family": "remote_session",
                "argv_sha256": "a" * 64,
                "exit_code": None,
            },
        ),
        event(
            "ndr:n1",
            source_family="NDR",
            source_instance="ndr-gateway-01",
            event_time=base_time + timedelta(seconds=30),
            ingest_time=base_time + timedelta(seconds=31),
            subject="ip:172.30.11.10",
            object_="ip:172.30.12.10",
            action="network.flow",
            dependency_group="ndr-flow:ndr-gateway-01:42",
            attributes={
                "eve_event_type": "flow",
                "protocol": "tcp",
                "app_protocol": "ssh",
                "source_port": 45000,
                "destination_port": 22,
                "flow_id": "42",
                "signature_id": None,
                "signature_severity": 0.0,
            },
        ),
    ]
    coverages = [
        coverage("EDR", "edr-target-01", base_time - timedelta(minutes=10), base_time + timedelta(hours=2)),
        coverage("EDR", "edr-target-02", base_time - timedelta(minutes=10), base_time + timedelta(hours=2)),
        coverage("NDR", "ndr-gateway-01", base_time - timedelta(minutes=10), base_time + timedelta(hours=2)),
    ]
    return events, coverages


@pytest.fixture
def artifacts(contracts: ContractSet) -> RuntimeArtifacts:
    value = RuntimeArtifacts.synthetic(contracts)
    value.entity_aliases = {
        "ip:172.30.11.10": "host:edr-target-01",
        "ip:172.30.12.10": "host:edr-target-02",
    }
    return value
