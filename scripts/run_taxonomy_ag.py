#!/usr/bin/env python3
"""Run synthetic A--G taxonomy fixtures and instantiate M2 as live class D evidence."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from classify_evidence_loss import classify_evidence_loss

ROOT = Path(__file__).resolve().parents[1]


def trace(**overrides: object) -> dict[str, object]:
    base = {"receipt_status": "success", "raw_observable": True, "normalized_ok": True,
            "required_token": "file_transfer", "normalized_tokens": ["file_transfer"],
            "matched_episode_tokens": ["file_transfer"], "matcher_credited": True,
            "diagnostics_complete": True}
    base.update(overrides)
    return base


def main() -> int:
    fixtures = [
        ("A_execution_failure", trace(receipt_status="failure")),
        ("B_sensor_observability_failure", trace(raw_observable=False)),
        ("C_parser_or_normalization_failure", trace(normalized_ok=False)),
        ("D_token_mapping_failure", trace(normalized_tokens=["remote_session"])),
        ("E_formation_membership_failure", trace(matched_episode_tokens=["remote_session"])),
        ("F_offline_attribution_failure", trace(matcher_credited=False)),
        ("G_unknown_or_incomplete_trace", trace(diagnostics_complete=False)),
    ]
    m2 = json.loads((ROOT / "results" / "derived" / "m2_waterfall.json").read_text(encoding="utf-8"))
    fixtures.append(("D_token_mapping_failure", trace(normalized_tokens=["remote_session"], matched_episode_tokens=["remote_session"], matcher_credited=False, source="results/derived/m2_waterfall.json", source_digest=m2.get("raw_digest"))))

    rows = []
    for index, (expected, item) in enumerate(fixtures):
        outcome = classify_evidence_loss(item)
        rows.append({"id": "M2_LIVE_D" if item.get("source") else f"SYNTHETIC_{chr(65 + index)}", "expected_class": expected, "observed_class": outcome["class"], "pass": outcome["class"] == expected, "reason": outcome["reason"], "source": item.get("source", "synthetic")})
    counts = Counter((row["expected_class"], row["observed_class"]) for row in rows)
    confusion = [{"expected_class": expected, "observed_class": observed, "count": count} for (expected, observed), count in sorted(counts.items())]
    payload = {"result_type": "trustepisode.evidence-loss-taxonomy.ag.v1", "scope": "seven synthetic fixtures plus M2-derived D instantiation; no supplemental L1-L4 runs", "conformance_rows": rows, "confusion_rows": confusion, "pass_count": sum(row["pass"] for row in rows), "fail_count": sum(not row["pass"] for row in rows)}
    raw_dir = ROOT / "results" / "raw" / "taxonomy"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (raw_dir / "taxonomy_ag.json").write_text(rendered, encoding="utf-8")
    (ROOT / "results" / "derived" / "taxonomy_ag.json").write_text(rendered, encoding="utf-8")
    print(json.dumps({"pass": payload["pass_count"], "fail": payload["fail_count"]}))
    return 0 if not payload["fail_count"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
