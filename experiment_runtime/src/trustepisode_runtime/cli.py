from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .benchmark import run_benchmark
from .aggregate import aggregate_campaign
from .bundle import BundleWriter, validate_bundle
from .canonical import parse_timestamp, sha256_digest, utf8_key
from .contract_io import ContractSet, load_online_records
from .demo import synthetic_fixture, synthetic_training_input
from .dataset import (
    build_training_input,
    calibration_group_key_from_events,
    load_sealed_run,
)
from .evaluation import evaluate_run, evaluation_rows
from .pipeline import PipelineResult, ReferencePipeline, RuntimeArtifacts
from .protocols import evaluate_outage_journal
from .replay import generate_po1_cells, generate_replay_children
from .training import fit_runtime_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trustepisode-runtime",
        description="TrustEpisode frozen-contract reference runtime",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fit = subparsers.add_parser("fit", help="fit normalizer-bound scorer and calibrator artifacts")
    _contracts_argument(fit)
    fit.add_argument("--input", required=True, type=Path)
    fit.add_argument("--output", required=True, type=Path)
    fit.add_argument("--force", action="store_true")
    fit.set_defaults(handler=_fit)

    training_input = subparsers.add_parser(
        "build-training-input",
        help="derive normalizer/scorer/calibrator cohorts from a frozen campaign",
    )
    _contracts_argument(training_input)
    training_input.add_argument("--campaign-plan", required=True, type=Path)
    training_input.add_argument("--output", required=True, type=Path)
    training_input.add_argument("--force", action="store_true")
    training_input.set_defaults(handler=_build_training_input)

    run = subparsers.add_parser("run", help="execute one immutable base run bundle")
    _contracts_argument(run)
    run.add_argument("--run-id", required=True)
    run.add_argument("--events", required=True, nargs="+", type=Path)
    run.add_argument("--coverage", required=True, nargs="+", type=Path)
    run.add_argument("--artifacts", required=True, type=Path)
    run.add_argument("--truth", type=Path)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--group-key")
    run.add_argument("--allow-synthetic", action="store_true")
    run.add_argument("--preserve-arrival-order", action="store_true")
    run.add_argument("--force", action="store_true")
    run.set_defaults(handler=_run)

    campaign = subparsers.add_parser(
        "process-campaign", help="resumably execute the fitted runtime over sealed campaign runs"
    )
    _contracts_argument(campaign)
    campaign.add_argument("--campaign-plan", required=True, type=Path)
    campaign.add_argument("--artifacts", required=True, type=Path)
    campaign.add_argument("--output-root", required=True, type=Path)
    campaign.add_argument(
        "--partitions",
        nargs="+",
        choices=("train", "development", "calibration", "locked_test"),
        default=["train", "development", "calibration", "locked_test"],
    )
    campaign.add_argument("--limit", type=int)
    campaign.add_argument("--force", action="store_true")
    campaign.set_defaults(handler=_process_campaign)

    aggregate = subparsers.add_parser(
        "aggregate-campaign", help="aggregate locked-test RT1-RT7 without synthetic fill"
    )
    aggregate.add_argument("--campaign-plan", required=True, type=Path)
    aggregate.add_argument("--runtime-root", required=True, type=Path)
    aggregate.add_argument("--replay-root", type=Path)
    aggregate.add_argument("--outage-root", type=Path)
    aggregate.add_argument("--benchmark-bundle", type=Path)
    aggregate.add_argument("--output", required=True, type=Path)
    aggregate.add_argument("--require-complete", action="store_true")
    aggregate.add_argument("--force", action="store_true")
    aggregate.set_defaults(handler=_aggregate_campaign)

    replay = subparsers.add_parser("replay", help="materialize and execute all RP0-RP7 children")
    _contracts_argument(replay)
    replay.add_argument("--base-run-id", required=True)
    replay.add_argument("--events", required=True, nargs="+", type=Path)
    replay.add_argument("--coverage", required=True, nargs="+", type=Path)
    replay.add_argument("--artifacts", required=True, type=Path)
    replay.add_argument("--truth", required=True, type=Path)
    replay.add_argument("--output", required=True, type=Path)
    replay.add_argument("--allow-synthetic", action="store_true")
    replay.add_argument("--force", action="store_true")
    replay.set_defaults(handler=_replay)

    po1 = subparsers.add_parser("po1-plan", help="materialize the frozen 40-cell PO1 allocation")
    po1.add_argument("--output", required=True, type=Path)
    po1.add_argument("--force", action="store_true")
    po1.set_defaults(handler=_po1_plan)

    outage = subparsers.add_parser(
        "outage-evaluate", help="produce paired RT5 rows from one sealed PO1 trace"
    )
    outage.add_argument("--journal", required=True, type=Path)
    outage.add_argument("--runtime-bundle", required=True, type=Path)
    outage.add_argument("--output", required=True, type=Path)
    outage.add_argument("--force", action="store_true")
    outage.set_defaults(handler=_outage_evaluate)

    benchmark = subparsers.add_parser(
        "benchmark", help="execute the frozen RT6 determinism and cost protocol"
    )
    _contracts_argument(benchmark)
    benchmark.add_argument("--events", required=True, nargs="+", type=Path)
    benchmark.add_argument("--coverage", required=True, nargs="+", type=Path)
    benchmark.add_argument("--artifacts", required=True, type=Path)
    benchmark.add_argument("--output", required=True, type=Path)
    benchmark.add_argument("--workers", nargs="+", type=int, default=[1, 2, 4, 8])
    benchmark.add_argument("--repeats", type=int, default=5)
    benchmark.add_argument("--allow-synthetic", action="store_true")
    benchmark.add_argument("--force", action="store_true")
    benchmark.set_defaults(handler=_benchmark)

    dry_run = subparsers.add_parser("dry-run", help="run a self-contained schema-valid fixture")
    _contracts_argument(dry_run)
    dry_run.add_argument("--output", required=True, type=Path)
    dry_run.add_argument("--force", action="store_true")
    dry_run.set_defaults(handler=_dry_run)

    validate = subparsers.add_parser("validate-bundle", help="verify every file and bundle digest")
    validate.add_argument("bundle", type=Path)
    validate.set_defaults(handler=_validate)

    validate_input = subparsers.add_parser(
        "validate-input", help="validate online NDJSON objects and the label firewall"
    )
    _contracts_argument(validate_input)
    validate_input.add_argument("paths", nargs="+", type=Path)
    validate_input.set_defaults(handler=_validate_input)
    return parser


