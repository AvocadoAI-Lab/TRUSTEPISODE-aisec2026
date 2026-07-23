from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
from scipy.optimize import linear_sum_assignment

from .canonical import parse_timestamp, sha256_digest, utf8_key
from .pipeline import PipelineResult, RuntimeArtifacts
from .scoring import sigmoid


@dataclass(frozen=True)
class EpisodeView:
    episode_id: str
    revision: int
    start: Any
    end: Any
    entities: frozenset[str]
    actions: frozenset[str]
    event_ids: tuple[str, ...]


@dataclass(frozen=True)
class TruthGroup:
    group_id: str
    start: Any
    end: Any
    entities: frozenset[str]
    required_actions: frozenset[str]


@dataclass(frozen=True)
class MatchEdge:
    episode_id: str
    revision: int
    group_id: str
    action_coverage: float
    entity_jaccard: float
    temporal_iou: float
    weight: float


def evaluate_run(
    run_id: str,
    pipeline: PipelineResult,
    truth: dict[str, Any],
    *,
    budget_fraction: float = 0.10,
    precision_k: int = 10,
    ablation_pipeline: PipelineResult | None = None,
    artifacts: RuntimeArtifacts | None = None,
) -> dict[str, Any]:
    aliases = {str(key): str(value) for key, value in (truth.get("entity_aliases") or {}).items()}
    groups = parse_truth_groups(truth, aliases=aliases)
    benign_tokens = frozenset(str(item) for item in truth.get("benign_action_tokens", []))
    conflict = bool(truth.get("truth_conflict", False))
    episodes = terminal_episode_views(pipeline, aliases=aliases)
    edges = qualified_edges(episodes, groups)
    assignments = maximum_weight_assignment(episodes, groups, edges)
    labels = {
        (episode.episode_id, episode.revision): label_episode(
            episode,
            edges,
            groups,
            benign_tokens,
            truth_conflict=conflict,
        )
        for episode in episodes
    }
    outcomes = {
        (item["episode_id"], item["revision"]): item for item in pipeline.outcomes
    }
    terminal_outcomes = [
        outcomes[(episode.episode_id, episode.revision)]
        for episode in episodes
        if (episode.episode_id, episode.revision) in outcomes
    ]
    outcome_labels = {
        (item["episode_id"], item["revision"]): labels[
            (item["episode_id"], item["revision"])
        ]
        for item in terminal_outcomes
    }
    return {
        "run_id": run_id,
        "truth_digest": sha256_digest(truth),
        "RT1": population_row(terminal_outcomes, outcome_labels),
        "RT2": {
            "EB1": formation_metrics(
                window_episodes(pipeline, entity_components=False, aliases=aliases),
                groups,
                benign_tokens=benign_tokens,
            ),
            "EB2": formation_metrics(
                window_episodes(pipeline, entity_components=True, aliases=aliases),
                groups,
                benign_tokens=benign_tokens,
            ),
            "EB3": formation_metrics(
                episodes,
                groups,
                benign_tokens=benign_tokens,
                edges=edges,
                assignments=assignments,
            ),
            "EB3-H": (
                formation_metrics(
                    terminal_episode_views(ablation_pipeline, aliases=aliases),
                    groups,
                    benign_tokens=benign_tokens,
                )
                if ablation_pipeline is not None
                else "N/A_not_executed"
            ),
        },
        "RT3a": ranking_rows(
            terminal_outcomes,
            outcome_labels,
            episodes,
            pipeline,
            artifacts=artifacts,
            budget_fraction=budget_fraction,
            precision_k=precision_k,
        ),
        "RT3b": calibration_rows(terminal_outcomes, outcome_labels),
        "RT4": "N/A_requires_paired_replay_bundle",
        "RT5": "N/A_requires_physical_outage_bundle",
        "RT6": "N/A_requires_cost_benchmark_bundle",
        "RT7": error_taxonomy(pipeline, outcome_labels),
    }


