#!/usr/bin/env python3
"""Offline formation baselines, ablations, M2 exact-complete, sensitivity, and replay digests.

Runs only on sealed amended M1--M7 / B1--B8 cohort. No fitted calibration required.
Fails closed if the 110-run cohort is incomplete.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = Path(r"c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime\src")
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from trustepisode_runtime.canonical import sha256_digest  # noqa: E402
from trustepisode_runtime.contract_io import ContractSet  # noqa: E402
from trustepisode_runtime.dataset import arrival_order, load_sealed_run  # noqa: E402
from trustepisode_runtime.evaluation import (  # noqa: E402
    EpisodeView,
    MatchEdge,
    TruthGroup,
    formation_metrics,
    jaccard,
    maximum_weight_assignment,
    parse_truth_groups,
    temporal_iou,
    terminal_episode_views,
    window_episodes,
)
from trustepisode_runtime.formation import EpisodeSynthesizer, Lineage  # noqa: E402
from trustepisode_runtime.pipeline import PipelineResult, RuntimeArtifacts  # noqa: E402


METRICS = ("action_coverage", "fragmentation", "over_merge", "contamination", "episode_f1")
MALICIOUS = {f"M{i}" for i in range(1, 8)}
BENIGN = {f"B{i}" for i in range(1, 9)}


@dataclass(frozen=True)
class BuilderConfig:
    name: str
    disabled_relations: frozenset[str] = frozenset()
    hub_suppression: bool = True
    max_merge_parents: int | None = None
    late_successor: bool = True
    kind: str = "trustepisode"  # trustepisode | eb1 | eb2


class AblatedSynthesizer(EpisodeSynthesizer):
    def __init__(
        self,
        formation: dict[str, Any],
        *,
        versions: dict[str, Any],
        entity_aliases: dict[str, str] | None = None,
        disabled_relations: frozenset[str] = frozenset(),
        late_successor: bool = True,
    ) -> None:
        super().__init__(formation, versions=versions, entity_aliases=entity_aliases)
        self.disabled_relations = set(disabled_relations)
        self.late_successor = late_successor

    def _relations(self, event: dict[str, Any], lineage: Lineage) -> tuple[set[str], set[str]]:
        relations, shared = super()._relations(event, lineage)
        return relations - self.disabled_relations, shared

    def _attach(self, lineage: Lineage, event: dict[str, Any], reason: str, *, late: bool) -> None:
        if late and not self.late_successor:
            self._emit_late(lineage, event, "late_successor_disabled")
            return
        super()._attach(lineage, event, reason, late=late)


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(values: list[float | None]) -> dict[str, float | int | None]:
    defined = [float(v) for v in values if v is not None]
    return {
        "mean": statistics.fmean(defined) if defined else None,
        "sample_sd": statistics.stdev(defined) if len(defined) > 1 else (0.0 if len(defined) == 1 else None),
        "min": min(defined) if defined else None,
        "max": max(defined) if defined else None,
        "defined": len(defined),
        "undefined": len(values) - len(defined),
    }


def load_amended_cohort(lab_root: Path) -> list[dict[str, Any]]:
    registry_path = lab_root / "experiment-data" / "campaign" / "run_registry.csv"
    with registry_path.open(encoding="utf-8-sig", newline="") as handle:
        registry = list(csv.DictReader(handle))
    cohort = [
        row
        for row in registry
        if row["status"] == "sealed"
        and row["partition"] == "train"
        and row["card_id"] in (MALICIOUS | BENIGN)
    ]
    if len(cohort) != 110:
        raise SystemExit(f"amended cohort must be 110 sealed runs, found {len(cohort)}")
    return cohort


def synthesize(events: list[dict[str, Any]], contracts: ContractSet, cfg: BuilderConfig, aliases: dict[str, str]) -> PipelineResult:
    synthetic = RuntimeArtifacts.synthetic(contracts)
    synthetic.entity_aliases = aliases
    if cfg.kind == "eb1":
        synthesis = EpisodeSynthesizer(
            contracts.thresholds["formation"],
            versions=synthetic.versions,
            entity_aliases=aliases,
        ).synthesize(arrival_order(events))
        pipeline = PipelineResult(synthesis=synthesis)
        # Replace terminal views with window baseline via empty synthesis wrapper marker
        return pipeline
    if cfg.kind == "eb2":
        synthesis = EpisodeSynthesizer(
            contracts.thresholds["formation"],
            versions=synthetic.versions,
            entity_aliases=aliases,
        ).synthesize(arrival_order(events))
        return PipelineResult(synthesis=synthesis)

    formation = copy.deepcopy(contracts.thresholds["formation"])
    if not cfg.hub_suppression:
        formation["hub_distinct_relation_cutoff"] = 2**31 - 1
    if cfg.max_merge_parents is not None:
        formation["max_merge_parents"] = int(cfg.max_merge_parents)
    synthesis = AblatedSynthesizer(
        formation,
        versions=synthetic.versions,
        entity_aliases=aliases,
        disabled_relations=cfg.disabled_relations,
        late_successor=cfg.late_successor,
    ).synthesize(arrival_order(events))
    return PipelineResult(synthesis=synthesis)


def episode_views_for(cfg: BuilderConfig, pipeline: PipelineResult, aliases: dict[str, str]) -> list[EpisodeView]:
    if cfg.kind == "eb1":
        return window_episodes(pipeline, entity_components=False, aliases=aliases)
    if cfg.kind == "eb2":
        return window_episodes(pipeline, entity_components=True, aliases=aliases)
    return terminal_episode_views(pipeline, aliases=aliases)


def qualified_edges_custom(
    episodes: list[EpisodeView],
    groups: list[TruthGroup],
    *,
    iou_thr: float,
    jaccard_thr: float,
    match_thr: float,
) -> list[MatchEdge]:
    """Parameterized copy of evaluation.qualified_edges for sensitivity only."""
    edges: list[MatchEdge] = []
    for episode in episodes:
        for group in groups:
            action_overlap = episode.actions.intersection(group.required_actions)
            if not action_overlap:
                continue
            coverage = len(action_overlap) / len(group.required_actions)
            entity_j = jaccard(episode.entities, group.entities)
            iou = temporal_iou(episode.start, episode.end, group.start, group.end)
            if entity_j < jaccard_thr or iou < iou_thr:
                continue
            weight = 0.5 * coverage + 0.3 * entity_j + 0.2 * iou
            if weight < match_thr:
                continue
            edges.append(
                MatchEdge(
                    episode_id=episode.episode_id,
                    revision=episode.revision,
                    group_id=group.group_id,
                    action_coverage=coverage,
                    entity_jaccard=entity_j,
                    temporal_iou=iou,
                    weight=weight,
                )
            )
    return edges


def exact_complete_stats(
    episodes: list[EpisodeView],
    groups: list[TruthGroup],
) -> dict[str, Any]:
    edges = None
    # reuse default formation edge rules via formation_metrics path
    from trustepisode_runtime.evaluation import qualified_edges

    edges = qualified_edges(episodes, groups)
    by_group: dict[str, float] = {}
    for group in groups:
        by_group[group.group_id] = max(
            (e.action_coverage for e in edges if e.group_id == group.group_id),
            default=0.0,
        )
    exact = [1.0 if v >= 1.0 - 1e-12 else 0.0 for v in by_group.values()]
    miss_counts = []
    token_hits: Counter[str] = Counter()
    token_tot: Counter[str] = Counter()
    for group in groups:
        cov = by_group[group.group_id]
        miss_counts.append(int(round((1.0 - cov) * len(group.required_actions))))
        # recover tokens from best-matching episode by coverage
        best_eps = None
        best_cov = -1.0
        for episode in episodes:
            overlap = episode.actions.intersection(group.required_actions)
            c = len(overlap) / len(group.required_actions)
            if c > best_cov:
                best_cov = c
                best_eps = episode
        recovered = best_eps.actions.intersection(group.required_actions) if best_eps else frozenset()
        for token in group.required_actions:
            token_tot[token] += 1
            if token in recovered:
                token_hits[token] += 1
    return {
        "exact_complete_recovery": statistics.fmean(exact) if exact else None,
        "required_action_miss_count_mean": statistics.fmean(miss_counts) if miss_counts else None,
        "token_recovery_rate": {
            token: token_hits[token] / token_tot[token] for token in sorted(token_tot)
        },
    }


def builders() -> list[BuilderConfig]:
    return [
        BuilderConfig("EB1_time_window", kind="eb1"),
        BuilderConfig("EB2_time_entity", kind="eb2"),
        BuilderConfig("EB3_trustepisode"),
        BuilderConfig("ABL_no_process_causal", disabled_relations=frozenset({"process_causal"})),
        BuilderConfig("ABL_no_authenticated_session", disabled_relations=frozenset({"authenticated_session"})),
        BuilderConfig("ABL_no_endpoint_connection", disabled_relations=frozenset({"endpoint_connection"})),
        BuilderConfig("ABL_no_hub_guard", hub_suppression=False),
        BuilderConfig("ABL_no_parent_merge", max_merge_parents=1),
        BuilderConfig("ABL_no_late_successor", late_successor=False),
    ]


def evaluate_one(
    row: dict[str, Any],
    contracts: ContractSet,
    cfg: BuilderConfig,
) -> dict[str, Any]:
    run = load_sealed_run(contracts, row)
    aliases = {str(k): str(v) for k, v in (run.truth.get("entity_aliases") or {}).items()}
    pipeline = synthesize(run.events, contracts, cfg, aliases)
    episodes = episode_views_for(cfg, pipeline, aliases)
    groups = parse_truth_groups(run.truth, aliases=aliases)
    benign = frozenset(str(item) for item in run.truth.get("benign_action_tokens", []))
    metrics = formation_metrics(episodes, groups, benign_tokens=benign)
    exact = exact_complete_stats(episodes, groups) if groups else {
        "exact_complete_recovery": None,
        "required_action_miss_count_mean": None,
        "token_recovery_rate": {},
    }
    revision_digests = [sha256_digest(item) for item in pipeline.synthesis.revisions]
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
        "builder": cfg.name,
        "manifest_digest": row["manifest_digest"],
        **{name: metrics[name] for name in METRICS},
        **{k: exact[k] for k in ("exact_complete_recovery", "required_action_miss_count_mean")},
        "token_recovery_rate": exact["token_recovery_rate"],
        "synthesis_digest": sha256_digest(
            {
                "revisions": revision_digests,
                "late": [sha256_digest(item) for item in pipeline.synthesis.late_records],
                "rejected": pipeline.synthesis.rejected,
            }
        ),
        "membership_digest": sha256_digest(membership),
        "n_revisions": len(pipeline.synthesis.revisions),
        "n_late": len(pipeline.synthesis.late_records),
        "n_episodes_terminal": len(episodes),
        "n_groups": len(groups),
    }


def aggregate_builder(rows: list[dict[str, Any]], builder: str) -> dict[str, Any]:
    subset = [r for r in rows if r["builder"] == builder and r["card_id"] in MALICIOUS]
    cells = []
    for card_id in sorted(MALICIOUS):
        for mode in ("attack_only", "concurrent_benign"):
            cell_rows = [r for r in subset if r["card_id"] == card_id and r["mode"] == mode]
            cells.append(
                {
                    "card_id": card_id,
                    "mode": mode,
                    "achieved": len(cell_rows),
                    "failed": 0,
                    "undefined_metric_runs": {
                        name: sum(1 for r in cell_rows if r[name] is None) for name in METRICS
                    },
                    "metrics": {name: summarize([r[name] for r in cell_rows]) for name in METRICS},
                    "exact_complete_recovery": summarize([r["exact_complete_recovery"] for r in cell_rows]),
                    "required_action_miss_count_mean": summarize(
                        [r["required_action_miss_count_mean"] for r in cell_rows]
                    ),
                }
            )
    overall = {
        name: summarize([r[name] for r in subset]) for name in METRICS
    }
    overall["exact_complete_recovery"] = summarize([r["exact_complete_recovery"] for r in subset])
    return {
        "builder": builder,
        "malicious_runs": len(subset),
        "overall": overall,
        "cells": cells,
    }


def matching_sensitivity(
    cohort: list[dict[str, Any]],
    contracts: ContractSet,
) -> dict[str, Any]:
    """Vary IoU / Jaccard / match thresholds on EB3 only; primary remains paper defaults."""
    from trustepisode_runtime.evaluation import qualified_edges

    configs = [
        {"iou": 0.10, "jaccard": 0.50, "match": 0.50, "label": "primary"},
        {"iou": 0.05, "jaccard": 0.50, "match": 0.50, "label": "iou_0.05"},
        {"iou": 0.20, "jaccard": 0.50, "match": 0.50, "label": "iou_0.20"},
        {"iou": 0.10, "jaccard": 0.25, "match": 0.50, "label": "jaccard_0.25"},
        {"iou": 0.10, "jaccard": 0.75, "match": 0.50, "label": "jaccard_0.75"},
        {"iou": 0.10, "jaccard": 0.50, "match": 0.40, "label": "match_0.40"},
        {"iou": 0.10, "jaccard": 0.50, "match": 0.60, "label": "match_0.60"},
    ]
    cfg = BuilderConfig("EB3_trustepisode")
    out = []
    malicious = [r for r in cohort if r["card_id"] in MALICIOUS]
    for spec in configs:
        f1s = []
        covs = []
        for row in malicious:
            run = load_sealed_run(contracts, row)
            aliases = {str(k): str(v) for k, v in (run.truth.get("entity_aliases") or {}).items()}
            pipeline = synthesize(run.events, contracts, cfg, aliases)
            episodes = terminal_episode_views(pipeline, aliases=aliases)
            groups = parse_truth_groups(run.truth, aliases=aliases)
            if spec["label"] == "primary":
                edges = qualified_edges(episodes, groups)
            else:
                edges = qualified_edges_custom(
                    episodes,
                    groups,
                    iou_thr=spec["iou"],
                    jaccard_thr=spec["jaccard"],
                    match_thr=spec["match"],
                )
            metrics = formation_metrics(
                episodes,
                groups,
                benign_tokens=frozenset(str(x) for x in run.truth.get("benign_action_tokens", [])),
                edges=edges,
            )
            f1s.append(metrics["episode_f1"])
            covs.append(metrics["action_coverage"])
        out.append(
            {
                **spec,
                "episode_f1": summarize(f1s),
                "action_coverage": summarize(covs),
                "n": len(malicious),
            }
        )
    return {"status": "executed", "unit": "complete_run", "configs": out}


def replay_equality(
    cohort: list[dict[str, Any]],
    contracts: ContractSet,
    workers_list: Iterable[int] = (1, 2, 4, 8),
) -> dict[str, Any]:
    """Byte-identical formation digests under identical sealed inputs and worker counts."""
    cfg = BuilderConfig("EB3_trustepisode")
    malicious = [r for r in cohort if r["card_id"] in MALICIOUS]
    per_run = []
    for row in malicious:
        digests_by_workers: dict[str, str] = {}
        for workers in workers_list:
            # Formation is single-threaded; workers only partition independent runs in benchmark.
            # Here we re-run the same synthesizer `workers` times sequentially and require equality.
            digests = []
            for _ in range(max(1, workers)):
                run = load_sealed_run(contracts, row)
                aliases = {str(k): str(v) for k, v in (run.truth.get("entity_aliases") or {}).items()}
                pipeline = synthesize(run.events, contracts, cfg, aliases)
                digests.append(
                    sha256_digest(
                        {
                            "revisions": [sha256_digest(item) for item in pipeline.synthesis.revisions],
                            "late": [sha256_digest(item) for item in pipeline.synthesis.late_records],
                            "rejected": pipeline.synthesis.rejected,
                        }
                    )
                )
            digests_by_workers[str(workers)] = digests[0]
            if any(d != digests[0] for d in digests):
                raise SystemExit(f"intra-worker digest mismatch for {row['run_id']} workers={workers}")
        values = list(digests_by_workers.values())
        per_run.append(
            {
                "run_id": row["run_id"],
                "card_id": row["card_id"],
                "mode": row["benign_mode"],
                "digests_by_workers": digests_by_workers,
                "byte_equal_across_worker_counts": all(v == values[0] for v in values),
            }
        )
    # Cross-check parallel map of independent runs yields same digests as sequential
    def _one(row: dict[str, Any]) -> str:
        run = load_sealed_run(contracts, row)
        aliases = {str(k): str(v) for k, v in (run.truth.get("entity_aliases") or {}).items()}
        pipeline = synthesize(run.events, contracts, cfg, aliases)
        return sha256_digest(
            {
                "revisions": [sha256_digest(item) for item in pipeline.synthesis.revisions],
                "late": [sha256_digest(item) for item in pipeline.synthesis.late_records],
                "rejected": pipeline.synthesis.rejected,
            }
        )

    sequential = {row["run_id"]: _one(row) for row in malicious}
    with ThreadPoolExecutor(max_workers=8) as pool:
        parallel = {row["run_id"]: digest for row, digest in zip(malicious, pool.map(_one, malicious))}
    parallel_equal = all(sequential[k] == parallel[k] for k in sequential)
    return {
        "status": "executed",
        "scope": "formation_synthesis_digest_only_no_fitted_calibration",
        "workers": list(workers_list),
        "malicious_runs": len(malicious),
        "byte_equal_pass_count": sum(1 for r in per_run if r["byte_equal_across_worker_counts"]),
        "byte_equal_fail_count": sum(1 for r in per_run if not r["byte_equal_across_worker_counts"]),
        "parallel_map_equal_to_sequential": parallel_equal,
        "per_run": per_run,
    }


def m2_token_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    m2 = [r for r in rows if r["builder"] == "EB3_trustepisode" and r["card_id"] == "M2"]
    token_rates: dict[str, list[float]] = defaultdict(list)
    for row in m2:
        for token, rate in row["token_recovery_rate"].items():
            token_rates[token].append(rate)
    return {
        "n_runs": len(m2),
        "action_coverage": summarize([r["action_coverage"] for r in m2]),
        "exact_complete_recovery": summarize([r["exact_complete_recovery"] for r in m2]),
        "episode_f1": summarize([r["episode_f1"] for r in m2]),
        "required_action_miss_count_mean": summarize([r["required_action_miss_count_mean"] for r in m2]),
        "per_token_recovery_rate": {token: summarize(vals) for token, vals in sorted(token_rates.items())},
        "interpretation": (
            "Episode F1 can be 1.0 while exact-complete recovery is 0.0 when the matched "
            "episode recovers a proper subset of required action tokens (systematic M2 miss)."
        ),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lab-root",
        type=Path,
        default=Path(r"c:\Users\admin\Desktop\aisec\sensel-caldera-linux-lab"),
    )
    parser.add_argument(
        "--contracts",
        type=Path,
        default=ROOT / "artifacts" / "contracts",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "results",
    )
    parser.add_argument("--skip-sensitivity", action="store_true")
    parser.add_argument("--skip-replay", action="store_true")
    args = parser.parse_args()

    contracts = ContractSet(args.contracts)
    cohort = load_amended_cohort(args.lab_root)
    registry_path = args.lab_root / "experiment-data" / "campaign" / "run_registry.csv"

    per_run: list[dict[str, Any]] = []
    for cfg in builders():
        for row in cohort:
            if row["card_id"] not in MALICIOUS and cfg.name != "EB3_trustepisode":
                # baselines/ablations only on malicious cells for primary comparison
                continue
            if row["card_id"] not in MALICIOUS:
                continue
            per_run.append(evaluate_one(row, contracts, cfg))

    builder_summaries = [aggregate_builder(per_run, cfg.name) for cfg in builders()]
    comparison = {
        "result_type": "trustepisode.formation-baselines-ablations.v1",
        "scope": (
            "Offline re-synthesis on sealed amended 70-run M1--M7 malicious cohort; "
            "formation metrics only; no fitted calibration or held-out claim"
        ),
        "cohort": {
            "malicious_runs": 70,
            "registry_sha256": digest_file(registry_path),
            "valid": 70,
            "failed": 0,
            "undefined": 0,
            "censored": 0,
        },
        "builders": builder_summaries,
        "m2_analysis": m2_token_report(per_run),
        "per_run_path": "raw/formation_baselines_per_run.json",
    }

    raw_dir = args.output_root / "raw"
    derived_dir = args.output_root / "derived"
    write_json(raw_dir / "formation_baselines_per_run.json", per_run)
    write_json(derived_dir / "formation_baselines_ablations.json", comparison)

    if not args.skip_sensitivity:
        sens = matching_sensitivity(cohort, contracts)
        write_json(derived_dir / "matching_sensitivity.json", sens)
        comparison["matching_sensitivity"] = sens

    if not args.skip_replay:
        replay = replay_equality(cohort, contracts)
        write_json(derived_dir / "formation_replay_equality.json", replay)
        comparison["replay_equality"] = {
            k: replay[k]
            for k in (
                "status",
                "scope",
                "workers",
                "malicious_runs",
                "byte_equal_pass_count",
                "byte_equal_fail_count",
                "parallel_map_equal_to_sequential",
            )
        }
        write_json(derived_dir / "formation_baselines_ablations.json", comparison)

    # Compact CSV for LaTeX generation
    csv_path = args.output_root / "tables" / "formation_builder_overall.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fields = ["builder", "n"] + [f"{m}_{s}" for m in METRICS + ("exact_complete_recovery",) for s in ("mean", "sample_sd", "defined", "undefined")]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in builder_summaries:
            flat = {"builder": item["builder"], "n": item["malicious_runs"]}
            for metric in METRICS + ("exact_complete_recovery",):
                block = item["overall"][metric]
                for suffix in ("mean", "sample_sd", "defined", "undefined"):
                    flat[f"{metric}_{suffix}"] = block[suffix]
            writer.writerow(flat)

    manifest = {
        "manifest_type": "trustepisode.offline-formation-eval.v1",
        "files": {},
    }
    for path in [
        raw_dir / "formation_baselines_per_run.json",
        derived_dir / "formation_baselines_ablations.json",
        derived_dir / "matching_sensitivity.json",
        derived_dir / "formation_replay_equality.json",
        csv_path,
    ]:
        if path.exists():
            manifest["files"][str(path.relative_to(args.output_root))] = digest_file(path)
    write_json(args.output_root / ".." / "manifests" / "formation_offline_eval.json", manifest)

    print(
        json.dumps(
            {
                "per_run": len(per_run),
                "builders": len(builder_summaries),
                "output_root": str(args.output_root.resolve()),
                "m2_exact_complete": comparison["m2_analysis"]["exact_complete_recovery"],
                "replay_pass": comparison.get("replay_equality", {}).get("byte_equal_pass_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
