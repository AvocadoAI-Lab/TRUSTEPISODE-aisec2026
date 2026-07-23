from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
from scipy.optimize import minimize

from .canonical import sha256_digest


@dataclass(frozen=True)
class RawModel:
    intercept: float
    weight_D: float
    weight_C: float
    artifact_digest: str
    status: str = "fitted"

    def score(self, D: float, C: int) -> float:
        value = self.intercept + self.weight_D * D + self.weight_C * C
        if not math.isfinite(value):
            raise ValueError("raw score is non-finite")
        return value


@dataclass(frozen=True)
class AffineCalibrator:
    slope: float
    intercept: float
    artifact_digest: str
    status: str = "fitted"

    def probability(self, z: float) -> float:
        if self.slope < 1e-6:
            raise ValueError("calibrator slope violates positive-slope contract")
        return sigmoid(self.slope * z + self.intercept)


def sigmoid(value: float) -> float:
    if value >= 0:
        denominator = 1.0 + math.exp(-value)
        return 1.0 / denominator
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def fit_raw_model(
    rows: Iterable[tuple[str, float, int, int]],
    *,
    detector_registry_digest: str,
    normalizer_digests: dict[str, str],
    regularization: float = 1e-4,
) -> tuple[RawModel, dict[str, Any]]:
    ordered = sorted(rows, key=lambda item: item[0].encode("utf-8"))
    if not ordered:
        raise ValueError("raw scorer training cohort is empty")
    revision_ids = [item[0] for item in ordered]
    matrix = np.asarray([[item[1], item[2]] for item in ordered], dtype=np.float64)
    labels = np.asarray([item[3] for item in ordered], dtype=np.float64)
    if not np.all(np.isfinite(matrix)) or not np.all((matrix >= 0) & (matrix <= 1)):
        raise ValueError("raw scorer feature matrix violates [0,1]")
    if not np.all(np.isin(labels, (0.0, 1.0))):
        raise ValueError("raw scorer labels must be binary")

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        b, weight_D, weight_C = parameters
        z = b + matrix[:, 0] * weight_D + matrix[:, 1] * weight_C
        loss = np.mean(np.logaddexp(0.0, z) - labels * z)
        loss += regularization * 0.5 * float(np.dot(parameters, parameters))
        residual = 1.0 / (1.0 + np.exp(-np.clip(z, -709.0, 709.0))) - labels
        gradient = np.asarray(
            [
                np.mean(residual),
                np.mean(residual * matrix[:, 0]),
                np.mean(residual * matrix[:, 1]),
            ]
        ) + regularization * parameters
        return float(loss), gradient

    result = minimize(
        objective,
        np.zeros(3, dtype=np.float64),
        method="L-BFGS-B",
        jac=True,
        bounds=((None, None), (0.0, None), (0.0, None)),
        options={"gtol": 1e-9, "ftol": 1e-12, "maxiter": 10_000, "maxls": 50},
    )
    if not result.success:
        raise RuntimeError(f"raw scorer fit failed closed: {result.message}")
    coefficients = [float(item) for item in result.x]
    solver_contract = {
        "solver": "deterministic_binary64_L-BFGS-B",
        "initial_point": [0.0, 0.0, 0.0],
        "projected_gradient_infinity_tolerance": 1e-9,
        "objective_change_tolerance": 1e-12,
        "maximum_iterations": 10000,
        "bounds": ["b_unconstrained", "w_D_nonnegative", "w_C_nonnegative"],
    }
    digest_payload = {
        "ordered_training_revision_ids": revision_ids,
        "ordered_labels": [int(item) for item in labels],
        "detector_registry_digest": detector_registry_digest,
        "normalizer_digests": normalizer_digests,
        "row_major_binary64_matrix": matrix.tobytes(order="C").hex(),
        "lambda": regularization,
        "solver_contract": solver_contract,
        "coefficients": coefficients,
    }
    artifact_digest = sha256_digest(digest_payload)
    artifact = {
        "artifact_type": "trustepisode.raw-model.v1",
        "status": "fitted",
        **digest_payload,
        "artifact_digest": artifact_digest,
        "optimizer": {
            "iterations": int(result.nit),
            "objective": float(result.fun),
            "projected_gradient_infinity_norm": float(np.max(np.abs(result.jac))),
        },
    }
    return RawModel(*coefficients, artifact_digest), artifact


def fit_affine_calibrator(
    rows: Iterable[tuple[str, float, int]],
    *,
    regularization: float = 1e-6,
) -> tuple[AffineCalibrator, dict[str, Any]]:
    ordered = sorted(rows, key=lambda item: item[0].encode("utf-8"))
    if not ordered:
        raise ValueError("calibration cohort is empty")
    revision_ids = [item[0] for item in ordered]
    logits = np.asarray([item[1] for item in ordered], dtype=np.float64)
    labels = np.asarray([item[2] for item in ordered], dtype=np.float64)
    if not np.all(np.isfinite(logits)) or not np.all(np.isin(labels, (0.0, 1.0))):
        raise ValueError("invalid calibration cohort")

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        slope, intercept = parameters
        calibrated = slope * logits + intercept
        loss = np.mean(np.logaddexp(0.0, calibrated) - labels * calibrated)
        loss += regularization * (slope * slope + intercept * intercept)
        residual = 1.0 / (1.0 + np.exp(-np.clip(calibrated, -709.0, 709.0))) - labels
        gradient = np.asarray(
            [np.mean(residual * logits), np.mean(residual)]
        ) + 2.0 * regularization * parameters
        return float(loss), gradient

    result = minimize(
        objective,
        np.asarray([1.0, 0.0], dtype=np.float64),
        method="L-BFGS-B",
        jac=True,
        bounds=((1e-6, None), (None, None)),
        options={"gtol": 1e-9, "ftol": 1e-12, "maxiter": 10_000, "maxls": 50},
    )
    if not result.success:
        raise RuntimeError(f"calibrator fit failed closed: {result.message}")
    slope, intercept = (float(item) for item in result.x)
    digest_payload = {
        "ordered_calibration_revision_ids": revision_ids,
        "ordered_labels": [int(item) for item in labels],
        "ordered_logits": [float(item) for item in logits],
        "regularization": regularization,
        "slope_lower_bound": 1e-6,
        "coefficients": [slope, intercept],
    }
    artifact_digest = sha256_digest(digest_payload)
    artifact = {
        "artifact_type": "trustepisode.affine-calibrator.v1",
        "status": "fitted",
        **digest_payload,
        "artifact_digest": artifact_digest,
        "optimizer": {"iterations": int(result.nit), "objective": float(result.fun)},
    }
    return AffineCalibrator(slope, intercept, artifact_digest), artifact
