from __future__ import annotations

from typing import Any

from .canonical import sha256_digest, utf8_key
from .contract_io import ContractSet
from .group_calibration import evaluate_group_candidate
from .pipeline import RuntimeArtifacts, build_versions
from .scoring import fit_affine_calibrator, fit_raw_model
from .support import support_contract_metadata


def fit_runtime_artifacts(
    contracts: ContractSet, training_input: dict[str, Any]
) -> tuple[RuntimeArtifacts, dict[str, Any]]:
    if training_input.get("training_input_type") != "trustepisode.runtime-training-input.v1":
        raise ValueError("unsupported training input type")
    normalizer_values = _normalizer_values(training_input["normalizer_values"])
    normalizer_digests = {
        detector_id: sha256_digest(values)
        for detector_id, values in sorted(normalizer_values.items(), key=lambda item: utf8_key(item[0]))
    }
    raw_rows = [
        (
            str(item["revision_id"]),
            float(item["D"]),
            int(item["C"]),
            int(item["label"]),
        )
        for item in training_input["raw_training_rows"]
    ]
    raw_model, raw_artifact = fit_raw_model(
        raw_rows,
        detector_registry_digest=sha256_digest(contracts.detectors),
        normalizer_digests=normalizer_digests,
        regularization=float(contracts.thresholds["raw_scorer_training"]["lambda"]),
    )
    d_only_model, d_only_artifact = fit_raw_model(
        [(revision_id, D, 0, label) for revision_id, D, _C, label in raw_rows],
        detector_registry_digest=sha256_digest(contracts.detectors),
        normalizer_digests=normalizer_digests,
        regularization=float(contracts.thresholds["raw_scorer_training"]["lambda"]),
    )
    calibration_rows = [
        (
            str(item["revision_id"]),
            _calibration_logit(item, raw_model),
            int(item["label"]),
        )
        for item in training_input["calibration_rows"]
    ]
    global_calibrator, global_artifact = fit_affine_calibrator(calibration_rows)

    group_calibrators = {}
    group_artifacts = {}
    if training_input.get("group_calibration"):
        raise ValueError(
            "externally asserted group gates are forbidden; use group_calibration_candidates"
        )
    for group_key, group in sorted(
        (training_input.get("group_calibration_candidates") or {}).items(),
        key=lambda item: utf8_key(item[0]),
    ):
        rows = [
            {
                "run_id": str(item["run_id"]),
                "revision_id": str(item["revision_id"]),
                "z": _calibration_logit(item, raw_model),
                "label": int(item["label"]),
            }
            for item in group["rows"]
        ]
        calibrator, artifact = evaluate_group_candidate(
            group_key,
            rows,
            global_calibrator,
            contracts.thresholds["calibration_group_gate"],
        )
        group_artifacts[group_key] = artifact
        if calibrator is not None:
            group_calibrators[group_key] = calibrator

    expected_instances = {
        family: sorted((str(item) for item in instances), key=utf8_key)
        for family, instances in training_input["expected_instances"].items()
    }
    if set(expected_instances) != {"EDR", "NDR"}:
        raise ValueError("expected_instances must contain exactly EDR and NDR")
    support_payload = {
        "source_mask": {"EDR": 1, "NDR": 1},
        "expected_instances": expected_instances,
        "allowed_health": ["healthy", "degraded"],
        "allowed_detector_states": ["available", "no_detection"],
        **support_contract_metadata(contracts.thresholds),
        "enabled_group_keys": sorted(group_calibrators, key=utf8_key),
        "status": "fitted",
    }
    support_digest = sha256_digest(support_payload)
    versions = build_versions(
        contracts,
        raw_model_digest=raw_model.artifact_digest,
        calibrator_digest=global_calibrator.artifact_digest,
        support_manifest_digest=support_digest,
        normalizer_values=normalizer_values,
    )
    artifacts = RuntimeArtifacts(
        status="fitted",
        normalizer_values=normalizer_values,
        raw_model=raw_model,
        global_calibrator=global_calibrator,
        expected_instances=expected_instances,
        support_manifest_digest=support_digest,
        versions=versions,
        d_only_model=d_only_model,
        group_calibrators=group_calibrators,
        entity_aliases={
            str(key): str(value)
            for key, value in (training_input.get("entity_aliases") or {}).items()
        },
    )
    details = {
        "raw_model_artifact": raw_artifact,
        "d_only_model_artifact": d_only_artifact,
        "global_calibrator_artifact": global_artifact,
        "group_calibrator_artifacts": group_artifacts,
        "support_manifest": support_payload,
        "support_manifest_digest": support_digest,
        "training_input_digest": sha256_digest(training_input),
    }
    return artifacts, details


def _normalizer_values(value: dict[str, Any]) -> dict[str, list[float]]:
    output: dict[str, list[float]] = {}
    for detector_id, raw_values in value.items():
        values = sorted(float(item) for item in raw_values)
        if not values:
            raise ValueError(f"normalizer cohort is empty: {detector_id}")
        if any(item < 0.0 or item > 1.0 for item in values):
            raise ValueError(f"normalizer value outside [0,1]: {detector_id}")
        output[str(detector_id)] = values
    return output


def _calibration_logit(item: dict[str, Any], raw_model) -> float:
    if "z" in item:
        return float(item["z"])
    return raw_model.score(float(item["D"]), int(item["C"]))
