from __future__ import annotations

import pytest

from trustepisode_runtime.firewall import LabelLeakageError, enforce
from trustepisode_runtime.scoring import fit_affine_calibrator, fit_raw_model


def test_label_firewall_rejects_nested_key_and_exact_value() -> None:
    with pytest.raises(LabelLeakageError):
        enforce({"attributes": {"scenario_id": "M1"}})
    with pytest.raises(LabelLeakageError):
        enforce({"attributes": {"token": "receipt-secret"}}, {"receipt-secret"})


def test_raw_scorer_and_calibrator_fit_frozen_domains() -> None:
    rows = [
        ("r1", 0.10, 0, 0),
        ("r2", 0.20, 0, 0),
        ("r3", 0.75, 1, 1),
        ("r4", 0.90, 1, 1),
    ]
    model, artifact = fit_raw_model(
        rows,
        detector_registry_digest="sha256:" + "1" * 64,
        normalizer_digests={"EDR": "sha256:" + "2" * 64, "NDR": "sha256:" + "3" * 64},
    )
    assert model.intercept < 0
    assert model.weight_D >= 0
    assert model.weight_C >= 0
    assert artifact["solver_contract"]["bounds"][0] == "b_unconstrained"
    calibration_rows = [(item[0], model.score(item[1], item[2]), item[3]) for item in rows]
    calibrator, _ = fit_affine_calibrator(calibration_rows)
    assert calibrator.slope >= 1e-6
    assert 0 < calibrator.probability(model.score(0.5, 1)) < 1