def _contracts_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--contracts", required=True, type=Path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def _fit(args: argparse.Namespace) -> int:
    contracts = ContractSet(args.contracts)
    training_input = _read_json(args.input)
    artifacts, details = fit_runtime_artifacts(contracts, training_input)
    writer = BundleWriter(args.output, bundle_type="training-artifacts", force=args.force)
    writer.write_json("inputs/training_input.json", training_input)
    writer.write_json("runtime_artifacts.json", artifacts.to_dict())
    writer.write_json("artifacts/raw_model.json", details["raw_model_artifact"])
    writer.write_json("artifacts/d_only_model.json", details["d_only_model_artifact"])
    writer.write_json("artifacts/global_calibrator.json", details["global_calibrator_artifact"])
    writer.write_json("artifacts/group_calibrators.json", details["group_calibrator_artifacts"])
    writer.write_json("artifacts/support_manifest.json", details["support_manifest"])
    manifest = writer.finalize(
        {
            "runtime_version": __version__,
            "status": "fitted",
            "training_input_digest": details["training_input_digest"],
        }
    )
    print(json.dumps({"output": str(args.output.resolve()), "bundle_digest": manifest["bundle_digest"]}))
    return 0


def _build_training_input(args: argparse.Namespace) -> int:
    contracts = ContractSet(args.contracts)
    value, diagnostics = build_training_input(contracts, args.campaign_plan)
    writer = BundleWriter(args.output, bundle_type="training-input", force=args.force)
    writer.write_json("training_input.json", value)
    writer.write_json("diagnostics.json", diagnostics)
    manifest = writer.finalize(
        {
            "runtime_version": __version__,
            "campaign_assignment_digest": value["campaign_assignment_digest"],
            "training_input_digest": diagnostics["training_input_digest"],
        }
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "raw_training_rows": diagnostics["raw_training_rows"],
                "calibration_rows": diagnostics["calibration_rows"],
                "bundle_digest": manifest["bundle_digest"],
            }
        )
    )
    return 0


