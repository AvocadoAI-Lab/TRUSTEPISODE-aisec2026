from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .bundle import validate_bundle
from .evaluation import average_precision, auroc, reliability_bins


def aggregate_campaign(
    campaign_plan_path: Path,
    runtime_root: Path,
    *,
    replay_root: Path | None = None,
    outage_root: Path | None = None,
    benchmark_bundle: Path | None = None,
    require_complete: bool = False,
    bootstrap_repetitions: int = 2000,
    bootstrap_seed: int = 20260710,
    budget_fraction: float = 0.10,
    precision_k: int = 10,
) -> tuple[dict[str, Any], str, str]:
    plan = load_json(campaign_plan_path)
    locked = [item for item in plan["rows"] if item["partition"] == "locked_test"]
    replay_locked = [
        item
        for item in locked
        if str(item.get("scenario_family", item.get("card_id", "")))
        in {f"M{index}" for index in range(1, 8)}
    ]
    runs = []
    missing_runtime = []
    for registry_row in locked:
        path = runtime_root / registry_row["run_id"]
        if not path.exists():
            missing_runtime.append(registry_row["run_id"])
            continue
        validate_bundle(path)
        content = path / "run" if (path / "run" / "offline").is_dir() else path
        runs.append(
            {
                "registry": registry_row,
                "evaluation": load_json(content / "offline" / "evaluation.json"),
                "rows": load_json_array(content / "offline" / "evaluation_rows.json"),
            }
        )

    completion = {
        "locked_runtime_expected": len(locked),
        "locked_runtime_present": len(runs),
        "missing_locked_runtime": missing_runtime,
        "runtime_complete": len(runs) == len(locked),
    }
    result: dict[str, Any] = {
        "result_type": "trustepisode.campaign-results.v1",
        "campaign_assignment_digest": plan["assignment_digest"],
        "completion": completion,
        "RT1": aggregate_rt1(runs),
        "RT2": aggregate_rt2(
            runs, repetitions=bootstrap_repetitions, seed=bootstrap_seed
        ),
        "RT3a": aggregate_ranking(
            runs,
            repetitions=bootstrap_repetitions,
            seed=bootstrap_seed,
            budget_fraction=budget_fraction,
            precision_k=precision_k,
        ),
        "RT3b": aggregate_calibration(
            runs, repetitions=bootstrap_repetitions, seed=bootstrap_seed
        ),
        "RT7": aggregate_rt7(runs),
    }
    rt4, rt4_completion = aggregate_rt4(
        replay_locked,
        replay_root,
        repetitions=bootstrap_repetitions,
        seed=bootstrap_seed,
    )
    result["RT4"] = rt4
    completion.update(rt4_completion)
    rt5, rt5_completion = aggregate_rt5(outage_root)
    result["RT5"] = rt5
    completion.update(rt5_completion)
    rt6, rt6_completion = aggregate_rt6(benchmark_bundle)
    result["RT6"] = rt6
    completion.update(rt6_completion)
    completion["all_formal_inputs_complete"] = all(
        completion[key]
        for key in ("runtime_complete", "replay_complete", "po1_complete", "rt6_complete")
    )
    if require_complete and not completion["all_formal_inputs_complete"]:
        raise ValueError(
            "formal aggregation incomplete: "
            + ", ".join(
                key
                for key in ("runtime_complete", "replay_complete", "po1_complete", "rt6_complete")
                if not completion[key]
            )
        )
    return result, markdown_report(result), latex_report(result)


