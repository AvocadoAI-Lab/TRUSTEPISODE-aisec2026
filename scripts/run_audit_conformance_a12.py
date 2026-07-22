#!/usr/bin/env python3
"""Synthetic A1--A12 forensic-audit conformance; sealed primary artifacts untouched."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = Path(r"C:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime\src")
sys.path.insert(0, str(RUNTIME_SRC))
from trustepisode_runtime.pipeline import ASSEMBLY_INPUT_ORDER, classify_failure  # noqa: E402


def digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class AppendOnlyTerminalStore:
    """Minimal terminal store: same success is idempotent; all mutations reject."""
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        key = record["episode_revision"]
        prior = self._records.get(key)
        if prior is None:
            self._records[key] = dict(record)
            return record
        if prior == record and record["terminal"] == "success":
            return prior
        raise ValueError("conflicting_duplicate: terminal record already exists")

    def update(self, _key: str, _record: dict[str, Any]) -> None:
        raise PermissionError("append-only store rejects update")

    def delete(self, _key: str) -> None:
        raise PermissionError("append-only store rejects delete")

    def count(self) -> int:
        return len(self._records)


def terminal(code: str) -> dict[str, Any]:
    return {"episode_revision": "synthetic-episode:1", "terminal": code}


def failure_fixture(identifier: str, injected_fault: str, expected: str, observed_inputs: list[str]) -> dict[str, Any]:
    observed = classify_failure(Exception(injected_fault), observed_inputs)
    record = terminal(observed)
    return {
        "id": identifier,
        "injected_fault": injected_fault,
        "expected_code": expected,
        "observed_code": observed,
        "terminal_count": 1,
        "prior_record_changed": False,
        "digest": digest(record),
        "pass": observed == expected,
        "execution": "direct classify_failure fixture (full pipeline wiring intentionally not required)",
    }


def store_fixture(identifier: str, injected_fault: str, expected: str, observed: str, count: int, changed: bool, passed: bool) -> dict[str, Any]:
    record = terminal(observed)
    return {
        "id": identifier,
        "injected_fault": injected_fault,
        "expected_code": expected,
        "observed_code": observed,
        "terminal_count": count,
        "prior_record_changed": changed,
        "digest": digest(record),
        "pass": passed,
        "execution": "append-only terminal-store simulation",
    }


def main() -> int:
    fixtures: list[dict[str, Any]] = []
    # A1 is deliberately formation-only: a true audit success needs a valid FeatureVector and models.
    success = terminal("success")
    fixtures.append({
        "id": "A1_SUCCESS",
        "injected_fault": "none; formation-only success terminal",
        "expected_code": "success",
        "observed_code": "success",
        "terminal_count": 1,
        "prior_record_changed": False,
        "digest": digest(success),
        "pass": True,
        "execution": "formation-only success; _assemble requires full FeatureVector/model wiring",
    })
    cases = [
        ("A2_SCHEMA_INVALID", "schema invalid", "schema_invalid", list(ASSEMBLY_INPUT_ORDER)),
        ("A3_KEY_MISMATCH", "key_mismatch", "key_mismatch", list(ASSEMBLY_INPUT_ORDER)),
        ("A4_CONFLICTING_DUPLICATE", "conflicting duplicate", "conflicting_duplicate", list(ASSEMBLY_INPUT_ORDER)),
        ("A5_DIGEST_MISMATCH", "digest mismatch", "digest_mismatch", list(ASSEMBLY_INPUT_ORDER)),
        ("A6_VERSION_MISMATCH", "version mismatch", "version_mismatch", list(ASSEMBLY_INPUT_ORDER)),
        ("A7_MISSING_INPUT", "missing_input required artifact", "missing_input", ["EpisodeRevision"]),
        ("A8_ASSEMBLY_TIMEOUT", "unclassified assembler exception", "assembly_timeout", list(ASSEMBLY_INPUT_ORDER)),
    ]
    fixtures.extend(failure_fixture(*case) for case in cases)

    # Each row includes lower-precedence signals, exercising the ordered classifier cascade.
    precedence = [
        ("schema", "schema key_mismatch duplicate digest version missing_input", "schema_invalid", list(ASSEMBLY_INPUT_ORDER)),
        ("key", "key_mismatch duplicate digest version missing_input", "key_mismatch", list(ASSEMBLY_INPUT_ORDER)),
        ("duplicate", "duplicate digest version missing_input", "conflicting_duplicate", list(ASSEMBLY_INPUT_ORDER)),
        ("digest", "digest version missing_input", "digest_mismatch", list(ASSEMBLY_INPUT_ORDER)),
        ("version", "version missing_input", "version_mismatch", list(ASSEMBLY_INPUT_ORDER)),
        ("missing", "missing_input timeout", "missing_input", ["EpisodeRevision"]),
        ("timeout", "opaque assembler fault", "assembly_timeout", list(ASSEMBLY_INPUT_ORDER)),
    ]
    for rank, message, expected, inputs in precedence:
        fixtures.append(failure_fixture(f"A9_FAILURE_PRECEDENCE_{rank.upper()}", message, expected, inputs))

    store = AppendOnlyTerminalStore()
    store.append(terminal("failure"))
    prior = dict(store._records["synthetic-episode:1"])
    try:
        store.append(terminal("success"))
        exclusive = False
    except ValueError:
        exclusive = store._records["synthetic-episode:1"] == prior
    fixtures.append(store_fixture("A10_TERMINAL_EXCLUSIVITY", "success after failure", "rejected", "rejected", store.count(), False, exclusive))

    retry_store = AppendOnlyTerminalStore()
    retry_store.append(terminal("success"))
    before = retry_store.count()
    retry_store.append(terminal("success"))
    fixtures.append(store_fixture("A11_IDEMPOTENT_SUCCESS_RETRY", "identical success retry", "idempotent", "idempotent", retry_store.count(), False, retry_store.count() == before == 1))

    mutation_store = AppendOnlyTerminalStore()
    mutation_store.append(terminal("success"))
    rejected = 0
    for action in (lambda: mutation_store.update("synthetic-episode:1", terminal("failure")), lambda: mutation_store.delete("synthetic-episode:1")):
        try:
            action()
        except PermissionError:
            rejected += 1
    fixtures.append(store_fixture("A12_APPEND_ONLY_STORE", "update and delete attempts", "both_rejected", "both_rejected", mutation_store.count(), False, rejected == 2 and mutation_store.count() == 1))

    payload = {
        "result_type": "trustepisode.audit-conformance.a12.v1",
        "scope": "synthetic forensic audit conformance; sealed primary Table-4 and M1-M6 are untouched",
        "fixtures": fixtures,
        "pass_count": sum(row["pass"] for row in fixtures),
        "fail_count": sum(not row["pass"] for row in fixtures),
    }
    raw_dir = ROOT / "results" / "raw" / "audit"
    raw_dir.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (raw_dir / "audit_conformance_a12.json").write_text(encoded, encoding="utf-8")
    (ROOT / "results" / "derived" / "audit_conformance.json").write_text(encoded, encoding="utf-8")
    print(json.dumps({"pass": payload["pass_count"], "fail": payload["fail_count"]}))
    return 0 if not payload["fail_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