def _run(args: argparse.Namespace) -> int:
    contracts = ContractSet(args.contracts)
    events = load_online_records(args.events, contracts, object_types={"NormalizedEvent"})
    coverage = load_online_records(args.coverage, contracts, object_types={"SourceCoverage"})
    if not args.preserve_arrival_order:
        events = arrival_order(events)
    artifacts = _load_artifacts(args.artifacts)
    truth = _read_json(args.truth) if args.truth else None
    result = ReferencePipeline(
        contracts,
        artifacts,
        allow_synthetic=args.allow_synthetic,
    ).run(events, coverage, group_key=args.group_key)
    ablation_result = ReferencePipeline(
        contracts,
        artifacts,
        allow_synthetic=args.allow_synthetic,
    ).run(events, coverage, group_key=args.group_key, hub_suppression=False)
    writer = BundleWriter(args.output, bundle_type="base-run", force=args.force)
    _write_run(
        writer,
        "",
        args.run_id,
        events,
        coverage,
        artifacts,
        result,
        truth,
        ablation_result=ablation_result,
        preserve_arrival_order=args.preserve_arrival_order,
    )
    manifest = writer.finalize(
        {
            "runtime_version": __version__,
            "run_id": args.run_id,
            "artifact_status": artifacts.status,
        }
    )
    print(json.dumps({"output": str(args.output.resolve()), "bundle_digest": manifest["bundle_digest"]}))
    return 0


def _process_campaign(args: argparse.Namespace) -> int:
    contracts = ContractSet(args.contracts)
    artifacts = _load_artifacts(args.artifacts)
    if artifacts.status != "fitted":
        raise ValueError("campaign processing requires fitted artifacts")
    plan = _read_json(args.campaign_plan)
    rows = [
        item
        for item in plan.get("rows", [])
        if item["partition"] in set(args.partitions)
    ]
    args.output_root.mkdir(parents=True, exist_ok=True)
    processed = 0
    skipped = 0
    for row in rows:
        if args.limit is not None and processed >= args.limit:
            break
        if row.get("status") != "sealed":
            raise ValueError(f"campaign run is not sealed: {row['run_id']}")
        output = args.output_root / row["run_id"]
        if output.exists() and not args.force:
            validate_bundle(output)
            skipped += 1
            continue
        run = load_sealed_run(contracts, row)
        group_key = calibration_group_key_from_events(run.events)
        result = ReferencePipeline(contracts, artifacts).run(
            arrival_order(run.events), run.coverage, group_key=group_key
        )
        ablation = ReferencePipeline(contracts, artifacts).run(
            arrival_order(run.events),
            run.coverage,
            group_key=group_key,
            hub_suppression=False,
        )
        writer = BundleWriter(output, bundle_type="campaign-run", force=args.force)
        _write_run(
            writer,
            "",
            run.run_id,
            arrival_order(run.events),
            run.coverage,
            artifacts,
            result,
            run.truth,
            ablation_result=ablation,
            preserve_arrival_order=False,
        )
        writer.finalize(
            {
                "runtime_version": __version__,
                "run_id": run.run_id,
                "partition": row["partition"],
                "base_campaign_id": row["base_campaign_id"],
                "sealed_run_manifest_digest": row["manifest_digest"],
                "campaign_assignment_digest": plan["assignment_digest"],
            }
        )
        processed += 1
    print(
        json.dumps(
            {
                "output_root": str(args.output_root.resolve()),
                "processed": processed,
                "skipped_valid": skipped,
            }
        )
    )
    return 0


def _aggregate_campaign(args: argparse.Namespace) -> int:
    result, markdown, latex = aggregate_campaign(
        args.campaign_plan,
        args.runtime_root,
        replay_root=args.replay_root,
        outage_root=args.outage_root,
        benchmark_bundle=args.benchmark_bundle,
        require_complete=args.require_complete,
    )
    writer = BundleWriter(args.output, bundle_type="campaign-results", force=args.force)
    writer.write_json("final_results.json", result)
    writer.write_bytes("FINAL_EXPERIMENT_REPORT_zh-TW.md", markdown.encode("utf-8"))
    writer.write_bytes("section4_results.tex", latex.encode("utf-8"))
    manifest = writer.finalize(
        {
            "runtime_version": __version__,
            "campaign_assignment_digest": result["campaign_assignment_digest"],
            "all_formal_inputs_complete": result["completion"]["all_formal_inputs_complete"],
        }
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "complete": result["completion"]["all_formal_inputs_complete"],
                "bundle_digest": manifest["bundle_digest"],
            }
        )
    )
    return 0