def evaluation_rows(
    run_id: str,
    pipeline: PipelineResult,
    truth: dict[str, Any],
    artifacts: RuntimeArtifacts,
) -> list[dict[str, Any]]:
    aliases = {
        str(key): str(value) for key, value in (truth.get("entity_aliases") or {}).items()
    }
    groups = parse_truth_groups(truth, aliases=aliases)
    benign_tokens = frozenset(str(item) for item in truth.get("benign_action_tokens", []))
    episodes = terminal_episode_views(pipeline, aliases=aliases)
    edges = qualified_edges(episodes, groups)
    conflict = bool(truth.get("truth_conflict", False))
    outcome_by_key = {
        (item["episode_id"], item["revision"]): item for item in pipeline.outcomes
    }
    feature_by_key = {
        (item["episode_id"], item["revision"]): item for item in pipeline.features
    }
    rows = []
    for episode in episodes:
        key = (episode.episode_id, episode.revision)
        label = label_episode(
            episode,
            edges,
            groups,
            benign_tokens,
            truth_conflict=conflict,
        )
        outcome = outcome_by_key.get(key)
        feature = feature_by_key.get(key)
        native_values = [
            finite_or_none(
                (pipeline.synthesis.event_by_id[event_id].get("attributes") or {}).get(
                    "signature_severity"
                )
            )
            for event_id in episode.event_ids
        ]
        native = [item for item in native_values if item is not None]
        is_audit = outcome is not None and outcome["object_type"] == "AuditRecord"
        eligible = bool(is_audit and outcome.get("decision_eligible"))
        z = float(outcome["z"]) if is_audit else None
        rows.append(
            {
                "run_id": run_id,
                "episode_id": episode.episode_id,
                "revision": episode.revision,
                "label": label["label"],
                "truth_group_id": label["group_id"],
                "action_coverage": label["action_coverage"],
                "contamination": label["contamination"],
                "outcome_type": outcome["object_type"] if outcome else "missing",
                "failure_code": outcome.get("failure_code") if outcome else "missing",
                "decision_eligible": eligible,
                "kappa": outcome.get("kappa") if is_audit else None,
                "eligibility_reason": outcome.get("eligibility_reason") if is_audit else None,
                "SB1": max(native) if native else None,
                "SB2": (
                    artifacts.d_only_model.score(float(feature["D"]), 0)
                    if eligible and feature is not None and artifacts.d_only_model is not None
                    else None
                ),
                "SB3": z if eligible else None,
                "SB4": sigmoid(z) if eligible and z is not None else None,
                "SB5": float(outcome["P"]) if eligible and outcome.get("P") is not None else None,
                "SB6": (
                    float(outcome["P"])
                    if eligible
                    and outcome.get("kappa") == "supported_group"
                    and outcome.get("P") is not None
                    else None
                ),
            }
        )
    return rows


def parse_truth_groups(
    truth: dict[str, Any], *, aliases: dict[str, str] | None = None
) -> list[TruthGroup]:
    aliases = aliases or {}
    groups: list[TruthGroup] = []
    for raw in truth.get("groups", []):
        required = frozenset(str(item) for item in raw["required_action_tokens"])
        if not required:
            raise ValueError(f"truth group {raw.get('group_id')} has no required actions")
        groups.append(
            TruthGroup(
                group_id=str(raw["group_id"]),
                start=parse_timestamp(raw["start"]),
                end=parse_timestamp(raw["end"]),
                entities=frozenset(aliases.get(str(item), str(item)) for item in raw["entities"]),
                required_actions=required,
            )
        )
    return sorted(groups, key=lambda item: utf8_key(item.group_id))


def terminal_episode_views(
    pipeline: PipelineResult, *, aliases: dict[str, str] | None = None
) -> list[EpisodeView]:
    merged_parents = {
        parent
        for revision in pipeline.synthesis.revisions
        for parent in revision["parent_episode_ids"]
    }
    first_finalized: dict[str, dict[str, Any]] = {}
    for revision in pipeline.synthesis.revisions:
        if revision["state"] != "finalized" or revision["episode_id"] in merged_parents:
            continue
        first_finalized.setdefault(revision["episode_id"], revision)
    return [
        episode_view(revision, pipeline.synthesis.event_by_id, aliases=aliases)
        for revision in sorted(
            first_finalized.values(),
            key=lambda item: utf8_key(item["episode_id"]),
        )
    ]


