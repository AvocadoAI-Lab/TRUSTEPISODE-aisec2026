from __future__ import annotations

import bisect
import ipaddress
import math
from dataclasses import dataclass
from typing import Any, Iterable

from .canonical import sha256_digest, sort_references, utf8_key


DETECTOR_IDS = {
    "EDR": (
        "edr.process_anomaly.v1",
        "edr.remote_execution.v1",
        "edr.persistence_change.v1",
    ),
    "NDR": (
        "ndr.flow_anomaly.v1",
        "ndr.lateral_session.v1",
        "ndr.transfer_anomaly.v1",
    ),
}

PROCESS_ANOMALY = {
    "process_execution": 0.20,
    "discovery": 0.35,
    "http_client": 0.40,
    "network_scan": 0.45,
    "archive": 0.55,
    "file_change": 0.60,
    "service_admin": 0.65,
    "file_transfer": 0.75,
    "remote_session": 0.80,
    "package_manager": 0.20,
}


@dataclass(frozen=True)
class DetectorValue:
    source_family: str
    detector_id: str
    dependency_group: str
    value: float
    reference: dict[str, Any]

    @property
    def deduplication_key(self) -> tuple[str, str, str]:
        return (self.source_family, self.detector_id, self.dependency_group)


class DetectorEngine:
    """Frozen, label-blind detector implementation for instrumented lab events."""

    implementation_version = "trustepisode.detector-implementation.v1"

    def evaluate(self, events: Iterable[dict[str, Any]]) -> list[DetectorValue]:
        values: list[DetectorValue] = []
        for event in events:
            if event["source_family"] == "EDR":
                values.extend(self._edr(event))
            elif event["source_family"] == "NDR":
                values.extend(self._ndr(event))
        return self._deduplicate(values)

    def _edr(self, event: dict[str, Any]) -> list[DetectorValue]:
        attributes = event.get("attributes") or {}
        if attributes.get("phase") != "start":
            return []
        family = str(attributes.get("command_family") or "process_execution")
        reference = event_reference(event)
        output = [
            DetectorValue(
                "EDR",
                "edr.process_anomaly.v1",
                event["dependency_group"],
                PROCESS_ANOMALY.get(family, 0.20),
                reference,
            )
        ]
        if family in {"remote_session", "file_transfer"}:
            output.append(
                DetectorValue(
                    "EDR",
                    "edr.remote_execution.v1",
                    event["dependency_group"],
                    0.90 if family == "remote_session" else 0.70,
                    reference,
                )
            )
        if family in {"file_change", "service_admin", "package_manager"}:
            value = {"file_change": 0.55, "service_admin": 0.65, "package_manager": 0.25}[family]
            output.append(
                DetectorValue(
                    "EDR",
                    "edr.persistence_change.v1",
                    event["dependency_group"],
                    value,
                    reference,
                )
            )
        return output

    def _ndr(self, event: dict[str, Any]) -> list[DetectorValue]:
        attributes = event.get("attributes") or {}
        native = finite_unit(attributes.get("signature_severity"))
        event_type = str(attributes.get("eve_event_type") or "flow")
        baseline = {"alert": 0.60, "http": 0.25, "dns": 0.20, "tls": 0.20, "flow": 0.15}.get(event_type, 0.15)
        flow_value = max(baseline, native or 0.0)
        reference = event_reference(event)
        output = [
            DetectorValue(
                "NDR",
                "ndr.flow_anomaly.v1",
                event["dependency_group"],
                flow_value,
                reference,
            )
        ]
        protocol = str(attributes.get("app_protocol") or attributes.get("protocol") or "").lower()
        port = attributes.get("destination_port")
        if (protocol == "ssh" or port == 22) and _both_private(event["subject"], event["object"]):
            output.append(
                DetectorValue(
                    "NDR",
                    "ndr.lateral_session.v1",
                    event["dependency_group"],
                    0.90,
                    reference,
                )
            )
        transfer_values = {"ssh": 0.65, "smb": 0.85, "nfs": 0.85, "ftp": 0.80, "http": 0.45}
        if protocol in transfer_values:
            output.append(
                DetectorValue(
                    "NDR",
                    "ndr.transfer_anomaly.v1",
                    event["dependency_group"],
                    transfer_values[protocol],
                    reference,
                )
            )
        return output

    @staticmethod
    def _deduplicate(values: list[DetectorValue]) -> list[DetectorValue]:
        grouped: dict[tuple[str, str, str], list[DetectorValue]] = {}
        for value in values:
            grouped.setdefault(value.deduplication_key, []).append(value)
        by_key: dict[tuple[str, str, str], DetectorValue] = {}
        for key, candidates in grouped.items():
            # A detector emits one root-level value: maximum evidence value,
            # then canonical reference digest for deterministic ties.
            by_key[key] = min(
                candidates,
                key=lambda item: (-item.value, sha256_digest(item.reference)),
            )
        return sorted(
            by_key.values(),
            key=lambda item: (
                utf8_key(item.source_family),
                utf8_key(item.detector_id),
                utf8_key(item.dependency_group),
            ),
        )


