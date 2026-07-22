# Claim-to-Evidence Matrix (DFRWS revision)

Evidence classes: live empirical | sealed offline replay | synthetic conformance | unit/integration | design-only | unsupported | future work

| Claim | RQ | Method | Evidence class | Cohort/fixture | Script | Raw | Derived | Digest/table | Manuscript | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| Sliding > fixed bins on coverage/exact | RQ5 | EB0 vs EB1–EB4 | sealed offline replay | 60 malicious | `run_fair_baselines.py` | `results/raw/fair_baselines/` | `fair_baselines.json` | Tab fair-baselines; macros TeCov/EbZero | Sec 4.5 | validated |
| EB1–EB4 no observed difference; 60/60 ties; Δ=0 | RQ5 | fair sliding | sealed offline replay | 60 malicious | `run_fair_baselines.py` | same | `fair_baselines.json` paired | Tab paired-eb1 | Sec 4.5; abstract | validated; not equivalence |
| Must not claim relation-aware > sliding-time | RQ5 | — | — | — | `verify_claims.py` | — | `claim_verification.json` | forbidden-phrase check | abstract/Sec4 | enforced |
| Canonical replay byte-identical all 60 | RQ1 | D1 | sealed offline replay | 60 M1–M6 | `run_determinism_matrix_60.py` | `results/raw/determinism/determinism_matrix_60.json` | `determinism_matrix.json` | Tab determinism; DetDOnePass=60 | Sec 4.6; abstract | validated |
| Raw delivery order not robust; re-canonicalized equal | RQ1 | D2 | sealed offline replay | 60 | same | same | same | DetDTwoRaw=0; DetDTwoCanon=60 | Sec 4.6 | validated |
| Late/horizon ingest invariants | RQ1/RQ2 | D3 | sealed offline replay | 60 | same | same | same | DetDThreePass=60 | Sec 4.6 | validated |
| Duplicate idempotent / conflict fail-closed | RQ1/RQ2 | D4 | sealed offline replay | 60 | same | same | same | DetDFourPass=60 | Sec 4.6 | validated |
| Single-writer architecture (not lock-free multi-writer) | RQ1 | D5 | design + documented | synthesizer | same | same | same | D5 note | Sec 4.6 | architecture guarantee |
| Seven AssemblyFailureRecord codes | RQ2 | A1–A12 | synthetic conformance | A1–A12 fixtures | `run_audit_conformance_a12.py` | `results/raw/audit/audit_conformance_a12.json` | `audit_conformance.json` | Tab audit-a12; AuditFailCodes=7 | Sec 4.7 | validated (18/18) |
| A–G taxonomy conformance | RQ3 | classifier | synthetic conformance | SYNTHETIC_A–G | `run_taxonomy_ag.py` / `classify_evidence_loss.py` | `results/raw/taxonomy/taxonomy_ag.json` | `taxonomy_ag.json` | Tab taxonomy-ag | Sec 4.8 | validated |
| M2 = D_token_mapping_failure | RQ3 | waterfall | live empirical | M2 sealed 10 runs | `run_m2_trace.py` | m2 raw | `m2_waterfall.json` | Tab m2-waterfall; MTwoClass | Sec 4.9 | validated |
| Taxonomy not fully field-validated | RQ3 | — | — | — | verify | — | — | wording check | Sec 4.8 | enforced |
| T1–T8 mechanism cards | RQ4 | targeted fixtures | synthetic conformance | T1–T8 | `run_targeted_cards.py` | `results/raw/targeted_cards/` | `mechanism_cards.json` | Tab mechanism; 8/8 | Sec 4.11 | validated; not live effectiveness |
| Live cohort does not stress advanced guards | RQ4 | EB1–EB4 tie | live + sealed offline | M1–M6 | fair baselines | — | fair_baselines | Tab scenario-families | Sec 4.5 | validated (negative) |
| AB0–AB3 contract properties | RQ2 | ablation stores | synthetic conformance | AB fixtures | `run_audit_baselines_ab.py` | `results/raw/audit_baselines/` | `ab_contract_baselines.json` | Tab ab-contract | Sec 4.10 | validated isolation study |
| Supplemental L1–L4 session/late live | — | live | future work / blocked | planned cohort | EXECUTION_PLAN.md | `results/raw/supplemental_live/` | — | Sec 4.12 blocked | blocked (API auth) |
| Fitted scorer/calibration | — | schema only | design-only | — | — | `results/raw/scorer/STATUS.json` | — | Sec 3.8 / App | not empirical |
| Primary Table-4 cells unchanged | — | sealed | live empirical | amended cohort | — | lab `table4_amended_results.json` | — | Tab table4 | Sec 4.5 | preserved |

## Digest anchors (regenerated on pack)

See `TrustEpisode_reproducibility_companion_v1.sha256` and Appendix archive block.
