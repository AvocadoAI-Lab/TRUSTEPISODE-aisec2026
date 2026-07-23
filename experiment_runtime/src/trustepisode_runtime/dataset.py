from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import parse_timestamp, sha256_digest, utf8_key
from .contract_io import ContractSet, load_online_records
from .evaluation import (
    label_episode,
    parse_truth_groups,
    qualified_edges,
    terminal_episode_views,
)
from .features import DETECTOR_IDS, DetectorEngine
from .formation import EpisodeSynthesizer
from .pipeline import PipelineResult, ReferencePipeline, RuntimeArtifacts, build_versions


@dataclass
class SealedRun:
    run_id: str
    partition: str
    path: Path
    events: list[dict[str, Any]]
    coverage: list[dict[str, Any]]
    truth: dict[str, Any]


def build_training_input(
    contracts: ContractSet, campaign_plan_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = json.loads(campaign_plan_path.read_text(encoding="utf-8"))
    rows = plan.get("rows") or []
    selected = [item for item in rows if item["partition"] in {"train", "calibration"}]
    if not selected:
        raise ValueError("campaign contains no train/calibration rows")
    runs = []
    for row in selected:
        if row.get("status") != "sealed" or row.get("manifest_digest") in {None, "", "pending"}:
            raise ValueError(
                f"required {row['partition']} run is not sealed: {row['run_id']}"
            )
        runs.append(load_sealed_run(contracts, row))

    synthetic = RuntimeArtifacts.synthetic(contracts)
    negative_values = {
        detector_id: []
        for family in ("EDR", "NDR")
        for detector_id in DETECTOR_IDS[family]
    }
    raw_label_counts = {"positive": 0, "negative": 0, "mixed": 0, "ambiguous": 0}
    for run in runs:
        if run.partition != "train":
            continue
        synthesis = EpisodeSynthesizer(
            contracts.thresholds["formation"],
            versions=synthetic.versions,
            entity_aliases=run.truth.get("entity_aliases") or {},
        ).synthesize(arrival_order(run.events))
        pipeline = PipelineResult(synthesis=synthesis)
        labels = labels_for_pipeline(pipeline, run.truth)
        terminal = {
            (item.episode_id, item.revision): item for item in terminal_episode_views(pipeline)
        }
        revision_by_key = {
            (item["episode_id"], item["revision"]): item for item in synthesis.revisions
        }
        for key, episode in terminal.items():
            label = labels[key]["label"]
            raw_label_counts[label] += 1
            if label != "negative":
                continue
            revision = revision_by_key[key]
            values = DetectorEngine().evaluate(
                synthesis.event_by_id[event_id]
                for event_id in revision["ordered_event_ids"]
            )
            for value in values:
                negative_values[value.detector_id].append(value.value)

    missing = [detector_id for detector_id, values in negative_values.items() if not values]
    if missing:
        raise ValueError(
            "negative training cohort does not cover registered detectors: "
            + ", ".join(sorted(missing, key=utf8_key))
        )

    provisional = provisional_artifacts(contracts, synthetic, negative_values)
    raw_rows = []
    calibration_rows = []
    calibration_by_group: dict[str, list[dict[str, Any]]] = {}
    exclusions: dict[str, int] = {}
    for run in runs:
        provisional.entity_aliases = {
            str(key): str(value)
            for key, value in (run.truth.get("entity_aliases") or {}).items()
        }
        result = ReferencePipeline(
            contracts, provisional, allow_synthetic=True
        ).run(arrival_order(run.events), run.coverage)
        labels = labels_for_pipeline(result, run.truth)
        feature_by_key = {
            (item["episode_id"], item["revision"]): item for item in result.features
        }
        outcome_by_key = {
            (item["episode_id"], item["revision"]): item for item in result.outcomes
        }
        for episode in terminal_episode_views(result):
            key = (episode.episode_id, episode.revision)
            label = labels[key]["label"]
            outcome = outcome_by_key.get(key)
            feature = feature_by_key.get(key)
            reason = cohort_exclusion(label, outcome, feature)
            if reason is not None:
                exclusions[reason] = exclusions.get(reason, 0) + 1
                continue
            revision_id = f"{run.run_id}:{episode.episode_id}:{episode.revision}"
            row = {
                "revision_id": revision_id,
                "D": float(feature["D"]),
                "C": int(feature["C"]),
                "label": int(label == "positive"),
            }
            if run.partition == "train":
                raw_rows.append(row)
            else:
                calibration_row = {**row, "run_id": run.run_id}
                calibration_rows.append(calibration_row)
                group_key = calibration_group_key(result)
                calibration_by_group.setdefault(group_key, []).append(calibration_row)

    if not raw_rows:
        raise ValueError("raw scorer training cohort is empty")
    if not calibration_rows:
        raise ValueError("calibration cohort is empty")
    input_value = {
        "training_input_type": "trustepisode.runtime-training-input.v1",
        "normalizer_values": negative_values,
        "raw_training_rows": sorted(raw_rows, key=lambda item: utf8_key(item["revision_id"])),
        "calibration_rows": sorted(
            calibration_rows, key=lambda item: utf8_key(item["revision_id"])
        ),
        "group_calibration_candidates": {
            key: {
                "rows": sorted(values, key=lambda item: utf8_key(item["revision_id"]))
            }
            for key, values in sorted(calibration_by_group.items(), key=lambda item: utf8_key(item[0]))
        },
        "expected_instances": {
            "EDR": ["edr-target-01", "edr-target-02"],
            "NDR": ["ndr-gateway-01"],
        },
        "entity_aliases": {
            "ip:172.30.11.10": "host:edr-target-01",
            "ip:172.30.12.10": "host:edr-target-02",
        },
        "campaign_assignment_digest": plan["assignment_digest"],
    }
    diagnostics = {
        "campaign_plan": str(campaign_plan_path.resolve()),
        "partitions_read": ["train", "calibration"],
        "partitions_not_read": ["development", "locked_test"],
        "sealed_runs_read": len(runs),
        "normalizer_counts": {
            key: len(value) for key, value in sorted(negative_values.items(), key=lambda item: utf8_key(item[0]))
        },
        "raw_label_counts_before_support_filter": raw_label_counts,
        "raw_training_rows": len(raw_rows),
        "calibration_rows": len(calibration_rows),
        "cohort_exclusions": exclusions,
        "training_input_digest": sha256_digest(input_value),
    }
    return input_value, diagnostics


def load_sealed_run(contracts: ContractSet, row: dict[str, Any]) -> SealedRun:
    path = Path(row["sealed_path"]).resolve()
    manifest = json.loads((path / "run_manifest.json").read_text(encoding="utf-8"))
    if manifest["bundle_digest"] != row["manifest_digest"]:
        raise ValueError(f"sealed manifest digest mismatch: {row['run_id']}")
    events = load_online_records(
        [
            path / "inputs" / "edr-01" / "normalized.ndjson",
            path / "inputs" / "edr-02" / "normalized.ndjson",
            path / "inputs" / "ndr" / "normalized" / "ndr.ndjson",
        ],
        contracts,
        object_types={"NormalizedEvent"},
    )
    coverage = load_online_records(
        [
            path / "inputs" / "edr-01" / "health.ndjson",
            path / "inputs" / "edr-02" / "health.ndjson",
            path / "inputs" / "ndr" / "health" / "ndr.ndjson",
        ],
        contracts,
        object_types={"SourceCoverage"},
    )
    truth = json.loads((path / "offline" / "truth.json").read_text(encoding="utf-8"))
    return SealedRun(row["run_id"], row["partition"], path, events, coverage, truth)


def labels_for_pipeline(
    pipeline: PipelineResult, truth: dict[str, Any]
) -> dict[tuple[str, int], dict[str, Any]]:
    aliases = {
        str(key): str(value) for key, value in (truth.get("entity_aliases") or {}).items()
    }
    episodes = terminal_episode_views(pipeline, aliases=aliases)
    groups = parse_truth_groups(truth, aliases=aliases)
    edges = qualified_edges(episodes, groups)
    benign = frozenset(str(item) for item in truth.get("benign_action_tokens", []))
    conflict = bool(truth.get("truth_conflict", False))
    return {
        (episode.episode_id, episode.revision): label_episode(
            episode,
            edges,
            groups,
            benign,
            truth_conflict=conflict,
        )
        for episode in episodes
    }


def provisional_artifacts(
    contracts: ContractSet,
    synthetic: RuntimeArtifacts,
    normalizer_values: dict[str, list[float]],
) -> RuntimeArtifacts:
    versions = build_versions(
        contracts,
        raw_model_digest=synthetic.raw_model.artifact_digest,
        calibrator_digest=synthetic.global_calibrator.artifact_digest,
        support_manifest_digest=synthetic.support_manifest_digest,
        normalizer_values=normalizer_values,
    )
    return RuntimeArtifacts(
        status="synthetic_test_only",
        normalizer_values=normalizer_values,
        raw_model=synthetic.raw_model,
        global_calibrator=synthetic.global_calibrator,
        expected_instances=synthetic.expected_instances,
        support_manifest_digest=synthetic.support_manifest_digest,
        versions=versions,
        d_only_model=synthetic.d_only_model,
    )


def cohort_exclusion(
    label: str,
    outcome: dict[str, Any] | None,
    feature: dict[str, Any] | None,
) -> str | None:
    if label not in {"positive", "negative"}:
        return f"label_{label}"
    if outcome is None or feature is None:
        return "missing_terminal_artifact"
    if outcome["object_type"] != "AuditRecord":
        return "assembly_failure"
    if not outcome["decision_eligible"] or outcome["kappa"] == "out_of_support":
        return "out_of_support"
    if feature["source_mask"] != {"EDR": 1, "NDR": 1}:
        return "source_mask_not_11"
    return None


def calibration_group_key(result: PipelineResult) -> str:
    return calibration_group_key_from_events(result.synthesis.event_by_id.values())


def calibration_group_key_from_events(events) -> str:
    parser_versions = sorted(
        {event["parser_version"] for event in events}, key=utf8_key
    )
    return sha256_digest(
        {
            "deployment_profile": "isolated-edr-ndr-lab.v1",
            "EDR_detector_version": "trustepisode.detector-implementation.v1",
            "NDR_detector_version": "trustepisode.detector-implementation.v1",
            "parser_versions": parser_versions,
        }
    )


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
