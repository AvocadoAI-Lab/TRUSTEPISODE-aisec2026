from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .canonical import sha256_digest, timestamp
from .features import DETECTOR_IDS


def synthetic_fixture() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    anchor = datetime(2026, 7, 12, 12, 0, 0, tzinfo=timezone.utc)
    events = [
        _event(
            "edr:demo:1",
            family="EDR",
            instance="edr-target-01",
            event_time=anchor,
            ingest_time=anchor + timedelta(seconds=1),
            subject="host:edr-target-01",
            object_="process:ssh",
            action="process.start.remote_session",
            group="edr-process:demo-root-1",
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
        _event(
            "ndr:demo:1",
            family="NDR",
            instance="ndr-gateway-01",
            event_time=anchor + timedelta(seconds=30),
            ingest_time=anchor + timedelta(seconds=31),
            subject="ip:172.30.11.10",
            object_="ip:172.30.12.10",
            action="network.flow",
            group="ndr-flow:ndr-gateway-01:42",
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
        _coverage("EDR", "edr-target-01", anchor),
        _coverage("EDR", "edr-target-02", anchor),
        _coverage("NDR", "ndr-gateway-01", anchor),
    ]
    truth = {
        "truth_type": "trustepisode.offline-truth.v1",
        "entity_aliases": {
            "ip:172.30.11.10": "host:edr-target-01",
            "ip:172.30.12.10": "host:edr-target-02",
        },
        "groups": [
            {
                "group_id": "demo-group-1",
                "start": timestamp(anchor),
                "end": timestamp(anchor + timedelta(seconds=30)),
                "entities": [
                    "host:edr-target-01",
                    "host:edr-target-02",
                    "process:ssh",
                ],
                "required_action_tokens": [
                    "command_family:remote_session",
                    "network.flow",
                ],
            }
        ],
        "benign_action_tokens": ["process.start.package_query"],
        "truth_conflict": False,
    }
    return events, coverages, truth


def synthetic_training_input() -> dict[str, Any]:
    detector_ids = tuple(
        detector_id
        for family in ("EDR", "NDR")
        for detector_id in DETECTOR_IDS[family]
    )
    normalizer_values = {
        detector_id: [0.0, 0.25, 0.5, 0.75, 1.0] for detector_id in detector_ids
    }
    raw_rows = []
    calibration_rows = []
    for index in range(20):
        label = int(index >= 10)
        D = 0.1 + 0.02 * index if not label else 0.6 + 0.015 * (index - 10)
        C = int(index % 3 == 0) if not label else 1
        revision_id = f"train:{index:02d}"
        raw_rows.append({"revision_id": revision_id, "D": D, "C": C, "label": label})
        calibration_rows.append(
            {
                "revision_id": f"cal:{index:02d}",
                "z": -2.0 + 0.2 * index,
                "label": label,
            }
        )
    return {
        "training_input_type": "trustepisode.runtime-training-input.v1",
        "normalizer_values": normalizer_values,
        "raw_training_rows": raw_rows,
        "calibration_rows": calibration_rows,
        "expected_instances": {
            "EDR": ["edr-target-01", "edr-target-02"],
            "NDR": ["ndr-gateway-01"],
        },
        "entity_aliases": {
            "ip:172.30.11.10": "host:edr-target-01",
            "ip:172.30.12.10": "host:edr-target-02",
        },
    }


def _event(
    event_id: str,
    *,
    family: str,
    instance: str,
    event_time: datetime,
    ingest_time: datetime,
    subject: str,
    object_: str,
    action: str,
    group: str,
    attributes: dict[str, Any],
) -> dict[str, Any]:
    pointer_digest = sha256_digest({"event_id": event_id, "family": family})
    return {
        "object_type": "NormalizedEvent",
        "schema_version": "trustepisode.online.v1",
        "event_id": event_id,
        "event_time": timestamp(event_time),
        "ingest_time": timestamp(ingest_time),
        "source_family": family,
        "source_instance": instance,
        "subject": subject,
        "object": object_,
        "action": action,
        "raw_pointer": {
            "object_id": f"demo:{event_id}",
            "content_digest": pointer_digest,
            "locator": f"fixture:{event_id}",
            "storage_schema_version": "fixture.raw.v1",
        },
        "dependency_group": group,
        "parser_version": f"fixture.{family.lower()}.v1",
        "attributes": attributes,
    }


def _coverage(family: str, instance: str, anchor: datetime) -> dict[str, Any]:
    return {
        "object_type": "SourceCoverage",
        "schema_version": "trustepisode.online.v1",
        "source_family": family,
        "source_instance": instance,
        "interval_start": timestamp(anchor - timedelta(minutes=10)),
        "interval_end": timestamp(anchor + timedelta(hours=2)),
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