class EmpiricalNormalizer:
    def __init__(self, negative_values: dict[str, list[float]]) -> None:
        self.values: dict[str, tuple[float, ...]] = {}
        for detector_id in sorted({item for values in DETECTOR_IDS.values() for item in values}):
            cohort = negative_values.get(detector_id) or []
            checked = [require_unit(item) for item in cohort]
            if not checked:
                raise ValueError(f"empty negative normalizer cohort: {detector_id}")
            self.values[detector_id] = tuple(sorted(checked))

    def transform(self, detector_id: str, raw_value: float) -> float:
        value = require_unit(raw_value)
        cohort = self.values[detector_id]
        less = bisect.bisect_left(cohort, value)
        less_or_equal = bisect.bisect_right(cohort, value)
        equal = less_or_equal - less
        return (less + 0.5 * equal) / len(cohort)

    def family_digest(self, family: str) -> str:
        return sha256_digest(
            {
                "family": family,
                "tie_rule": "(count_less+0.5*count_equal)/N",
                "detectors": [
                    {"detector_id": detector_id, "values": list(self.values[detector_id])}
                    for detector_id in DETECTOR_IDS[family]
                ],
            }
        )


class FeatureExtractor:
    version = "trustepisode.feature.v1"

    def __init__(
        self,
        detector_engine: DetectorEngine,
        normalizer: EmpiricalNormalizer,
        detector_registry_digest: str,
    ) -> None:
        self.engine = detector_engine
        self.normalizer = normalizer
        self.detector_registry_digest = detector_registry_digest

    def extract(
        self,
        revision: dict[str, Any],
        event_by_id: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Any], list[DetectorValue]]:
        events = [event_by_id[event_id] for event_id in revision["ordered_event_ids"]]
        detector_values = self.engine.evaluate(events)
        normalized = [
            (self.normalizer.transform(item.detector_id, item.value), item)
            for item in detector_values
        ]
        normalized.sort(
            key=lambda pair: (
                -pair[0],
                utf8_key(pair[1].detector_id),
                utf8_key(pair[1].dependency_group),
            )
        )
        eligible_count = len(normalized)
        D = (
            sum(value for value, _ in normalized[: min(3, eligible_count)]) / min(3, eligible_count)
            if eligible_count
            else 0.0
        )
        source_mask = {
            family: int(any(event["source_family"] == family for event in events))
            for family in ("EDR", "NDR")
        }
        corroboration_support = {
            family: int(any(item.source_family == family for item in detector_values))
            for family in ("EDR", "NDR")
        }
        observation = {
            family: (
                "not_examined"
                if source_mask[family] == 0
                else "detected"
                if corroboration_support[family]
                else "examined_none"
            )
            for family in ("EDR", "NDR")
        }
        feature = {
            "object_type": "FeatureVector",
            "schema_version": "trustepisode.online.v1",
            "episode_id": revision["episode_id"],
            "revision": revision["revision"],
            "D": D,
            "C": corroboration_support["EDR"] * corroboration_support["NDR"],
            "source_mask": source_mask,
            "detector_observation": observation,
            "detector_registry_digest": self.detector_registry_digest,
            "eligible_detector_count": eligible_count,
            "corroboration_support": corroboration_support,
            "feature_version": self.version,
            "normalizer_hashes": {
                family: self.normalizer.family_digest(family) for family in ("EDR", "NDR")
            },
            "ordered_input_references": sort_references(
                item.reference for item in detector_values
            ),
        }
        return feature, detector_values


def finite_unit(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and 0.0 <= number <= 1.0 else None


def require_unit(value: Any) -> float:
    number = finite_unit(value)
    if number is None:
        raise ValueError(f"detector value outside finite [0,1]: {value!r}")
    return number


def event_reference(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference_kind": "object",
        "raw_pointer": event["raw_pointer"],
        "dependency_group": event["dependency_group"],
        "relation": "feature",
    }


def _both_private(subject: str, object_: str) -> bool:
    try:
        first = ipaddress.ip_address(subject.split(":", 1)[1])
        second = ipaddress.ip_address(object_.split(":", 1)[1])
    except (IndexError, ValueError):
        return False
    return first.is_private and second.is_private
