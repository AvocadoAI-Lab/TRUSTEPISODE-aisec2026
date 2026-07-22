# TrustEpisode Round Delivery Report — Fair Baselines / Mechanism / M2 / Determinism

Date: 2026-07-21  
Paper: *TrustEpisode: A Deterministic and Replayable Contract for EDR/NDR Episode Formation*  
Scheme: **B** (formation/audit; no fitted ML effectiveness)

---

## 1. Modified / added files (this round)

### Scripts
- `scripts/run_fair_baselines.py` (+ `.sh`)
- `scripts/run_targeted_cards.py` (+ `.sh`)
- `scripts/run_m2_trace.py` (+ `.sh`)
- `scripts/run_determinism_matrix.py` (+ `.sh`)
- `scripts/run_contamination_analysis.py`
- `scripts/run_paired_analysis.sh` (wrapper)
- `scripts/run_optional_scorer.py` (+ `.sh`, fail-closed exit 2)
- `scripts/generate_tables.py` (macros + fair/paired/mechanism tables)
- `scripts/verify_claims.py`

### Results (new; sealed Table-4 cells untouched)
- `results/raw/fair_baselines/`
- `results/raw/targeted_cards/`
- `results/raw/m2_trace/`
- `results/raw/determinism/`
- `results/raw/scorer/STATUS.json`
- `results/derived/{fair_baselines,mechanism_cards,m2_waterfall,determinism_matrix,contamination_tradeoff}.json`
- `results/tables/{result_macros,tab_fair_baselines,tab_paired,mechanism_rows}.tex`

### Manuscript
- `main.tex` abstract
- `sections/{intro,arch,exps,conc,related}.tex`
- `CLAIM_EVIDENCE_MATRIX.md`
- this report

---

## 2. Fair baseline definitions

| ID | Definition |
|---|---|
| **EB0_FIXED_BIN_300s** | Legacy naive fixed 300 s bins; secondary reference only |
| **EB1_SLIDING_TIME** | \(W_{gap}=300\), \(W_{max}=3600\); time proximity only; same event-time order / finalization |
| **EB2_SLIDING_ENTITY** | Same lifecycle; entity overlap only; no causal/session/endpoint precedence; no hub/merge/late |
| **EB3_RELATION_NO_ADVANCED_GUARDS** | All relations; hub off; no parent merge; no late successor |
| **EB4_TRUSTEPISODE** | Full production policy |

Primary comparison: EB1 vs EB2 vs EB3 vs EB4. EB0 legacy only.

---

## 3. Configuration digests (`results/derived/fair_baselines.json`)

| Builder | config_digest |
|---|---|
| EB0_FIXED_BIN_300s | `sha256:c77007a1fe4ff72a6608a7d3f44934c20596215c5cc7349cd1d5e5ee72ae5352` |
| EB1_SLIDING_TIME | `sha256:476e9c34ea98c0af080259c5fced3ed2d6b94a07bf65140f69bfbfb5228cd0b0` |
| EB2_SLIDING_ENTITY | `sha256:1f56732096212771adb5c274cf0ee8e0639f23601a05d136b548d90b411aa771` |
| EB3_RELATION_NO_ADVANCED_GUARDS | `sha256:9dba25444641deb49d9a3b45d6604ee4c7e0c10389390fdee1193ca7e3478ecf` |
| EB4_TRUSTEPISODE | `sha256:b5d28d7dd88eb3e23b6f73e9e5c52bda6c00a73b7d9bf977f8b0d4491ea3950e` |

Bootstrap: seed `20260721`, \(n=2000\), unit = complete run.

---

## 4. Paired comparison (EB4 − EB1_SLIDING_TIME)

All primary metrics: mean/median Δ = 0; 95% CI [0,0]; W/T/L = 0/60/0; interpretation = **not statistically resolved**.

---

## 5–6. Mechanism cards & ablation trigger

| Card | Pass | Ablation differentially triggered? |
|---|---|---|
| T1_PROCESS_CAUSAL | pass | yes (1→2 episodes without causal) |
| T2_AUTH_SESSION | pass | session alone insufficient under v1 (entity still links) — documented |
| T3_ENDPOINT_MAPPING | pass | endpoint alone insufficient under v1 — documented |
| T4_HUB_GUARD | pass | yes (episode count changes) |
| T5_PARENT_MERGE | pass | yes (parent IDs) |
| T6_LATE_SUCCESSOR | pass | yes |
| T7_BEYOND_HORIZON | pass | yes (LateEvidenceRecord) |
| T8_TIE_BREAK | pass | canonical equal; raw reverse differs |

Live M1–M6: advanced guards **not** differentially exercised (EB1–EB4 metrics identical).

---

## 7–8. M2 waterfall & class