def episode_view(
    revision: dict[str, Any],
    event_by_id: dict[str, dict[str, Any]],
    *,
    aliases: dict[str, str] | None = None,
) -> EpisodeView:
    aliases = aliases or {}
    events = [event_by_id[event_id] for event_id in revision["ordered_event_ids"]]
    actions: dict[str, set[str]] = {}
    for event in events:
        tokens = {event["action"]}
        family = (event.get("attributes") or {}).get("command_family")
        if family:
            tokens.add(f"command_family:{family}")
        actions.setdefault(event["dependency_group"], set()).update(tokens)
    return EpisodeView(
        episode_id=revision["episode_id"],
        revision=revision["revision"],
        start=parse_timestamp(revision["event_time_start"]),
        end=parse_timestamp(revision["event_time_end"]),
        entities=frozenset(
            aliases.get(entity, entity)
            for event in events
            for entity in (event["subject"], event["object"])
        ),
        actions=frozenset(token for values in actions.values() for token in values),
        event_ids=tuple(revision["ordered_event_ids"]),
    )


def qualified_edges(
    episodes: list[EpisodeView], groups: list[TruthGroup]
) -> list[MatchEdge]:
    edges: list[MatchEdge] = []
    for episode in episodes:
        for group in groups:
            action_overlap = episode.actions.intersection(group.required_actions)
            if not action_overlap:
                continue
            coverage = len(action_overlap) / len(group.required_actions)
            entity = jaccard(episode.entities, group.entities)
            temporal = temporal_iou(episode.start, episode.end, group.start, group.end)
            if entity < 0.50 or temporal < 0.10:
                continue
            weight = 0.5 * coverage + 0.3 * entity + 0.2 * temporal
            if weight >= 0.50:
                edges.append(
                    MatchEdge(
                        episode.episode_id,
                        episode.revision,
                        group.group_id,
                        coverage,
                        entity,
                        temporal,
                        weight,
                    )
                )
    return edges


def maximum_weight_assignment(
    episodes: list[EpisodeView], groups: list[TruthGroup], edges: list[MatchEdge]
) -> list[MatchEdge]:
    if not episodes or not groups:
        return []
    episode_index = {(item.episode_id, item.revision): index for index, item in enumerate(episodes)}
    group_index = {item.group_id: index for index, item in enumerate(groups)}
    matrix = np.full((len(episodes), len(groups)), -1e9, dtype=np.float64)
    edge_map: dict[tuple[int, int], MatchEdge] = {}
    for edge in edges:
        row = episode_index[(edge.episode_id, edge.revision)]
        column = group_index[edge.group_id]
        tie = 1e-12 * (
            edge.entity_jaccard
            - abs((episodes[row].start - groups[column].start).total_seconds()) / 1e9
        )
        matrix[row, column] = edge.weight + tie
        edge_map[(row, column)] = edge
    rows, columns = linear_sum_assignment(matrix, maximize=True)
    return [
        edge_map[(row, column)]
        for row, column in zip(rows, columns, strict=True)
        if (row, column) in edge_map
    ]


