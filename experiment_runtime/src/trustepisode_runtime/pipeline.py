from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .canonical import digest_fields, sha256_digest, sort_references
from .contract_io import ContractSet
from .features import DETECTOR_IDS, DetectorEngine, DetectorValue, EmpiricalNormalizer, FeatureExtractor
from .formation import EpisodeSynthesizer, SynthesisResult
from .scoring import AffineCalibrator, RawModel
from .support import SupportResolution, SupportResolver, support_contract_metadata


ASSEMBLY_INPUT_ORDER = [
    "EpisodeRevision",
    "FeatureVector",
    "RawLogit",
    "SupportDecision",
    "CalibratedProbability",
    "UProfile",
    "SourceCoverage",
]
AUDIT_DIGEST_FIELDS = (
    "object_type",
    "schema_version",
    "episode_id",
    "revision",
    "episode_revision_digest",
    "D",
    "C",
    "z",
    "P",
    "kappa",
    "calibration_group_key",
    "decision_eligible",
    "U",
    "source_mask",
    "detector_observation",
    "health_snapshot",
    "resolved_detector_state",
    "eligible_detector_count",
    "eligibility_reason",
    "coverage_ref_ids",
    "health_snapshot_digest",
    "ordered_evidence_references",
    "versions",
)
FAILURE_DIGEST_FIELDS = (
    "object_type",
    "schema_version",
    "episode_id",
    "revision",
    "episode_revision_digest",
    "failure_code",
    "observed_input_types",
    "assembly_policy_version",
)
VERSION_COMPONENTS = (
    "schema",
    "parser",
    "formation_policy",
    "detector_registry",
    "feature_policy",
    "normalizer",
    "raw_model",
    "calibrator",
    "support_policy",
    "sufficiency_policy",
    "assembly_policy",
    "manifest",
)


