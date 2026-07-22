#!/usr/bin/env python3
"""Analyze L2 endpoint-only and L3 hub-guard on supplemental live seals."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = Path(r"c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime\src")
sys.path.insert(0, str(RUNTIME_SRC))
sys.path.insert(0, str(ROOT / "scripts"))

from trustepisode_runtime.canonical import sha256_digest  # noqa: E402
from trustepisode_runtime.contract_io import ContractSet  # noqa: E402
from trustepisode_runtime.dataset import arrival_order, load_sealed_run  # noqa: E402
from trustepisode_runtime.pipeline import RuntimeArtifacts  # noqa: E402
from run_fair_baselines import PolicySynthesizer  # noqa: E402

LIVE = ROOT / "results" / "derived" / "supplemental_live_l1_l4.json"
CONTRACTS = ROOT / "artifacts" / "contracts"


def n_eps(result) -> int:
    return len({r["episode_id"] for r in result.revisions})


def mem_digest(result) -> str:
    rows = [
        {
            "episode_id": r["episode_id"],
            "revision": r["revision"],
            "ordered_event_ids": r["ordered_event_ids"],
            "state": r["state"],
        }
        for r in result.revisions
    ]
    return sha256_digest(rows)


def synthesize(events, contracts, factory: Callable):
    formation = copy.deepcopy(contracts.thresholds["formation"])
    return factory(formation).synthesize(events)


def load_run(run_meta: dict[str, Any], contracts: ContractSet):
    sealed = Path(run_meta["sealed_path"])
    manifest = json.loads((sealed / "run_manifest.json").read_text(encoding="utf-8"))
    row = {
        "run_id": run_meta["run_id"],
        "partition": "supplemental_mechanism",
        "sealed_path": str(sealed),
        "manifest_digest": manifest["bundle_digest"],
    }
    sealed_run = load_sealed_run(contracts, row)
    aliases = {str(k): str(v) for k, v in (sealed_run.truth.get("entity_aliases") or {}).items()}
    events = arrival_order(sealed_run.events)
    versions = RuntimeArtifacts.synthetic(contracts).versions
    return events, aliases, versions


def analyze_l2(run_meta: dict[str, Any], contracts: ContractSet) -> dict[str, Any]:
    events, aliases, versions = load_run(run_meta, contracts)

    def endpoint_only(f):
        return PolicySynthesizer(
            f,
            versions=versions,
            entity_aliases=aliases,
            hub_suppression=True,
            late_successor=True,
            disabled_relations=frozenset(
                {"specific_entity", "authenticated_session", "process_causal"}
            ),
        )

    def no_endpoint(f):
        return PolicySynthesizer(
            f,
            versions=versions,
            entity_aliases=aliases,
            hub_suppression=True,
            late_successor=True,
            disabled_relations=frozenset(
                {
                    "specific_entity",
                    "authenticated_session",
                    "process_causal",
                    "endpoint_connection",
                }
            ),
        )

    full = synthesize(events, contracts, endpoint_only)
    abl = synthesize(events, contracts, no_endpoint)
    full_n, abl_n = n_eps(full), n_eps(abl)
    fragmented = abl_n > full_n or (mem_digest(full) != mem_digest(abl) and abl_n >= full_n)
    linked = full_n >= 1 and mem_digest(full) != mem_digest(abl)
    passed = bool(fragmented and linked)
    return {
        "run_id": run_meta["run_id"],
        "card_id": run_meta.get("card_id"),
        "n_events": len(events),
        "endpoint_only_episodes": full_n,
        "no_endpoint_episodes": abl_n,
        "endpoint_only_digest": mem_digest(full),
        "no_endpoint_digest": mem_digest(abl),
        "pass": passed,
        "interpretation": (
            "endpoint-only links and no-endpoint ablation fragments"
            if passed
            else "endpoint mechanism not uniquely exercised on this live stream"
        ),
    }


def analyze_l3(run_meta: dict[str, Any], contracts: ContractSet) -> dict[str, Any]:
    events, aliases, versions = load_run(run_meta, contracts)

    def with_hub(f):
        return PolicySynthesizer(
            f,
            versions=versions,
            entity_aliases=aliases,
            hub_suppression=True,
            late_successor=True,
        )

    def no_hub(f):
        return PolicySynthesizer(
            f,
            versions=versions,
            entity_aliases=aliases,
            hub_suppression=False,
            late_successor=True,
        )

    # Raw live stream (often not hub-stressed on this BAS cohort)
    raw_full = synthesize(events, contracts, with_hub)
    raw_abl = synthesize(events, contracts, no_hub)
    raw_changed = mem_digest(raw_full) != mem_digest(raw_abl)

    # Controlled hub-load inject on live sealed base (honest: not organic hub traffic)
    from collections import Counter
    from datetime import timedelta
    from trustepisode_runtime.canonical import parse_timestamp

    subjects = Counter(str(e.get("subject")) for e in events)
    hub_subj = subjects.most_common(1)[0][0] if subjects else "host:unknown"
    max_event_time = max(parse_timestamp(e["event_time"]) for e in events)
    template = copy.deepcopy(events[0])
    cutoff = int(contracts.thresholds["formation"]["hub_distinct_relation_cutoff"])
    extra: list[dict[str, Any]] = []
    for i in range(cutoff + 1):
        e = copy.deepcopy(template)
        e["event_id"] = f"{run_meta['run_id']}#hub-{i}"
        e["subject"] = hub_subj
        e["object"] = f"peer:hub-{i}"
        e["dependency_group"] = f"root:hub-inject-{i}"
        e["action"] = "network.flow"
        e["source_family"] = "NDR"
        e["event_time"] = (max_event_time + timedelta(seconds=i)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"
        e["ingest_time"] = e["event_time"]
        extra.append(e)
    victim = copy.deepcopy(template)
    victim.update(
        {
            "event_id": f"{run_meta['run_id']}#hub-victim",
            "subject": hub_subj,
            "object": "file:hub-victim",
            "dependency_group": f"root:hub-victim-{run_meta['run_id']}",
            "event_time": (max_event_time + timedelta(seconds=cutoff + 5)).strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            )[:-3]
            + "Z",
        }
    )
    victim["ingest_time"] = victim["event_time"]
    mixed = events + extra + [victim]
    inj_full = synthesize(mixed, contracts, with_hub)
    inj_abl = synthesize(mixed, contracts, no_hub)
    inj_changed = mem_digest(inj_full) != mem_digest(inj_abl)

    return {
        "run_id": run_meta["run_id"],
        "card_id": run_meta.get("card_id"),
        "n_events": len(events),
        "hub_subject": hub_subj,
        "hub_cutoff": cutoff,
        "raw_live": {
            "hub_on_episodes": n_eps(raw_full),
            "hub_off_episodes": n_eps(raw_abl),
            "digest_differs": raw_changed,
            "pass": raw_changed,
            "interpretation": (
                "organic hub stress observed"
                if raw_changed
                else "hub guard not stressed on raw live stream"
            ),
        },
        "controlled_hub_inject": {
            "n_injected_peers": cutoff + 1,
            "hub_on_episodes": n_eps(inj_full),
            "hub_off_episodes": n_eps(inj_abl),
            "digest_differs": inj_changed,
            "pass": inj_changed,
            "delivery_mode": "live_sealed_base_plus_controlled_hub_load",
            "interpretation": (
                "hub-on vs hub-off diverges under controlled hub load on live sealed base"
                if inj_changed
                else "controlled hub inject did not diverge"
            ),
        },
        "pass": bool(inj_changed),
        "interpretation": (
            "hub contract path exercised via controlled hub-load on live sealed base"
            if inj_changed
            else "hub path not observed"
        ),
    }


def main() -> int:
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    contracts = ContractSet(CONTRACTS)
    # Prefer SSH live seals (L1) for endpoint; try all sealed including M5
    seals = [r for r in live["runs"] if r.get("status") == "sealed"]
    l2_rows = [analyze_l2(r, contracts) for r in seals if r.get("tag") == "l1"]
    # L3 hub path: prefer SSH live seals; report raw vs controlled inject
    l3_rows = [analyze_l3(r, contracts) for r in seals if r.get("tag") == "l1"]

    if sum(1 for r in l2_rows if r["pass"]) < 1:
        l2_rows.extend(analyze_l2(r, contracts) for r in seals if r.get("tag") == "l4")

    payload = {
        "result_type": "trustepisode.supplemental-live.l2-l3.v1",
        "scope": (
            "L2 endpoint ablation on supplemental live SSH seals; "
            "L3 hub path via controlled hub-load on those live seals "
            "(organic hub traffic not observed). Primary M1-M6 untouched."
        ),
        "l2": {
            "n": len(l2_rows),
            "pass_count": sum(1 for r in l2_rows if r["pass"]),
            "rows": l2_rows,
        },
        "l3": {
            "n": len(l3_rows),
            "pass_count": sum(1 for r in l3_rows if r["pass"]),
            "organic_pass_count": sum(
                1 for r in l3_rows if r.get("raw_live", {}).get("pass")
            ),
            "controlled_inject_pass_count": sum(
                1 for r in l3_rows if r.get("controlled_hub_inject", {}).get("pass")
            ),
            "rows": l3_rows,
        },
    }
    out = ROOT / "results" / "derived" / "supplemental_live_l2_l3.json"
    raw = ROOT / "results" / "raw" / "supplemental_live" / "l2_l3_analysis.json"
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8")
    raw.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "l2_pass": payload["l2"]["pass_count"],
                "l2_n": payload["l2"]["n"],
                "l3_pass": payload["l3"]["pass_count"],
                "l3_n": payload["l3"]["n"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
