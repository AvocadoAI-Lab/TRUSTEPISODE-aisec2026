#!/usr/bin/env python3
"""Synthetic conformance cards for downstream-agent canonical-record mutations."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

import jsonschema
import rfc8785


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "artifacts" / "contracts"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    def check(item: Any) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("non-finite JSON number")
        if isinstance(item, dict):
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)

    check(value)
    return rfc8785.dumps(value)


def digest_matches(record: dict[str, Any], schema: dict[str, Any]) -> bool:
    definition = schema["$defs"].get(record.get("object_type"), {})
    fields = definition.get("x-canonical-digest-fields")
    if not fields or any(field not in record for field in fields):
        return False
    payload = {field: record[field] for field in fields}
    actual = "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()
    return actual == record.get("canonical_digest")


def classify(
    record: dict[str, Any],
    validator: jsonschema.Draft202012Validator,
    schema: dict[str, Any],
) -> str:
    if next(validator.iter_errors(record), None) is not None:
        return "schema_reject"
    if not digest_matches(record, schema):
        return "digest_reject"
    return "accept"


def mutate(record: dict[str, Any], fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    changed = copy.deepcopy(record)
    fn(changed)
    return changed


def mutate_and_reseal(
    record: dict[str, Any],
    schema: dict[str, Any],
    fn: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    """Negative control: an unkeyed digest is integrity, not writer authentication."""
    changed = mutate(record, fn)
    fields = schema["$defs"][changed["object_type"]]["x-canonical-digest-fields"]
    payload = {field: changed[field] for field in fields}
    changed["canonical_digest"] = (
        "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()
    )
    return changed


def evaluate() -> dict[str, Any]:
    schema = load_json(CONTRACTS / "trustepisode_online.v1.schema.json")
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    supported = load_json(CONTRACTS / "examples" / "audit_record.valid.json")
    unsupported = load_json(
        CONTRACTS / "examples" / "audit_record.out_of_support.valid.json"
    )

    cards = [
        {
            "id": "AI0_VALID_CANONICAL_READ",
            "operation": "consume unchanged canonical AuditRecord",
            "guard": "closed schema plus canonical digest",
            "expected": "accept",
            "record": supported,
        },
        {
            "id": "AI1_ASSERTED_FACT_INJECTION",
            "operation": "add agent_asserted_fact to canonical record",
            "guard": "additionalProperties false",
            "expected": "schema_reject",
            "record": mutate(
                supported,
                lambda r: r.__setitem__("agent_asserted_fact", "host is compromised"),
            ),
        },
        {
            "id": "AI2_LABEL_LEAKAGE",
            "operation": "add malicious_label to online record",
            "guard": "additionalProperties false",
            "expected": "schema_reject",
            "record": mutate(
                supported,
                lambda r: r.__setitem__("malicious_label", 1),
            ),
        },
        {
            "id": "AI3_UNSUPPORTED_PROBABILITY",
            "operation": "replace out-of-support null P with 0.98",
            "guard": "support-probability coupling",
            "expected": "schema_reject",
            "record": mutate(
                unsupported,
                lambda r: r.__setitem__("P", 0.98),
            ),
        },
        {
            "id": "AI4_PROVENANCE_REMOVAL",
            "operation": "remove ordered evidence references",
            "guard": "required provenance field",
            "expected": "schema_reject",
            "record": mutate(
                supported,
                lambda r: r.pop("ordered_evidence_references"),
            ),
        },
        {
            "id": "AI5_REVISION_DIGEST_TAMPER",
            "operation": "swap revision digest without resealing record",
            "guard": "canonical digest binding",
            "expected": "digest_reject",
            "record": mutate(
                supported,
                lambda r: r.__setitem__(
                    "episode_revision_digest", "sha256:" + "a" * 64
                ),
            ),
        },
        {
            "id": "AI6_EVIDENCE_DIGEST_TAMPER",
            "operation": "swap evidence content digest without resealing record",
            "guard": "canonical digest binding",
            "expected": "digest_reject",
            "record": mutate(
                supported,
                lambda r: r["ordered_evidence_references"][0]["raw_pointer"].__setitem__(
                    "content_digest", "sha256:" + "b" * 64
                ),
            ),
        },
        {
            "id": "AI7_RESEALED_ALLOWED_FIELD",
            "operation": "replace allowed D and recompute unkeyed digest",
            "guard": "external writer authorization required",
            "expected": "accept",
            "record": mutate_and_reseal(
                supported,
                schema,
                lambda r: r.__setitem__("D", 0.42),
            ),
        },
    ]

    rows = []
    for card in cards:
        observed = classify(card["record"], validator, schema)
        rows.append(
            {
                "id": card["id"],
                "operation": card["operation"],
                "guard": card["guard"],
                "expected": card["expected"],
                "observed": observed,
                "pass": observed == card["expected"],
            }
        )

    pass_count = sum(1 for row in rows if row["pass"])
    payload = {
        "result_type": "trustepisode.agent-boundary-conformance.v1",
        "canonicalization": "RFC 8785/JCS",
        "scope": (
            "synthetic canonical-record conformance; not LLM accuracy, deployed "
            "authorization, or agent-runtime security"
        ),
        "cards": rows,
        "pass_count": pass_count,
        "fail_count": len(rows) - pass_count,
        "all_pass": pass_count == len(rows),
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    raw_dir = ROOT / "results" / "raw" / "agent_boundary"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "agent_boundary_conformance.json").write_text(raw, encoding="utf-8")
    (ROOT / "results" / "derived" / "agent_boundary_conformance.json").write_text(
        raw, encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "pass_count": payload["pass_count"],
                "fail_count": payload["fail_count"],
                "all_pass": payload["all_pass"],
            }
        )
    )
    return payload


if __name__ == "__main__":
    evaluate()
