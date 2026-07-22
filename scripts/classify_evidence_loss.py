#!/usr/bin/env python3
"""Deterministic evidence-loss taxonomy classifier."""
from __future__ import annotations
from typing import Any


def classify_evidence_loss(trace: dict[str, Any]) -> dict[str, Any]:
    required = trace.get("required_token")
    normalized = trace.get("normalized_tokens", trace.get("normalized_token", []))
    episode = trace.get("matched_episode_tokens", trace.get("episode_tokens", []))
    if isinstance(normalized, str):
        normalized = [normalized]
    if isinstance(episode, str):
        episode = [episode]
    if trace.get("receipt_status") != "success":
        return {"class": "A_execution_failure", "reason": "receipt is not successful", "required_token": required}
    if not trace.get("raw_observable", False):
        return {"class": "B_sensor_observability_failure", "reason": "successful receipt lacks raw observability", "required_token": required}
    if not trace.get("normalized_ok", False):
        return {"class": "C_parser_or_normalization_failure", "reason": "raw evidence did not normalize", "required_token": required}
    if required not in normalized:
        return {"class": "D_token_mapping_failure", "reason": "required token is missing or mapped differently in normalized evidence", "required_token": required, "normalized_tokens": normalized}
    if required not in episode:
        return {"class": "E_formation_membership_failure", "reason": "normalized required token is absent from matched episode", "required_token": required}
    if not trace.get("matcher_credited", False):
        return {"class": "F_offline_attribution_failure", "reason": "matched episode contains token but matcher gave no credit", "required_token": required}
    if trace.get("diagnostics_complete") is False:
        return {"class": "G_unknown_or_incomplete_trace", "reason": "diagnostics are incomplete", "required_token": required}
    return {"class": "G_unknown_or_incomplete_trace", "reason": "no evidence-loss condition is established", "required_token": required}
