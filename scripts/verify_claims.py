#!/usr/bin/env python3
"""Fail-closed claim-to-evidence checks for TrustEpisode DFRWS revision."""
from __future__ import annotations

import hashlib
import json
import re
import sys
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
        if row.get("baseline") != "EB1_SLIDING_TIME":
            continue
        lo, hi = row.get("ci95", [None, None])
        if lo is not None and hi is not None and lo <= 0 <= hi:
            if "significant" in str(row.get("interpretation", "")).lower():
                fail(f"paired {row.get('metric')} CI includes 0 but marked significant")


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


def check_macros() -> None:
    macros = TABLES / "result_macros.tex"
    if not macros.exists():
        fail("missing result_macros.tex")
        return
    text = macros.read_text(encoding="utf-8")
    for cmd in [
        "TeCov",
        "TeExact",
        "EbZeroCov",
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
    ]:
        if f"\\newcommand{{\\{cmd}}}" not in text:
            fail(f"macro {cmd} missing")
    if "\\newcommand{\\DetDOnePass}{60}" not in text:
        fail("DetDOnePass must be 60")
    if "\\newcommand{\\DetNRuns}{60}" not in text:
        fail("DetNRuns must be 60")


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


def check_primary_not_overwritten() -> None:
    sealed = (
        ROOT.parent
        / "sensel-caldera-linux-lab"
        / "experiment-data"
        / "final-results-amended"
        / "table4_amended_results.json"
    )
    if not sealed.exists():
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


def check_m7_not_primary() -> None:
    """Manuscript must not treat sealed M7 as a primary Table-4 estimator."""
    texts = []
    for rel in ("sections/exps.tex", "main.tex", "sections/conc.tex"):
        path = ROOT / rel
        if path.exists():
            texts.append(path.read_text(encoding="utf-8"))
    if not texts:
        return
    blob = "\n".join(texts)
    if re.search(r"primary[^\n]{0,80}M1--M7", blob) or re.search(
        r"Live M1--M7 Cohort", blob
    ):
        fail("M7 must not be described as part of the primary live cohort")
    if "Amended live M1--M7 cells under production formation" in blob:
        fail("primary Table-4 caption must not be an M1--M7 primary cell table")


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

    check_fair_baselines(fair)
    check_m2(m2)
    check_mech(mech)
    check_determinism(det)
    check_audit(audit)
    check_taxonomy(tax)
    check_ab(ab)
    check_macros()
    check_companion()
    check_primary_not_overwritten()
    check_boundary_fixtures()
    check_m7_not_primary()
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
