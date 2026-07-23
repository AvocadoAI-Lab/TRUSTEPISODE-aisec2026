#!/usr/bin/env python3
"""Generate LaTeX macros/tables from fair-baseline and companion result JSON."""
from __future__ import annotations

import json
from pathlib import Path


def fmt(mean, sd=None) -> str:
    if mean is None:
        return "undefined"
    if sd is None:
        return f"{mean:.3f}"
    return f"${mean:.3f}\\pm{sd:.3f}$"


def _det_block(det: dict, *keys: str) -> dict:
    for k in keys:
        if k in det:
            return det[k]
    return {}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    derived = root / "results" / "derived"
    fair = json.loads((derived / "fair_baselines.json").read_text(encoding="utf-8"))
    m2 = json.loads((derived / "m2_waterfall.json").read_text(encoding="utf-8"))
    mech = json.loads((derived / "mechanism_cards.json").read_text(encoding="utf-8"))
    det = json.loads((derived / "determinism_matrix.json").read_text(encoding="utf-8"))
    cont = json.loads((derived / "contamination_tradeoff.json").read_text(encoding="utf-8"))
    audit = json.loads((derived / "audit_conformance.json").read_text(encoding="utf-8"))
    tax = json.loads((derived / "taxonomy_ag.json").read_text(encoding="utf-8"))
    ab = json.loads((derived / "ab_contract_baselines.json").read_text(encoding="utf-8"))
    agent = json.loads(
        (derived / "agent_boundary_conformance.json").read_text(encoding="utf-8")
    )
    llm = json.loads(
        (derived / "llm_grounding_pilot.json").read_text(encoding="utf-8")
    )
    gemma = json.loads(
        (derived / "llm_grounding_replication_gemma3_1b.json").read_text(
            encoding="utf-8"
        )
    )

    by = {b["builder"]: b for b in fair["builders"]}
    eb0, eb1, eb4 = by["EB0_FIXED_BIN_300s"], by["EB1_SLIDING_TIME"], by["EB4_TRUSTEPISODE"]
    fair_n = int(fair.get("cohort", {}).get("malicious_runs", eb4.get("n", 60)))

    def m(builder, metric):
        block = builder["metrics"][metric]
        return block["mean"], block["sample_sd"]

    paired_index = {
        (row["baseline"], row["metric"]): row for row in fair["paired_comparisons"]
    }
    paired_rows = []
    for row in fair["paired_comparisons"]:
        if row["baseline"] != "EB1_SLIDING_TIME":
            continue
        if row["metric"] not in {
            "action_coverage",
            "exact_complete_recovery",
            "fragmentation",
            "contamination",
            "episode_f1",
        }:
            continue
        lo, hi = row["ci95"]
        interp = row["interpretation"].replace("_", " ")
        if row["win"] == 0 and row["loss"] == 0:
            interp = "no observed difference"
        elif interp.strip() == "not statistically resolved":
            interp = "not resolved"
        paired_rows.append(
            f"{row['metric'].replace('_', '\\_')} & "
            f"${row['mean_delta']:.3f}$ & ${row['median_delta']:.3f}$ & "
            f"$[{lo:.3f},{hi:.3f}]$ & "
            f"{row['win']}/{row['tie']}/{row['loss']} & "
            f"{interp} \\\\"
        )

    builder_rows = []
    for name in [
        "EB0_FIXED_BIN_300s",
        "EB1_SLIDING_TIME",
        "EB2_SLIDING_ENTITY",
        "EB3_RELATION_NO_ADVANCED_GUARDS",
        "EB4_TRUSTEPISODE",
    ]:
        b = by[name]
        o = b["metrics"]
        role = b["role"]
        builder_rows.append(
            f"{name.replace('_', '\\_')} & {role} & "
            f"{fmt(o['action_coverage']['mean'], o['action_coverage']['sample_sd'])} & "
            f"{fmt(o['exact_complete_recovery']['mean'], o['exact_complete_recovery']['sample_sd'])} & "
            f"{fmt(o['fragmentation']['mean'], o['fragmentation']['sample_sd'])} & "
            f"{fmt(o['contamination']['mean'], o['contamination']['sample_sd'])} & "
            f"{fmt(o['episode_f1']['mean'], o['episode_f1']['sample_sd'])} \\\\"
        )

    mech_rows = []
    for c in mech["cards"]:
        status = "pass" if c["pass"] else "fail"
        exp = (
            c["expected_transition"]
            .replace("_", " ")
            .replace("[", "(")
            .replace("]", ")")
            .replace("'", "")
        )
        obs = (
            c["observed_transition"]
            .replace("_", "-")
            .replace("[", "(")
            .replace("]", ")")
            .replace("'", "")
            .replace("=", ":")
        )
        if len(exp) > 36:
            exp = exp[:33] + "..."
        if len(obs) > 36:
            obs = obs[:33] + "..."
        name = c["mechanism"].replace("_", "-")
        mech_rows.append(f"{name} & {status} & {exp} & {obs} \\\\")

    d1 = _det_block(det, "D1_CANONICAL_REPLAY")
    d2 = _det_block(det, "D2_DELIVERY_ORDER", "D2_INPUT_PERMUTATION")
    d3 = _det_block(det, "D3_INGEST_DELAY")
    d4 = _det_block(det, "D4_DUPLICATES", "D4_DUPLICATE_RETRY")
    n_runs = int(det.get("n_runs", d1.get("pass_count", 0)))
    d1_pass = int(d1.get("pass_count", 0))
    d1_reps = int((d1.get("rows") or [{}])[0].get("repeats", 10)) if d1.get("rows") else 10
    d1_exec = n_runs * d1_reps
    d2_canon = int(d2.get("canonical_reorder_pass_count", 0))
    d2_raw = int(d2.get("raw_order_robust_pass_count", 0))
    d3_pass = int(d3.get("pass_count", 0))
    d4_pass = int(d4.get("pass_count", 0))

    audit_pass = int(audit.get("pass_count", 0))
    audit_fail = int(audit.get("fail_count", 0))
    audit_total = audit_pass + audit_fail
    fail_codes = {
        "schema_invalid",
        "key_mismatch",
        "conflicting_duplicate",
        "digest_mismatch",
        "version_mismatch",
        "missing_input",
        "assembly_timeout",
    }
    covered = {
        f.get("observed_code")
        for f in audit.get("fixtures", [])
        if f.get("observed_code") in fail_codes and f.get("pass")
    }
    tax_rows = tax.get("conformance_rows", [])
    tax_pass = sum(1 for r in tax_rows if r.get("pass"))
    tax_total = len(tax_rows)
    tax_live = sum(1 for r in tax_rows if r.get("pass") and str(r.get("source", "")).startswith("results/"))

    det_rows = [
        f"D1 canonical replay & {n_runs} & {d1_reps}$\\times$/run & byte-identical digests & "
        f"{d1_pass} & {n_runs - d1_pass} & canonical ordered input \\\\",
        f"D2 raw delivery order & {n_runs} & 6 perms & equals baseline without reorder & "
        f"{d2_raw} & {n_runs - d2_raw} & not order-robust \\\\",
        f"D2 re-canonicalized & {n_runs} & 6 perms & equals baseline after sort & "
        f"{d2_canon} & {n_runs - d2_canon} & canonicalization required \\\\",
        f"D3 ingest delay & {n_runs} & horizon grid & successor/late invariants & "
        f"{d3_pass} & {n_runs - d3_pass} & prior digest preserved \\\\",
        f"D4 duplicates & {n_runs} & conflict/idempotent & reject or no-op & "
        f"{d4_pass} & {n_runs - d4_pass} & fail-closed conflicts \\\\",
        r"D5 single-writer & architecture & ownership & no same-run multi-writer & "
        r"documented & 0 & not lock-free concurrency \\",
    ]

    audit_fixture_rows = []
    for f in audit.get("fixtures", []):
        fid = str(f.get("id", "")).replace("_", "\\_")
        exp = str(f.get("expected_code", "")).replace("_", "\\_")
        obs = str(f.get("observed_code", "")).replace("_", "\\_")
        status = "pass" if f.get("pass") else "fail"
        prior = "no" if not f.get("prior_record_changed") else "yes"
        audit_fixture_rows.append(
            f"{fid} & {exp} & {obs} & {f.get('terminal_count', 0)} & {prior} & {status} \\\\"
        )

    tax_tex_rows = []
    for r in tax_rows:
        exp = str(r.get("expected_class", "")).replace("_", "\\_")
        obs = str(r.get("observed_class", "")).replace("_", "\\_")
        src = "live M2" if "M2" in str(r.get("id", "")) else "synthetic"
        status = "pass" if r.get("pass") else "fail"
        tax_tex_rows.append(f"{exp} & {obs} & {src} & {status} \\\\")

    ab_prop_rows = []
    for p in ab.get("property_matrix", []):
        name = str(p["property"]).replace("_", "\\_")
        def yn(v):
            return "yes" if v else "no"

        ab_prop_rows.append(
            f"{name} & {yn(p['AB0_Mutable'])} & {yn(p['AB1_Noncanonical'])} & "
            f"{yn(p['AB2_Silent_failure'])} & {yn(p['AB3_TrustEpisode'])} & "
            f"{str(p['evidence_type']).replace('_', ' ')} \\\\"
        )

    agent_rows = []
    for card in agent.get("cards", []):
        card_id = str(card["id"]).split("_", 1)[0]
        operation = str(card["operation"]).replace("_", "\\_")
        guard = str(card["guard"]).replace("_", "\\_")
        expected = str(card["expected"]).replace("_", " ")
        observed = str(card["observed"]).replace("_", " ")
        status = "pass" if card.get("pass") else "fail"
        agent_rows.append(
            f"{card_id} & {operation} & {guard} & {expected} & {observed} & {status} \\\\"
        )
    agent_pass = int(agent.get("pass_count", 0))
    agent_total = len(agent.get("cards", []))

    llm_summary = llm["summary"]
    llm_total = int(llm_summary["total"])
    gemma_summary = gemma["summary"]
    gemma_total = int(gemma_summary["total"])

    def llm_model_row(label: str, summary: dict, total: int) -> str:
        return (
            f"{label} & {summary['json_shape_pass']}/{total} & "
            f"{summary['answer_pass']}/{total} & "
            f"{summary['abstention_pass']}/{total} & "
            f"{summary['citation_set_pass']}/{total} & "
            f"{summary['exact_pass']}/{total} & "
            f"{summary['invalid_reference_count']} \\\\"
        )

    llm_rows = [
        llm_model_row("Qwen2.5-7B", llm_summary, llm_total),
        llm_model_row("Gemma3-1B", gemma_summary, gemma_total),
    ]

    out = root / "results" / "tables"
    out.mkdir(parents=True, exist_ok=True)
    (out / "fair_builder_rows.tex").write_text("\n".join(builder_rows) + "\n", encoding="utf-8")
    (out / "paired_eb1_rows.tex").write_text("\n".join(paired_rows) + "\n", encoding="utf-8")
    (out / "mechanism_rows.tex").write_text("\n".join(mech_rows) + "\n", encoding="utf-8")
    (out / "determinism_rows.tex").write_text("\n".join(det_rows) + "\n", encoding="utf-8")
    (out / "audit_fixture_rows.tex").write_text("\n".join(audit_fixture_rows) + "\n", encoding="utf-8")
    (out / "taxonomy_rows.tex").write_text("\n".join(tax_tex_rows) + "\n", encoding="utf-8")
    (out / "ab_property_rows.tex").write_text("\n".join(ab_prop_rows) + "\n", encoding="utf-8")
    (out / "agent_boundary_rows.tex").write_text(
        "\n".join(agent_rows) + "\n", encoding="utf-8"
    )

    eb1_action = paired_index[("EB1_SLIDING_TIME", "action_coverage")]
    eb2_action = paired_index[("EB2_SLIDING_ENTITY", "action_coverage")]
    eb1_action_lo, eb1_action_hi = eb1_action["ci95"]

    macros = f"""% Auto-generated from results/derived — do not edit by hand.
\\newcommand{{\\TeCov}}{{{m(eb4,'action_coverage')[0]:.3f}}}
\\newcommand{{\\TeExact}}{{{m(eb4,'exact_complete_recovery')[0]:.3f}}}
\\newcommand{{\\TeFOne}}{{{m(eb4,'episode_f1')[0]:.3f}}}
\\newcommand{{\\TeContam}}{{{m(eb4,'contamination')[0]:.3f}}}
\\newcommand{{\\EbZeroCov}}{{{m(eb0,'action_coverage')[0]:.3f}}}
\\newcommand{{\\EbZeroExact}}{{{m(eb0,'exact_complete_recovery')[0]:.3f}}}
\\newcommand{{\\EbZeroFOne}}{{{m(eb0,'episode_f1')[0]:.3f}}}
\\newcommand{{\\EbOneSlideCov}}{{{m(eb1,'action_coverage')[0]:.3f}}}
\\newcommand{{\\EbOneSlideExact}}{{{m(eb1,'exact_complete_recovery')[0]:.3f}}}
\\newcommand{{\\EbOneSlideFOne}}{{{m(eb1,'episode_f1')[0]:.3f}}}
\\newcommand{{\\EbOneActionDelta}}{{{eb1_action['mean_delta']:.3f}}}
\\newcommand{{\\EbOneActionCILo}}{{{eb1_action_lo:.3f}}}
\\newcommand{{\\EbOneActionCIHi}}{{{eb1_action_hi:.3f}}}
\\newcommand{{\\EbOneActionWTL}}{{{eb1_action['win']}/{eb1_action['tie']}/{eb1_action['loss']}}}
\\newcommand{{\\EbTwoActionWTL}}{{{eb2_action['win']}/{eb2_action['tie']}/{eb2_action['loss']}}}
\\newcommand{{\\MTwoClass}}{{{m2['final_classification'].replace('_', '\\_')}}}
\\newcommand{{\\MechPass}}{{{mech['pass_count']}}}
\\newcommand{{\\MechFail}}{{{mech['fail_count']}}}
\\newcommand{{\\DetNRuns}}{{{n_runs}}}
\\newcommand{{\\DetDOnePass}}{{{d1_pass}}}
\\newcommand{{\\DetDOneExec}}{{{d1_exec}}}
\\newcommand{{\\DetDTwoCanonPass}}{{{d2_canon}}}
\\newcommand{{\\DetDTwoRawPass}}{{{d2_raw}}}
\\newcommand{{\\DetDThreePass}}{{{d3_pass}}}
\\newcommand{{\\DetDFourPass}}{{{d4_pass}}}
\\newcommand{{\\AuditPass}}{{{audit_pass}}}
\\newcommand{{\\AuditTotal}}{{{audit_total}}}
\\newcommand{{\\AuditFailCodes}}{{{len(covered)}}}
\\newcommand{{\\TaxPass}}{{{tax_pass}}}
\\newcommand{{\\TaxTotal}}{{{tax_total}}}
\\newcommand{{\\TaxLive}}{{{tax_live}}}
\\newcommand{{\\AgentBoundaryPass}}{{{agent_pass}}}
\\newcommand{{\\AgentBoundaryTotal}}{{{agent_total}}}
\\newcommand{{\\LlmPilotExact}}{{{llm_summary['exact_pass']}}}
\\newcommand{{\\LlmPilotTotal}}{{{llm_total}}}
\\newcommand{{\\LlmPilotAnswers}}{{{llm_summary['answer_pass']}}}
\\newcommand{{\\LlmPilotAbstain}}{{{llm_summary['abstention_pass']}}}
\\newcommand{{\\LlmPilotCitations}}{{{llm_summary['citation_set_pass']}}}
\\newcommand{{\\LlmPilotInvalidRefs}}{{{llm_summary['invalid_reference_count']}}}
\\newcommand{{\\GemmaPilotJson}}{{{gemma_summary['json_shape_pass']}}}
\\newcommand{{\\GemmaPilotAnswers}}{{{gemma_summary['answer_pass']}}}
\\newcommand{{\\GemmaPilotAbstain}}{{{gemma_summary['abstention_pass']}}}
\\newcommand{{\\GemmaPilotCitations}}{{{gemma_summary['citation_set_pass']}}}
\\newcommand{{\\GemmaPilotExact}}{{{gemma_summary['exact_pass']}}}
\\newcommand{{\\GemmaPilotInvalidRefs}}{{{gemma_summary['invalid_reference_count']}}}
\\newcommand{{\\ConcConcurrent}}{{{cont['summary_by_builder']['EB4_TRUSTEPISODE']['concurrent_contamination_mean']:.3f}}}
"""
    (out / "result_macros.tex").write_text(macros, encoding="utf-8")

    (out / "tab_fair_baselines.tex").write_text(
        rf"""\begin{{table*}}[!t]
\caption{{Fair sliding-gap baselines versus legacy fixed bins on the sealed {fair_n}-run M1--M7 malicious cohort
(mean $\pm$ sample SD). Primary comparisons share $W_{{gap}}=300$\,s and $W_{{max}}=3600$\,s.}}
\label{{tab:fair-baselines}}
\centering
\scriptsize
\setlength{{\tabcolsep}}{{4pt}}
\begin{{tabular}}{{@{{}}llccccc@{{}}}}
\toprule
\textbf{{Builder}} & \textbf{{Role}} & \textbf{{Coverage}} & \textbf{{Exact-comp.}} & \textbf{{Frag.}} & \textbf{{Contam.}} & \textbf{{F1}} \\
\midrule
"""
        + "\n".join(builder_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table*}
""",
        encoding="utf-8",
    )

    (out / "tab_paired.tex").write_text(
        r"""\begin{table*}[!t]
\caption{Paired differences EB4$-$EB1\_SLIDING\_TIME (contamination/fragmentation flipped so positive favors EB4).
Bootstrap: 2000 run-cluster resamples, seed 20260721. Zero deltas reported as no observed difference.}
\label{tab:paired-eb1}
\centering
\small
\setlength{\tabcolsep}{5pt}
\begin{tabular}{@{}lccccc@{}}
\toprule
\textbf{Metric} & \textbf{Mean $\Delta$} & \textbf{Median $\Delta$} & \textbf{95\% CI} & \textbf{W/T/L} & \textbf{Interpretation} \\
\midrule
"""
        + "\n".join(paired_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table*}
""",
        encoding="utf-8",
    )

    (out / "tab_mechanism.tex").write_text(
        r"""\begin{table*}[!t]
\caption{Targeted synthetic mechanism cards (conformance only; not mixed into primary effectiveness).}
\label{tab:mechanism}
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}llll@{}}
\toprule
\textbf{Card} & \textbf{Result} & \textbf{Expected} & \textbf{Observed} \\
\midrule
"""
        + "\n".join(mech_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table*}
""",
        encoding="utf-8",
    )

    (out / "tab_determinism.tex").write_text(
        r"""\begin{table*}[!t]
\caption{Determinism matrix on all \DetNRuns{} sealed malicious runs (D1--D5).}
\label{tab:determinism}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}lp{0.08\textwidth}p{0.12\textwidth}p{0.18\textwidth}ccp{0.18\textwidth}@{}}
\toprule
\textbf{Test} & \textbf{Runs} & \textbf{Variants} & \textbf{Expected invariant} & \textbf{Pass} & \textbf{Fail} & \textbf{Interpretation} \\
\midrule
"""
        + "\n".join(det_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table*}
""",
        encoding="utf-8",
    )

    (out / "tab_audit_a12.tex").write_text(
        r"""\begin{table*}[!t]
\caption{A1--A12 audit conformance fixtures (synthetic; covers all seven AssemblyFailureRecord codes).}
\label{tab:audit-a12}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}llllcc@{}}
\toprule
\textbf{Fixture} & \textbf{Expected} & \textbf{Observed} & \textbf{Term.} & \textbf{Prior chg?} & \textbf{Result} \\
\midrule
"""
        + "\n".join(audit_fixture_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table*}
""",
        encoding="utf-8",
    )

    (out / "tab_taxonomy_ag.tex").write_text(
        r"""\begin{table*}[!t]
\caption{A--G evidence-loss taxonomy conformance (synthetic A--G plus one sealed live M2 as D).}
\label{tab:taxonomy-ag}
\centering
\scriptsize
\begin{tabular}{@{}llcc@{}}
\toprule
\textbf{True class} & \textbf{Predicted} & \textbf{Source} & \textbf{Result} \\
\midrule
"""
        + "\n".join(tax_tex_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table*}
""",
        encoding="utf-8",
    )

    (out / "tab_ab_contract.tex").write_text(
        r"""\begin{table*}[!t]
\caption{Contract ablation / reference-implementation comparison (synthetic isolation study; not SOTA product baselines).}
\label{tab:ab-contract}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}lccccp{0.18\textwidth}@{}}
\toprule
\textbf{Property} & \textbf{AB0 Mutable} & \textbf{AB1 Noncan.} & \textbf{AB2 Silent} & \textbf{TrustEpisode} & \textbf{Evidence} \\
\midrule
"""
        + "\n".join(ab_prop_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table*}
""",
        encoding="utf-8",
    )

    (out / "tab_agent_boundary.tex").write_text(
        r"""\begin{table*}[!t]
\caption{Downstream-agent canonical-record boundary cards (synthetic conformance only; not LLM accuracy or deployed authorization).}
\label{tab:agent-boundary}
\centering
\scriptsize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}p{0.04\textwidth}p{0.34\textwidth}p{0.22\textwidth}llll@{}}
\toprule
\textbf{Card} & \textbf{Operation} & \textbf{Guard} & \textbf{Expected} & \textbf{Observed} & \textbf{Result} \\
\midrule
"""
        + "\n".join(agent_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table*}
""",
        encoding="utf-8",
    )

    (out / "tab_llm_grounding.tex").write_text(
        r"""\begin{table}[!t]
\caption{Held-out AuditRecord pilots. Gemma was locked after the Qwen result but before model download. Exact requires answer, abstention flag, and citation set to match.}
\label{tab:llm-grounding}
\centering
\scriptsize
\setlength{\tabcolsep}{2pt}
\begin{tabular}{@{}lcccccc@{}}
\toprule
\textbf{Model} & \textbf{JSON} & \textbf{Answer} & \textbf{Abst.} & \textbf{Cite} & \textbf{Exact} & \textbf{Bad ptr.} \\
\midrule
"""
        + "\n".join(llm_rows)
        + r"""
\bottomrule
\end{tabular}
\end{table}
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "n_runs": n_runs,
                "d1_pass": d1_pass,
                "d1_exec": d1_exec,
                "audit_pass": audit_pass,
                "audit_fail_codes": len(covered),
                "tax_pass": tax_pass,
                "tax_total": tax_total,
                "agent_boundary_pass": agent_pass,
                "agent_boundary_total": agent_total,
                "llm_pilot_exact": llm_summary["exact_pass"],
                "llm_pilot_total": llm_total,
                "gemma_pilot_exact": gemma_summary["exact_pass"],
                "gemma_pilot_total": gemma_total,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
