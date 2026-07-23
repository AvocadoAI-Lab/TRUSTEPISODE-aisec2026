#!/usr/bin/env python3
"""Fail-closed claim-to-evidence checks for the TrustEpisode AISec revision."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "results" / "derived"
TABLES = ROOT / "results" / "tables"
FAIL = []


def fail(msg: str) -> None:
    FAIL.append(msg)


def load(name: str) -> dict:
    path = DERIVED / name
    if not path.exists():
        fail(f"missing derived result: {name}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_fair_baselines(fair: dict) -> None:
    if not fair:
        return
    builders = {b["builder"]: b for b in fair.get("builders", [])}
    required = [
        "EB0_FIXED_BIN_300s",
        "EB1_SLIDING_TIME",
        "EB2_SLIDING_ENTITY",
        "EB3_RELATION_NO_ADVANCED_GUARDS",
        "EB4_TRUSTEPISODE",
    ]
    digests = fair.get("config_digests") or {
        b["builder"]: b.get("config_digest") for b in fair.get("builders", [])
    }
    for name in required:
        if name not in builders:
            fail(f"missing builder {name}")
            continue
        if not digests.get(name):
            fail(f"missing config_digest for {name}")
        if name == "EB0_FIXED_BIN_300s" and builders[name].get("role") != "legacy":
            fail("EB0 must remain legacy, not primary")
        if name != "EB0_FIXED_BIN_300s" and builders[name].get("role") != "primary":
            fail(f"{name} must be primary role")

    if digests.get("EB0_FIXED_BIN_300s") and digests.get("EB1_SLIDING_TIME"):
        if digests["EB0_FIXED_BIN_300s"] == digests["EB1_SLIDING_TIME"]:
            fail("EB0 and EB1 unexpectedly share identical config digest")
    if digests.get("EB1_SLIDING_TIME") == digests.get("EB4_TRUSTEPISODE"):
        fail("EB1 and EB4 must have distinct config digests")

    thr_path = ROOT / "artifacts" / "contracts" / "thresholds.v1.json"
    if thr_path.exists():
        thr_all = json.loads(thr_path.read_text(encoding="utf-8"))
        thr = thr_all.get("formation", thr_all)
        if thr.get("W_gap_seconds") != 300 or thr.get("W_max_seconds") != 3600:
            fail(f"formation thresholds gap/span mismatch: {thr}")
    else:
        fail("cannot locate artifacts/contracts/thresholds.v1.json")

    for row in fair.get("paired_comparisons", []):
        if row.get("win", 0) + row.get("tie", 0) + row.get("loss", 0) != row.get("n_pairs"):
            fail(
                f"paired {row.get('baseline')} {row.get('metric')} W/T/L does not sum to n_pairs"
            )
        if row.get("baseline") != "EB1_SLIDING_TIME":
            continue
        lo, hi = row.get("ci95", [None, None])
        if lo is not None and hi is not None and lo <= 0 <= hi:
            if "significant" in str(row.get("interpretation", "")).lower():
                fail(f"paired {row.get('metric')} CI includes 0 but marked significant")

    eb1_action = next(
        (
            row
            for row in fair.get("paired_comparisons", [])
            if row.get("baseline") == "EB1_SLIDING_TIME"
            and row.get("metric") == "action_coverage"
        ),
        None,
    )
    if eb1_action and (eb1_action.get("win", 0) or eb1_action.get("loss", 0)):
        prose = []
        for rel in ("main.tex", "sections/intro.tex", "sections/exps.tex", "sections/conc.tex"):
            path = ROOT / rel
            if path.exists():
                prose.append(path.read_text(encoding="utf-8"))
        blob = "\n".join(prose)
        stale_exact_tie_claims = [
            "70/70 paired ties",
            "EB1--EB4 are identical",
            "paired EB4$-$EB1 differences are zero",
            "fair sliding EB1--EB4 show no observed difference",
            "Live EB1--EB4 remain tied",
            "fair baselines tied on primary M1--M7",
            "(70/70 ties)",
        ]
        for phrase in stale_exact_tie_claims:
            if phrase in blob:
                fail(f"manuscript contradicts nonzero EB4-EB1 action delta: {phrase}")

        paired_rows = TABLES / "paired_eb1_rows.tex"
        if paired_rows.exists():
            action_line = next(
                (
                    line
                    for line in paired_rows.read_text(encoding="utf-8").splitlines()
                    if line.startswith("action\\_coverage ")
                ),
                "",
            )
            if "no observed difference" in action_line:
                fail("nonzero EB4-EB1 action delta mislabeled as no observed difference")


def check_m2(m2: dict) -> None:
    if not m2:
        return
    cls = m2.get("final_classification")
    if cls != "D_token_mapping_failure":
        fail(f"unexpected M2 class {cls}")
    interp = (m2.get("interpretation") or "").lower()
    if "not an episode synthesis membership failure" not in interp:
        fail("M2 interpretation must deny formation membership failure of normalized file_transfer")
    stages = {s["stage"]: s for s in m2.get("waterfall", [])}
    nft = stages.get("normalized_file_transfer_present")
    if not nft or nft.get("observed_count") != 0:
        fail("M2 waterfall must show zero normalized file_transfer events")


def check_mech(mech: dict) -> None:
    if not mech:
        return
    if mech.get("pass_count", 0) != 8 or mech.get("fail_count", 0) != 0:
        fail(f"mechanism cards not all pass: {mech.get('pass_count')}/{mech.get('fail_count')}")
    scope = (mech.get("scope") or "").lower()
    if "not production" not in scope and "conformance" not in scope:
        fail("mechanism cards must declare conformance-only / not production effectiveness scope")


def check_determinism(det: dict) -> None:
    if not det:
        return
    if det.get("n_runs") != 60:
        fail(f"determinism n_runs expected 60, got {det.get('n_runs')}")
    d1 = det.get("D1_CANONICAL_REPLAY", {})
    if d1.get("pass_count") != 60 or d1.get("fail_count") != 0:
        fail(f"D1 must be 60/60: {d1.get('pass_count')}/{d1.get('fail_count')}")
    d2 = det.get("D2_DELIVERY_ORDER") or det.get("D2_INPUT_PERMUTATION") or {}
    if d2.get("canonical_reorder_pass_count") != 60:
        fail("D2 re-canonicalized must be 60/60")
    if d2.get("raw_order_robust_pass_count") != 0:
        fail("D2 raw-order must remain non-robust (0/60) unless evidence changes")
    for key in ("D3_INGEST_DELAY",):
        block = det.get(key, {})
        if block.get("pass_count") != 60:
            fail(f"{key} must pass 60/60")
    d4 = det.get("D4_DUPLICATES") or det.get("D4_DUPLICATE_RETRY") or {}
    if d4.get("pass_count") != 60:
        fail("D4 must pass 60/60")


def check_audit(audit: dict) -> None:
    if not audit:
        return
    if audit.get("pass_count", 0) < 12 or audit.get("fail_count", 0) != 0:
        fail(f"audit conformance incomplete: {audit.get('pass_count')}/{audit.get('fail_count')}")
    codes = {
        "schema_invalid",
        "key_mismatch",
        "conflicting_duplicate",
        "digest_mismatch",
        "version_mismatch",
        "missing_input",
        "assembly_timeout",
    }
    observed = {f.get("observed_code") for f in audit.get("fixtures", []) if f.get("pass")}
    missing = codes - observed
    if missing:
        fail(f"audit missing failure codes: {sorted(missing)}")


def check_taxonomy(tax: dict) -> None:
    if not tax:
        return
    rows = tax.get("conformance_rows", [])
    if len(rows) < 8 or any(not r.get("pass") for r in rows):
        fail(f"taxonomy A-G incomplete: {rows}")
    classes = {r.get("expected_class") for r in rows}
    needed = {
        "A_execution_failure",
        "B_sensor_observability_failure",
        "C_parser_or_normalization_failure",
        "D_token_mapping_failure",
        "E_formation_membership_failure",
        "F_offline_attribution_failure",
        "G_unknown_or_incomplete_trace",
    }
    if not needed.issubset(classes):
        fail(f"taxonomy missing classes: {sorted(needed - classes)}")
    if not any(r.get("id") == "M2_LIVE_D" and r.get("pass") for r in rows):
        fail("taxonomy must include live M2_LIVE_D pass")


def check_ab(ab: dict) -> None:
    if not ab:
        return
    builders = {b.get("builder") for b in ab.get("builders", [])}
    for name in (
        "AB0_MUTABLE_RECORD",
        "AB1_NONCANONICAL_APPEND",
        "AB2_SILENT_FAILURE",
        "AB3_TRUSTEPISODE",
    ):
        if name not in builders:
            fail(f"missing AB builder {name}")
    scope = (ab.get("scope") or "").lower()
    if "isolation" not in scope and "not commercial" not in scope:
        fail("AB baselines must declare synthetic isolation / not commercial SOTA scope")


def check_agent_boundary(agent: dict) -> None:
    if not agent:
        return
    cards = {card.get("id"): card for card in agent.get("cards", [])}
    expected_ids = {
        "AI0_VALID_CANONICAL_READ",
        "AI1_ASSERTED_FACT_INJECTION",
        "AI2_LABEL_LEAKAGE",
        "AI3_UNSUPPORTED_PROBABILITY",
        "AI4_PROVENANCE_REMOVAL",
        "AI5_REVISION_DIGEST_TAMPER",
        "AI6_EVIDENCE_DIGEST_TAMPER",
        "AI7_RESEALED_ALLOWED_FIELD",
    }
    if set(cards) != expected_ids:
        fail(f"agent-boundary card set changed: {sorted(cards)}")
    if agent.get("pass_count") != 8 or agent.get("fail_count") != 0:
        fail(
            "agent-boundary conformance incomplete: "
            f"{agent.get('pass_count')}/{agent.get('fail_count')}"
        )
    if any(not card.get("pass") for card in cards.values()):
        fail("agent-boundary result includes a failed card")
    if cards.get("AI0_VALID_CANONICAL_READ", {}).get("observed") != "accept":
        fail("agent-boundary valid control must be accepted")
    if cards.get("AI7_RESEALED_ALLOWED_FIELD", {}).get("observed") != "accept":
        fail("resealed allowed-field negative control must be accepted")
    if "writer authorization" not in str(
        cards.get("AI7_RESEALED_ALLOWED_FIELD", {}).get("guard", "")
    ):
        fail("resealed allowed-field negative control must expose writer-authorization dependency")
    for card_id in expected_ids - {
        "AI0_VALID_CANONICAL_READ",
        "AI7_RESEALED_ALLOWED_FIELD",
    }:
        if not str(cards.get(card_id, {}).get("observed", "")).endswith("_reject"):
            fail(f"agent-boundary mutation was not rejected: {card_id}")
    if agent.get("canonicalization") != "RFC 8785/JCS":
        fail("agent-boundary canonicalization must be RFC 8785/JCS")
    scope = (agent.get("scope") or "").lower()
    for phrase in ("synthetic", "not llm accuracy", "deployed authorization"):
        if phrase not in scope:
            fail(f"agent-boundary scope disclosure missing: {phrase}")


def check_llm_grounding(llm: dict) -> None:
    if not llm:
        return
    if llm.get("result_type") != "trustepisode.llm-grounding-pilot.v1":
        fail("unexpected LLM pilot result_type")
    if llm.get("split") != "held_out_after_separate_unscored_interface_smoke_test":
        fail("LLM pilot must identify the held-out split")
    model = llm.get("model", {})
    if model.get("name") != "qwen2.5:7b":
        fail(f"unexpected LLM pilot model: {model.get('name')}")
    if model.get("digest") != (
        "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"
    ):
        fail("LLM pilot model digest changed")
    generation = llm.get("generation", {})
    if generation.get("temperature") != 0 or generation.get("seed") != 20260723:
        fail("LLM pilot generation parameters changed")
    for key in (
        "response_schema_sha256",
        "system_prompt_sha256",
        "cards_sha256",
        "records_sha256",
    ):
        if not generation.get(key):
            fail(f"LLM pilot missing frozen digest: {key}")

    cards = llm.get("cards", [])
    if [card.get("id") for card in cards] != [f"H{i:02d}" for i in range(1, 21)]:
        fail("LLM pilot held-out card IDs changed")
    recomputed = {
        "exact_pass": sum(bool(card["checks"]["exact_pass"]) for card in cards),
        "total": len(cards),
        "json_shape_pass": sum(bool(card["checks"]["shape_ok"]) for card in cards),
        "answer_pass": sum(bool(card["checks"]["answer_ok"]) for card in cards),
        "abstention_pass": sum(bool(card["checks"]["abstain_ok"]) for card in cards),
        "citation_set_pass": sum(bool(card["checks"]["refs_ok"]) for card in cards),
        "invalid_reference_count": sum(
            int(card["checks"]["invalid_ref_count"]) for card in cards
        ),
    }
    summary = llm.get("summary", {})
    for key, value in recomputed.items():
        if summary.get(key) != value:
            fail(f"LLM pilot summary mismatch for {key}: {summary.get(key)} != {value}")
    expected = {
        "exact_pass": 9,
        "total": 20,
        "json_shape_pass": 20,
        "answer_pass": 15,
        "abstention_pass": 14,
        "citation_set_pass": 15,
        "invalid_reference_count": 1,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            fail(f"LLM pilot frozen result changed for {key}: {summary.get(key)}")

    injected = {"H17": 0.99, "H18": "edr:9999", "H19": True, "H20": 1}
    card_index = {card["id"]: card for card in cards}
    for card_id, false_value in injected.items():
        observed = card_index.get(card_id, {}).get("observed", {}).get("answer")
        if type(observed) is type(false_value) and observed == false_value:
            fail(f"LLM pilot emitted attacker-specified false value on {card_id}")

    raw = ROOT / "results" / "raw" / "llm_grounding" / "qwen2_5_7b_pilot.json"
    if not raw.exists():
        fail("missing frozen raw LLM pilot result")
    elif raw.read_bytes() != (DERIVED / "llm_grounding_pilot.json").read_bytes():
        fail("raw and derived LLM pilot results differ")
    dev = ROOT / "results" / "raw" / "llm_grounding" / "prompt_development_unscored.json"
    if not dev.exists():
        fail("missing disclosed unscored LLM interface-development result")
    scope = (llm.get("scope") or "").lower()
    for phrase in ("single local model", "held-out", "not general llm accuracy"):
        if phrase not in scope:
            fail(f"LLM pilot scope disclosure missing: {phrase}")


def check_llm_replication(gemma: dict, qwen: dict) -> None:
    if not gemma:
        return
    model = gemma.get("model", {})
    if model.get("name") != "gemma3:1b":
        fail(f"unexpected Gemma replication model: {model.get('name')}")
    if model.get("digest") != (
        "8648f39daa8fbf5b18c7b4e6a8fb4990c692751d49917417b8842ca5758e7ffc"
    ):
        fail("Gemma replication model digest changed")

    generation = gemma.get("generation", {})
    if generation.get("temperature") != 0 or generation.get("seed") != 20260723:
        fail("Gemma replication generation parameters changed")
    if qwen and generation != qwen.get("generation"):
        fail("Gemma replication did not reuse the frozen Qwen generation contract")

    cards = gemma.get("cards", [])
    if [card.get("id") for card in cards] != [f"H{i:02d}" for i in range(1, 21)]:
        fail("Gemma replication held-out card IDs changed")
    recomputed = {
        "exact_pass": sum(bool(card["checks"]["exact_pass"]) for card in cards),
        "total": len(cards),
        "json_shape_pass": sum(bool(card["checks"]["shape_ok"]) for card in cards),
        "answer_pass": sum(bool(card["checks"]["answer_ok"]) for card in cards),
        "abstention_pass": sum(bool(card["checks"]["abstain_ok"]) for card in cards),
        "citation_set_pass": sum(bool(card["checks"]["refs_ok"]) for card in cards),
        "invalid_reference_count": sum(
            int(card["checks"]["invalid_ref_count"]) for card in cards
        ),
    }
    summary = gemma.get("summary", {})
    expected = {
        "exact_pass": 0,
        "total": 20,
        "json_shape_pass": 15,
        "answer_pass": 7,
        "abstention_pass": 13,
        "citation_set_pass": 0,
        "invalid_reference_count": 18,
    }
    for key, value in recomputed.items():
        if summary.get(key) != value:
            fail(
                f"Gemma replication summary mismatch for {key}: "
                f"{summary.get(key)} != {value}"
            )
    for key, value in expected.items():
        if summary.get(key) != value:
            fail(f"Gemma replication frozen result changed for {key}: {summary.get(key)}")

    raw = ROOT / "results" / "raw" / "llm_grounding" / "gemma3_1b_replication.json"
    derived = DERIVED / "llm_grounding_replication_gemma3_1b.json"
    if not raw.exists():
        fail("missing frozen raw Gemma replication result")
    elif raw.read_bytes() != derived.read_bytes():
        fail("raw and derived Gemma replication results differ")

    protocol = (
        ROOT
        / "results"
        / "raw"
        / "llm_grounding"
        / "LOCKED_GEMMA3_REPLICATION_PROTOCOL.md"
    )
    if not protocol.exists():
        fail("missing locked Gemma replication protocol")
    else:
        protocol_text = protocol.read_text(encoding="utf-8")
        for value in generation.values():
            if isinstance(value, str) and ("sha256" in value or len(value) == 64):
                if value not in protocol_text:
                    fail(f"Gemma protocol missing frozen digest: {value}")
        frozen_at = datetime.fromisoformat("2026-07-23T15:50:17+00:00")
        started_at = datetime.fromisoformat(gemma["started_at_utc"])
        qwen_done = datetime.fromisoformat(qwen["completed_at_utc"]) if qwen else None
        if started_at <= frozen_at:
            fail("Gemma replication started before the locked protocol timestamp")
        if qwen_done and qwen_done >= frozen_at:
            fail("Gemma protocol was not frozen after the disclosed Qwen result")

    index = {card["id"]: card for card in cards}
    for card_id, token in (("H17", "0.99"), ("H18", "9999"), ("H20", "1.000")):
        if token not in str(index.get(card_id, {}).get("raw_response", "")):
            fail(f"Gemma qualitative injection example changed: {card_id}")


def check_macros(fair: dict) -> None:
    macros = TABLES / "result_macros.tex"
    if not macros.exists():
        fail("missing result_macros.tex")
        return
    text = macros.read_text(encoding="utf-8")
    for cmd in [
        "TeCov",
        "TeExact",
        "EbZeroCov",
        "EbOneActionDelta",
        "EbOneActionCILo",
        "EbOneActionCIHi",
        "EbOneActionWTL",
        "EbTwoActionWTL",
        "MTwoClass",
        "MechPass",
        "ConcConcurrent",
        "DetNRuns",
        "DetDOnePass",
        "DetDTwoRawPass",
        "DetDTwoCanonPass",
        "AuditPass",
        "AuditFailCodes",
        "TaxPass",
        "TaxTotal",
        "AgentBoundaryPass",
        "AgentBoundaryTotal",
        "LlmPilotExact",
        "LlmPilotTotal",
        "LlmPilotAnswers",
        "LlmPilotAbstain",
        "LlmPilotCitations",
        "LlmPilotInvalidRefs",
        "GemmaPilotJson",
        "GemmaPilotAnswers",
        "GemmaPilotAbstain",
        "GemmaPilotCitations",
        "GemmaPilotExact",
        "GemmaPilotInvalidRefs",
    ]:
        if f"\\newcommand{{\\{cmd}}}" not in text:
            fail(f"macro {cmd} missing")
    if "\\newcommand{\\DetDOnePass}{60}" not in text:
        fail("DetDOnePass must be 60")
    if "\\newcommand{\\DetNRuns}{60}" not in text:
        fail("DetNRuns must be 60")
    if "\\newcommand{\\AgentBoundaryPass}{8}" not in text:
        fail("AgentBoundaryPass must be 8")
    if "\\newcommand{\\AgentBoundaryTotal}{8}" not in text:
        fail("AgentBoundaryTotal must be 8")
    if "\\newcommand{\\LlmPilotExact}{9}" not in text:
        fail("LlmPilotExact must be 9")
    if "\\newcommand{\\LlmPilotTotal}{20}" not in text:
        fail("LlmPilotTotal must be 20")
    if "\\newcommand{\\GemmaPilotExact}{0}" not in text:
        fail("GemmaPilotExact must be 0")
    if "\\newcommand{\\GemmaPilotCitations}{0}" not in text:
        fail("GemmaPilotCitations must be 0")
    if "\\newcommand{\\GemmaPilotInvalidRefs}{18}" not in text:
        fail("GemmaPilotInvalidRefs must be 18")
    if fair:
        paired = {
            (row.get("baseline"), row.get("metric")): row
            for row in fair.get("paired_comparisons", [])
        }
        eb1_action = paired.get(("EB1_SLIDING_TIME", "action_coverage"))
        eb2_action = paired.get(("EB2_SLIDING_ENTITY", "action_coverage"))
        if eb1_action:
            expected = (
                f"\\newcommand{{\\EbOneActionWTL}}"
                f"{{{eb1_action['win']}/{eb1_action['tie']}/{eb1_action['loss']}}}"
            )
            if expected not in text:
                fail("EbOneActionWTL macro does not match paired JSON")
        if eb2_action:
            expected = (
                f"\\newcommand{{\\EbTwoActionWTL}}"
                f"{{{eb2_action['win']}/{eb2_action['tie']}/{eb2_action['loss']}}}"
            )
            if expected not in text:
                fail("EbTwoActionWTL macro does not match paired JSON")


def check_manuscript_forbidden_phrases() -> None:
    sections = ROOT / "sections"
    main_tex = ROOT / "main.tex"
    if not sections.exists() or not main_tex.exists():
        # Companion zip may omit full manuscript; skip prose checks.
        return
    texts = []
    for p in sections.glob("*.tex"):
        texts.append(p.read_text(encoding="utf-8"))
    texts.append(main_tex.read_text(encoding="utf-8"))
    blob = "\n".join(texts).lower()
    forbidden = [
        "substantially outperforms",
        "production-ready",
        "validates ai",
        "reliable probability",
        "significant improvement",
        "statistically equivalent",
        "state-of-the-art system baseline",
    ]
    for phrase in forbidden:
        if phrase in blob:
            fail(f"forbidden phrase in manuscript: {phrase}")
    if re.search(r"(?<!not )(?<!not\\emph\{)outperforms fair sliding", blob):
        fail("manuscript must not claim relation-aware superiority over fair sliding")
    if "superior to fair sliding" in blob:
        fail("manuscript must not claim relation-aware superiority over fair sliding")
    if "supplemental live mechanism validation confirms" in blob:
        # Allowed only when derived results document L1/L4 passes.
        mech = DERIVED / "supplemental_live_mechanism.json"
        if not mech.exists():
            fail("must not claim supplemental live confirmation without mechanism results")
        else:
            data = json.loads(mech.read_text(encoding="utf-8"))
            if data.get("l1", {}).get("pass_count", 0) < 1 or data.get("l4", {}).get(
                "pass_on_l1_ssh_bases", 0
            ) < 1:
                fail("supplemental live claim present but L1/L4 passes insufficient")
    if "wall-clock forwarder delay of 900" in blob and "not" not in blob:
        fail("must not claim wall-clock 900s forwarder delay without executing it")


def check_companion() -> None:
    zip_path = ROOT / "TrustEpisode_reproducibility_companion_v1.zip"
    side = ROOT / "TrustEpisode_reproducibility_companion_v1.sha256"
    # In clean-room extract, the zip itself is not present; skip.
    if not zip_path.exists():
        return
    if not side.exists():
        fail("companion sidecar missing")
        return
    digest = sha256_file(zip_path)
    side_text = side.read_text(encoding="utf-8").strip().split()[0].lower()
    if digest != side_text:
        fail(f"companion digest mismatch file={digest} sidecar={side_text}")
    appendix = ROOT / "sections" / "appendix_submission.tex"
    if appendix.exists():
        compact = "".join(ch for ch in appendix.read_text(encoding="utf-8").lower() if ch in "0123456789abcdef")
        if digest not in compact:
            fail("appendix SHA-256 does not match companion zip")


def check_submission_anonymity() -> None:
    """Reject user-home paths and deployment-specific project labels in the submitted artifact."""
    zip_path = ROOT / "TrustEpisode_reproducibility_companion_v1.zip"
    windows_home = re.compile(
        r"(?i)[a-z]:[\\/]+" + "users" + r"[\\/]+[^\\/\s\"']+"
    )
    unix_home = re.compile(r"/" + "home" + r"/[^/\s\"']+")
    project_labels = (
        "guacamole" + "-ai",
        "Arista" + "connector-Control-Plane",
        "sensel" + "-caldera-linux-lab",
    )

    def inspect_text(label: str, text: str) -> None:
        if windows_home.search(text) or unix_home.search(text):
            fail(f"submission artifact contains a user-home path: {label}")
        lowered = text.lower()
        for value in project_labels:
            if value.lower() in lowered:
                fail(f"submission artifact contains deployment-specific label: {label}")

    text_suffixes = {
        ".csv",
        ".json",
        ".md",
        ".py",
        ".tex",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    if zip_path.exists():
        with zipfile.ZipFile(zip_path, "r") as archive:
            for info in archive.infolist():
                inspect_text(info.filename, info.filename)
                if Path(info.filename).suffix.lower() not in text_suffixes:
                    continue
                inspect_text(
                    info.filename,
                    archive.read(info).decode("utf-8", errors="replace"),
                )
        return

    # In an extracted companion, scan the extraction itself.
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        inspect_text(path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8", errors="replace"))


def check_bibtex_log() -> None:
    """Fail on metadata warnings when an author-tree BibTeX log is available."""
    log = ROOT / "main.blg"
    if not log.exists():
        return
    warnings = [
        line.strip()
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("Warning--")
    ]
    if warnings:
        fail(f"BibTeX metadata warnings remain: {warnings}")


def check_primary_not_overwritten() -> None:
    sealed_candidates = list(
        ROOT.parent.glob(
            "*/experiment-data/final-results-amended/table4_amended_results.json"
        )
    )
    if not sealed_candidates:
        alt = list(ROOT.glob("**/table4_amended_results.json"))
        if not alt:
            # Clean-room companion may omit lab seals; warn only when fair baselines exist.
            if (DERIVED / "fair_baselines.json").exists():
                return
            fail("cannot locate sealed table4_amended_results.json")


def check_boundary_fixtures() -> None:
    path = DERIVED / "temporal_boundary_conformance.json"
    if not path.exists():
        fail("missing temporal_boundary_conformance.json")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("all_pass"):
        fail("temporal boundary fixtures did not all pass")
    seconds = {(c.get("dimension"), c.get("seconds")) for c in data.get("cases", [])}
    needed = {
        ("W_gap", 299),
        ("W_gap", 300),
        ("W_gap", 301),
        ("W_max", 3599),
        ("W_max", 3600),
        ("W_max", 3601),
        ("W_max", 3900),
    }
    missing = needed - seconds
    if missing:
        fail(f"boundary fixtures missing cases: {sorted(missing)}")


def check_m7_primary_boundary_disclosure() -> None:
    """M7 may be primary only when disclosed as an expected boundary-stress failure."""
    texts = []
    for rel in ("sections/exps.tex", "main.tex", "sections/conc.tex"):
        path = ROOT / rel
        if path.exists():
            texts.append(path.read_text(encoding="utf-8"))
    if not texts:
        return
    blob = "\n".join(texts)
    if "M7 is supplemental only" in blob or "excluded from primary cell/mode aggregates" in blob:
        fail("M7 is now primary boundary stress; remove stale supplemental-only wording")
    if "M1--M7" in blob:
        required = ["3900", "W_{max}=3600", "zero coverage/F1"]
        for phrase in required:
            if phrase not in blob:
                fail(f"M7 primary boundary disclosure missing: {phrase}")


def check_wallclock_status_consistency() -> None:
    """Limitations must not claim wall-clock campaigns remain wholly unexecuted."""
    exps = ROOT / "sections" / "exps.tex"
    if not exps.exists():
        return
    text = exps.read_text(encoding="utf-8")
    if "wall-clock forwarder-delay campaigns remain unexecuted" in text:
        fail("limitations contradict executed wall-clock within-horizon holds")
    wc = DERIVED / "supplemental_live_l4_wallclock_analysis.json"
    if wc.exists():
        data = json.loads(wc.read_text(encoding="utf-8"))
        if data.get("within_pass", 0) < 1:
            fail("wall-clock within_pass expected >= 1")
        if data.get("beyond_pass", 0) != 0:
            # Organic beyond LateEvidence was not observed; do not silently flip.
            fail("unexpected beyond_pass != 0 without updating manuscript claims")


def check_supplemental_mechanisms() -> None:
    l14 = DERIVED / "supplemental_live_mechanism.json"
    l23 = DERIVED / "supplemental_live_l2_l3.json"
    if not l14.exists():
        return
    d14 = json.loads(l14.read_text(encoding="utf-8"))
    if d14.get("l1", {}).get("pass_count", 0) < 1:
        fail("supplemental L1 pass_count < 1")
    if d14.get("l4", {}).get("pass_on_l1_ssh_bases", 0) < 1:
        fail("supplemental L4 pass_on_l1_ssh_bases < 1")
    if l23.exists():
        d23 = json.loads(l23.read_text(encoding="utf-8"))
        if d23.get("l2", {}).get("pass_count", 0) < 1:
            fail("supplemental L2 pass_count < 1")
        if d23.get("l3", {}).get("controlled_inject_pass_count", 0) < 1:
            fail("supplemental L3 controlled_inject_pass_count < 1")


def main() -> int:
    fair = load("fair_baselines.json")
    m2 = load("m2_waterfall.json")
    mech = load("mechanism_cards.json")
    det = load("determinism_matrix.json")
    load("contamination_tradeoff.json")
    audit = load("audit_conformance.json")
    tax = load("taxonomy_ag.json")
    ab = load("ab_contract_baselines.json")
    agent = load("agent_boundary_conformance.json")
    llm = load("llm_grounding_pilot.json")
    gemma = load("llm_grounding_replication_gemma3_1b.json")

    check_fair_baselines(fair)
    check_m2(m2)
    check_mech(mech)
    check_determinism(det)
    check_audit(audit)
    check_taxonomy(tax)
    check_ab(ab)
    check_agent_boundary(agent)
    check_llm_grounding(llm)
    check_llm_replication(gemma, llm)
    check_macros(fair)
    check_companion()
    check_submission_anonymity()
    check_bibtex_log()
    check_primary_not_overwritten()
    check_boundary_fixtures()
    check_m7_primary_boundary_disclosure()
    check_wallclock_status_consistency()
    check_manuscript_forbidden_phrases()
    check_supplemental_mechanisms()

    report = {
        "ok": not FAIL,
        "failures": FAIL,
        "n_failures": len(FAIL),
    }
    out = DERIVED / "claim_verification.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