@dataclass
class RuntimeArtifacts:
    status: str
    normalizer_values: dict[str, list[float]]
    raw_model: RawModel
    global_calibrator: AffineCalibrator
    expected_instances: dict[str, list[str]]
    support_manifest_digest: str
    versions: dict[str, dict[str, str]]
    d_only_model: RawModel | None = None
    group_calibrators: dict[str, AffineCalibrator] = field(default_factory=dict)
    entity_aliases: dict[str, str] = field(default_factory=dict)

    @classmethod
    def synthetic(
        cls,
        contracts: ContractSet,
        *,
        expected_instances: dict[str, list[str]] | None = None,
    ) -> "RuntimeArtifacts":
        values = {
            detector_id: [0.0, 0.25, 0.5, 0.75, 1.0]
            for family in DETECTOR_IDS.values()
            for detector_id in family
        }
        raw_payload = {"status": "synthetic_test_only", "coefficients": [-1.5, 3.0, 0.5]}
        calibration_payload = {"status": "synthetic_test_only", "coefficients": [1.0, 0.0]}
        raw = RawModel(-1.5, 3.0, 0.5, sha256_digest(raw_payload), "synthetic_test_only")
        d_only_payload = {"status": "synthetic_test_only", "coefficients": [-1.5, 3.0, 0.0]}
        d_only = RawModel(
            -1.5,
            3.0,
            0.0,
            sha256_digest(d_only_payload),
            "synthetic_test_only",
        )
        calibrator = AffineCalibrator(1.0, 0.0, sha256_digest(calibration_payload), "synthetic_test_only")
        instances = expected_instances or {
            "EDR": ["edr-target-01", "edr-target-02"],
            "NDR": ["ndr-gateway-01"],
        }
        support_payload = {
            "source_mask": {"EDR": 1, "NDR": 1},
            "expected_instances": instances,
            "allowed_health": ["healthy", "degraded"],
            "allowed_detector_states": ["available", "no_detection"],
            **support_contract_metadata(contracts.thresholds),
            "status": "synthetic_test_only",
        }
        support_digest = sha256_digest(support_payload)
        versions = build_versions(
            contracts,
            raw_model_digest=raw.artifact_digest,
            calibrator_digest=calibrator.artifact_digest,
            support_manifest_digest=support_digest,
            normalizer_values=values,
        )
        return cls(
            status="synthetic_test_only",
            normalizer_values=values,
            raw_model=raw,
            global_calibrator=calibrator,
            expected_instances=instances,
            support_manifest_digest=support_digest,
            versions=versions,
            d_only_model=d_only,
        )

    @classmethod
    def from_path(cls, path: Path) -> "RuntimeArtifacts":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeArtifacts":
        raw_data = data["raw_model"]
        d_only_data = data.get("d_only_model")
        calibrator_data = data["global_calibrator"]
        groups = {
            key: AffineCalibrator(
                float(value["slope"]),
                float(value["intercept"]),
                value["artifact_digest"],
                value.get("status", "fitted"),
            )
            for key, value in (data.get("group_calibrators") or {}).items()
        }
        return cls(
            status=data["status"],
            normalizer_values=data["normalizer_values"],
            raw_model=RawModel(
                float(raw_data["intercept"]),
                float(raw_data["weight_D"]),
                float(raw_data["weight_C"]),
                raw_data["artifact_digest"],
                raw_data.get("status", data["status"]),
            ),
            global_calibrator=AffineCalibrator(
                float(calibrator_data["slope"]),
                float(calibrator_data["intercept"]),
                calibrator_data["artifact_digest"],
                calibrator_data.get("status", data["status"]),
            ),
            expected_instances=data["expected_instances"],
            support_manifest_digest=data["support_manifest_digest"],
            versions=data["versions"],
            d_only_model=(
                RawModel(
                    float(d_only_data["intercept"]),
                    float(d_only_data["weight_D"]),
                    0.0,
                    d_only_data["artifact_digest"],
                    d_only_data.get("status", data["status"]),
                )
                if d_only_data
                else None
            ),
            group_calibrators=groups,
            entity_aliases=data.get("entity_aliases") or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": "trustepisode.runtime-artifacts.v1",
            "status": self.status,
            "normalizer_values": self.normalizer_values,
            "raw_model": {
                "status": self.raw_model.status,
                "intercept": self.raw_model.intercept,
                "weight_D": self.raw_model.weight_D,
                "weight_C": self.raw_model.weight_C,
                "artifact_digest": self.raw_model.artifact_digest,
            },
            "d_only_model": (
                {
                    "status": self.d_only_model.status,
                    "intercept": self.d_only_model.intercept,
                    "weight_D": self.d_only_model.weight_D,
                    "weight_C": 0.0,
                    "artifact_digest": self.d_only_model.artifact_digest,
                }
                if self.d_only_model is not None
                else None
            ),
            "global_calibrator": {
                "status": self.global_calibrator.status,
                "slope": self.global_calibrator.slope,
                "intercept": self.global_calibrator.intercept,
                "artifact_digest": self.global_calibrator.artifact_digest,
            },
            "group_calibrators": {
                key: {
                    "status": item.status,
                    "slope": item.slope,
                    "intercept": item.intercept,
                    "artifact_digest": item.artifact_digest,
                }
                for key, item in sorted(self.group_calibrators.items())
            },
            "expected_instances": self.expected_instances,
            "support_manifest_digest": self.support_manifest_digest,
            "entity_aliases": self.entity_aliases,
            "versions": self.versions,
        }


@dataclass
class PipelineResult:
    synthesis: SynthesisResult
    features: list[dict[str, Any]] = field(default_factory=list)
    support_decisions: list[dict[str, Any]] = field(default_factory=list)
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    detector_outputs: list[dict[str, Any]] = field(default_factory=list)
    outcome_latency_ms: list[float] = field(default_factory=list)


