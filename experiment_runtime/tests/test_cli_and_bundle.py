from __future__ import annotations

import json
from datetime import timedelta

import pytest

from trustepisode_runtime.bundle import validate_bundle
from trustepisode_runtime.canonical import parse_timestamp, timestamp
from trustepisode_runtime.cli import main


def test_dry_run_writes_a_valid_evaluated_bundle(tmp_path, contracts) -> None:
    output = tmp_path / "dry-run"
    exit_code = main(
        [
            "dry-run",
            "--contracts",
            str(contracts.root),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    manifest = validate_bundle(output)
    assert manifest["bundle_type"] == "synthetic-dry-run"
    evaluation = json.loads(
        (output / "run" / "offline" / "evaluation.json").read_text(encoding="utf-8")
    )
    assert evaluation["RT1"]["C_dec_all"] >= 1
    assert evaluation["RT2"]["EB3"]["qualified_edge_count"] >= 1
    assert evaluation["RT3a"]["SB3"]["C_dec_binary"] >= 1


def test_bundle_validation_detects_tampering(tmp_path, contracts) -> None:
    output = tmp_path / "dry-run"
    assert main(
        ["dry-run", "--contracts", str(contracts.root), "--output", str(output)]
    ) == 0
    metadata = output / "run" / "run_metadata.json"
    metadata.write_text(metadata.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from manifest"):
        validate_bundle(output)


def test_po1_cli_materializes_exact_frozen_design(tmp_path) -> None:
    output = tmp_path / "po1"
    assert main(["po1-plan", "--output", str(output)]) == 0
    value = json.loads((output / "po1_cells.json").read_text(encoding="utf-8"))
    cells = value["cells"]
    assert len(cells) == 40
    assert {item["source_family"] for item in cells} == {"EDR", "NDR"}
    assert {item["duration_seconds"] for item in cells} == {120, 600}


def test_validate_input_accepts_dry_run_online_streams(tmp_path, contracts) -> None:
    output = tmp_path / "dry-run"
    assert main(
        ["dry-run", "--contracts", str(contracts.root), "--output", str(output)]
    ) == 0
    assert main(
        [
            "validate-input",
            "--contracts",
            str(contracts.root),
            str(output / "run" / "inputs" / "events.ndjson"),
            str(output / "run" / "inputs" / "source_coverage.ndjson"),
        ]
    ) == 0


def test_outage_evaluator_emits_two_rows_for_one_trace(tmp_path, contracts) -> None:
    dry_run = tmp_path / "dry-run"
    assert main(
        ["dry-run", "--contracts", str(contracts.root), "--output", str(dry_run)]
    ) == 0
    revision = json.loads(
        (dry_run / "run" / "outputs" / "episode_revisions.ndjson")
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )
    anchor = parse_timestamp(revision["watermark"])
    journal = {
        "journal_type": "trustepisode.po1-outage-journal.v1",
        "formal": False,
        "run_id": "outage-test",
        "po1_cell_id": "a" * 64,
        "source_family": "EDR",
        "duration_seconds": 120,
        "repetition_index": 0,
        "allocated_card_id": "M1",
        "trace_digest": "sha256:" + "b" * 64,
        "t_anchor": timestamp(anchor - timedelta(seconds=3)),
        "t_stop": timestamp(anchor - timedelta(seconds=2)),
        "t_detect": timestamp(anchor - timedelta(seconds=1)),
        "t_restore": timestamp(anchor - timedelta(microseconds=1)),
        "t_h1": timestamp(anchor + timedelta(seconds=30)),
        "t_h2": timestamp(anchor + timedelta(seconds=60)),
        "t_ready": timestamp(anchor + timedelta(seconds=30)),
        "t_stable": None,
        "t_censor": timestamp(anchor + timedelta(seconds=1800)),
        "censor_reason": None,
    }
    journal_path = tmp_path / "journal.json"
    journal_path.write_text(json.dumps(journal), encoding="utf-8")
    output = tmp_path / "rt5"
    assert main(
        [
            "outage-evaluate",
            "--journal",
            str(journal_path),
            "--runtime-bundle",
            str(dry_run / "run"),
            "--output",
            str(output),
        ]
    ) == 0
    rows = json.loads((output / "rt5_rows.json").read_text(encoding="utf-8"))["rows"]
    assert len(rows) == 2
    assert rows[0]["trace_digest"] == rows[1]["trace_digest"]
