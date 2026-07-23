# Claim-to-Evidence Matrix (AISec revision)

Evidence classes: live empirical | sealed offline replay | synthetic conformance | unit/integration | design-only | unsupported | future work

Companion execution boundary: the anonymous archive first verifies that Python imports its
packaged reference runtime, executes all 38 implementation tests, and re-executes A1--A12, A--G,
AB0--AB3, AI0--AI7, T1--T8, contract validation, and temporal boundary fixtures. It regenerates
tables and verifies the remaining reported summaries from
sealed JSON; it does not re-run live collection, raw-lab cohort re-synthesis, or Ollama. Producer
scripts below remain provenance pointers even when their raw inputs are intentionally not packed.
Supplemental live-result copies redact only absolute local `source_path` prefixes for anonymous
review; the author-retained sealed originals are unchanged.

| Claim | RQ | Method | Evidence class | Cohort/fixture | Script | Raw | Derived | Digest/table | Manuscript | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| Sliding policies descriptively improve over fixed bins | RQ5 | EB0 vs EB1–EB4 | sealed offline re-synthesis of live traces | 70 malicious M1–M7 | `run_fair_baselines.py` | `results/raw/fair_baselines/` | `fair_baselines.json` | Tab fair-baselines; macros TeCov/EbZero | Sec 4.5 | validated; paired uncertainty reported |
| EB4 matches EB2 on action coverage | RQ5 | fair sliding | sealed offline re-synthesis of live traces | 70 malicious M1–M7 | `run_fair_baselines.py` | same | `fair_baselines.json` paired | EbTwoActionWTL=0/70/0 | Sec 4.5; abstract | exact observed tie; not an equivalence test |
| EB4 trails EB1 on one concurrent-benign M7 run | RQ5 | EB4−EB1 | sealed offline re-synthesis of live traces | 70 malicious M1–M7 | `run_fair_baselines.py` | same | `fair_baselines.json` paired | W/T/L=0/69/1; mean Δ=−0.014; CI [−0.043,0] | Sec 4.5; abstract | not statistically resolved; no superiority claim |
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
| Live cohort rarely stresses advanced guards | RQ4 | EB1–EB4 comparison | live + sealed offline | M1–M7 | fair baselines | `results/raw/fair_baselines/per_run.json` | `fair_baselines.json` | one EB4 loss vs EB1/EB3 on concurrent-benign M7 | Sec 4.5 | validated negative/boundary-cost result |
| AB0–AB3 contract properties | RQ2 | ablation stores | synthetic conformance | AB fixtures | `run_audit_baselines_ab.py` | `results/raw/audit_baselines/` | `ab_contract_baselines.json` | Tab ab-contract | Sec 4.10 | validated isolation study |
| Downstream canonical-record boundary behavior | RQ6 | closed schema + RFC 8785 digest verification; external writer authorization is separate | synthetic conformance | AI0–AI7 | `run_agent_boundary_conformance.py` | `results/raw/agent_boundary/` | `agent_boundary_conformance.json` | Tab agent-boundary; 8/8 specified outcomes | Agent-Facing Mutation Conformance | one valid control accepted; six schema-invalid/unsealed mutations rejected; one resealed allowed-field negative control accepted, proving authorization is still required |
| Local-model AuditRecord reading | RQ6 | frozen prompt/schema + exact held-out labels | synthetic held-out single-model pilot | H01–H20 | `run_llm_grounding_pilot.py` | `results/raw/llm_grounding/qwen2_5_7b_pilot.json` | `llm_grounding_pilot.json` | Tab llm-grounding; answer 15/20, citation set 15/20, exact 9/20 | Held-Out Local-Model Grounding Pilot | once-run Qwen2.5-7B; 0/4 attacker-specified false values emitted but 0/4 prompt-conflict exact; not general LLM accuracy |
| Deployment-default model transfer audit | RQ6 | post-Qwen locked protocol; identical prompt/schema/cards/records/seed/scorer | exploratory same-card replication | H01–H20 | `run_llm_grounding_pilot.py` | `results/raw/llm_grounding/gemma3_1b_replication.json`; `LOCKED_GEMMA3_REPLICATION_PROTOCOL.md` | `llm_grounding_replication_gemma3_1b.json` | Tab llm-grounding; JSON 15/20, answer 7/20, citation set 0/20, exact 0/20, invalid pointers 18 | Held-Out Local-Model Grounding Audits | once-run Gemma3-1B; locked only after Qwen result; illustrative transfer failure, not preregistered model comparison or size-effect estimate |
| Supplemental L1–L4 mechanism evidence | — | live bases + offline ablation / controlled inject / wall-clock | mixed, explicitly partitioned | L1 3/3; L2 3/3; L3 controlled 3/3; L4 controlled 3/3; wall-clock within 2/2; beyond 0/2 organic LateEvidence | supplemental scripts | `results/raw/supplemental_live/` | supplemental derived JSON | Sec 4.14 | complete within stated evidence classes; not primary effectiveness |
| Fitted scorer/calibration | — | schema only | design-only | — | — | `results/raw/scorer/STATUS.json` | — | Sec 3.8 / App | not empirical |
| Primary Table-4 cells unchanged | — | sealed | live empirical | amended cohort | — | lab `table4_amended_results.json` | — | Tab table4 | Sec 4.5 | preserved |

## Digest anchors (regenerated on pack)

See `TrustEpisode_reproducibility_companion_v1.sha256` and Appendix archive block.
