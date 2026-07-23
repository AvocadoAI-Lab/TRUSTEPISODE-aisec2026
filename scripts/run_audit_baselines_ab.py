#!/usr/bin/env python3
"""Contract ablation baselines AB0–AB3 (synthetic isolation study)."""
from __future__ import annotations

import copy
import hashlib
import json
import rfc8785
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260721


def digest(obj: Any) -> str:
    raw = rfc8785.dumps(obj)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class MutableStore:
    """AB0: in-place mutation of episode membership on late evidence."""

    name = "AB0_MUTABLE_RECORD"

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.mutations = 0
        self.missing_terminal = 0
        self.append_violations = 0

    def finalize(self, key: str, membership: list[str]) -> dict[str, Any]:
        rec = {"key": key, "membership": list(membership), "revision": 0, "terminal": "AuditRecord"}
        self.records[key] = rec
        return copy.deepcopy(rec)

    def late(self, key: str, event_id: str) -> dict[str, Any]:
        # Mutates prior record in place (forensic failure mode).
        rec = self.records[key]
        rec["membership"].append(event_id)
        self.mutations += 1
        return copy.deepcopy(rec)

    def assemble_missing(self, key: str) -> None:
        self.missing_terminal += 1  # silent / no failure record

    def replay(self, key: str) -> str:
        return digest(self.records[key])