def aggregate_rt1(runs: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [item["evaluation"]["RT1"] for item in runs]
    count_fields = (
        "runs",
        "terminal_episodes",
        "C_dec_all",
        "C_dec_score",
        "C_dec_binary",
        "supported_global_count",
        "supported_group_count",
        "out_of_support_audit_count",
        "assembly_failure_count",
        "outcome_positive",
        "outcome_negative",
        "outcome_mixed",
        "outcome_ambiguous",
        "failure_positive",
        "failure_negative",
        "failure_mixed",
        "failure_ambiguous",
    )
    output = {field: sum(int(row.get(field, 0)) for row in rows) for field in count_fields}
    denominator = output["C_dec_all"]
    output["score_coverage"] = safe_ratio(output["C_dec_score"], denominator)
    output["binary_coverage"] = safe_ratio(output["C_dec_binary"], denominator)
    output["out_of_support_rate_over_all"] = safe_ratio(
        output["out_of_support_audit_count"], denominator
    )
    output["failure_rate_over_all"] = safe_ratio(
        output["assembly_failure_count"], denominator
    )
    output["binary_prevalence"] = safe_ratio(
        output["outcome_positive"],
        output["outcome_positive"] + output["outcome_negative"],
    )
    output["class_conditional_failure_rates"] = {
        label: safe_ratio(output[f"failure_{label}"], output[f"outcome_{label}"])
        for label in ("positive", "negative", "mixed", "ambiguous")
    }
    return output


def aggregate_rt2(
    runs: list[dict[str, Any]], *, repetitions: int, seed: int
) -> dict[str, Any]:
    output = {}
    for builder in ("EB1", "EB2", "EB3", "EB3-H"):
        output[builder] = {}
        for metric in (
            "action_coverage",
            "fragmentation",
            "over_merge",
            "contamination",
            "episode_f1",
        ):
            by_run = {
                item["registry"]["run_id"]: item["evaluation"]["RT2"][builder].get(metric)
                for item in runs
            }
            defined = [float(value) for value in by_run.values() if value is not None]
            output[builder][metric] = {
                "mean": float(np.mean(defined)) if defined else None,
                "interval_95": bootstrap_scalar(by_run, repetitions, seed),
                "defined_runs": len(defined),
                "undefined_runs": len(by_run) - len(defined),
            }
    return output


def aggregate_ranking(
    runs: list[dict[str, Any]],
    *,
    repetitions: int,
    seed: int,
    budget_fraction: float,
    precision_k: int,
) -> dict[str, Any]:
    all_rows = [
        {**row, "base_campaign_id": item["registry"]["base_campaign_id"]}
        for item in runs
        for row in item["rows"]
    ]
    output = {}
    for scorer in ("SB1", "SB2", "SB3"):
        metric = ranking_metric(all_rows, scorer, budget_fraction, precision_k)
        metric["intervals_95"] = bootstrap_rows(
            all_rows,
            lambda values: ranking_metric(values, scorer, budget_fraction, precision_k),
            ("AUPRC", "recall_at_budget", "AUROC", "precision_at_k"),
            repetitions,
            seed,
        )
        output[scorer] = metric
    return output


def ranking_metric(
    rows: list[dict[str, Any]], scorer: str, budget_fraction: float, precision_k: int
) -> dict[str, Any]:
    all_count = len(rows)
    binary = [
        item
        for item in rows
        if item["decision_eligible"] and item["label"] in {"positive", "negative"}
    ]
    scored = [item for item in binary if finite(item.get(scorer))]
    ordered = sorted(
        scored,
        key=lambda item: (
            -float(item[scorer]),
            item["run_id"].encode("utf-8"),
            item["episode_id"].encode("utf-8"),
            int(item["revision"]),
        ),
    )
    labels = [int(item["label"] == "positive") for item in ordered]
    scores = [float(item[scorer]) for item in ordered]
    budget = max(1, math.ceil(budget_fraction * len(ordered))) if ordered else 0
    positives = sum(labels)
    k = min(precision_k, len(ordered))
    return {
        "C_dec_all": all_count,
        "C_dec_score": len(scored),
        "C_dec_binary": len(binary),
        "score_coverage": safe_ratio(len(scored), all_count),
        "binary_coverage": safe_ratio(len(binary), all_count),
        "AUPRC": average_precision(labels),
        "recall_at_budget": safe_ratio(sum(labels[:budget]), positives),
        "AUROC": auroc(labels, scores),
        "precision_at_k": safe_ratio(sum(labels[:k]), k),
    }


def aggregate_calibration(
    runs: list[dict[str, Any]], *, repetitions: int, seed: int
) -> dict[str, Any]:
    rows = [
        {**row, "base_campaign_id": item["registry"]["base_campaign_id"]}
        for item in runs
        for row in item["rows"]
    ]
    output = {}
    for mapping in ("SB4", "SB5", "SB6"):
        metric = calibration_metric(rows, mapping)
        if metric == "N/A":
            output[mapping] = metric
            continue
        metric["intervals_95"] = bootstrap_rows(
            rows,
            lambda values: calibration_metric(values, mapping),
            ("Brier", "NLL"),
            repetitions,
            seed,
        )
        output[mapping] = metric
    return output


def calibration_metric(rows: list[dict[str, Any]], mapping: str) -> dict[str, Any] | str:
    all_count = len(rows)
    binary = [
        item
        for item in rows
        if item["decision_eligible"] and item["label"] in {"positive", "negative"}
    ]
    selected = [item for item in binary if finite(item.get(mapping))]
    if mapping == "SB6" and not selected:
        return "N/A"
    y = [int(item["label"] == "positive") for item in selected]
    probabilities = [float(item[mapping]) for item in selected]
    global_count = sum(item.get("kappa") == "supported_global" for item in rows)
    group_count = sum(item.get("kappa") == "supported_group" for item in rows)
    oos_count = sum(item.get("kappa") == "out_of_support" for item in rows)
    failure_count = sum(item.get("outcome_type") == "AssemblyFailureRecord" for item in rows)
    return {
        "C_dec_all": all_count,
        "C_dec_score": len(selected),
        "C_dec_binary": len(binary),
        "Brier": mean_or_none(
            [(probability - label) ** 2 for probability, label in zip(probabilities, y, strict=True)]
        ),
        "NLL": mean_or_none(
            [
                -(label * math.log(max(probability, 1e-15)) + (1 - label) * math.log(max(1 - probability, 1e-15)))
                for probability, label in zip(probabilities, y, strict=True)
            ]
        ),
        "reliability_bins": reliability_bins(y, probabilities),
        "score_coverage": safe_ratio(len(selected), all_count),
        "binary_coverage": safe_ratio(len(binary), all_count),
        "supported_global_rate_over_all": safe_ratio(global_count, all_count),
        "supported_group_rate_over_all": safe_ratio(group_count, all_count),
        "out_of_support_rate_over_all": safe_ratio(oos_count, all_count),
        "failure_rate_over_all": safe_ratio(failure_count, all_count),
    }


def aggregate_rt7(runs: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {**row, "base_campaign_id": item["registry"]["base_campaign_id"]}
        for item in runs
        for row in item["rows"]
    ]
    run_count = len(runs)
    terminal_count = len(rows)
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in runs:
        evaluation = item["evaluation"]
        if (evaluation["RT2"]["EB3"].get("fragmentation") or 0) > 0:
            categories["fragmentation"].append(item)
        if (evaluation["RT2"]["EB3"].get("over_merge") or 0) > 0:
            categories["over_merge"].append(item)
        for category in (
            "collector_outage",
            "parser_failure",
            "unsupported_calibration",
            "label_ambiguity",
        ):
            if evaluation["RT7"].get(category, 0) > 0:
                categories[category].append(item)
    output = {}
    for category in (
        "fragmentation",
        "over_merge",
        "collector_outage",
        "parser_failure",
        "unsupported_calibration",
        "label_ambiguity",
    ):
        affected = categories[category]
        representative = None
        if affected and affected[0]["rows"]:
            row = affected[0]["rows"][0]
            representative = f"{row['run_id']}:{row['episode_id']}:{row['revision']}"
        output[category] = {
            "count": len(affected),
            "run_fraction": safe_ratio(len(affected), run_count),
            "candidate_fraction": safe_ratio(len(affected), terminal_count),
            "representative_revision_id": representative,
            "adjudication_status": "requires_manual_review" if affected else "not_applicable",
        }
    return output


def aggregate_rt4(
    locked: list[dict[str, Any]],
    root: Path | None,
    *,
    repetitions: int,
    seed: int,
) -> tuple[Any, dict[str, Any]]:
    if root is None:
        return "pending", {"replay_expected": len(locked), "replay_present": 0, "replay_complete": False}
    by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    present = 0
    for registry in locked:
        path = root / registry["run_id"]
        if not path.exists():
            continue
        validate_bundle(path)
        value = load_json(path / "rt4_replay_summary.json")
        present += 1
        for row in value["rows"]:
            key = (
                str(row["intervention_id"]),
                str(row.get("source_family")),
                json.dumps(row["level"], sort_keys=True),
            )
            by_key[key].append({**row, "base_campaign_id": registry["base_campaign_id"]})
    rows = []
    scalar_fields = (
        "delta_action_coverage",
        "delta_fragmentation",
        "delta_z",
        "delta_supported_Brier",
        "delta_supported_NLL",
        "supported_coverage",
        "revision_count",
        "stabilization_seconds",
    )
    for key, values in sorted(by_key.items()):
        row = {
            "intervention_id": key[0],
            "source_family": None if key[1] == "None" else key[1],
            "level": json.loads(key[2]),
            "valid_runs": sum(bool(item["valid"]) for item in values),
            "invalid_runs": sum(not bool(item["valid"]) for item in values),
        }
        for field in scalar_fields:
            by_run = {item["base_campaign_id"]: item.get(field) for item in values if item["valid"]}
            defined = [float(item) for item in by_run.values() if item is not None]
            row[field] = {
                "mean": float(np.mean(defined)) if defined else None,
                "interval_95": bootstrap_scalar(by_run, repetitions, seed),
            }
        row["U_axis_transitions"] = {
            axis: sum(int(item["U_axis_transitions"].get(axis, 0)) for item in values if item["valid"])
            for axis in ("coverage", "provenance", "lateness", "contradiction", "calibration")
        }
        rows.append(row)
    return {"rows": rows}, {
        "replay_expected": len(locked),
        "replay_present": present,
        "replay_complete": present == len(locked),
    }


def aggregate_rt5(root: Path | None) -> tuple[Any, dict[str, Any]]:
    if root is None:
        return "pending", {"po1_cells_expected": 40, "po1_cells_present": 0, "po1_complete": False}
    rows = []
    for path in sorted(root.glob("*/rt5_rows.json"), key=lambda item: item.as_posix().encode("utf-8")):
        value = load_json(path)
        rows.extend(value["rows"])
    cells = {item["po1_cell_id"] for item in rows if item.get("formal")}
    paired = all(
        len(group) == 2 and len({item["trace_digest"] for item in group}) == 1
        for cell in cells
        for group in [[item for item in rows if item.get("formal") and item["po1_cell_id"] == cell]]
    )
    complete = len(cells) == 40 and len([item for item in rows if item.get("formal")]) == 80 and paired
    return {"rows": rows}, {
        "po1_cells_expected": 40,
        "po1_cells_present": len(cells),
        "po1_complete": complete,
    }


def aggregate_rt6(bundle: Path | None) -> tuple[Any, dict[str, Any]]:
    if bundle is None or not bundle.exists():
        return "pending", {"rt6_complete": False}
    validate_bundle(bundle)
    value = load_json(bundle / "rt6_rows.json")
    complete = bool(value.get("formal")) and [item["worker_count"] for item in value["rows"]] == [1, 2, 4, 8]
    return value, {"rt6_complete": complete}


def bootstrap_scalar(
    by_run: dict[str, Any], repetitions: int, seed: int
) -> list[float] | None:
    defined = {key: float(value) for key, value in by_run.items() if value is not None}
    if not defined:
        return None
    run_ids = sorted(defined, key=lambda item: item.encode("utf-8"))
    generator = np.random.default_rng(seed)
    samples = np.empty(repetitions, dtype=np.float64)
    for index in range(repetitions):
        selected = generator.integers(0, len(run_ids), size=len(run_ids))
        samples[index] = float(np.mean([defined[run_ids[int(item)]] for item in selected]))
    return [float(item) for item in np.percentile(samples, [2.5, 97.5])]


def bootstrap_rows(
    rows: list[dict[str, Any]],
    metric_fn: Callable[[list[dict[str, Any]]], dict[str, Any] | str],
    fields: tuple[str, ...],
    repetitions: int,
    seed: int,
) -> dict[str, list[float] | None]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["base_campaign_id"]].append(row)
    if not grouped:
        return {field: None for field in fields}
    run_ids = sorted(grouped, key=lambda item: item.encode("utf-8"))
    generator = np.random.default_rng(seed)
    samples = {field: [] for field in fields}
    for _index in range(repetitions):
        selected = generator.integers(0, len(run_ids), size=len(run_ids))
        values = [
            {**row, "run_id": f"boot-{draw_index}:{row['run_id']}"}
            for draw_index, selected_index in enumerate(selected)
            for row in grouped[run_ids[int(selected_index)]]
        ]
        metric = metric_fn(values)
        if metric == "N/A":
            continue
        for field in fields:
            if metric.get(field) is not None:
                samples[field].append(float(metric[field]))
    return {
        field: (
            [float(item) for item in np.percentile(values, [2.5, 97.5])]
            if values
            else None
        )
        for field, values in samples.items()
    }