def formation_metrics(
    episodes: list[EpisodeView],
    groups: list[TruthGroup],
    *,
    benign_tokens: frozenset[str] = frozenset(),
    edges: list[MatchEdge] | None = None,
    assignments: list[MatchEdge] | None = None,
) -> dict[str, float | int | None]:
    edges = qualified_edges(episodes, groups) if edges is None else edges
    assignments = maximum_weight_assignment(episodes, groups, edges) if assignments is None else assignments
    group_degree = {
        group.group_id: sum(edge.group_id == group.group_id for edge in edges) for group in groups
    }
    episode_degree = {
        (episode.episode_id, episode.revision): sum(
            edge.episode_id == episode.episode_id and edge.revision == episode.revision
            for edge in edges
        )
        for episode in episodes
    }
    action_coverage = mean_or_none(
        [
            max((edge.action_coverage for edge in edges if edge.group_id == group.group_id), default=0.0)
            for group in groups
        ]
    )
    fragmentation = mean_or_none([max(0, group_degree[group.group_id] - 1) for group in groups])
    over_merge = mean_or_none(
        [int(episode_degree[(episode.episode_id, episode.revision)] > 1) for episode in episodes]
    )
    precision = len(assignments) / len(episodes) if episodes else None
    recall = len(assignments) / len(groups) if groups else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else 0.0
        if precision is not None and recall is not None
        else None
    )
    contamination_values = []
    for episode in episodes:
        selected = sorted(
            (
                edge
                for edge in edges
                if edge.episode_id == episode.episode_id and edge.revision == episode.revision
            ),
            key=lambda item: (-item.action_coverage, -item.weight, utf8_key(item.group_id)),
        )
        if not selected:
            continue
        group = next(item for item in groups if item.group_id == selected[0].group_id)
        malicious = episode.actions.intersection(group.required_actions)
        benign = episode.actions.intersection(benign_tokens)
        denominator = len(malicious.union(benign))
        if denominator:
            contamination_values.append(len(benign) / denominator)
    return {
        "action_coverage": action_coverage,
        "fragmentation": fragmentation,
        "over_merge": over_merge,
        "contamination": mean_or_none(contamination_values),
        "episode_f1": f1,
        "qualified_edge_count": len(edges),
        "assigned_edge_count": len(assignments),
    }


def label_episode(
    episode: EpisodeView,
    edges: list[MatchEdge],
    groups: list[TruthGroup],
    benign_tokens: frozenset[str],
    *,
    truth_conflict: bool,
) -> dict[str, Any]:
    incident = sorted(
        (
            edge
            for edge in edges
            if edge.episode_id == episode.episode_id and edge.revision == episode.revision
        ),
        key=lambda item: (-item.action_coverage, -item.weight, utf8_key(item.group_id)),
    )
    if truth_conflict:
        return {"label": "ambiguous", "group_id": None, "action_coverage": 0.0, "contamination": None}
    if not incident:
        label = "negative" if episode.actions.intersection(benign_tokens) else "ambiguous"
        return {"label": label, "group_id": None, "action_coverage": 0.0, "contamination": None}
    selected = incident[0]
    group = next(item for item in groups if item.group_id == selected.group_id)
    benign = episode.actions.intersection(benign_tokens)
    malicious = episode.actions.intersection(group.required_actions)
    denominator = len(malicious.union(benign))
    contamination = len(benign) / denominator if denominator else None
    if selected.action_coverage >= 0.50 and contamination is not None and contamination >= 0.25:
        label = "mixed"
    elif selected.action_coverage >= 0.50 and contamination is not None and contamination < 0.25:
        label = "positive"
    else:
        label = "ambiguous"
    return {
        "label": label,
        "group_id": selected.group_id,
        "action_coverage": selected.action_coverage,
        "contamination": contamination,
    }