| Stage | Expected | Observed | Drop |
|---|---:|---:|---:|
| receipt_success | 10 | 10 | 0 |
| raw_observable | 10 | 10 | 0 |
| normalized_file_transfer_present | 10 | 0 | 10 |
| normalized_as_remote_session_instead | 10 | 10 | — |
| episode_retained_file_transfer | 10 | 0 | 10 |
| episode_retained_remote_session | 10 | 10 | 0 |

**Final class: `D_token_mapping_failure`.** Must **not** call M2 coverage 0.75 a formation membership failure of already-normalized `file_transfer`.

---

## 9. Determinism matrix (12-run sample)

| Test | Result |
|---|---|
| D1 canonical replay ×10 | 12/12 pass |
| D2 re-canonicalized permutation | 12/12 pass |
| D2 raw delivery-order robustness | 0/12 pass |
| D4 duplicate retry | 12/12 pass |
| D5 same-run parallel | single-writer documented; not claimed |

---

## 10. Contamination trade-off

Concurrent-benign mean contamination ≈ **0.356**, identical for EB0–EB4 on concurrent subset. Completeness↑ vs fixed bins; **no contamination improvement vs fair sliding baselines**.

---

## 11. Optional ML scorer

**Not executed.** `run_optional_scorer.py` fail-closed (exit 2). Insufficient sealed labels for leakage-free run-level held-out. Scheme B: no AUPRC claimed.

---

## 12. Section 3 / 4 structure

**§3:** ownership → Evidence Fabric → health → Episode Synthesis → late revision → audit → **design-only** feature/scorer/calibrator interfaces → boundary (evaluated = formation/audit only).

**§4:** RQ1 fair baselines → RQ2 mechanism → RQ3 M2 observability → RQ4 determinism; plus contamination trade-off; limitations; no RQ5 scorer.

---

## 13. Abstract / conclusion

Updated to report: legacy EB0 gains; fair sliding **ties**; contamination trade-off; mechanism conformance; M2 token-mapping class; replay vs order-robustness split; unevaluated calibration/outage.

---

## 14. Claim-to-evidence

See `CLAIM_EVIDENCE_MATRIX.md`.

---

## 15. Supplementary archive SHA-256

```
45c191952c48411e0de534c2d99762c451e44f56f031277ceb8354715e1949ef
```
File: `TrustEpisode_reproducibility_companion_v1.zip` (matches appendix + sidecar).  
Note: round-2 fair-baseline/mechanism/M2/determinism JSON live under `results/` in the paper tree; companion ZIP is the prior sealed reproducibility bundle and was **not** silently rewritten.

---

## 16. Incomplete items & why

| Item | Why |
|---|---|
| Fitted scorer / group calibration / Brier/NLL | Labels/gate unmet; Scheme B |
| Formal RP partial telemetry / PO1 outage | Not executed (~50–80h); out of claim scope |
| M7 | Deprioritized by instruction |
| Live differential for hub/merge/late | Cohort does not trigger; only synthetic cards |
| Token-mapping bugfix for M2 | Diagnosed; fix deferred as post-analysis correction with new digests |

---

## 17. Strict AISec re-score

| Dimension | Score | Notes |
|---|---|---|
| Novelty | 5 / 10 | Clear formation contract; fair-baseline honesty reduces claimed empirical novelty |
| Technical soundness | 7.5 / 10 | Claims now aligned; M2 class correct; determinism split honest |
| Baseline fairness | 8 / 10 | Sliding fair baselines primary; fixed bins demoted |
| Experimental completeness | 6 / 10 | P0/P1 formation asks done; no ML/outage |
| AI/ML relevance | 2.5 / 10 | No fitted held-out ranking → weak AISec fit |
| Reproducibility | 7.5 / 10 | Scripts + digests + macros; companion SHA verified |
| Clarity | 8 / 10 | Abstract/§4 match evidence |
| **Overall** | **Weak Reject for AISec; better as security-systems / forensics correlation paper** | |

### Final venue judgment

**Not Accept-ready for AISec** as an AI/ML paper.  
**Weak Reject** at AISec if kept formation-only without ML.  
**Better venue fit:** security systems / digital forensics / SOC correlation workshop or systems track, **after** optionally completing a minimal locked-run scorer if AISec is mandatory.

**Verdict: 不適合以 AI 有效性主張投 AISec；可改投 security systems／forensics venue，或補最小可信 held-out scorer 後再議 borderline Weak Accept。**

---

## PDF (this round)

- `main.pdf` — 9 pages
- SHA-256: `B26B3A9628510A4E4D8C011FFBF013CF3C55AC5A0E21838C9B8AB06913FAAD03`
- `scripts/verify_claims.py` → `results/derived/claim_verification.json` (`ok: true`)