def _replay(args: argparse.Namespace) -> int:
    contracts = ContractSet(args.contracts)
    events = arrival_order(
        load_online_records(args.events, contracts, object_types={"NormalizedEvent"})
    )
    coverage = load_online_records(args.coverage, contracts, object_types={"SourceCoverage"})
    artifacts = _load_artifacts(args.artifacts)
    truth = _read_json(args.truth)
    children = generate_replay_children(args.base_run_id, events)
    writer = BundleWriter(args.output, bundle_type="paired-replay", force=args.force)
    summary = []
    replay_results: list[tuple[Any, PipelineResult, dict[str, Any]]] = []
    for index, child in enumerate(children):
        child_run_id = f"{args.base_run_id}:{child.child_key}"
        prefix = f"children/{index:02d}_{_safe_name(child.child_key)}"
        result = ReferencePipeline(
            contracts,
            artifacts,
            allow_synthetic=args.allow_synthetic,
        ).run(child.events, coverage)
        ablation_result = ReferencePipeline(
            contracts,
            artifacts,
            allow_synthetic=args.allow_synthetic,
        ).run(child.events, coverage, hub_suppression=False)
        metrics = _write_run(
            writer,
            prefix,
            child_run_id,
            child.events,
            coverage,
            artifacts,
            result,
            truth,
            ablation_result=ablation_result,
            preserve_arrival_order=True,
        )
        child_manifest = child.manifest(events)
        writer.write_json(f"{prefix}/replay_child.json", child_manifest)
        summary.append({**child_manifest, "metrics": metrics})
        replay_results.append((child, result, metrics))
    rt4_rows = _rt4_rows(replay_results)
    writer.write_json(
        "rt4_replay_summary.json",
        {"base_run_id": args.base_run_id, "children": summary, "rows": rt4_rows},
    )
    manifest = writer.finalize(
        {
            "runtime_version": __version__,
            "base_run_id": args.base_run_id,
            "child_count": len(children),
        }
    )
    print(json.dumps({"output": str(args.output.resolve()), "children": len(children), "bundle_digest": manifest["bundle_digest"]}))
    return 0


def _po1_plan(args: argparse.Namespace) -> int:
    cells = generate_po1_cells()
    writer = BundleWriter(args.output, bundle_type="po1-plan", force=args.force)
    writer.write_json("po1_cells.json", {"contract_version": "trustepisode.po1.v3", "cells": cells})
    writer.write_bytes("po1_cells.csv", _po1_csv(cells).encode("utf-8"))
    manifest = writer.finalize({"runtime_version": __version__, "cell_count": len(cells)})
    print(json.dumps({"output": str(args.output.resolve()), "cells": len(cells), "bundle_digest": manifest["bundle_digest"]}))
    return 0


def _outage_evaluate(args: argparse.Namespace) -> int:
    journal = _read_json(args.journal)
    value = evaluate_outage_journal(journal, args.runtime_bundle)
    writer = BundleWriter(args.output, bundle_type="physical-outage-evaluation", force=args.force)
    writer.write_json("inputs/outage_journal.json", journal)
    writer.write_json("rt5_rows.json", value)
    manifest = writer.finalize(
        {
            "runtime_version": __version__,
            "po1_cell_id": journal["po1_cell_id"],
            "trace_digest": journal["trace_digest"],
            "formal": bool(journal["formal"]),
        }
    )
    print(json.dumps({"output": str(args.output.resolve()), "rows": 2, "bundle_digest": manifest["bundle_digest"]}))
    return 0


def _benchmark(args: argparse.Namespace) -> int:
    contracts = ContractSet(args.contracts)
    events = arrival_order(
        load_online_records(args.events, contracts, object_types={"NormalizedEvent"})
    )
    coverage = load_online_records(
        args.coverage, contracts, object_types={"SourceCoverage"}
    )
    artifacts = _load_artifacts(args.artifacts)
    value = run_benchmark(
        contracts,
        artifacts,
        events,
        coverage,
        worker_counts=args.workers,
        measured_repetitions=args.repeats,
        allow_synthetic=args.allow_synthetic,
    )
    writer = BundleWriter(args.output, bundle_type="rt6-benchmark", force=args.force)
    writer.write_json("inputs/runtime_artifacts.json", artifacts.to_dict())
    writer.write_json("rt6_rows.json", value)
    manifest = writer.finalize(
        {
            "runtime_version": __version__,
            "formal": value["formal"],
            "workers": args.workers,
            "measured_repetitions": args.repeats,
        }
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "formal": value["formal"],
                "bundle_digest": manifest["bundle_digest"],
            }
        )
    )
    return 0