def population_row(
    outcomes: list[dict[str, Any]], labels: dict[tuple[str, int], dict[str, Any]]
) -> dict[str, Any]:
    all_count = len(outcomes)
    scored = [
        item
        for item in outcomes
        if item["object_type"] == "AuditRecord"
        and item["decision_eligible"]
        and isinstance(item["P"], (int, float))
    ]
    binary = [
        item
        for item in scored
        if labels[(item["episode_id"], item["revision"])]["label"] in {"positive", "negative"}
    ]
    row: dict[str, Any] = {
        "runs": 1,
        "terminal_episodes": all_count,
        "C_dec_all": all_count,
        "C_dec_score": len(scored),
        "C_dec_binary": len(binary),
        "supported_global_count": sum(item.get("kappa") == "supported_global" for item in outcomes),
        "supported_group_count": sum(item.get("kappa") == "supported_group" for item in outcomes),
        "out_of_support_audit_count": sum(item.get("kappa") == "out_of_support" for item in outcomes),
        "assembly_failure_count": sum(item["object_type"] == "AssemblyFailureRecord" for item in outcomes),
        "score_coverage": len(scored) / all_count if all_count else None,
        "binary_coverage": len(binary) / all_count if all_count else None,
        "out_of_support_rate_over_all": sum(item.get("kappa") == "out_of_support" for item in outcomes) / all_count if all_count else None,
        "failure_rate_over_all": sum(item["object_type"] == "AssemblyFailureRecord" for item in outcomes) / all_count if all_count else None,
    }
    for label in ("positive", "negative", "mixed", "ambiguous"):
        row[f"outcome_{label}"] = sum(
            labels[(item["episode_id"], item["revision"])]["label"] == label for item in outcomes
        )
        row[f"failure_{label}"] = sum(
            item["object_type"] == "AssemblyFailureRecord"
            and labels[(item["episode_id"], item["revision"])]["label"] == label
            for item in outcomes
        )
    row["class_conditional_failure_rates"] = {
        label: (
            row[f"failure_{label}"] / row[f"outcome_{label}"]
            if row[f"outcome_{label}"]
            else None
        )
        for label in ("positive", "negative", "mixed", "ambiguous")
    }
    positives = sum(
        labels[(item["episode_id"], item["revision"])]["label"] == "positive" for item in binary
    )
    row["binary_prevalence"] = positives / len(binary) if binary else None
    return row


def ranking_rows(
    outcomes: list[dict[str, Any]],
    labels: dict[tuple[str, int], dict[str, Any]],
    episodes: list[EpisodeView],
    pipeline: PipelineResult,
    *,
    artifacts: RuntimeArtifacts | None,
    budget_fraction: float,
    precision_k: int,
) -> dict[str, Any]:
    by_key = {(item["episode_id"], item["revision"]): item for item in outcomes}
    binary_keys = [
        key
        for key, item in by_key.items()
        if item["object_type"] == "AuditRecord"
        and item["decision_eligible"]
        and labels[key]["label"] in {"positive", "negative"}
    ]
    sb3 = [(key, float(by_key[key]["z"])) for key in binary_keys]
    native_by_event = {
        event_id: finite_or_none((event.get("attributes") or {}).get("signature_severity"))
        for event_id, event in pipeline.synthesis.event_by_id.items()
    }
    episode_by_key = {(item.episode_id, item.revision): item for item in episodes}
    sb1 = []
    for key in binary_keys:
        values = [native_by_event[event_id] for event_id in episode_by_key[key].event_ids]
        finite = [item for item in values if item is not None]
        if finite:
            sb1.append((key, max(finite)))
    feature_by_key = {
        (item["episode_id"], item["revision"]): item for item in pipeline.features
    }
    sb2 = []
    if artifacts is not None and artifacts.d_only_model is not None:
        sb2 = [
            (
                key,
                artifacts.d_only_model.score(float(feature_by_key[key]["D"]), 0),
            )
            for key in binary_keys
            if key in feature_by_key
        ]
    return {
        "SB1": rank_metrics(
            sb1, labels, len(outcomes), len(binary_keys), budget_fraction, precision_k
        ),
        "SB2": (
            rank_metrics(
                sb2,
                labels,
                len(outcomes),
                len(binary_keys),
                budget_fraction,
                precision_k,
            )
            if artifacts is not None and artifacts.d_only_model is not None
            else "N/A_missing_frozen_artifact"
        ),
        "SB3": rank_metrics(
            sb3, labels, len(outcomes), len(binary_keys), budget_fraction, precision_k
        ),
    }