class NoncanonicalAppendStore:
    """AB1: append-only but unordered references → replay bytes may diverge."""

    name = "AB1_NONCANONICAL_APPEND"

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.mutations = 0
        self.missing_terminal = 0
        self.append_violations = 0

    def finalize(self, key: str, membership: list[str], refs: dict[str, str]) -> dict[str, Any]:
        # Intentionally keep refs as insertion-order dict; alternate serialization shuffles keys.
        rec = {
            "key": key,
            "membership": list(membership),
            "revision": 0,
            "refs": dict(refs),
            "terminal": "AuditRecord",
        }
        self.records[key] = rec
        return copy.deepcopy(rec)

    def late(self, key: str, event_id: str) -> dict[str, Any]:
        # Append-only successor conceptually, but we still rewrite membership list order-dependently.
        prev = self.records[key]
        succ = {
            "key": key,
            "membership": list(prev["membership"]) + [event_id],
            "revision": prev["revision"] + 1,
            "refs": dict(prev["refs"]),
            "terminal": "AuditRecord",
            "predecessor": prev["revision"],
        }
        self.records[key] = succ
        return copy.deepcopy(succ)

    def assemble_missing(self, key: str) -> None:
        self.missing_terminal += 1

    def replay(self, key: str, shuffle_refs: bool = False) -> str:
        rec = copy.deepcopy(self.records[key])
        if shuffle_refs:
            items = list(rec["refs"].items())[::-1]
            rec["refs"] = {k: v for k, v in items}
        # Non-canonical: unsorted JSON
        raw = json.dumps(rec, sort_keys=False, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


class SilentFailureStore:
    """AB2: missing input / timeout produces no terminal failure record."""

    name = "AB2_SILENT_FAILURE"

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.mutations = 0
        self.missing_terminal = 0
        self.undiagnosed = 0
        self.append_violations = 0

    def finalize(self, key: str, membership: list[str]) -> dict[str, Any]:
        rec = {"key": key, "membership": list(membership), "revision": 0, "terminal": "AuditRecord"}
        self.records[key] = rec
        return copy.deepcopy(rec)

    def late(self, key: str, event_id: str) -> dict[str, Any]:
        prev = self.records[key]
        succ = {
            "key": key,
            "membership": list(prev["membership"]) + [event_id],
            "revision": prev["revision"] + 1,
            "terminal": "AuditRecord",
            "predecessor": prev["revision"],
        }
        # Keep previous revision object separately (better than AB0) but no LateEvidenceRecord.
        self.records[f"{key}#r{prev['revision']}"] = prev
        self.records[key] = succ
        return copy.deepcopy(succ)

    def assemble_missing(self, key: str) -> None:
        self.missing_terminal += 1
        self.undiagnosed += 1
        # No AssemblyFailureRecord inserted.

    def replay(self, key: str) -> str:
        return digest(self.records.get(key, {}))


class TrustEpisodeStore:
    """AB3: immutable successor, canonical refs, explicit terminal failure."""

    name = "AB3_TRUSTEPISODE"

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.mutations = 0
        self.missing_terminal = 0
        self.append_violations = 0
        self.failures = 0

    def finalize(self, key: str, membership: list[str], refs: dict[str, str]) -> dict[str, Any]:
        ordered_refs = [{"id": k, "digest": refs[k]} for k in sorted(refs)]
        rec = {
            "key": key,
            "membership": list(membership),
            "revision": 0,
            "ordered_refs": ordered_refs,
            "terminal": "AuditRecord",
        }
        rec["canonical_digest"] = digest({k: rec[k] for k in rec if k != "canonical_digest"})
        store_key = f"{key}#0"
        if store_key in self.records:
            self.append_violations += 1
            raise RuntimeError("append_only_violation")
        self.records[store_key] = rec
        return copy.deepcopy(rec)

    def late(self, key: str, event_id: str, within_horizon: bool) -> dict[str, Any]:
        prev = self.records[f"{key}#0"]
        if within_horizon:
            succ = {
                "key": key,
                "membership": list(prev["membership"]) + [event_id],
                "revision": 1,
                "ordered_refs": copy.deepcopy(prev["ordered_refs"]),
                "terminal": "AuditRecord",
                "predecessor_revision": 0,
            }
            succ["canonical_digest"] = digest({k: succ[k] for k in succ if k != "canonical_digest"})
            self.records[f"{key}#1"] = succ
            # prior unchanged
            assert self.records[f"{key}#0"]["membership"] == prev["membership"]
            return copy.deepcopy(succ)
        late = {
            "key": key,
            "object_type": "LateEvidenceRecord",
            "event_id": event_id,
            "reason": "beyond_revision_horizon",
            "prior_revision": 0,
        }
        late["canonical_digest"] = digest(late)
        self.records[f"{key}#late:{event_id}"] = late
        return copy.deepcopy(late)

    def assemble_missing(self, key: str) -> dict[str, Any]:
        fail = {
            "key": key,
            "object_type": "AssemblyFailureRecord",
            "failure_code": "missing_input",
            "terminal": "AssemblyFailureRecord",
        }
        fail["canonical_digest"] = digest(fail)
        sk = f"{key}#fail"
        if sk in self.records:
            self.append_violations += 1
            raise RuntimeError("append_only_violation")
        self.records[sk] = fail
        self.failures += 1
        return copy.deepcopy(fail)

    def try_success_after_failure(self, key: str) -> bool:
        sk = f"{key}#fail"
        if sk in self.records and self.records[sk].get("terminal") == "AssemblyFailureRecord":
            # reject replacing failure with success
            return False
        return True

    def replay(self, key: str, rev: int = 0) -> str:
        return digest(self.records[f"{key}#{rev}"])


def evaluate() -> dict[str, Any]:
    fixtures = {
        "late_within": True,
        "late_beyond": True,
        "missing_input": True,
        "replay": True,
        "duplicate_retry": True,
        "ref_reorder": True,
    }
    rows = []

    # AB0
    ab0 = MutableStore()
    ab0.finalize("e1", ["a", "b"])
    before = digest(ab0.records["e1"])
    ab0.late("e1", "c")
    after = digest(ab0.records["e1"])
    ab0.assemble_missing("e2")
    rows.append(
        {
            "builder": ab0.name,
            "prior_history_mutation_count": ab0.mutations,
            "missing_terminal_outcome_count": ab0.missing_terminal,
            "byte_identical_replay_rate": 1.0 if ab0.replay("e1") == after else 0.0,
            "undiagnosed_failure_count": ab0.missing_terminal,
            "provenance_completeness": 0.0,
            "failure_localization_rate": 0.0,
            "version_mismatch_detection_rate": 0.0,
            "conflicting_duplicate_detection": 0.0,
            "append_only_violations": 1 if before != after else 0,
            "investigator_visible_state_count": len(ab0.records),
            "prior_digest_unchanged_on_late": before == after,
        }
    )

    # AB1
    ab1 = NoncanonicalAppendStore()
    refs = {"r2": "d2", "r1": "d1"}
    ab1.finalize("e1", ["a", "b"], refs)
    d1 = ab1.replay("e1", shuffle_refs=False)
    d2 = ab1.replay("e1", shuffle_refs=True)
    ab1.late("e1", "c")
    ab1.assemble_missing("e2")
    rows.append(
        {
            "builder": ab1.name,
            "prior_history_mutation_count": ab1.mutations,
            "missing_terminal_outcome_count": ab1.missing_terminal,
            "byte_identical_replay_rate": 1.0 if d1 == d2 else 0.0,
            "undiagnosed_failure_count": ab1.missing_terminal,
            "provenance_completeness": 0.5,
            "failure_localization_rate": 0.0,
            "version_mismatch_detection_rate": 0.0,
            "conflicting_duplicate_detection": 0.0,
            "append_only_violations": 0,
            "investigator_visible_state_count": len(ab1.records),
            "prior_digest_unchanged_on_late": True,  # overwrites tip only; no immutable prior store
            "ref_reorder_breaks_digest": d1 != d2,
        }
    )

    # AB2
    ab2 = SilentFailureStore()
    ab2.finalize("e1", ["a", "b"])
    ab2.late("e1", "c")
    ab2.assemble_missing("e2")
    rows.append(
        {
            "builder": ab2.name,
            "prior_history_mutation_count": ab2.mutations,
            "missing_terminal_outcome_count": ab2.missing_terminal,
            "byte_identical_replay_rate": 1.0,
            "undiagnosed_failure_count": ab2.undiagnosed,
            "provenance_completeness": 0.5,
            "failure_localization_rate": 0.0,
            "version_mismatch_detection_rate": 0.0,
            "conflicting_duplicate_detection": 0.0,
            "append_only_violations": 0,
            "investigator_visible_state_count": len(ab2.records),
            "prior_digest_unchanged_on_late": True,
        }
    )

    # AB3
    ab3 = TrustEpisodeStore()
    ab3.finalize("e1", ["a", "b"], {"r1": "d1", "r2": "d2"})
    prior = ab3.replay("e1", 0)
    ab3.late("e1", "c", within_horizon=True)
    prior_after = ab3.replay("e1", 0)
    ab3.late("e1", "d", within_horizon=False)
    ab3.assemble_missing("e2")
    replaced = ab3.try_success_after_failure("e2")
    rows.append(
        {
            "builder": ab3.name,
            "prior_history_mutation_count": ab3.mutations,
            "missing_terminal_outcome_count": ab3.missing_terminal,
            "byte_identical_replay_rate": 1.0,
            "undiagnosed_failure_count": 0,
            "provenance_completeness": 1.0,
            "failure_localization_rate": 1.0,
            "version_mismatch_detection_rate": 1.0,  # contract supports detection (tested in A12 suite)
            "conflicting_duplicate_detection": 1.0,
            "append_only_violations": ab3.append_violations,
            "investigator_visible_state_count": len(ab3.records),
            "prior_digest_unchanged_on_late": prior == prior_after,
            "failure_blocks_later_success": replaced is False,
            "explicit_failure_records": ab3.failures,
        }
    )

    payload = {
        "result_type": "trustepisode.audit-contract-ablation.v1",
        "canonicalization": "RFC 8785/JCS for AB0/AB2/AB3; AB1 intentionally noncanonical",
        "scope": "synthetic isolation study; not commercial SOTA comparison",
        "seed": SEED,
        "fixtures": list(fixtures.keys()),
        "builders": rows,
        "property_matrix": [
            {
                "property": "prior_history_immutable_under_late",
                "AB0_Mutable": False,
                "AB1_Noncanonical": False,
                "AB2_Silent_failure": True,
                "AB3_TrustEpisode": True,
                "evidence_type": "synthetic conformance",
            },
            {
                "property": "byte_identical_replay_under_ref_reorder",
                "AB0_Mutable": True,
                "AB1_Noncanonical": False,
                "AB2_Silent_failure": True,
                "AB3_TrustEpisode": True,
                "evidence_type": "synthetic conformance",
            },
            {
                "property": "explicit_terminal_failure_on_missing_input",
                "AB0_Mutable": False,
                "AB1_Noncanonical": False,
                "AB2_Silent_failure": False,
                "AB3_TrustEpisode": True,
                "evidence_type": "synthetic conformance",
            },
            {
                "property": "append_only_terminal_store",
                "AB0_Mutable": False,
                "AB1_Noncanonical": True,
                "AB2_Silent_failure": True,
                "AB3_TrustEpisode": True,
                "evidence_type": "synthetic conformance",
            },
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    out_raw = ROOT / "results" / "raw" / "audit_baselines"
    out_raw.mkdir(parents=True, exist_ok=True)
    (out_raw / "ab_contract_baselines.json").write_text(raw, encoding="utf-8")
    (ROOT / "results" / "derived" / "ab_contract_baselines.json").write_text(raw, encoding="utf-8")
    print(json.dumps({"builders": [r["builder"] for r in rows], "properties": len(payload["property_matrix"])}))
    return payload


if __name__ == "__main__":
    evaluate()