def _dry_run(args: argparse.Namespace) -> int:
    contracts = ContractSet(args.contracts)
    training_input = synthetic_training_input()
    artifacts, training_details = fit_runtime_artifacts(contracts, training_input)
    events, coverage, truth = synthetic_fixture()
    result = ReferencePipeline(contracts, artifacts).run(arrival_order(events), coverage)
    ablation_result = ReferencePipeline(contracts, artifacts).run(
        arrival_order(events), coverage, hub_suppression=False
    )
    writer = BundleWriter(args.output, bundle_type="synthetic-dry-run", force=args.force)
    writer.write_json("training/training_input.json", training_input)
    writer.write_json("training/training_details.json", training_details)
    metrics = _write_run(
        writer,
        "run",
        "synthetic-dry-run",
        arrival_order(events),
        coverage,
        artifacts,
        result,
        truth,
        ablation_result=ablation_result,
        preserve_arrival_order=False,
    )
    writer.write_json("po1/po1_cells.json", {"cells": generate_po1_cells()})
    manifest = writer.finalize(
        {
            "runtime_version": __version__,
            "purpose": "schema and pipeline verification only; never a paper result",
            "metrics_digest": sha256_digest(metrics),
        }
    )
    validate_bundle(args.output)
    print(json.dumps({"output": str(args.output.resolve()), "bundle_digest": manifest["bundle_digest"], "validated": True}))
    return 0


def _validate(args: argparse.Namespace) -> int:
    manifest = validate_bundle(args.bundle)
    print(json.dumps({"bundle": str(args.bundle.resolve()), "bundle_digest": manifest["bundle_digest"], "files": len(manifest["files"]), "valid": True}))
    return 0


def _validate_input(args: argparse.Namespace) -> int:
    contracts = ContractSet(args.contracts)
    records = load_online_records(args.paths, contracts)
    counts: dict[str, int] = {}
    for record in records:
        object_type = str(record["object_type"])
        counts[object_type] = counts.get(object_type, 0) + 1
    print(
        json.dumps(
            {
                "files": len(args.paths),
                "records": len(records),
                "object_type_counts": counts,
                "valid": True,
            },
            sort_keys=True,
        )
    )
    return 0


def _write_run(
    writer: BundleWriter,
    prefix: str,
    run_id: str,
    events: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    artifacts: RuntimeArtifacts,
    result: PipelineResult,
    truth: dict[str, Any] | None,
    *,
    ablation_result: PipelineResult | None = None,
    preserve_arrival_order: bool,
) -> dict[str, Any] | None:
    root = prefix.rstrip("/")

    def path(value: str) -> str:
        return f"{root}/{value}" if root else value

    writer.write_ndjson(path("inputs/events.ndjson"), events)
    writer.write_ndjson(path("inputs/source_coverage.ndjson"), coverage)
    writer.write_json(path("inputs/runtime_artifacts.json"), artifacts.to_dict())
    writer.write_ndjson(path("outputs/episode_revisions.ndjson"), result.synthesis.revisions)
    writer.write_ndjson(path("outputs/late_evidence.ndjson"), result.synthesis.late_records)
    writer.write_json(path("outputs/rejected_events.json"), result.synthesis.rejected)
    writer.write_ndjson(path("outputs/features.ndjson"), result.features)
    writer.write_ndjson(path("outputs/support_decisions.ndjson"), result.support_decisions)
    writer.write_ndjson(path("outputs/detector_values.ndjson"), result.detector_outputs)
    writer.write_ndjson(path("outputs/assembly_outcomes.ndjson"), result.outcomes)
    metrics = None
    if truth is not None:
        writer.write_json(path("offline/truth.json"), truth)
        metrics = evaluate_run(
            run_id,
            result,
            truth,
            ablation_pipeline=ablation_result,
            artifacts=artifacts,
        )
        writer.write_json(path("offline/evaluation.json"), metrics)
        writer.write_json(
            path("offline/evaluation_rows.json"),
            evaluation_rows(run_id, result, truth, artifacts),
        )
    writer.write_json(
        path("run_metadata.json"),
        {
            "metadata_type": "trustepisode.run-metadata.v1",
            "run_id": run_id,
            "runtime_version": __version__,
            "artifact_status": artifacts.status,
            "input_event_count": len(events),
            "input_coverage_count": len(coverage),
            "terminal_outcome_count": len(result.outcomes),
            "preserve_arrival_order": preserve_arrival_order,
            "online_input_digest": sha256_digest({"events": events, "coverage": coverage}),
            "truth_join_stage": "after_terminal_assembly_outcomes" if truth is not None else "not_joined",
        },
    )
    return metrics


