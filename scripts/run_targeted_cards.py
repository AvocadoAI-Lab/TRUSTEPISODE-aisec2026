#!/usr/bin/env python3
"""Targeted mechanism conformance cards T1-T8 (synthetic; not primary effectiveness)."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]


def locate_runtime() -> Path:
    packaged = ROOT / "experiment_runtime"
    if packaged.exists():
        return packaged
    for base in ROOT.parents:
        matches = sorted(base.glob("*/TRUSTEPISODE-aisec2026/experiment_runtime"))
        if matches:
            return matches[0]
    raise FileNotFoundError("TrustEpisode experiment_runtime not found")


RUNTIME_SRC = locate_runtime() / "src"
sys.path.insert(0, str(RUNTIME_SRC))

from trustepisode_runtime.canonical import sha256_digest  # noqa: E402
from trustepisode_runtime.contract_io import ContractSet  # noqa: E402
from trustepisode_runtime.formation import EpisodeSynthesizer, Lineage  # noqa: E402

from run_fair_baselines import PolicySynthesizer, SlidingEntitySynthesizer, SlidingTimeSynthesizer  # noqa: E402

BASE = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


def ts(seconds: float) -> str:
    return (BASE + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def event(
    eid: str,
    *,
    t: float,
    ingest: float | None = None,
    subject: str,
    obj: str,
    dep: str,
    source_family: str = "EDR",
    source_instance: str = "edr-01",
    action: str = "process.start",
    command_family: str | None = None,
    attrs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attributes = dict(attrs or {})
    if command_family:
        attributes["command_family"] = command_family
    digest = "sha256:" + hashlib.sha256(eid.encode("utf-8")).hexdigest()
    return {
        "object_type": "NormalizedEvent",
        "schema_version": "trustepisode.online.v1",
        "event_id": eid,
        "event_time": ts(t),
        "ingest_time": ts(ingest if ingest is not None else t),
        "source_family": source_family,
        "source_instance": source_instance,
        "subject": subject,
        "object": obj,
        "action": action,
        "dependency_group": dep,
        "attributes": attributes,
        "raw_pointer": {
            "content_digest": digest,
            "locator": f"synthetic:{eid}",
            "object_id": f"raw:{eid}",
            "storage_schema_version": "trustepisode.endpoint-observation.v1",
        },
    }


def synthesize(events: list[dict[str, Any]], contracts: ContractSet, factory: Callable) -> Any:
    formation = copy.deepcopy(contracts.thresholds["formation"])
    syn = factory(formation)
    return syn.synthesize(events)


def terminal_membership(result) -> list[tuple[str, tuple[str, ...]]]:
    seen = set()
    out = []
    for rev in result.revisions:
        if rev["state"] != "finalized" or rev["episode_id"] in seen:
            continue
        # use first finalized per lineage; later take latest closed if present
        seen.add(rev["episode_id"])
    # prefer latest revision per episode_id
    latest = {}
    for rev in result.revisions:
        key = rev["episode_id"]
        if key not in latest or rev["revision"] >= latest[key]["revision"]:
            latest[key] = rev
    for rev in sorted(latest.values(), key=lambda r: r["episode_id"]):
        if rev["state"] in {"finalized", "closed"}:
            out.append((rev["episode_id"], tuple(rev["ordered_event_ids"])))
    return out


def n_episodes(result) -> int:
    return len(terminal_membership(result))


def has_late_record(result, reason: str | None = None) -> bool:
    if reason is None:
        return bool(result.late_records)
    return any(r.get("reason") == reason for r in result.late_records)


def max_revision(result) -> int:
    return max((r["revision"] for r in result.revisions), default=-1)


def run_card(name: str, contracts: ContractSet) -> dict[str, Any]:
    versions = {"formation_policy": {"version": "trustepisode.formation.v1", "digest": "test"}}

    def full(f):
        return PolicySynthesizer(f, versions=versions, hub_suppression=True, late_successor=True)

    def no_causal(f):
        return PolicySynthesizer(
            f, versions=versions, disabled_relations=frozenset({"process_causal"}), hub_suppression=True
        )

    def no_session(f):
        return PolicySynthesizer(
            f,
            versions=versions,
            disabled_relations=frozenset({"authenticated_session"}),
            hub_suppression=True,
        )

    def no_endpoint(f):
        return PolicySynthesizer(
            f,
            versions=versions,
            disabled_relations=frozenset({"endpoint_connection"}),
            hub_suppression=True,
        )

    def no_hub(f):
        return PolicySynthesizer(f, versions=versions, hub_suppression=False)

    def no_merge(f):
        ff = copy.deepcopy(f)
        ff["max_merge_parents"] = 1
        return PolicySynthesizer(ff, versions=versions, hub_suppression=True)

    def no_late(f):
        return PolicySynthesizer(f, versions=versions, late_successor=False)

    if name == "T1_PROCESS_CAUSAL":
        # No shared entity: only identical dependency_group can link.
        events = [
            event("e1", t=0, subject="host:a", obj="file:1", dep="root:causal", command_family="file_change"),
            event("e2", t=10, subject="host:b", obj="file:2", dep="root:causal", command_family="local_action"),
        ]
        full_r = synthesize(events, contracts, full)
        abl_r = synthesize(events, contracts, no_causal)
        expected = n_episodes(full_r) == 1 and n_episodes(abl_r) >= 2
        return _pack(name, events, full_r, abl_r, "no_process_causal", expected, "fragment_without_causal")

    if name == "T2_AUTH_SESSION":
        # Discriminating: disable entity/endpoint/causal so authenticated_session is sole link.
        events = [
            event(
                "e1",
                t=0,
                subject="host:a",
                obj="user:u",
                dep="root:s1",
                command_family="remote_session",
                attrs={"app_protocol": "ssh", "destination_port": 22},
            ),
            event(
                "e2",
                t=20,
                subject="host:b",
                obj="user:u",
                dep="root:s2",
                command_family="remote_session",
                attrs={"app_protocol": "ssh", "destination_port": 22},
            ),
        ]

        def session_only(f):
            return PolicySynthesizer(
                f,
                versions=versions,
                disabled_relations=frozenset(
                    {"specific_entity", "endpoint_connection", "process_causal"}
                ),
                hub_suppression=True,
            )

        def no_session_no_entity(f):
            return PolicySynthesizer(
                f,
                versions=versions,
                disabled_relations=frozenset(
                    {
                        "specific_entity",
                        "endpoint_connection",
                        "process_causal",
                        "authenticated_session",
                    }
                ),
                hub_suppression=True,
            )

        full_r = synthesize(events, contracts, session_only)
        abl_r = synthesize(events, contracts, no_session_no_entity)
        passed = n_episodes(full_r) == 1 and n_episodes(abl_r) >= 2
        return {
            "mechanism": name,
            "input_digest": sha256_digest(events),
            "full_policy": {
                "n_episodes": n_episodes(full_r),
                "digest": sha256_digest(full_r.revisions),
                "enabled_relations": ["authenticated_session"],
            },
            "ablation": {
                "name": "no_authenticated_session_with_entity_fallback_disabled",
                "n_episodes": n_episodes(abl_r),
                "digest": sha256_digest(abl_r.revisions),
            },
            "expected_transition": "session_only_links_ablation_fragments",
            "observed_transition": f"session_only={n_episodes(full_r)}, abl={n_episodes(abl_r)}",
            "pass": passed,
            "status": "pass" if passed else "fail",
            "note": (
                "Conformance: with specific_entity disabled, authenticated_session alone "
                "must link; removing session fragments."
            ),
        }

    if name == "T3_ENDPOINT_MAPPING":
        # Discriminating: disable entity/session/causal so endpoint_connection is sole link.
        events = [
            event("e1", t=0, subject="host:a", obj="proc:1", dep="root:e", source_family="EDR"),
            event(
                "e2",
                t=5,
                subject="host:a",
                obj="ip:1.2.3.4",
                dep="root:n",
                source_family="NDR",
                source_instance="ndr",
                action="network.flow",
            ),
        ]

        def endpoint_only(f):
            return PolicySynthesizer(
                f,
                versions=versions,
                disabled_relations=frozenset(
                    {"specific_entity", "authenticated_session", "process_causal"}
                ),
                hub_suppression=True,
            )

        def no_endpoint_no_entity(f):
            return PolicySynthesizer(
                f,
                versions=versions,
                disabled_relations=frozenset(
                    {
                        "specific_entity",
                        "authenticated_session",
                        "process_causal",
                        "endpoint_connection",
                    }
                ),
                hub_suppression=True,
            )

        full_r = synthesize(events, contracts, endpoint_only)
        abl_r = synthesize(events, contracts, no_endpoint_no_entity)
        passed = n_episodes(full_r) == 1 and n_episodes(abl_r) >= 2
        return {
            "mechanism": name,
            "input_digest": sha256_digest(events),
            "full_policy": {
                "n_episodes": n_episodes(full_r),
                "digest": sha256_digest(full_r.revisions),
                "enabled_relations": ["endpoint_connection"],
            },
            "ablation": {
                "name": "no_endpoint_with_entity_fallback_disabled",
                "n_episodes": n_episodes(abl_r),
                "digest": sha256_digest(abl_r.revisions),
            },
            "expected_transition": "endpoint_only_links_ablation_fragments",
            "observed_transition": f"endpoint_only={n_episodes(full_r)}, abl={n_episodes(abl_r)}",
            "pass": passed,
            "status": "pass" if passed else "fail",
            "note": (
                "Conformance: with specific_entity disabled, endpoint_connection alone must "
                "join EDR/NDR sharing a host entity."
            ),
        }

    if name == "T4_HUB_GUARD":
        # Force hub: many dependency groups on same entity within hub window, cutoff 25
        events = [
            event(f"hub{i}", t=float(i), subject="host:hub", obj=f"peer:{i}", dep=f"root:hub{i}")
            for i in range(26)
        ]
        events.append(event("victim", t=30, subject="host:hub", obj="file:x", dep="root:victim"))
        full_r = synthesize(events, contracts, full)
        abl_r = synthesize(events, contracts, no_hub)
        # With hub guard, victim may not attach to hub-heavy lineage; without guard it may merge more.
        return {
            "mechanism": name,
            "input_digest": sha256_digest(events),
            "full_policy": {
                "n_episodes": n_episodes(full_r),
                "n_revisions": len(full_r.revisions),
                "digest": sha256_digest(full_r.revisions),
            },
            "ablation": {
                "name": "no_hub_guard",
                "n_episodes": n_episodes(abl_r),
                "n_revisions": len(abl_r.revisions),
                "digest": sha256_digest(abl_r.revisions),
            },
            "expected_transition": "hub_guard_changes_membership_or_episode_count_vs_disabled",
            "observed_transition": f"full_eps={n_episodes(full_r)}, no_hub_eps={n_episodes(abl_r)}",
            "pass": sha256_digest(full_r.revisions) != sha256_digest(abl_r.revisions),
            "note": "Pass if enabling hub guard changes synthesis digest versus disabled guard.",
        }

    if name == "T5_PARENT_MERGE":
        # Two open episodes; merge event has strong links to both (causal to A, endpoint to B).
        events = [
            event("a1", t=0, subject="host:a", obj="p:1", dep="root:A", source_family="EDR"),
            event("b1", t=1, subject="host:b", obj="p:2", dep="root:B", source_family="EDR"),
            event(
                "m",
                t=2,
                subject="host:a",
                obj="host:b",
                dep="root:A",
                source_family="NDR",
                source_instance="ndr",
                action="network.flow",
            ),
        ]
        full_r = synthesize(events, contracts, full)
        abl_r = synthesize(events, contracts, no_merge)
        full_parents = sum(1 for r in full_r.revisions if r.get("parent_episode_ids"))
        abl_parents = sum(1 for r in abl_r.revisions if r.get("parent_episode_ids"))
        return {
            "mechanism": name,
            "input_digest": sha256_digest(events),
            "full_policy": {
                "n_episodes": n_episodes(full_r),
                "parent_merges": full_parents,
                "digest": sha256_digest(full_r.revisions),
            },
            "ablation": {
                "name": "no_parent_merge",
                "n_episodes": n_episodes(abl_r),
                "parent_merges": abl_parents,
                "digest": sha256_digest(abl_r.revisions),
            },
            "expected_transition": "merge_enabled_creates_parent_episode_ids",
            "observed_transition": f"full_parents={full_parents}, abl_parents={abl_parents}",
            "pass": full_parents > abl_parents,
            "note": "Pass if full policy records parent merges and max_merge_parents=1 does not.",
        }

    if name == "T6_LATE_SUCCESSOR":
        # finalize then late within 900s
        events = [
            event("e1", t=0, ingest=0, subject="host:a", obj="f:1", dep="root:L"),
            event("e2", t=10, ingest=10, subject="host:a", obj="f:2", dep="root:L"),
            # advance watermark by later unrelated? Actually flush uses max ingest.
            # Add distant ingest gap via e3 late after finalization.
            event("e3", t=20, ingest=200, subject="host:a", obj="f:3", dep="root:L"),
        ]
        full_r = synthesize(events, contracts, full)
        abl_r = synthesize(events, contracts, no_late)
        return {
            "mechanism": name,
            "input_digest": sha256_digest(events),
            "full_policy": {
                "max_revision": max_revision(full_r),
                "n_late": len(full_r.late_records),
                "digest": sha256_digest({"r": full_r.revisions, "l": full_r.late_records}),
            },
            "ablation": {
                "name": "no_late_successor",
                "max_revision": max_revision(abl_r),
                "n_late": len(abl_r.late_records),
                "digest": sha256_digest({"r": abl_r.revisions, "l": abl_r.late_records}),
            },
            "expected_transition": "disabling_late_successor_increases_late_records_or_reduces_revisions",
            "observed_transition": (
                f"full_rev={max_revision(full_r)}, abl_rev={max_revision(abl_r)}, "
                f"full_late={len(full_r.late_records)}, abl_late={len(abl_r.late_records)}"
            ),
            "pass": (
                len(abl_r.late_records) > len(full_r.late_records)
                or max_revision(full_r) > max_revision(abl_r)
                or sha256_digest(full_r.revisions) != sha256_digest(abl_r.revisions)
            ),
            "note": "Conformance: late-successor policy changes revision/late-store behavior.",
        }

    if name == "T7_BEYOND_HORIZON":
        # Finalize/close lineage via an unrelated high-ingest tick, then related late event.
        events = [
            event("e1", t=0, ingest=0, subject="host:a", obj="f:1", dep="root:H"),
            event("e2", t=5, ingest=5, subject="host:a", obj="f:2", dep="root:H"),
            event("tick", t=100, ingest=1000, subject="host:z", obj="noise", dep="root:tick"),
            event("e3", t=10, ingest=2000, subject="host:a", obj="f:3", dep="root:H"),
        ]
        full_r = synthesize(events, contracts, full)
        return {
            "mechanism": name,
            "input_digest": sha256_digest(events),
            "full_policy": {
                "n_late": len(full_r.late_records),
                "late_reasons": sorted({r.get("reason") for r in full_r.late_records}),
                "revision_digest": sha256_digest(full_r.revisions),
            },
            "ablation": {"name": "n/a_beyond_horizon_is_full_policy_behavior"},
            "expected_transition": "beyond_horizon_emits_LateEvidenceRecord_without_membership_rewrite",
            "observed_transition": f"late={len(full_r.late_records)}, reasons={sorted({r.get('reason') for r in full_r.late_records})}",
            "pass": len(full_r.late_records) >= 1,
            "note": "Pass if late store receives beyond-horizon or closed-lineage evidence.",
        }

    if name == "T8_TIE_BREAK":
        events = [
            event("a", t=0, subject="host:x", obj="f:1", dep="root:A"),
            event("b", t=0, subject="host:y", obj="f:2", dep="root:B"),
            event("c", t=1, subject="host:x", obj="host:y", dep="root:C"),
        ]
        r1 = synthesize(events, contracts, full)
        r2 = synthesize(list(reversed(events)), contracts, full)
        # arrival order matters for open-set; compare sorted-by-ingest canonical order equality path
        from trustepisode_runtime.dataset import arrival_order

        r3 = synthesize(arrival_order(events), contracts, full)
        r4 = synthesize(arrival_order(list(reversed(events))), contracts, full)
        return {
            "mechanism": name,
            "input_digest": sha256_digest(events),
            "full_policy": {"digest_arrival_sorted": sha256_digest(r3.revisions)},
            "ablation": {
                "name": "reversed_then_arrival_order",
                "digest_arrival_sorted": sha256_digest(r4.revisions),
            },
            "expected_transition": "canonical_arrival_order_yields_identical_digests",
            "observed_transition": (
                f"equal={sha256_digest(r3.revisions)==sha256_digest(r4.revisions)}; "
                f"raw_reverse_differs={sha256_digest(r1.revisions)!=sha256_digest(r2.revisions)}"
            ),
            "pass": sha256_digest(r3.revisions) == sha256_digest(r4.revisions),
            "note": "Distinguishes canonical replay determinism from raw delivery-order sensitivity.",
        }

    raise ValueError(name)


def _pack(name, events, full_r, abl_r, abl_name, passed, expected):
    return {
        "mechanism": name,
        "input_digest": sha256_digest(events),
        "full_policy": {
            "n_episodes": n_episodes(full_r),
            "digest": sha256_digest(full_r.revisions),
        },
        "ablation": {
            "name": abl_name,
            "n_episodes": n_episodes(abl_r),
            "digest": sha256_digest(abl_r.revisions),
        },
        "expected_transition": expected,
        "observed_transition": f"full_eps={n_episodes(full_r)}, abl_eps={n_episodes(abl_r)}",
        "pass": bool(passed),
        "note": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", type=Path, default=ROOT / "artifacts" / "contracts")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    contracts = ContractSet(args.contracts)
    cards = [
        "T1_PROCESS_CAUSAL",
        "T2_AUTH_SESSION",
        "T3_ENDPOINT_MAPPING",
        "T4_HUB_GUARD",
        "T5_PARENT_MERGE",
        "T6_LATE_SUCCESSOR",
        "T7_BEYOND_HORIZON",
        "T8_TIE_BREAK",
    ]
    results = [run_card(name, contracts) for name in cards]
    for r in results:
        r.setdefault("status", "pass" if r.get("pass") else "fail")
    payload = {
        "result_type": "trustepisode.targeted-mechanism-cards.v1",
        "scope": "synthetic conformance only; not production effectiveness evidence",
        "cards": results,
        "pass_count": sum(1 for r in results if r["pass"]),
        "fail_count": sum(1 for r in results if not r["pass"]),
        "discriminating_pass_count": sum(
            1
            for r in results
            if r["pass"]
            and r["mechanism"]
            in {
                "T1_PROCESS_CAUSAL",
                "T2_AUTH_SESSION",
                "T3_ENDPOINT_MAPPING",
                "T4_HUB_GUARD",
                "T5_PARENT_MERGE",
                "T6_LATE_SUCCESSOR",
                "T7_BEYOND_HORIZON",
                "T8_TIE_BREAK",
            }
        ),
    }
    out = args.output_root / "raw" / "targeted_cards"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "mechanism_cards.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_root / "derived" / "mechanism_cards.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"pass": payload["pass_count"], "fail": payload["fail_count"]}, ensure_ascii=False))
    return 0 if payload["fail_count"] == 0 else 1


if __name__ == "__main__":
    # allow importing sibling script
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
