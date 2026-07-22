from __future__ import annotations

import hashlib
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> Any:
    def parse_int(token: str) -> int:
        if token == "-0":
            raise ValueError(f"{path}: negative zero is forbidden")
        return int(token)

    def parse_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value) or (value == 0.0 and token.startswith("-")):
            raise ValueError(f"{path}: non-finite/negative-zero number")
        return value

    def reject_constant(token: str) -> None:
        raise ValueError(f"{path}: non-JSON numeric constant {token}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_int=parse_int,
        parse_float=parse_float,
        parse_constant=reject_constant,
    )


def canonical_example_bytes(value: Any) -> bytes:
    """RFC 8785-equivalent encoding for the supplied ASCII, finite-number examples."""

    def check(item: Any) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("non-finite JSON number")
        if isinstance(item, dict):
            if any(not key.isascii() for key in item):
                raise ValueError("example verifier requires ASCII object keys")
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)

    check(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify_schema_and_examples() -> None:
    schema = load_json(ROOT / "trustepisode_online.v1.schema.json")
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    for name in (
        "audit_record.valid.json",
        "audit_record.out_of_support.valid.json",
        "assembly_failure.valid.json",
        "late_evidence.valid.json",
    ):
        record = load_json(ROOT / "examples" / name)
        validator.validate(record)
        definition = schema["$defs"][record["object_type"]]
        fields = definition["x-canonical-digest-fields"]
        payload = {field: record[field] for field in fields}
        actual = "sha256:" + hashlib.sha256(canonical_example_bytes(payload)).hexdigest()
        if actual != record["canonical_digest"]:
            raise AssertionError(f"{name}: canonical digest mismatch")

    rejected = load_json(ROOT / "examples" / "audit_record.reject-label.json")
    if not list(validator.iter_errors(rejected)):
        raise AssertionError("label-leakage example unexpectedly passed")


def verify_registry() -> None:
    registry = load_json(ROOT / "result_registry.v1.json")
    if registry["unexecuted_cell"] != "pending":
        raise AssertionError("unexecuted result sentinel changed")
    if registry["not_applicable_cell"] != "N/A":
        raise AssertionError("not-applicable sentinel changed")
    expected = {"RT1", "RT2", "RT3a", "RT3b", "RT4", "RT5", "RT6", "RT7"}
    if set(registry["registries"]) != expected:
        raise AssertionError("RT registry keys changed")
    for key in ("RT1", "RT3a", "RT3b"):
        if "C_dec_binary" not in registry["registries"][key]["columns"]:
            raise AssertionError(f"{key}: C_dec_binary missing")
    rt5 = registry["registries"]["RT5"]
    if "po1_cell_id" not in rt5["row_key"] or "trace_digest" not in rt5["columns"]:
        raise AssertionError("RT5 does not preserve physical-trace pairing")


def verify_closed_protocols() -> None:
    thresholds = load_json(ROOT / "thresholds.v1.json")
    if thresholds["raw_scorer_training"]["intercept_domain"] != "b in real numbers (unconstrained)":
        raise AssertionError("raw scorer intercept is not unconstrained")
    resolver = thresholds["detector_availability_resolution"]
    if "eligible_detector_count=0" not in resolver["feature_eligibility_precedence"]:
        raise AssertionError("zero-detector eligibility precedence missing")
    if "balanced" not in thresholds["calibration_group_gate"]["fold_assignment_artifact"].lower():
        # The algorithm is load-balanced; the sealed artifact must still be present.
        if "positive_count" not in thresholds["calibration_group_gate"]["fold_assignment_artifact"]:
            raise AssertionError("balanced group-fold artifact missing")

    schema = load_json(ROOT / "trustepisode_online.v1.schema.json")
    audit_required = set(schema["$defs"]["AuditRecord"]["required"])
    if not {"detector_observation", "eligible_detector_count", "eligibility_reason"}.issubset(audit_required):
        raise AssertionError("AuditRecord detector/eligibility fields missing")
    if schema["$defs"]["EvidenceReference"]["properties"]["reference_kind"]["const"] != "object":
        raise AssertionError("object reference discriminator missing")
    if "ReferenceSentinel" not in schema["$defs"] or "VersionBinding" not in schema["$defs"]:
        raise AssertionError("reference sentinel or version binding missing")
    if "preserves array element order" not in schema["x-array-order-rule"]:
        raise AssertionError("application-level array ordering rule missing")

    cards = load_json(ROOT / "scenario_cards.v1.json")
    if cards["contract_version"] != "trustepisode.scenario-cards.v3":
        raise AssertionError("Linux-only scenario-card contract is not v3")
    if [item["id"] for item in cards["malicious_cards"]] != [f"M{i}" for i in range(1, 8)]:
        raise AssertionError("malicious card IDs changed")
    if [item["id"] for item in cards["benign_cards"]] != [f"B{i}" for i in range(1, 9)]:
        raise AssertionError("benign card IDs changed")
    abilities = cards["ability_catalog"]
    allowed_images = set(cards["image_contract"]["allowed_keys"])
    if allowed_images != {"ubuntu2204_edr_target_v1", "ubuntu2204_edr_service_v1"}:
        raise AssertionError("scenario-card image set is not the frozen Linux-only set")
    serialized_cards = json.dumps(cards, sort_keys=True).lower()
    if "powershell" in serialized_cards or "win11" in serialized_cards or "windows target" in serialized_cards:
        raise AssertionError("Windows execution dependency remains in Linux-only cards")
    required = {"id", "image_keys", "ability_ids", "offset_seconds", "success_receipt_abilities", "cleanup_ability_ids", "expected", "failure_predicates", "cleanup_success"}
    for card in cards["malicious_cards"] + cards["benign_cards"]:
        if not required.issubset(card):
            raise AssertionError(f"{card['id']}: incomplete execution tuple")
        if len(card["ability_ids"]) != len(card["offset_seconds"]):
            raise AssertionError(f"{card['id']}: ability/offset mismatch")
        if any(item not in abilities for item in card["ability_ids"] + card["cleanup_ability_ids"]):
            raise AssertionError(f"{card['id']}: unknown ability")
        if not set(card["success_receipt_abilities"]).issubset(card["ability_ids"]):
            raise AssertionError(f"{card['id']}: success receipt ability is not executed")
        if not set(card["image_keys"]).issubset(allowed_images):
            raise AssertionError(f"{card['id']}: unknown image key")
    declared = set(cards["template_variables"]["target_command_required"])
    forbidden_variables = set(cards["template_variables"]["orchestrator_only_required"])
    for ability_id, ability in abilities.items():
        referenced = set(re.findall(r"\$\{([A-Za-z0-9_]+)\}", ability["command"]))
        unknown = referenced - declared
        if unknown:
            raise AssertionError(f"{ability_id}: undeclared variables {sorted(unknown)}")
        leaked = referenced & forbidden_variables
        if leaked:
            raise AssertionError(f"{ability_id}: orchestrator-only variables leaked {sorted(leaked)}")
        if ability["executor"] != "bash_no_profile":
            raise AssertionError(f"{ability_id}: non-Linux executor {ability['executor']}")

    lab = load_json(ROOT / "lab_manifest.v1.json")
    if lab["contract_version"] != "trustepisode.lab-manifest.v3":
        raise AssertionError("lab manifest is not v3")
    expected_services = {"caldera", "target-linux", "target-linux-02", "ndr-gateway"}
    if set(lab["formal_topology"]["data_plane"]["services"]) != expected_services:
        raise AssertionError("formal data-plane service set changed")
    execution = lab["formal_topology"]["execution_plane"]
    if "ENABLE_SANDCAT=false" not in execution["caldera_role"]:
        raise AssertionError("formal card-execution boundary is not explicit")
    if "excluded from RT1-RT7" not in execution["optional_mirrors"]:
        raise AssertionError("optional operational mirrors entered the primary evaluation")
    if lab["frozen_contracts"]["scenario_cards"] != cards["contract_version"]:
        raise AssertionError("lab/scenario-card contract mismatch")

    baselines = load_json(ROOT / "baseline_registry.v1.json")
    if set(baselines["baselines"]) != {"EB1", "EB2", "SB1", "SB2"}:
        raise AssertionError("baseline registry keys changed")
    if baselines["baselines"]["EB1"]["window_width_microseconds"] != 300_000_000:
        raise AssertionError("EB1 window changed")
    if "b in real" not in baselines["baselines"]["SB2"]["domains"][0]:
        raise AssertionError("SB2 intercept is not unconstrained")

    perturbations = load_json(ROOT / "perturbations.v1.json")
    if perturbations["contract_version"] != "trustepisode.perturbations.v3":
        raise AssertionError("perturbation contract is not v3")
    if "Cartesian" not in perturbations["design_matrix"]:
        raise AssertionError("source-dose matrix missing")
    replay = {item["id"]: item for item in perturbations["replay"]}
    if not all(item in replay["RP3"] for item in ("candidate_order", "index")):
        raise AssertionError("RP3 index contract missing")
    if not all(item in replay["RP5"] for item in ("anchor", "buffer_width", "buffer_index")):
        raise AssertionError("RP5 buffer contract missing")
    if "duplicate_id_preimage" not in replay["RP7"]:
        raise AssertionError("RP7 duplicate preimage missing")
    outage = perturbations["physical_outage"]["timestamp_contract"]
    if not all(item in outage for item in ("t_anchor", "t_ready", "t_censor", "detection_censoring", "recovery_censoring")):
        raise AssertionError("PO1 anchor/ready/censoring missing")
    po1 = perturbations["physical_outage"]
    sources = po1["source_families"]
    durations = po1["outage_duration_seconds"]
    repetitions = po1["valid_repetitions_per_source_duration_cell"]
    cards_order = po1["allocation"]["card_order"]
    expanded = []
    for source_index, source in enumerate(sources):
        for duration_index, duration in enumerate(durations):
            for repetition_index in range(repetitions):
                card_index = (repetition_index + 2 * source_index + duration_index) % 4
                expanded.append((source, duration, repetition_index, cards_order[card_index]))
    if len(expanded) != po1["required_physical_trace_count"] or len(expanded) != 40:
        raise AssertionError("PO1 does not expand to exactly 40 traces")
    allocation_counts = {card_id: 0 for card_id in cards_order}
    for _, _, _, card_id in expanded:
        allocation_counts[card_id] += 1
    if set(cards_order) != {"M1", "M3", "M4", "M7"} or set(allocation_counts.values()) != {10}:
        raise AssertionError(f"PO1 card allocation is not balanced: {allocation_counts}")
    if "same immutable raw trace" not in po1["comparator_reuse"]:
        raise AssertionError("PO1 comparator trace reuse is not frozen")
    if lab["frozen_contracts"]["perturbations"] != perturbations["contract_version"]:
        raise AssertionError("lab/perturbation contract mismatch")

    split = load_json(ROOT / "split_policy.v1.json")
    if split["contract_version"] != "trustepisode.split-policy.v2":
        raise AssertionError("split policy is not v2")
    po1_split = split["physical_outage_population"]
    if po1_split["partition"] != "locked_test" or po1_split["trace_count"] != 40:
        raise AssertionError("PO1 split population is not frozen to 40 locked-test traces")
    if lab["frozen_contracts"]["split_policy"] != split["contract_version"]:
        raise AssertionError("lab/split-policy contract mismatch")

    with (ROOT / "run_registry.template.csv").open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    required_registry_fields = {
        "offline_receipt_ids",
        "receipt_preimage_digest",
        "label_firewall_status",
        "raw_bundle_digest",
        "po1_cell_id",
        "allocated_card_id",
    }
    if not required_registry_fields.issubset(header) or "marker_preimage_digest" in header:
        raise AssertionError("run registry does not implement receipt/PO1 v3 fields")


def verify_manifest() -> None:
    manifest = load_json(ROOT / "manifest.v1.json")
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        content = path.read_bytes()
        if len(content) != entry["bytes"]:
            raise AssertionError(f"{entry['path']}: byte count mismatch")
        actual = hashlib.sha256(content).hexdigest()
        if actual != entry["sha256"]:
            raise AssertionError(f"{entry['path']}: SHA-256 mismatch")


def main() -> None:
    for path in ROOT.rglob("*.json"):
        load_json(path)
    verify_schema_and_examples()
    verify_registry()
    verify_closed_protocols()
    verify_manifest()
    print("TrustEpisode contract validation: PASS")


if __name__ == "__main__":
    main()