class ReferencePipeline:
    def __init__(
        self,
        contracts: ContractSet,
        artifacts: RuntimeArtifacts,
        *,
        allow_synthetic: bool = False,
    ) -> None:
        self.contracts = contracts
        self.artifacts = artifacts
        if artifacts.status != "fitted" and not allow_synthetic:
            raise ValueError("formal inference requires fitted runtime artifacts")
        expected_versions = build_versions(
            contracts,
            raw_model_digest=artifacts.raw_model.artifact_digest,
            calibrator_digest=artifacts.global_calibrator.artifact_digest,
            support_manifest_digest=artifacts.support_manifest_digest,
            normalizer_values=artifacts.normalizer_values,
        )
        if artifacts.versions != expected_versions:
            raise ValueError("runtime artifact VersionSet does not match current contracts")
        normalizer = EmpiricalNormalizer(artifacts.normalizer_values)
        detector_digest = sha256_digest(contracts.detectors)
        self.extractor = FeatureExtractor(DetectorEngine(), normalizer, detector_digest)
        self.resolver = SupportResolver(
            expected_instances=artifacts.expected_instances,
            support_manifest_digest=artifacts.support_manifest_digest,
            enabled_group_keys=artifacts.group_calibrators,
        )

    def run(
        self,
        events: Iterable[dict[str, Any]],
        coverage_records: Iterable[dict[str, Any]],
        *,
        group_key: str | None = None,
        flush: bool = True,
        hub_suppression: bool = True,
    ) -> PipelineResult:
        event_list = list(events)
        coverage_list = list(coverage_records)
        for event in event_list:
            self.contracts.validate_online(event)
            if event["object_type"] != "NormalizedEvent":
                raise ValueError("event stream contains a non-NormalizedEvent")
        for coverage in coverage_list:
            self.contracts.validate_online(coverage)
            if coverage["object_type"] != "SourceCoverage":
                raise ValueError("coverage stream contains a non-SourceCoverage object")

        formation = copy.deepcopy(self.contracts.thresholds["formation"])
        if not hub_suppression:
            formation["hub_distinct_relation_cutoff"] = 2**31 - 1
        synthesizer = EpisodeSynthesizer(
            formation,
            versions=self.artifacts.versions,
            entity_aliases=self.artifacts.entity_aliases,
        )
        synthesis = synthesizer.synthesize(event_list, flush=flush)
        result = PipelineResult(synthesis=synthesis)
        for revision in synthesis.revisions:
            started_ns = time.perf_counter_ns()
            outcome = self._process_revision(
                revision,
                synthesis.event_by_id,
                coverage_list,
                result,
                group_key=group_key,
            )
            result.outcome_latency_ms.append(
                (time.perf_counter_ns() - started_ns) / 1_000_000.0
            )
            result.outcomes.append(outcome)
        for record in synthesis.late_records:
            self.contracts.validate_online(record)
        return result

    def _process_revision(
        self,
        revision: dict[str, Any],
        event_by_id: dict[str, dict[str, Any]],
        coverage: list[dict[str, Any]],
        result: PipelineResult,
        *,
        group_key: str | None,
    ) -> dict[str, Any]:
        observed_inputs = ["EpisodeRevision"]
        revision_digest = sha256_digest(revision)
        try:
            self.contracts.validate_online(revision)
            feature, detector_values = self.extractor.extract(revision, event_by_id)
            observed_inputs.append("FeatureVector")
            self.contracts.validate_online(feature)
            result.features.append(feature)
            result.detector_outputs.extend(
                serialize_detector_value(revision, item) for item in detector_values
            )

            z = self.artifacts.raw_model.score(feature["D"], feature["C"])
            observed_inputs.append("RawLogit")
            support = self.resolver.resolve(
                revision,
                feature,
                coverage,
                group_key=group_key,
                calibration_available=self.artifacts.global_calibrator.status in {"fitted", "synthetic_test_only"},
            )
            observed_inputs.append("SupportDecision")
            self.contracts.validate_online(support.decision)
            result.support_decisions.append(support.decision)
            probability = self._calibrate(z, support.decision)
            observed_inputs.append("CalibratedProbability")
            U = self._sufficiency(revision, support, event_by_id)
            observed_inputs.append("UProfile")
            observed_inputs.append("SourceCoverage")
            audit = self._assemble(
                revision,
                revision_digest,
                feature,
                z,
                probability,
                support,
                U,
                event_by_id,
            )
            self.contracts.validate_online(audit)
            return audit
        except Exception as exc:
            failure_code = classify_failure(exc, observed_inputs)
            failure = {
                "object_type": "AssemblyFailureRecord",
                "schema_version": "trustepisode.online.v1",
                "episode_id": revision["episode_id"],
                "revision": revision["revision"],
                "episode_revision_digest": revision_digest,
                "failure_code": failure_code,
                "observed_input_types": [
                    item for item in ASSEMBLY_INPUT_ORDER if item in observed_inputs
                ],
                "assembly_policy_version": "trustepisode.assembly.v1",
            }
            failure["canonical_digest"] = digest_fields(failure, FAILURE_DIGEST_FIELDS)
            self.contracts.validate_online(failure)
            return failure

    def _calibrate(self, z: float, decision: dict[str, Any]) -> float | None:
        if not decision["decision_eligible"]:
            return None
        if decision["kappa"] == "supported_group":
            key = decision["calibration_group_key"]
            if key not in self.artifacts.group_calibrators:
                raise ValueError("missing_input: selected group calibrator missing")
            return self.artifacts.group_calibrators[key].probability(z)
        return self.artifacts.global_calibrator.probability(z)

    @staticmethod
    def _sufficiency(
        revision: dict[str, Any],
        support: SupportResolution,
        event_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, str]:
        family_health = support.health_snapshot
        if any(item == "unknown" for item in family_health.values()):
            coverage = "unknown"
        elif any(
            item.health in {"down", "not_applicable"} or not item.parser_valid
            for item in support.family_coverage.values()
        ):
            coverage = "unavailable"
        elif any(item == "degraded" for item in family_health.values()):
            coverage = "degraded"
        else:
            coverage = "complete"

        required_refs_present = all(
            reference["reference_kind"] == "object"
            for item in support.family_coverage.values()
            for reference in item.references
        )
        provenance = "complete" if required_refs_present else "missing"
        if revision["late_evidence_reason"] == "accepted_within_horizon":
            lateness = "late_accepted"
        elif revision["state"] in {"open", "finalized"}:
            lateness = "revisable"
        else:
            lateness = "stable"
        contradiction = contradiction_status(
            [event_by_id[event_id] for event_id in revision["ordered_event_ids"]]
        )
        return {
            "coverage": coverage,
            "provenance": provenance,
            "lateness": lateness,
            "contradiction": contradiction,
            "calibration": support.decision["kappa"],
        }

    def _assemble(
        self,
        revision: dict[str, Any],
        revision_digest: str,
        feature: dict[str, Any],
        z: float,
        probability: float | None,
        support: SupportResolution,
        U: dict[str, str],
        event_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        if any(
            reference["reference_kind"] != "object"
            for item in support.family_coverage.values()
            for reference in item.references
        ):
            raise ValueError("missing_input: required SourceCoverage reference is absent")
        membership = [
            {
                "reference_kind": "object",
                "raw_pointer": event_by_id[event_id]["raw_pointer"],
                "dependency_group": event_by_id[event_id]["dependency_group"],
                "relation": "membership",
            }
            for event_id in revision["ordered_event_ids"]
        ]
        links = [
            {
                "reference_kind": "object",
                "raw_pointer": event_by_id[event_id]["raw_pointer"],
                "dependency_group": event_by_id[event_id]["dependency_group"],
                "relation": "link",
            }
            for event_id in revision["ordered_event_ids"][1:]
        ]
        contradiction_reference = {
            "reference_kind": "sentinel",
            "relation": "contradiction",
            "dependency_group": f"contradiction:{revision['episode_id']}:{revision['revision']}",
            "sentinel_reason": "not_applicable" if U["contradiction"] == "none" else "unresolved_optional",
            "expected_object_id": None,
        }
        references = sort_references(
            [
                *membership,
                *links,
                *feature["ordered_input_references"],
                *support.decision["ordered_coverage_references"],
                contradiction_reference,
            ]
        )
        decision = support.decision
        audit = {
            "object_type": "AuditRecord",
            "schema_version": "trustepisode.online.v1",
            "episode_id": revision["episode_id"],
            "revision": revision["revision"],
            "episode_revision_digest": revision_digest,
            "D": feature["D"],
            "C": feature["C"],
            "z": z,
            "P": probability,
            "kappa": decision["kappa"],
            "calibration_group_key": decision["calibration_group_key"],
            "decision_eligible": decision["decision_eligible"],
            "U": U,
            "source_mask": feature["source_mask"],
            "detector_observation": feature["detector_observation"],
            "health_snapshot": support.health_snapshot,
            "resolved_detector_state": decision["resolved_detector_state"],
            "eligible_detector_count": decision["eligible_detector_count"],
            "eligibility_reason": decision["eligibility_reason"],
            "coverage_ref_ids": decision["coverage_ref_ids"],
            "health_snapshot_digest": decision["health_snapshot_digest"],
            "ordered_evidence_references": references,
            "versions": self.artifacts.versions,
        }
        audit["canonical_digest"] = digest_fields(audit, AUDIT_DIGEST_FIELDS)
        return audit


def build_versions(
    contracts: ContractSet,
    *,
    raw_model_digest: str,
    calibrator_digest: str,
    support_manifest_digest: str,
    normalizer_values: dict[str, list[float]],
) -> dict[str, dict[str, str]]:
    payloads: dict[str, tuple[str, Any]] = {
        "schema": ("trustepisode.online.v1", contracts.schema),
        "parser": ("trustepisode.parsers.v1", {"EDR": "endpoint-exec.v1", "NDR": "suricata.v1"}),
        "formation_policy": ("trustepisode.formation.v1", contracts.thresholds["formation"]),
        "detector_registry": ("trustepisode.detectors.v1", contracts.detectors),
        "feature_policy": ("trustepisode.feature.v1", {"top_k": 3, "implementation": "detector-implementation.v1"}),
        "normalizer": ("trustepisode.normalizer.v1", normalizer_values),
        "raw_model": ("trustepisode.raw-model.v1", raw_model_digest),
        "calibrator": ("trustepisode.calibrator.v1", calibrator_digest),
        "support_policy": (
            "trustepisode.support.v1",
            {
                "support_manifest_digest": support_manifest_digest,
                "resolution_contract": contracts.thresholds[
                    "detector_availability_resolution"
                ],
            },
        ),
        "sufficiency_policy": ("trustepisode.sufficiency.v1", contracts.thresholds["contradiction_rules"]),
        "assembly_policy": ("trustepisode.assembly.v1", contracts.thresholds["assembly"]),
    }
    versions = {
        name: {"version": version, "digest": value if isinstance(value, str) and value.startswith("sha256:") else sha256_digest(value)}
        for name, (version, value) in payloads.items()
    }
    versions["manifest"] = {
        "version": "trustepisode.runtime-manifest.v1",
        "digest": sha256_digest(versions),
    }
    if set(versions) != set(VERSION_COMPONENTS):
        raise AssertionError("VersionSet is incomplete")
    return versions


def serialize_detector_value(
    revision: dict[str, Any], value: DetectorValue
) -> dict[str, Any]:
    return {
        "episode_id": revision["episode_id"],
        "revision": revision["revision"],
        "source_family": value.source_family,
        "detector_id": value.detector_id,
        "dependency_group": value.dependency_group,
        "value": value.value,
        "reference": value.reference,
    }


def contradiction_status(events: list[dict[str, Any]]) -> str:
    endpoint_bindings: dict[str, str] = {}
    process_parents: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    applicable = False
    unevaluable = False
    for event in events:
        attributes = event.get("attributes") or {}
        endpoint_key = attributes.get("endpoint_key")
        endpoint_host = attributes.get("endpoint_host")
        if endpoint_key is not None:
            applicable = True
            if endpoint_host is None:
                unevaluable = True
            elif endpoint_key in endpoint_bindings and endpoint_bindings[endpoint_key] != endpoint_host:
                return "present"
            else:
                endpoint_bindings[str(endpoint_key)] = str(endpoint_host)
        process_key_fields = tuple(attributes.get(item) for item in ("host", "boot_id", "pid", "start_time"))
        if all(item is not None for item in process_key_fields):
            applicable = True
            lineage = (attributes.get("parent_pid"), attributes.get("root_id"))
            if None in lineage:
                unevaluable = True
            elif process_key_fields in process_parents and process_parents[process_key_fields] != lineage:
                return "present"
            else:
                process_parents[process_key_fields] = lineage
    if unevaluable:
        return "unevaluable"
    return "none" if not applicable or applicable else "none"


def classify_failure(exc: Exception, observed_inputs: list[str]) -> str:
    message = str(exc).lower()
    if "schema" in type(exc).__module__ or "schema" in message:
        return "schema_invalid"
    if "key_mismatch" in message:
        return "key_mismatch"
    if "conflicting" in message or "duplicate" in message:
        return "conflicting_duplicate"
    if "digest" in message:
        return "digest_mismatch"
    if "version" in message:
        return "version_mismatch"
    if "missing_input" in message or set(observed_inputs) != set(ASSEMBLY_INPUT_ORDER):
        return "missing_input"
    return "assembly_timeout"