def rank_metrics(
    scores: list[tuple[tuple[str, int], float]],
    labels: dict[tuple[str, int], dict[str, Any]],
    all_count: int,
    binary_total: int,
    budget_fraction: float,
    precision_k: int,
) -> dict[str, Any]:
    ordered = sorted(scores, key=lambda item: (-item[1], utf8_key(item[0][0]), item[0][1]))
    y = [int(labels[key]["label"] == "positive") for key, _ in ordered]
    values = [score for _, score in ordered]
    score_count = len(y)
    budget = max(1, math.ceil(budget_fraction * score_count)) if score_count else 0
    positives = sum(y)
    return {
        "C_dec_all": all_count,
        "C_dec_score": score_count,
        "C_dec_binary": binary_total,
        "score_coverage": score_count / all_count if all_count else None,
        "binary_coverage": binary_total / all_count if all_count else None,
        "AUPRC": average_precision(y),
        "recall_at_budget": sum(y[:budget]) / positives if positives else None,
        "AUROC": auroc(y, values),
        "precision_at_k": sum(y[: min(precision_k, score_count)]) / min(precision_k, score_count) if score_count else None,
    }


def calibration_rows(
    outcomes: list[dict[str, Any]], labels: dict[tuple[str, int], dict[str, Any]]
) -> dict[str, Any]:
    eligible = [
        item
        for item in outcomes
        if item["object_type"] == "AuditRecord"
        and item["decision_eligible"]
        and labels[(item["episode_id"], item["revision"])]["label"] in {"positive", "negative"}
    ]
    y = [
        int(labels[(item["episode_id"], item["revision"])]["label"] == "positive")
        for item in eligible
    ]
    return {
        "SB4": calibration_metrics(outcomes, y, [sigmoid(float(item["z"])) for item in eligible]),
        "SB5": calibration_metrics(outcomes, y, [float(item["P"]) for item in eligible]),
        "SB6": (
            calibration_metrics(
                outcomes,
                [value for value, item in zip(y, eligible, strict=True) if item["kappa"] == "supported_group"],
                [float(item["P"]) for item in eligible if item["kappa"] == "supported_group"],
            )
            if any(item["kappa"] == "supported_group" for item in eligible)
            else "N/A"
        ),
    }


def calibration_metrics(
    outcomes: list[dict[str, Any]], y: list[int], probabilities: list[float]
) -> dict[str, Any]:
    count = len(outcomes)
    failures = sum(item["object_type"] == "AssemblyFailureRecord" for item in outcomes)
    oos = sum(item.get("kappa") == "out_of_support" for item in outcomes)
    global_count = sum(item.get("kappa") == "supported_global" for item in outcomes)
    group_count = sum(item.get("kappa") == "supported_group" for item in outcomes)
    return {
        "C_dec_all": count,
        "C_dec_score": len(probabilities),
        "C_dec_binary": len(probabilities),
        "Brier": mean_or_none([(probability - label) ** 2 for probability, label in zip(probabilities, y, strict=True)]),
        "NLL": mean_or_none([
            -(label * math.log(max(probability, 1e-15)) + (1 - label) * math.log(max(1 - probability, 1e-15)))
            for probability, label in zip(probabilities, y, strict=True)
        ]),
        "reliability_bins": reliability_bins(y, probabilities),
        "score_coverage": len(probabilities) / count if count else None,
        "binary_coverage": len(probabilities) / count if count else None,
        "supported_global_rate_over_all": global_count / count if count else None,
        "supported_group_rate_over_all": group_count / count if count else None,
        "out_of_support_rate_over_all": oos / count if count else None,
        "failure_rate_over_all": failures / count if count else None,
    }


def reliability_bins(y: list[int], probabilities: list[float]) -> list[dict[str, Any]]:
    bins = []
    for index in range(10):
        lower = index / 10
        upper = (index + 1) / 10
        selected = [
            (label, probability)
            for label, probability in zip(y, probabilities, strict=True)
            if lower <= probability < upper or index == 9 and probability == 1.0
        ]
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(selected),
                "mean_probability": mean_or_none([item[1] for item in selected]),
                "positive_fraction": mean_or_none([item[0] for item in selected]),
            }
        )
    return bins


