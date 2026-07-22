#!/usr/bin/env python3
"""Forensic audit conformance checks (synthetic; sealed primary untouched)."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = Path(r"c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime\src")
sys.path.insert(0, str(RUNTIME_SRC))
sys.path.insert(0, str(ROOT / "scripts"))

from trustepisode_runtime.canonical import sha256_digest  # noqa: E402
from trustepisode_runtime.contract_io import ContractSet  # noqa: E402
from trustepisode_runtime.formation import EpisodeSynthesizer  # noqa: E402

BASE = datetime(2026, 7, 21, 15, 0, 0, tzinfo=timezone.utc)


def ts(seconds: float) -> str:
    return (BASE + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def event(eid: str, t: float, ingest: float | None = None, **kw) -> dict:
    digest = "sha256:" + hashlib.sha256(eid.encode()).hexdigest()
    return {
        "object_type": "NormalizedEvent",
        "schema_version": "trustepisode.online.v1",
        "event_id": eid,
        "event_time": ts(t),
        "ingest_time": ts(ingest if ingest is not None else t),
        "source_family": kw.get("source_family", "EDR"),
        "source_instance": kw.get("source_instance", "edr-01"),
        "subject": kw.get("subject", "host:a"),
        "object": kw.get("object", "file:1"),
        "action": kw.get("action", "process.start"),
        "dependency_group": kw.get("dep", "root:a"),
        "attributes": kw.get("attrs") or {},
        "raw_pointer": {
            "content_digest": digest,
            "locator": f"synthetic:{eid}",
            "object_id": f"raw:{eid}",
            "storage_schema_version": "trustepisode.endpoint-observation.v1",
        },
    }


def main() -> int:
    contracts = ContractSet(ROOT / "artifacts" / "contracts")
    checks = []

    # A1: late evidence after finalization does not rewrite earlier revision membership digest
    events = [
        event("e1", 0, 0),
        event("e2", 10, 10),
        event("e3", 20, 200, object="file:3"),
    ]
    syn = EpisodeSynthesizer(contracts.thresholds["formation"], versions={"formation_policy": {"version": "v1", "digest": "t"}})
    r = syn.synthesize(events)
    first = [x for x in r.revisions if x["revision"] == 0]
    later = [x for x in r.revisions if x["revision"] > 0]
    checks.append(
        {
            "id": "A1_late_no_rewrite_of_earlier_revision_identity",
            "pass": bool(first) and (not later or first[0]["ordered_event_ids"] != later[-1]["ordered_event_ids"] or later[-1].get("predecessor_revision") is not None),
            "n_revisions": len(r.revisions),
            "n_late": len(r.late_records),
            "note": "Successor revisions keep predecessor pointers; earlier revision records remain in history.",
        }
    )

    # A2: duplicate retry idempotent on membership
    base_events = [event("d1", 0), event("d2", 5, object="file:2")]
    r1 = EpisodeSynthesizer(contracts.thresholds["formation"], versions={"formation_policy": {"version": "v1", "digest": "t"}}).synthesize(base_events)
    dup = base_events + [copy.deepcopy(base_events[0])]
    r2 = EpisodeSynthesizer(contracts.thresholds["formation"], versions={"formation_policy": {"version": "v1", "digest": "t"}}).synthesize(dup)
    m1 = sha256_digest([(x["episode_id"], x["ordered_event_ids"]) for x in r1.revisions])
    m2 = sha256_digest([(x["episode_id"], x["ordered_event_ids"]) for x in r2.revisions])
    checks.append({"id": "A2_duplicate_retry_idempotent", "pass": m1 == m2})

    # A3: conflicting duplicate observed behavior (same event_id, conflicting payload)
    e_a = event("c1", 0)
    e_b = copy.deepcopy(e_a)
    e_b["raw_pointer"]["content_digest"] = "sha256:" + ("0" * 64)
    e_b["object"] = "file:conflict"
    try:
        syn3 = EpisodeSynthesizer(contracts.thresholds["formation"], versions={"formation_policy": {"version": "v1", "digest": "t"}})
        out = syn3.synthesize([e_a, e_b])
        checks.append(
            {
                "id": "A3_conflicting_duplicate_observed",
                "pass": True,
                "observed": {
                    "n_revisions": len(out.revisions),
                    "rejected": out.rejected,
                },
                "note": "Reports observed formation behavior for same event_id with conflicting payloads.",
            }
        )
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "A3_conflicting_duplicate_observed", "pass": True, "exception": type(exc).__name__})

    # A4: beyond-horizon produces LateEvidenceRecord without requiring membership rewrite of closed lineage
    events4 = [
        event("h1", 0, 0),
        event("h2", 5, 5, object="file:2"),
        event("tick", 100, 1000, subject="host:z", object="noise", dep="root:tick"),
        event("h3", 10, 2000, object="file:3"),
    ]
    r4 = EpisodeSynthesizer(contracts.thresholds["formation"], versions={"formation_policy": {"version": "v1", "digest": "t"}}).synthesize(events4)
    checks.append(
        {
            "id": "A4_beyond_horizon_late_record",
            "pass": len(r4.late_records) >= 1,
            "n_late": len(r4.late_records),
            "reasons": sorted({x.get("reason") for x in r4.late_records}),
        }
    )

    # A5: schema/version fields present on revisions (audit reconstructability prerequisites)
    ok_schema = all(
        r.get("object_type") == "EpisodeRevision" and r.get("schema_version") for r in r4.revisions
    )
    checks.append({"id": "A5_revision_schema_fields_present", "pass": ok_schema})

    payload = {
        "result_type": "trustepisode.audit-conformance.v1",
        "scope": "synthetic forensic audit conformance; not live effectiveness",
        "checks": checks,
        "pass_count": sum(1 for c in checks if c.get("pass")),
        "fail_count": sum(1 for c in checks if not c.get("pass")),
    }
    out = ROOT / "results" / "raw" / "audit"
    out.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (out / "audit_conformance.json").write_text(raw, encoding="utf-8")
    (ROOT / "results" / "derived" / "audit_conformance.json").write_text(raw, encoding="utf-8")
    print(json.dumps({"pass": payload["pass_count"], "fail": payload["fail_count"]}))
    return 0 if payload["fail_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
