from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from .canonical import parse_timestamp
from .contract_io import iter_ndjson


def evaluate_outage_journal(
    journal: dict[str, Any], runtime_bundle: Path
) -> dict[str, Any]:
    if journal.get("journal_type") != "trustepisode.po1-outage-journal.v1":
        raise ValueError("unsupported outage journal")
    outcomes = list(iter_ndjson(runtime_bundle / "outputs" / "assembly_outcomes.ndjson"))
    revisions = list(iter_ndjson(runtime_bundle / "outputs" / "episode_revisions.ndjson"))
    revision_by_key = {
        (item["episode_id"], int(item["revision"])): item for item in revisions
    }
    t_stop = parse_timestamp(journal["t_stop"])
    t_restore = parse_timestamp(journal["t_restore"])
    t_ready = parse_timestamp(journal["t_ready"]) if journal.get("t_ready") else None
    t_censor = parse_timestamp(journal["t_censor"])
    window_end = t_ready or t_censor
    selected = []
    for outcome in outcomes:
        revision = revision_by_key.get((outcome["episode_id"], int(outcome["revision"])))
        if revision is None:
            continue
        observed = parse_timestamp(revision["watermark"])
        if t_stop <= observed <= window_end:
            selected.append(outcome)

    stable_candidates = [
        parse_timestamp(item["watermark"])
        for item in revisions
        if item["state"] == "closed" and parse_timestamp(item["watermark"]) >= t_restore
    ]
    t_stable = min(stable_candidates) if stable_candidates else None
    common = {
        "po1_cell_id": journal["po1_cell_id"],
        "source_family": journal["source_family"],
        "duration_seconds": journal["duration_seconds"],
        "repetition_index": journal["repetition_index"],
        "allocated_card_id": journal["allocated_card_id"],
        "trace_digest": journal["trace_digest"],
        "formal": bool(journal["formal"]),
        "t_anchor": journal["t_anchor"],
        "t_stop": journal["t_stop"],
        "t_detect": journal.get("t_detect"),
        "t_restore": journal["t_restore"],
        "t_h1": journal.get("t_h1"),
        "t_h2": journal.get("t_h2"),
        "t_ready": journal.get("t_ready"),
        "t_stable": _iso_or_none(t_stable),
        "t_censor": journal["t_censor"],
        "censor_reason": _censor_reason(journal, t_ready, t_stable),
        "health_detection_seconds": (
            (parse_timestamp(journal["t_detect"]) - t_stop).total_seconds()
            if journal.get("t_detect")
            else None
        ),
        "recovery_seconds": (
            (t_ready - t_restore).total_seconds() if t_ready is not None else None
        ),
        "stable_revision_seconds": (
            (t_stable - t_restore).total_seconds() if t_stable is not None else None
        ),
        "candidate_outcome_count": len(selected),
    }
    trust_eligible = [
        item
        for item in selected
        if item["object_type"] == "AuditRecord" and item.get("decision_eligible") is True
    ]
    trust_oos = [
        item
        for item in selected
        if item["object_type"] == "AuditRecord" and item.get("kappa") == "out_of_support"
    ]
    ob1_eligible = [item for item in selected if _ob1_eligible(item)]
    ob1_oos = [
        item
        for item in selected
        if item["object_type"] != "AuditRecord" or not _ob1_has_available_source(item)
    ]
    denominator = len(selected)
    rows = [
        {
            **common,
            "comparator": "TrustEpisode",
            "decision_eligible_fraction": len(trust_eligible) / denominator if denominator else None,
            "out_of_support_rate": len(trust_oos) / denominator if denominator else None,
        },
        {
            **common,
            "comparator": "OB1_available_source_denominator",
            "decision_eligible_fraction": len(ob1_eligible) / denominator if denominator else None,
            "out_of_support_rate": len(ob1_oos) / denominator if denominator else None,
        },
    ]
    if rows[0]["trace_digest"] != rows[1]["trace_digest"]:
        raise AssertionError("outage comparators do not share one trace")
    return {
        "registry": "RT5",
        "journal_run_id": journal["run_id"],
        "rows": rows,
    }


def _ob1_has_available_source(outcome: dict[str, Any]) -> bool:
    if outcome.get("object_type") != "AuditRecord":
        return False
    health = outcome.get("health_snapshot") or {}
    return any(health.get(family) in {"healthy", "degraded"} for family in ("EDR", "NDR"))


def _ob1_eligible(outcome: dict[str, Any]) -> bool:
    return (
        outcome.get("object_type") == "AuditRecord"
        and int(outcome.get("eligible_detector_count", 0)) > 0
        and _ob1_has_available_source(outcome)
    )


def _censor_reason(
    journal: dict[str, Any], t_ready, t_stable
) -> str | None:
    reasons = []
    if not journal.get("t_detect"):
        reasons.append("detection_right_censored_at_restore")
    if t_ready is None:
        reasons.append("ready_right_censored")
    if t_stable is None:
        reasons.append("stable_revision_right_censored")
    return "+".join(reasons) if reasons else None


def _iso_or_none(value) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")
