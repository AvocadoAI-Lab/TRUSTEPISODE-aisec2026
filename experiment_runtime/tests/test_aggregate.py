from __future__ import annotations

import json

from trustepisode_runtime.aggregate import aggregate_campaign
from trustepisode_runtime.cli import main


def test_campaign_aggregate_uses_pooled_rows_and_preserves_pending_protocols(
    tmp_path, contracts
) -> None:
    runtime_root = tmp_path / "runtime"
    run_id = "locked-run-01"
    assert main(
        [
            "dry-run",
            "--contracts",
            str(contracts.root),
            "--output",
            str(runtime_root / run_id),
        ]
    ) == 0
    plan = {
        "assignment_digest": "sha256:" + "a" * 64,
        "rows": [
            {
                "run_id": run_id,
                "base_campaign_id": "b" * 64,
                "partition": "locked_test",
                "scenario_family": "M1",
            }
        ],
    }
    plan_path = tmp_path / "campaign.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    result, markdown, latex = aggregate_campaign(
        plan_path,
        runtime_root,
        bootstrap_repetitions=20,
    )
    assert result["completion"]["runtime_complete"] is True
    assert result["completion"]["all_formal_inputs_complete"] is False
    assert result["RT1"]["C_dec_all"] >= 1
    assert result["RT3a"]["SB3"]["C_dec_binary"] >= 1
    assert result["RT4"] == "pending"
    assert result["completion"]["replay_expected"] == 1
    assert "尚未完整" in markdown
    assert "all_formal_inputs_complete=false" in latex
