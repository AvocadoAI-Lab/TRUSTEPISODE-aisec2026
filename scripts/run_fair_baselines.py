#!/usr/bin/env python3
"""Fair sliding-gap baselines, legacy fixed-bin reference, and paired bootstrap.

Primary comparisons (same W_gap=300s, W_max=3600s as TrustEpisode):
  EB1_SLIDING_TIME
  EB2_SLIDING_ENTITY
  EB3_RELATION_NO_ADVANCED_GUARDS
  EB4_TRUSTEPISODE

Legacy reference (not primary):
  EB0_FIXED_BIN_300s

Does not modify sealed primary Table-4 artifacts.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

from trustepisode_runtime.canonical import parse_timestamp, sha256_digest, utf8_key  # noqa: E402
from trustepisode_runtime.contract_io import ContractSet  # noqa: E402
from trustepisode_runtime.dataset import arrival_order, load_sealed_run  # noqa: E402
from trustepisode_runtime.evaluation import (  # noqa: E402
    formation_metrics,
    label_episode,
    parse_truth_groups,
    qualified_edges,
    terminal_episode_views,
    window_episodes,
)
from trustepisode_runtime.formation import (  # noqa: E402
    RELATION_PRECEDENCE,
    EpisodeSynthesizer,
    Lineage,
    LinkCandidate,
)
from trustepisode_runtime.pipeline import PipelineResult, RuntimeArtifacts  # noqa: E402

MALICIOUS = {f"M{i}" for i in range(1, 8)}
PRIMARY_METRICS = (
    "action_coverage",
    "exact_complete_recovery",
    "fragmentation",
    "over_merge",
    "contamination",
    "episode_precision",
    "episode_recall",
    "episode_f1",
)
BOOTSTRAP_SEED = 20260721
BOOTSTRAP_N = 2000


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def digest_json(obj: Any) -> str:
    return sha256_digest(obj)


@dataclass(frozen=True)
class BuilderSpec:
    name: str
    kind: str  # fixed_bin | sliding_time | sliding_entity | relation_no_guards | trustepisode
    role: str  # primary | legacy


BUILDERS = [
    BuilderSpec("EB0_FIXED_BIN_300s", "fixed_bin", "legacy"),
    BuilderSpec("EB1_SLIDING_TIME", "sliding_time", "primary"),
    BuilderSpec("EB2_SLIDING_ENTITY", "sliding_entity", "primary"),
    BuilderSpec("EB3_RELATION_NO_ADVANCED_GUARDS", "relation_no_guards", "primary"),
    BuilderSpec("EB4_TRUSTEPISODE", "trustepisode", "primary"),
]


class SlidingTimeSynthesizer(EpisodeSynthesizer):
    """Same gap/span lifecycle as production, but link on time proximity only."""

    def _relations(self, event: dict[str, Any], lineage: Lineage) -> tuple[set[str], set[str]]:
        shared: set[str] = set()
        event_entities = self._entities(event)
        for event_id in lineage.event_ids:
            shared |= event_entities.intersection(self._entities(self.events[event_id]))
        return {"time_proximity"}, shared

    def _candidate(self, event: dict[str, Any], lineage: Lineage) -> LinkCandidate | None:
        event_time = parse_timestamp(event["event_time"])
        times = [parse_timestamp(self.events[item]["event_time"]) for item in lineage.event_ids]
        delta = min(abs((event_time - item).total_seconds()) for item in times)
        if delta > self.gap:
            return None
        start, end = min([*times, event_time]), max([*times, event_time])
        if (end - start).total_seconds() > self.max_span:
            return None
        return LinkCandidate(
            episode_id=lineage.episode_id,
            relation_classes=("time_proximity",),
            primary_reason="time_proximity",
            rho=0,
            delta_seconds=delta,
            start_time=start,
        )


class SlidingEntitySynthesizer(EpisodeSynthesizer):
    """Sliding gap/span with entity overlap only (no causal/session/endpoint)."""

    def _relations(self, event: dict[str, Any], lineage: Lineage) -> tuple[set[str], set[str]]:
        relations: set[str] = set()
        shared_entities: set[str] = set()
        event_entities = self._entities(event)
        for event_id in lineage.event_ids:
            shared = event_entities.intersection(self._entities(self.events[event_id]))
            shared_entities.update(shared)
            if shared:
                relations.add("specific_entity")
        return relations, shared_entities


class PolicySynthesizer(EpisodeSynthesizer):
    def __init__(
        self,
        formation: dict[str, Any],
        *,
        versions: dict[str, Any],
        entity_aliases: dict[str, str] | None = None,
        disabled_relations: frozenset[str] = frozenset(),
        hub_suppression: bool = True,
        late_successor: bool = True,
    ) -> None:
        if not hub_suppression:
            formation = copy.deepcopy(formation)
            formation["hub_distinct_relation_cutoff"] = 2**31 - 1
        super().__init__(formation, versions=versions, entity_aliases=entity_aliases)
        self.disabled_relations = set(disabled_relations)
        self.late_successor = late_successor

    def _relations(self, event: dict[str, Any], lineage: Lineage) -> tuple[set[str], set[str]]:
        relations, shared = super()._relations(event, lineage)
        return relations - self.disabled_relations, shared

    def _attach(self, lineage: Lineage, event: dict[str, Any], reason: str, *, late: bool) -> None:
        if late and not self.late_successor:
            # Ablation: refuse late membership without touching LateEvidenceRecord assembly.
            self.result.rejected.append(
                {"event_id": event["event_id"], "reason": "late_successor_disabled"}
            )
            return
        super()._attach(lineage, event, reason, late=late)


def load_cohort(lab_root: Path, families: set[str], expected: int) -> list[dict[str, Any]]:
    registry = lab_root / "experiment-data" / "campaign" / "run_registry.csv"
    with registry.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    cohort = [
        row
        for row in rows
        if row["status"] == "sealed"
        and row["partition"] == "train"
        and row["card_id"] in families
    ]
    if len(cohort) != expected:
        raise SystemExit(
            f"expected {expected} sealed malicious train runs in {sorted(families)}, "
            f"found {len(cohort)}"
        )
    return cohort


def exact_complete(episodes, groups) -> float | None:
    if not groups:
        return None
    edges = qualified_edges(episodes, groups)
    vals = []
    for group in groups:
        cov = max((e.action_coverage for e in edges if e.group_id == group.group_id), default=0.0)
        vals.append(1.0 if cov >= 1.0 - 1e-12 else 0.0)
    return sum(vals) / len(vals)


def extended_metrics(episodes, groups, benign_tokens, truth_conflict: bool) -> dict[str, Any]:
    base = formation_metrics(episodes, groups, benign_tokens=benign_tokens)
    edges = qualified_edges(episodes, groups)
    assignments = []
    # reuse assignment via formation_metrics internals already computed; recompute lightly
    from trustepisode_runtime.evaluation import maximum_weight_assignment

    assignments = maximum_weight_assignment(episodes, groups, edges)
    precision = len(assignments) / len(episodes) if episodes else None
    recall = len(assignments) / len(groups) if groups else None
    labels = [
        label_episode(ep, edges, groups, benign_tokens, truth_conflict=truth_conflict)["label"]
        for ep in episodes
    ]
    label_counts = Counter(labels)
    unmatched_groups = len(groups) - len({a.group_id for a in assignments})
    return {
        **base,
        "exact_complete_recovery": exact_complete(episodes, groups),
        "episode_precision": precision,
        "episode_recall": recall,
        "predicted_episode_count": len(episodes),
        "truth_group_count": len(groups),
        "unmatched_truth_group_count": unmatched_groups,
        "mixed_rate": label_counts["mixed"] / len(episodes) if episodes else None,
        "ambiguous_rate": label_counts["ambiguous"] / len(episodes) if episodes else None,
        "label_counts": dict(label_counts),
    }


def build_pipeline(events, contracts: ContractSet, spec: BuilderSpec, aliases: dict[str, str]) -> PipelineResult:
    synthetic = RuntimeArtifacts.synthetic(contracts)
    synthetic.entity_aliases = aliases
    formation = copy.deepcopy(contracts.thresholds["formation"])
    cfg_digest = digest_json(
        {
            "builder": spec.name,
            "kind": spec.kind,
            "W_gap_seconds": formation["W_gap_seconds"],
            "W_max_seconds": formation["W_max_seconds"],
            "W_revision_seconds": formation["W_revision_seconds"],
            "L_watermark_seconds": formation["L_watermark_seconds"],
            "hub_distinct_relation_cutoff": formation["hub_distinct_relation_cutoff"],
            "max_merge_parents": formation["max_merge_parents"],
        }
    )
    ordered = arrival_order(events)
    if spec.kind == "fixed_bin":
        synthesis = EpisodeSynthesizer(
            formation, versions=synthetic.versions, entity_aliases=aliases
        ).synthesize(ordered)
        return PipelineResult(synthesis=synthesis), cfg_digest
    if spec.kind == "sliding_time":
        synthesis = SlidingTimeSynthesizer(
            formation, versions=synthetic.versions, entity_aliases=aliases
        ).synthesize(ordered)
        return PipelineResult(synthesis=synthesis), cfg_digest
    if spec.kind == "sliding_entity":
        synthesis = SlidingEntitySynthesizer(
            formation, versions=synthetic.versions, entity_aliases=aliases
        ).synthesize(ordered)
        return PipelineResult(synthesis=synthesis), cfg_digest
    if spec.kind == "relation_no_guards":
        formation["max_merge_parents"] = 1
        synthesis = PolicySynthesizer(
            formation,
            versions=synthetic.versions,
            entity_aliases=aliases,
            hub_suppression=False,
            late_successor=False,
        ).synthesize(ordered)
        return PipelineResult(synthesis=synthesis), cfg_digest
    # trustepisode full
    synthesis = PolicySynthesizer(
        formation,
        versions=synthetic.versions,
        entity_aliases=aliases,
        hub_suppression=True,
        late_successor=True,
    ).synthesize(ordered)
    return PipelineResult(synthesis=synthesis), cfg_digest


def episodes_for(spec: BuilderSpec, pipeline: PipelineResult, aliases: dict[str, str]):
    if spec.kind == "fixed_bin":
        return window_episodes(pipeline, entity_components=False, aliases=aliases)
    return terminal_episode_views(pipeline, aliases=aliases)


def evaluate_run(row, contracts, spec: BuilderSpec) -> dict[str, Any]:
    run = load_sealed_run(contracts, row)
    aliases = {str(k): str(v) for k, v in (run.truth.get("entity_aliases") or {}).items()}
    pipeline, cfg_digest = build_pipeline(run.events, contracts, spec, aliases)
    episodes = episodes_for(spec, pipeline, aliases)
    groups = parse_truth_groups(run.truth, aliases=aliases)
    benign = frozenset(str(x) for x in run.truth.get("benign_action_tokens", []))
    metrics = extended_metrics(
        episodes, groups, benign, truth_conflict=bool(run.truth.get("truth_conflict", False))
    )
    membership = [
        {
            "episode_id": item["episode_id"],
            "revision": item["revision"],
            "ordered_event_ids": item["ordered_event_ids"],
            "state": item["state"],
        }
        for item in pipeline.synthesis.revisions
    ]
    return {
        "run_id": row["run_id"],
        "card_id": row["card_id"],
        "mode": row["benign_mode"],
        "builder": spec.name,
        "role": spec.role,
        "config_digest": cfg_digest,
        "manifest_digest": row["manifest_digest"],
        "synthesis_digest": sha256_digest(
            {
                "revisions": [sha256_digest(x) for x in pipeline.synthesis.revisions],
                "late": [sha256_digest(x) for x in pipeline.synthesis.late_records],
                "rejected": pipeline.synthesis.rejected,
            }
        ),
        "membership_digest": sha256_digest(membership),
        **{k: metrics[k] for k in PRIMARY_METRICS},
        "predicted_episode_count": metrics["predicted_episode_count"],
        "truth_group_count": metrics["truth_group_count"],
        "unmatched_truth_group_count": metrics["unmatched_truth_group_count"],
        "mixed_rate": metrics["mixed_rate"],
        "ambiguous_rate": metrics["ambiguous_rate"],
        "label_counts": metrics["label_counts"],
    }


def summarize(vals: list[float | None]) -> dict[str, Any]:
    defined = [float(v) for v in vals if v is not None]
    return {
        "mean": statistics.fmean(defined) if defined else None,
        "sample_sd": statistics.stdev(defined) if len(defined) > 1 else (0.0 if len(defined) == 1 else None),
        "defined": len(defined),
        "undefined": len(vals) - len(defined),
    }


def paired_bootstrap(
    deltas: list[float],
    *,
    seed: int,
    n: int,
) -> dict[str, Any]:
    if not deltas:
        return {"mean": None, "median": None, "ci95": [None, None], "n": 0}
    rng_state = seed
    # portable LCG
    def rand() -> float:
        nonlocal rng_state
        rng_state = (1103515245 * rng_state + 12345) % (2**31)
        return rng_state / (2**31)

    samples = []
    m = len(deltas)
    for _ in range(n):
        acc = 0.0
        for _i in range(m):
            acc += deltas[int(rand() * m) % m]
        samples.append(acc / m)
    samples.sort()
    lo = samples[int(0.025 * (n - 1))]
    hi = samples[int(0.975 * (n - 1))]
    # two-sided sign test
    pos = sum(1 for d in deltas if d > 0)
    neg = sum(1 for d in deltas if d < 0)
    ties = sum(1 for d in deltas if d == 0)
    # exact binomial two-sided p for non-ties
    k = min(pos, neg)
    n_eff = pos + neg
    p = 0.0
    if n_eff > 0:
        # sum C(n,i) / 2^n for i=0..k and mirror
        from math import comb

        cdf = sum(comb(n_eff, i) for i in range(0, k + 1)) / (2**n_eff)
        p = min(1.0, 2.0 * cdf)
    mean = statistics.fmean(deltas)
    median = statistics.median(deltas)
    # effect size: mean / sd of deltas
    sd = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
    effect = (mean / sd) if sd > 1e-12 else None
    ci_includes_zero = lo <= 0.0 <= hi
    return {
        "mean_delta": mean,
        "median_delta": median,
        "ci95": [lo, hi],
        "win": pos,
        "tie": ties,
        "loss": neg,
        "sign_test_p": p,
        "effect_size_mean_over_sd": effect,
        "ci_includes_zero": ci_includes_zero,
        "interpretation": (
            "not_statistically_resolved"
            if ci_includes_zero
            else ("observed_positive_shift" if mean > 0 else "observed_negative_shift")
        ),
        "n_pairs": len(deltas),
        "bootstrap_n": n,
        "bootstrap_seed": seed,
    }


def paired_comparisons(per_run: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_builder: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in per_run:
        by_builder[row["builder"]][row["run_id"]] = row
    reference = "EB4_TRUSTEPISODE"
    baselines = [
        "EB0_FIXED_BIN_300s",
        "EB1_SLIDING_TIME",
        "EB2_SLIDING_ENTITY",
        "EB3_RELATION_NO_ADVANCED_GUARDS",
    ]
    out = []
    ref_map = by_builder[reference]
    for baseline in baselines:
        base_map = by_builder[baseline]
        for metric in PRIMARY_METRICS:
            deltas = []
            for run_id, ref_row in ref_map.items():
                other = base_map[run_id]
                a, b = ref_row[metric], other[metric]
                if a is None or b is None:
                    continue
                # contamination: lower is better → flip sign so positive means EB4 better
                if metric == "contamination":
                    deltas.append(float(b) - float(a))
                elif metric in {"fragmentation", "over_merge"}:
                    deltas.append(float(b) - float(a))
                else:
                    deltas.append(float(a) - float(b))
            stats = paired_bootstrap(deltas, seed=BOOTSTRAP_SEED, n=BOOTSTRAP_N)
            out.append(
                {
                    "comparison": f"{reference} - {baseline}",
                    "baseline": baseline,
                    "metric": metric,
                    "direction": (
                        "EB4_lower_better"
                        if metric in {"contamination", "fragmentation", "over_merge"}
                        else "EB4_higher_better"
                    ),
                    **stats,
                }
            )
    return out


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lab-root",
        type=Path,
        default=ROOT / "external_lab_data_not_included",
        help="Path to the separately distributed sealed lab bundle.",
    )
    parser.add_argument("--contracts", type=Path, default=ROOT / "artifacts" / "contracts")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    parser.add_argument(
        "--families",
        choices=("m1-m6", "m1-m7"),
        default="m1-m7",
        help="Primary amended fair comparison uses M1--M7; M1--M6 is retained for legacy determinism comparisons.",
    )
    args = parser.parse_args()

    if args.families == "m1-m6":
        families = {f"M{i}" for i in range(1, 7)}
        expected = 60
        fam_label = "M1--M6"
        derived_name = "fair_baselines.json"
        raw_subdir = "fair_baselines"
    else:
        families = MALICIOUS
        expected = 70
        fam_label = "M1--M7"
        derived_name = "fair_baselines_m1m7.json"
        raw_subdir = "fair_baselines_m1m7"

    contracts = ContractSet(args.contracts)
    cohort = load_cohort(args.lab_root, families, expected)
    per_run: list[dict[str, Any]] = []
    config_digests: dict[str, str] = {}
    for spec in BUILDERS:
        for row in cohort:
            result = evaluate_run(row, contracts, spec)
            per_run.append(result)
            config_digests[spec.name] = result["config_digest"]

    overall = []
    for spec in BUILDERS:
        rows = [r for r in per_run if r["builder"] == spec.name]
        overall.append(
            {
                "builder": spec.name,
                "role": spec.role,
                "config_digest": config_digests[spec.name],
                "n": len(rows),
                "metrics": {m: summarize([r[m] for r in rows]) for m in PRIMARY_METRICS},
                "mode_attack_only": {
                    m: summarize([r[m] for r in rows if r["mode"] == "attack_only"])
                    for m in PRIMARY_METRICS
                },
                "mode_concurrent_benign": {
                    m: summarize([r[m] for r in rows if r["mode"] == "concurrent_benign"])
                    for m in PRIMARY_METRICS
                },
            }
        )

    paired = paired_comparisons(per_run)
    n_mal = len(cohort)
    payload = {
        "result_type": "trustepisode.fair-sliding-baselines.v1",
        "scope": (
            f"offline re-synthesis on sealed {n_mal} malicious train runs ({fam_label}); "
            "does not overwrite Table-4 primary cells"
        ),
        "cohort": {
            "malicious_runs": n_mal,
            "families": sorted(families),
            "valid": n_mal,
            "failed": 0,
            "undefined": 0,
            "censored": 0,
            "registry_sha256": digest_file(
                args.lab_root / "experiment-data" / "campaign" / "run_registry.csv"
            ),
        },
        "builders": overall,
        "config_digests": config_digests,
        "paired_comparisons": paired,
        "bootstrap": {"seed": BOOTSTRAP_SEED, "n": BOOTSTRAP_N, "unit": "complete_run"},
    }

    raw_dir = args.output_root / "raw" / raw_subdir
    derived = args.output_root / "derived"
    write_json(raw_dir / "per_run.json", per_run)
    write_json(derived / derived_name, payload)
    write_json(
        raw_dir / "execution_record.json",
        {
            "command": f"python scripts/run_fair_baselines.py --families {args.families}",
            "builders": [b.name for b in BUILDERS],
            "config_digests": config_digests,
            "per_run_digest": digest_file(raw_dir / "per_run.json"),
            "derived_digest": digest_file(derived / derived_name),
        },
    )
    print(
        json.dumps(
            {
                "families": args.families,
                "derived": str(derived / derived_name),
                "per_run": len(per_run),
                "builders": len(BUILDERS),
                "paired_rows": len(paired),
                "config_digests": config_digests,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