def error_taxonomy(
    pipeline: PipelineResult, labels: dict[tuple[str, int], dict[str, Any]]
) -> dict[str, Any]:
    terminal_keys = set(labels)
    terminal_outcomes = [
        item
        for item in pipeline.outcomes
        if (item["episode_id"], item["revision"]) in terminal_keys
    ]
    failures = [
        item
        for item in terminal_outcomes
        if item["object_type"] == "AssemblyFailureRecord"
    ]
    return {
        "assembly_failure": len(failures),
        "collector_outage": sum(
            item.get("health_snapshot", {}).get(family) == "down"
            for item in terminal_outcomes
            for family in ("EDR", "NDR")
        ),
        "parser_failure": sum(
            "parser_invalid" in item.get("resolved_detector_state", {}).values()
            for item in terminal_outcomes
        ),
        "unsupported_calibration": sum(
            item.get("eligibility_reason") == "calibration_out_of_support"
            for item in terminal_outcomes
        ),
        "label_ambiguity": sum(item["label"] == "ambiguous" for item in labels.values()),
        "closed_index_expired": sum(item["reason"] == "closed_index_expired" for item in pipeline.synthesis.rejected),
    }


def window_episodes(
    pipeline: PipelineResult,
    *,
    entity_components: bool,
    aliases: dict[str, str] | None = None,
) -> list[EpisodeView]:
    events = sorted(
        pipeline.synthesis.event_by_id.values(),
        key=lambda item: (parse_timestamp(item["event_time"]), utf8_key(item["event_id"])),
    )
    if not events:
        return []
    anchor = parse_timestamp(events[0]["event_time"])
    bins: dict[int, list[dict[str, Any]]] = {}
    for event in events:
        index = math.floor((parse_timestamp(event["event_time"]) - anchor).total_seconds() / 300)
        bins.setdefault(index, []).append(event)
    groups: list[list[dict[str, Any]]] = []
    for index in sorted(bins):
        members = bins[index]
        if not entity_components:
            groups.append(members)
            continue
        groups.extend(entity_components_for_bin(members))
    output = []
    for index, members in enumerate(groups):
        pseudo = {
            "episode_id": f"baseline:{'EB2' if entity_components else 'EB1'}:{index}",
            "revision": 0,
            "ordered_event_ids": [item["event_id"] for item in members],
            "event_time_start": min(item["event_time"] for item in members),
            "event_time_end": max(item["event_time"] for item in members),
        }
        output.append(episode_view(pseudo, pipeline.synthesis.event_by_id, aliases=aliases))
    return output


def entity_components_for_bin(events: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    parent = list(range(len(events)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[max(root_left, root_right)] = min(root_left, root_right)

    entities = [{item["subject"], item["object"]} for item in events]
    for left in range(len(events)):
        for right in range(left + 1, len(events)):
            if entities[left].intersection(entities[right]):
                union(left, right)
    components: dict[int, list[dict[str, Any]]] = {}
    for index, event in enumerate(events):
        components.setdefault(find(index), []).append(event)
    return [components[key] for key in sorted(components)]


def temporal_iou(start_a, end_a, start_b, end_b) -> float:
    intersection = max(0.0, (min(end_a, end_b) - max(start_a, start_b)).total_seconds())
    union = max(0.0, (max(end_a, end_b) - min(start_a, start_b)).total_seconds())
    if union == 0:
        return 1.0 if start_a == start_b else 0.0
    return intersection / union


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    union = left.union(right)
    return len(left.intersection(right)) / len(union) if union else 0.0


def mean_or_none(values: Iterable[float | int]) -> float | None:
    items = list(values)
    return sum(items) / len(items) if items else None


def average_precision(y: list[int]) -> float | None:
    positives = sum(y)
    if positives == 0:
        return None
    return sum(
        sum(y[:index]) / index
        for index, label in enumerate(y, start=1)
        if label
    ) / positives


def auroc(y: list[int], scores: list[float]) -> float | None:
    positives = [score for label, score in zip(y, scores, strict=True) if label == 1]
    negatives = [score for label, score in zip(y, scores, strict=True) if label == 0]
    if not positives or not negatives:
        return None
    wins = sum(
        1.0 if positive > negative else 0.5 if positive == negative else 0.0
        for positive in positives
        for negative in negatives
    )
    return wins / (len(positives) * len(negatives))


def finite_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None