def arrival_order(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        events,
        key=lambda item: (
            parse_timestamp(item["ingest_time"]),
            parse_timestamp(item["event_time"]),
            utf8_key(item["source_instance"]),
            utf8_key(item["event_id"]),
        ),
    )


def _load_artifacts(path: Path) -> RuntimeArtifacts:
    candidate = path / "runtime_artifacts.json" if path.is_dir() else path
    return RuntimeArtifacts.from_path(candidate)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "._-" else "_" for character in value)


def _po1_csv(cells: list[dict[str, Any]]) -> str:
    fields = (
        "po1_cell_id",
        "source_family",
        "duration_seconds",
        "repetition_index",
        "allocated_card_id",
        "partition",
        "bootstrap_cluster_id",
    )
    lines = [",".join(fields)]
    lines.extend(",".join(str(item[field]) for field in fields) for item in cells)
    return "\n".join(lines) + "\n"


def _rt4_rows(
    replay_results: list[tuple[Any, PipelineResult, dict[str, Any]]]
) -> list[dict[str, Any]]:
    if not replay_results or replay_results[0][0].intervention_id != "RP0":
        raise ValueError("RP0 must be the first replay child")
    baseline = _replay_statistics(replay_results[0][1], replay_results[0][2])
    rows = []
    for child, result, metrics in replay_results:
        statistics = _replay_statistics(result, metrics)
        rows.append(
            {
                "intervention_id": child.intervention_id,
                "source_family": child.source_family,
                "level": child.level,
                "valid": child.valid,
                "invalid_reason": child.invalid_reason,
                "delta_action_coverage": _delta(statistics["action_coverage"], baseline["action_coverage"]),
                "delta_fragmentation": _delta(statistics["fragmentation"], baseline["fragmentation"]),
                "delta_z": _delta(statistics["mean_z"], baseline["mean_z"]),
                "delta_supported_Brier": _delta(statistics["Brier"], baseline["Brier"]),
                "delta_supported_NLL": _delta(statistics["NLL"], baseline["NLL"]),
                "supported_coverage": statistics["supported_coverage"],
                "U_axis_transitions": _u_transitions(replay_results[0][1], result),
                "revision_count": len(result.synthesis.revisions),
                "stabilization_seconds": statistics["stabilization_seconds"],
            }
        )
    return rows


def _replay_statistics(result: PipelineResult, metrics: dict[str, Any]) -> dict[str, Any]:
    audits = [item for item in result.outcomes if item["object_type"] == "AuditRecord"]
    z_values = [float(item["z"]) for item in audits]
    closed = [item for item in result.synthesis.revisions if item["state"] == "closed"]
    stabilization = [
        (
            parse_timestamp(item["watermark"])
            - parse_timestamp(item["event_time_end"])
        ).total_seconds()
        for item in closed
    ]
    calibration = metrics["RT3b"]["SB5"]
    formation = metrics["RT2"]["EB3"]
    return {
        "action_coverage": formation["action_coverage"],
        "fragmentation": formation["fragmentation"],
        "mean_z": sum(z_values) / len(z_values) if z_values else None,
        "Brier": calibration["Brier"],
        "NLL": calibration["NLL"],
        "supported_coverage": calibration["score_coverage"],
        "stabilization_seconds": sum(stabilization) / len(stabilization) if stabilization else None,
    }


def _u_transitions(base: PipelineResult, child: PipelineResult) -> dict[str, int]:
    base_by_key = {
        (item["episode_id"], item["revision"]): item
        for item in base.outcomes
        if item["object_type"] == "AuditRecord"
    }
    child_by_key = {
        (item["episode_id"], item["revision"]): item
        for item in child.outcomes
        if item["object_type"] == "AuditRecord"
    }
    common = set(base_by_key).intersection(child_by_key)
    axes = ("coverage", "provenance", "lateness", "contradiction", "calibration")
    return {
        axis: sum(base_by_key[key]["U"][axis] != child_by_key[key]["U"][axis] for key in common)
        for axis in axes
    }


def _delta(value: float | None, baseline: float | None) -> float | None:
    return value - baseline if value is not None and baseline is not None else None


if __name__ == "__main__":
    raise SystemExit(main())