def markdown_report(result: dict[str, Any]) -> str:
    completion = result["completion"]
    lines = [
        "# TrustEpisode 正式實驗結果彙總",
        "",
        f"- Campaign assignment digest: `{result['campaign_assignment_digest']}`",
        f"- Locked-test runtime: {completion['locked_runtime_present']}/{completion['locked_runtime_expected']}",
        f"- Paired replay: {completion['replay_present']}/{completion['replay_expected']}",
        f"- PO1 cells: {completion['po1_cells_present']}/{completion['po1_cells_expected']}",
        f"- 全部正式輸入完整: `{str(completion['all_formal_inputs_complete']).lower()}`",
        "",
        "## RT1",
        "",
        "| all | score | binary | supported global | supported group | OOS | failures |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        "| {C_dec_all} | {C_dec_score} | {C_dec_binary} | {supported_global_count} | {supported_group_count} | {out_of_support_audit_count} | {assembly_failure_count} |".format(
            **result["RT1"]
        ),
        "",
        "## RT3a",
        "",
        "| Scorer | AUPRC | AUROC | Recall@budget | Precision@k |",
        "|---|---:|---:|---:|---:|",
    ]
    for scorer, row in result["RT3a"].items():
        lines.append(
            f"| {scorer} | {format_value(row['AUPRC'])} | {format_value(row['AUROC'])} | {format_value(row['recall_at_budget'])} | {format_value(row['precision_at_k'])} |"
        )
    lines.extend(["", "## 完成判定", ""])
    lines.append(
        "全部 RT1--RT7 正式輸入已封存，可移除論文中的 `pending`。"
        if completion["all_formal_inputs_complete"]
        else "尚未完整；缺少的正式輸入維持 `pending`，不得以 smoke/synthetic 數值取代。"
    )
    return "\n".join(lines) + "\n"


def latex_report(result: dict[str, Any]) -> str:
    completion = result["completion"]
    lines = [
        "% Generated by trustepisode-runtime aggregate-campaign.",
        f"% campaign_assignment_digest={result['campaign_assignment_digest']}",
        f"% all_formal_inputs_complete={str(completion['all_formal_inputs_complete']).lower()}",
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "Scorer & AUPRC & AUROC & Recall@budget & Precision@$k$ \\\\",
        "\\midrule",
    ]
    for scorer, row in result["RT3a"].items():
        lines.append(
            f"{scorer} & {format_value(row['AUPRC'])} & {format_value(row['AUROC'])} & {format_value(row['recall_at_budget'])} & {format_value(row['precision_at_k'])} \\\\" 
        )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    return "\n".join(lines) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def load_json_array(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"JSON object array required: {path}")
    return value


def safe_ratio(numerator: int | float, denominator: int | float) -> float | None:
    return numerator / denominator if denominator else None


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def mean_or_none(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def format_value(value: Any) -> str:
    return "pending" if value is None else f"{float(value):.4f}"
