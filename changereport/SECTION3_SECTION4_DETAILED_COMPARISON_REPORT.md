# Section 3／Section 4 詳細內文比較報告（紅刪綠增，中英對照）

日期：2026-07-10  
比較基準：修改前 `sections/arch.tex`、`sections/exps.tex` 的正文內容  
修改後檔案：`sections/arch.tex`、`sections/exps.tex`  

> 標註規則：<span style="color:red">紅色＝刪除或不再主張</span>；<span style="color:green">綠色＝新增或改寫後主張</span>。若 Markdown 檢視器不顯示顏色，請以「紅色／綠色」文字辨識。

---

## A. Section 3 Method 整體方向

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Section 3 開頭 | <span style="color:red">The method has four boundaries... maliciousness likelihood is separated from operational impact... agentic retrieval is used for assurance...</span> | <span style="color:green">TrustEpisode estimates whether a candidate episode produced from monitored security telemetry contains malicious activity...</span> | 刪除「四層風險框架」語氣，改成候選 episode calibration 問題。 | Replaced the broad risk-framework framing with a narrower candidate-episode calibration problem. |
| Section 3 開頭流程 | <span style="color:red">Evidence Fabric Layer + Episode Synthesis + Calibrated Trust Scoring + Agentic Evidence Assurance Layer</span> | <span style="color:green">events and source health -> Evidence Fabric -> Episode Synthesis -> compact scorer -> calibrator -> (P, U, AuditRecord)</span> | 新版只保留可實作、可驗證的 scoring path 與 sufficiency path。 | The new method keeps only the executable scoring path and sufficiency path. |
| Figure 1 | <span style="color:red">Identity on the primary telemetry path; Feature Extractor and Scope Resolver absent; ownership inconsistent with Table 2</span> | <span style="color:green">EDR/NDR-only primary path with explicit owners for NormalizedEvent, EpisodeRevision, [D,C], z, kappa, P, U, and AuditRecord</span> | Figure 1 已依 ownership table 重畫，Identity 明確不是 online input。 | Figure 1 now matches the ownership table and explicitly excludes Identity from online input. |

---

## B. Section 3.1 Problem Formulation and Assumptions

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Input definition | <span style="color:red">EDR, NDR, Syslog, identity logs, OT/ICS visibility, asset or CMDB records, policy records, maintenance schedules, and curated CTI</span> | <span style="color:green">observed security telemetry + source-health snapshot</span> | 輸入從大量知識線縮小為 telemetry 與 source health。 | Inputs were narrowed from many knowledge channels to telemetry plus source health. |
| Output definition | <span style="color:red">P, I, R, U, factor-level score trace, cited assurance narrative</span> | <span style="color:green">raw logit z, scoped calibrated probability P, structured U, immutable AuditRecord</span> | 刪除 impact、priority、narrative output；保留 probability、sufficiency、audit。 | Removed impact, priority, and narrative outputs; retained probability, sufficiency, and audit. |
| Probability meaning | <span style="color:red">operationally meaningful risk outputs</span> | <span style="color:green">P(Y=1 | observed evidence, source mask, source-health snapshot, frozen pipeline version)</span> | 把「風險」改成明確條件機率，避免外推為全域攻擊機率。 | Replaced vague risk wording with an explicit conditional probability. |
| Assumptions | <span style="color:red">agent non-authority assumption</span> | <span style="color:green">label-blind online assumption</span> | 因 agent 已不屬於 Section 3，改成 ground truth 不進 online path。 | Since the agent is out of scope, the assumption now protects against label leakage. |
| Notation table | <span style="color:red">I_epsilon, R_epsilon, K_epsilon, Q_epsilon, T_epsilon, G_epsilon, Crit, Exp, Scope, Sens</span> | <span style="color:green">e_i, epsilon^(r), E_epsilon, m_epsilon, h_epsilon, D_epsilon, C_epsilon, z_epsilon, P_epsilon, U_epsilon, W_gap, W_max</span> | 移除 orphan symbols 與無實驗支撐符號，只保留 Section 3 後續使用的符號。 | Removed unsupported or orphan symbols and retained only symbols used later in Section 3. |

---

## C. Section 3.2 Evidence Fabric

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Evidence object | <span style="color:red">e_i=(t_i,s_i,c_i,u_i,v_i,a_i,x_i,q_i,r_i,omega_i,p_i,m_i)</span> | <span style="color:green">e_i=(id_i,t_event,t_ingest,s_i,u_i,o_i,a_i,x_i,p_i,delta_i)</span> | 新 schema 加入 event time / ingest time 與 dependency group；移除 freshness、source reliability、CTI metadata 等未實作 scoring 欄位。 | The new schema keeps timing, provenance, and dependency deduplication while removing unsupported scoring metadata. |
| Graph node types | <span style="color:red">processes, hosts, users, files, IPs, domains, services, assets, identity sessions, CTI objects, policy records, maintenance windows</span> | <span style="color:green">source-neutral normalized events and canonical subject/object entities</span> | 從大型 typed evidence graph 縮為 online 可重播 event schema。 | The large typed graph was narrowed to replayable normalized events. |
| Schema support | <span style="color:red">OCSF + STIX as event/CTI schema support</span> | <span style="color:green">OCSF only as engineering field alignment, not calibration evidence</span> | Section 3 不再使用 CTI/STIX；OCSF 只作欄位對齊。 | Section 3 no longer uses CTI/STIX; OCSF is only field-alignment support. |
| Missing source handling | <span style="color:red">Missing source categories are represented explicitly...</span> | <span style="color:green">SourceCoverage stream with expected, health, lag, reason, coverage-policy version</span> | 新增獨立 SourceCoverage，避免把「沒有事件」誤解成「collector 健康」。 | Added SourceCoverage to distinguish no events from collector unavailability. |
| Ownership | <span style="color:red">No single ownership table</span> | <span style="color:green">Online object ownership table: NormalizedEvent, SourceCoverage, EpisodeRevision, FeatureVector, raw logit, CalibrationStatus, P, U, AuditRecord</span> | 明確每個 state 的 producer 與 forbidden actions。 | Added clear producers, consumers, and forbidden actions for every online object. |
| Identity boundary | <span style="color:red">Identity could enter the primary source path and alter the candidate universe</span> | <span style="color:green">Identity is post-inference and offline only; it cannot enter NormalizedEvent, Episode Synthesis, candidate IDs/membership, features, or calibrator manifests</span> | Identity pilot gate 只控制離線 exploratory annotation，不再控制 primary candidates。 | The Identity gate controls only an offline exploratory annotation, never primary candidates. |

---

## D. Section 3.3 Episode Synthesis

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Episode definition | <span style="color:red">epsilon=(V,E,t0,t1,A_epsilon) with affected asset set</span> | <span style="color:green">episode revision epsilon^(r) emitted by deterministic builder</span> | 刪除 affected asset set，避免導向 impact/priority。 | Removed affected asset set to avoid reintroducing impact/priority logic. |
| Linking formula | <span style="color:red">L(e_i,e_j)=w_T exp(...) + w_C causal + w_E entity + w_S source + w_K coherence + w_X correlation</span> | <span style="color:green">ell(e_i,e_j)=1 only when W_gap, W_max, and at least one allowed non-temporal relation hold</span> | 刪除 learned/weighted link score，改為 deterministic label-blind predicates。 | Replaced learned weighted linking with deterministic label-blind predicates. |
| Join threshold | <span style="color:red">max L(e_i,e_j) > theta_epsilon</span> | <span style="color:green">deterministic attach, merge, or start-new behavior under formation_policy_version</span> | 閾值家族改成可重播 formation policy。 | Threshold-style joining was replaced by replayable formation-policy behavior. |
| Relation types | <span style="color:red">attack-stage coherence, CTI, asset context, cross-source evidence jointly support episode hypothesis</span> | <span style="color:green">process parent/child, authenticated session, remote session, network endpoint mapping, same specific canonical entity</span> | link predicate 只保留可檢查、可實作關係。 | Link predicates now include only implementable and checkable relations. |
| Lifecycle | <span style="color:red">close inactive episodes and splits by validation-fitted threshold</span> | <span style="color:green">watermark, revision horizon, late-store/drop policy, new ScoreRecord per accepted late event</span> | 新增 streaming 與 revision 規格，避免默默改歷史。 | Added streaming and revision rules so history is not silently rewritten. |

---

## E. Section 3.4 Feature Semantics and Raw Score

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Feature set | <span style="color:red">D, K, C, Q, T, H, G, impact features</span> | <span style="color:green">Primary model uses D and C only</span> | 刪除無 ground truth 或會混淆責任的 feature。 | Removed features without ground truth or with unclear ownership. |
| Behavioral deviation | <span style="color:red">frequency deviation, z-score, graph reconstruction error, rare relations, etc.</span> | <span style="color:green">d_i = empirical CDF of source-native detector score fitted on training benign windows</span> | 從多種候選寫法改成單一可重現定義。 | Replaced a menu of possible definitions with one reproducible definition. |
| Corroboration | <span style="color:red">independent agreement among endpoint, network, identity, asset, and CTI sources</span> | <span style="color:green">C = binom(k,2)/binom(K,2), fixed expected source denominator</span> | 移除 available-source denominator，避免 outage 時 1/1 等於 3/3。 | Replaced available-source logic with fixed-denominator independent pairs. |
| Evidence quality | <span style="color:red">Q gates supporting and contradicting evidence and contributes to U</span> | <span style="color:green">Source health and provenance move to SourceCoverage and U, not to the raw scorer</span> | `Q` 不再作為 scorer feature。 | Q was removed from the scorer; source quality is handled by coverage and U. |
| Raw model | <span style="color:red">z includes D, K, C, bounded T, H and quality gates</span> | <span style="color:green">z = b + w_D D + w_C C, w_D,w_C >= 0</span> | 主模型縮為 stateless compact scorer。 | The main model is now a stateless compact scorer. |
| Objective | <span style="color:red">weighted BCE + ranking + calibration + monotonic + stability + CTI + sufficiency losses</span> | <span style="color:green">unweighted proper log-loss + L2</span> | 訓練目標只剩一個正式版本。 | The training objective now has one formal version. |

---

## F. Section 3.5 Scoring, Calibration, and U

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Maliciousness | <span style="color:red">P=Calibrate(sigma(z^P)) after quality-gated multi-feature formula</span> | <span style="color:green">P=sigma(a_g z + b_g), a_g > 0</span> | calibration 公式唯一化，raw score 不混稱 probability。 | Calibration is now a single affine formula, and raw score is not called probability. |
| Impact section | <span style="color:red">Operational impact I=h_I(Crit,Exp,Scope,Sens)</span> | <span style="color:green">Removed from Section 3</span> | 因沒有獨立 impact ground truth，整節刪除。 | Removed because the paper lacks independent labels for consequence modeling. |
| Priority section | <span style="color:red">R=P x I</span> | <span style="color:green">Removed from Section 3</span> | 不再把 operational queueing signal 放入本論文方法。 | Operational queueing is no longer part of the method. |
| U definition | <span style="color:red">U=h_U(G,Q,C,R_contr,L), output is sufficient/reduced/insufficient/contradictory</span> | <span style="color:green">U=(coverage, provenance, lateness, contradiction, calibration support)</span> | `U` 從互斥 class 改成五軸 deterministic profile。 | U changed from a mutually exclusive class to a deterministic five-axis profile. |
| Calibration support | <span style="color:red">Temperature scaling, isotonic regression, or learned calibration layer</span> | <span style="color:green">Global affine calibrator by default; group calibrator only with sample support</span> | 刪除校準方法選單，改成唯一主方法與 sample gate。 | Removed the calibration-method menu and added a sample-support gate. |
| Unsupported regimes | <span style="color:red">No explicit out-of-support rule</span> | <span style="color:green">calibration_status=out_of_support, decision_eligible=false</span> | 新增 unsupported source mask 行為。 | Added explicit behavior for unsupported source masks. |

---

## G. Section 3.6 Online Operation / Agentic Assurance / Failure Handling

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Online operation | <span style="color:red">compute P, I, R, U; store CTI items and counterfactuals without CTI/NDR/identity/asset criticality</span> | <span style="color:green">AuditRecord stores episode revision, versions, raw logit, P, features, source mask, source health, U, raw evidence references</span> | AuditRecord 改成 per-revision append-only technical record。 | AuditRecord became a per-revision append-only technical record. |
| Agentic assurance section | <span style="color:red">Agentic Evidence Assurance Protocol, citation gate, contradiction gate, retrieval, cited narrative</span> | <span style="color:green">Removed from Section 3</span> | Agent 不屬於本論文方法或實驗。 | Agent assurance is outside the method and experiments. |
| Failure handling | <span style="color:red">Missing NDR, stale CTI, conflicting CTI, stale CMDB, high-priority incomplete episode</span> | <span style="color:green">SourceCoverage and U expose missing, late, contradictory, and unsupported regimes without changing P</span> | failure handling 收斂到 SourceCoverage、U、AuditRecord。 | Failure handling is now represented through SourceCoverage, U, and AuditRecord. |
| Section ending | <span style="color:red">Safety boundaries with many removed modules</span> | <span style="color:green">The primary method is restricted to observed security telemetry, deterministic evidence sufficiency, and version-bound episode scoring.</span> | 結尾明確縮小方法邊界。 | The ending explicitly narrows the method boundary. |

---

## H. Section 4 Research Questions

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| RQ list | <span style="color:red">Five questions including direct LLM/RAG triage, misleading CTI, analyst-verifiable narratives, operational feasibility</span> | <span style="color:green">Four questions: episode validity, scoring/calibration, partial telemetry, reproducibility/cost</span> | RQ 從廣泛敘事改成四個能由 Lab 驗證的問題。 | RQs were narrowed to four lab-verifiable questions. |
| RQ2 | <span style="color:red">risk ranking and calibration relative to direct LLM/RAG triage</span> | <span style="color:green">compact scorer and affine calibration vs fixed baselines on same candidate population</span> | 移除 LLM/RAG baseline。 | Removed the LLM/RAG baseline. |
| RQ3 | <span style="color:red">telemetry loss, benign drift, misleading CTI</span> | <span style="color:green">partial telemetry, delay, late revisions surfaced through source masks, calibration support, and U</span> | robustness 改成 telemetry/missingness/calibration support。 | Robustness now focuses on telemetry, missingness, and calibration support. |

---

## I. Section 4 Dataset and Lab Setting

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Evaluation tiers | <span style="color:red">Tier 1, Tier 2, Tier 3 all appear as empirical evaluation pillars</span> | <span style="color:green">Formal claims use only the controlled Caldera v5.3.0 laboratory; public provenance datasets remain related-work context</span> | 移除不具 frozen EDR/NDR contract 的 formal Tier 1。 | Removed the formal Tier 1 because it does not implement the frozen EDR/NDR contract. |
| Ground truth scope | <span style="color:red">Attack reports and labels excluded from RAG corpus</span> | <span style="color:green">Labels join immutable AuditRecords only after online inference and insertion</span> | 因 RAG 已刪除，改成可驗證的 ground-truth firewall。 | Replaced the RAG boundary with an enforceable offline label firewall. |
| Controlled Lab | <span style="color:red">EDR, NDR, Syslog, identity, asset inventory, curated CTI, scoring service</span> | <span style="color:green">Frozen endpoint/network telemetry only; Identity is an offline M5-ID annotation</span> | Lab 範圍縮小且可驗證。 | Lab scope is smaller and verifiable. |
| Implementation | <span style="color:red">normalization service, graph store, scoring service, retrieval index, analyst-facing case interface</span> | <span style="color:green">Caldera control plane separated from telemetry data plane; source-health monitoring; offline Ground Truth Store</span> | 從產品服務敘事改為實驗拓樸與資料隔離。 | Replaced product-service narrative with experiment topology and data isolation. |

---

## J. Section 4 Ground Truth, Scenarios, and Splits

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Ground truth | <span style="color:red">Attack reports and scenario labels used only as ground truth</span> | <span style="color:green">Forbidden fields: operation_id, ability_id, adversary_profile, technique_label, attack_marker, scenario_class, label, split</span> | 新增具體 forbidden-field list 和 integration test 要求。 | Added a concrete forbidden-field list and integration-test requirement. |
| Label policy | <span style="color:red">No explicit episode-level positive/negative/mixed/ambiguous policy</span> | <span style="color:green">positive, negative, mixed, ambiguous labels with versioned policy</span> | 補上 episode-level label semantics。 | Added episode-level label semantics. |
| Scenarios | <span style="color:red">Scenario families described broadly in prose；M8 混入 replay 命名</span> | <span style="color:green">M1--M7 malicious scenario table、B1--B8 benign/hard-negative suite；replay 僅使用 RP0--RP7</span> | 場景改成最小可執行目錄，M8 已完全移除，不再與 replay interventions 混用。 | Scenarios became an executable minimum catalogue; M8 was removed and replay interventions use RP0--RP7 only. |
| Splits | <span style="color:red">Any analyst feedback used for recalibration logged separately</span> | <span style="color:green">split by campaign/run/time block; train/development/calibration/test isolated</span> | split policy 從敘述補強為硬規則。 | Split policy became a hard rule. |

---

## K. Section 4 Baselines, Ablations, and Metrics

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Baselines | <span style="color:red">static severity, fixed rule correlation, provenance scoring, CAPTAIN-inspired baseline, direct LLM/RAG triage</span> | <span style="color:green">EB1/EB2/EB3/EB3-H formation comparisons and SB1--SB7 scoring/calibration comparisons</span> | baseline 分成 formation 與 scoring，避免 candidate population 不公平，且刪除未註冊的 SB8。 | Baselines are split into formation and scoring groups to keep candidate populations fair, with the unregistered SB8 removed. |
| Component ablations | <span style="color:red">remove CTI, permit unbounded CTI, no-CTI/stale/conflicting/misleading CTI</span> | <span style="color:green">hub-suppression, D-only, uncalibrated, global/group-calibration, and missing-as-zero registered comparisons</span> | robustness/ablation 改為直接驗證核心 episode、corroboration 與 calibration 契約，不再使用 A1--A8 舊編號。 | Ablations now test the core episode, corroboration, and calibration contracts without the obsolete A1--A8 identifiers. |
| Evidence assurance metrics | <span style="color:red">citation-support precision, unsupported-claim rate, contradiction retrieval recall, agentic-investigation latency</span> | <span style="color:green">episode validity, AUPRC+prevalence, Brier, NLL, reliability, unsupported-rate, deterministic replay, latency</span> | metric 不再評估 agent narrative，改評估 calibration 與 replay。 | Metrics no longer evaluate agent narratives; they evaluate calibration and replay. |
| Statistics | <span style="color:red">means and confidence intervals over scenario seeds, time windows, or analyst samples</span> | <span style="color:green">statistical unit is independent campaign/run; cluster bootstrap; paired comparisons for replay perturbation</span> | 統計單位明確，不把 episodes 當獨立樣本。 | Statistical unit is now explicit; episodes are not treated as independent samples. |

---

## L. Section 4 Results and Discussion

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Result tables | <span style="color:red">Direct LLM/RAG triage row and trace-completeness column</span> | <span style="color:green">RT1--RT7 registries separate formation, ranking, calibration, replay, outage, cost, and errors</span> | 未執行欄位為 pending，結構不適用才是 N/A。 | Unexecuted cells are pending; only structural inapplicability is N/A. |
| Case studies | <span style="color:red">APT lateral movement with contextual CTI; false positive reduced by assurance layer narrative</span> | <span style="color:green">Registered RT1--RT7 schemas and absent plots until locked outputs exist</span> | 刪除尚未支撐的 narrative case studies，改成預註冊結果契約。 | Removed unsupported case studies and added pre-registered result contracts. |
| Discussion | <span style="color:red">Beyond adaptive provenance detection; Why Agentic RAG does not score; asset criticality and CTI quality limitations</span> | <span style="color:green">Limitations and Safety: controlled-lab scope, manifest-specific calibration, isolated non-destructive emulation</span> | 討論改成範圍限制與安全邊界。 | Discussion now focuses on scope limits and safety boundaries. |

### L.1 Submission Appendix and Ownership Follow-up

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Appendix A.1 | <span style="color:red">Prose summary claiming versioned objects</span> | <span style="color:green">Eight-object schema registry plus producer, canonical JSON/null, digest, late-record, assembly-outcome, and firewall rules</span> | 將摘要換成可核對且 producer 閉合的線上資料契約。 | Replaced the summary with an auditable, producer-closed online data contract. |
| Appendix A.2--A.4 | <span style="color:red">Narrative-only synthesis, parameter, and calibration summaries</span> | <span style="color:green">Candidate total order and IDs; parameter/threshold ownership; eight-row calibrator invalidation matrix</span> | 補齊正文逐項承諾的演算法與 matrix。 | Added the algorithm and matrix explicitly promised by the main text. |
| Appendix A.5 | <span style="color:red">Claim that reviewers received external scenario-card files</span> | <span style="color:green">In-PDF Lab/card/label contract with required counts and achieved counts pending</span> | PDF 不再把未附的 machine files 當成已交付證據。 | The PDF no longer treats unavailable machine files as delivered evidence. |
| Appendix A.6 | <span style="color:red">Result-contract summary only</span> | <span style="color:green">Three populations, deterministic split, exact interventions/metrics, and RT1--RT7 pending schema</span> | Population、matching 與結果 registry 現在確實存在。 | Populations, matching, and result registries now exist. |
| Identity | <span style="color:red">Pilot-gated Identity could share the primary path</span> | <span style="color:green">Offline post-inference annotation only; EDR/NDR candidate universe is invariant</span> | gate passage 也不能改變 primary candidate。 | Even a passed gate cannot alter the primary candidate universe. |

---

## M. 最終一致性檢查／Final Consistency Check

| 檢查項 | 結果 | 中文說明 | English explanation |
|---|---:|---|---|
| Section 3/4 禁用詞掃描 | 通過 | 指定禁用詞與舊公式在 `sections/arch.tex`、`sections/exps.tex` 無命中。 | The forbidden-term and obsolete-formula scan has no hits in Section 3/4 files. |
| Citation key 存在性 | 通過 | Section 3/4 使用的 citation keys 均存在於 `bib/references.bib`。 | All Section 3/4 citation keys exist in `bib/references.bib`. |
| Whole-paper scope | 通過 | Title、Abstract、Sections 1/2/5 已同步改為 EDR/NDR formation 與 scoped calibration。 | Title, abstract, and Sections 1/2/5 now match the final method boundary. |
| Submission appendix substance | 通過 | A.1--A.6 包含 schema、algorithm、threshold/U、calibration、Lab/labels 與 population/split/intervention/RT contracts。 | A.1--A.6 contain the artifacts promised by the main text. |
| PDF compile | 通過 | 已編譯 12 頁 `main.pdf`；投稿版 12/12 頁均已渲染檢查。`main_full.pdf` 不屬投稿驗證基準。 | Tectonic compiled the 12-page submission and all submission pages were inspected; `main_full.pdf` is outside the submission baseline. |
| AISec page limit | 通過 | Conclusion 位於第 9 頁、全文 12 頁，符合 10-page main / 12-page overall，但無剩餘頁數。 | The conclusion is on page 9 and the PDF reaches the 12-page overall limit. |
| Generative AI declaration | 已移除 | 依本次稿件決策刪除 PDF 尾段；正式投稿前須另核對 submission-system disclosure 規則。 | The trailing declaration was removed for this manuscript; submission-system disclosure rules still require a final author check. |
| Submission figures | 通過 | 投稿版保留 Figures 1--4；Figure 1/2 已同步 sole-producer、fixed-deadline 與 LateEvidenceRecord 契約。 | The submission retains Figures 1--4; Figures 1/2 now match sole-producer, fixed-deadline, and LateEvidenceRecord contracts. |

---

## N. 殘留風險／Remaining Risk

| 風險 | 中文說明 | English explanation |
|---|---|---|
| Empirical results | RT1--RT7 尚未執行，因此真實數值、intervals 與 plots 仍為 pending。 | RT1--RT7 have not been executed; real values, intervals, and plots remain pending. |
| Figure assets | 舊 figure 檔仍存在，但新版 Section 3/4 不再引用含 removed-module 語意的圖。 | Old figure assets remain, but revised Section 3/4 no longer references figures that imply removed modules. |
| TeX build | 已用專案內可攜 Tectonic 完成；若要改用 `latexmk`，仍需另外安裝完整 TeX toolchain。 | Completed with the portable Tectonic binary in the project; using `latexmk` would still require a full TeX toolchain. |

---

## O. AISec 頁數改良補遺／AISec Page-Limit Addendum

| 階段 | 頁數／Figures | 中文說明 | English explanation |
|---|---:|---|---|
| 完整改稿初版 | 22 / 9 | 方法、實驗與完整附錄均在單一 PDF，超過 AISec 全文限制。 | Method, evaluation, and the full appendix were in one PDF and exceeded the AISec overall limit. |
| 圖量收斂版 | 18 / 5 | 刪除四張重複流程圖，但完整 Appendix A--F 仍占主要篇幅。 | Four redundant workflow figures were removed, but the full Appendix A--F still dominated the page count. |
| 最終投稿版 | 12 / 4 | 投稿附錄提供可稽核 contracts；Conclusion 位於第 9 頁。 | The auditable submission is 12 pages, and the conclusion is on page 9. |
| 歷史完整重現版 | 20 / 9 | 只作內部歷史基準，不是投稿交付物，也不封裝於 companion。 | Historical internal baseline only; it is neither submitted nor packaged in the companion. |

頁數與全篇 scope 一致性已完成；目前唯一主要研究限制是 locked-test 結果尚未產生，RT1--RT7 仍維持 `pending`。

---

## P. Section 3 契約閉合補遺／Contract-Closure Addendum

| 原缺口 | 紅色刪除／Removed | 綠色新增／Added | 最終判定 |
|---|---|---|---|
| `m` ownership | <span style="color:red">由多段文字隱含計算</span> | <span style="color:green">Feature Extractor 單獨產生 health-independent `m`</span> | 已閉合 |
| Detector availability | <span style="color:red">Feature Extractor 無 health input 卻產生 health-dependent state</span> | <span style="color:green">Feature Extractor 產生 `o_det`；Scope Resolver 依固定 precedence 產生 resolved `a_det`</span> | 已閉合 |
| Eligibility | <span style="color:red">Assembler 隱含序列化 `decision_eligible`</span> | <span style="color:green">Scope Resolver 以 SupportDecision 單獨產生 `a_det,kappa,g,e`</span> | 已閉合 |
| Late revision | <span style="color:red">finalized episode 如何接受 late evidence 未定義</span> | <span style="color:green">首次 finalization 固定 `t_f+900s`；獨立 revisable index；late successor 不 reopen、不延長 deadline</span> | 已閉合 |
| Figure 2 | <span style="color:red">Late-store / drop</span> | <span style="color:green">closed successor + LateEvidenceRecord；late-store only</span> | 已閉合 |
| Conditional group | <span style="color:red">無 group key、final refit、exclusive resolver</span> | <span style="color:green">RFC 8785/SHA-256 key、calibration-partition final refit、duplicate-key rejection、group/global/OOS resolver</span> | 已閉合 |
| `u_contradiction` | <span style="color:red">frozen online rule 未實體化</span> | <span style="color:green">CR1 endpoint binding、CR2 normalized flow direction、CR3 process lineage</span> | 已閉合 |
| `horizon_exceeded` | <span style="color:red">不可在 immutable AuditRecord 中合法出現</span> | <span style="color:green">從 `U.lateness` 移除；beyond-horizon evidence 改由 LateEvidenceRecord 表達</span> | 已閉合 |
| Assembly failure | <span style="color:red">one AuditRecord per revision 與 fail-closed 衝突</span> | <span style="color:green">每個 revision 恰有一個 terminal AssemblyOutcome：AuditRecord 或 AssemblyFailureRecord</span> | 已閉合 |

---

## Q. Section 4 附件、重複次數、引用與表格補遺／Artifact, Repetition, Reference, and Table Addendum

| 原缺口 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation | 最終判定 |
|---|---|---|---|---|---:|
| Companion availability | <span style="color:red">Machine-readable contracts were described without a submission-bound artifact.</span> | <span style="color:green">The exact companion ZIP and SHA-256 are required supplementary material; a missing or mismatched upload invalidates the claim.</span> | PDF 已綁定必要 ZIP 與 digest；投稿時必須實際上傳完全相同的附件。 | The PDF binds a required ZIP and digest; the exact artifact must be uploaded with the submission. | PDF 已閉合；投稿動作必須完成 |
| Table 4 repetitions | <span style="color:red">10 successful repetitions per card/mode</span> | <span style="color:green">requires 10 valid repetitions per card/mode; achieved counts pending</span> | 將 protocol requirement 與尚未產生的實驗結果分離，避免虛構成功次數。 | Separates the protocol requirement from unexecuted achieved counts. | 已閉合 |
| CALDERA metadata | <span style="color:red">CALDERA v5.3.0 year inconsistent with its official release</span> | <span style="color:green">Year 2025; release 2025-04-24; annotated tag object and peeled commit retained separately</span> | 依官方 release 修正年份，保留正確的 tag object／peeled commit 區分。 | Corrected the release year while preserving the distinct tag-object and peeled-commit identifiers. | 已閉合 |
| OCSF metadata | <span style="color:red">Unverified version/commit concern</span> | <span style="color:green">OCSF 1.8.0, commit 6fa6499a0f8c9f449d342816e90e5f687c224b0a retained</span> | 對照官方 release 後確認原資料正確，無需改動。 | Official release metadata confirms the existing version and commit. | 已驗證 |
| Reference [14] | <span style="color:red">Incorrect author list and primary category</span> | <span style="color:green">Renjie Wu, Hu Wang, Hsiang-Ting Chen, Gustavo Carneiro; primaryClass=cs.CV</span> | 依 arXiv 正式條目修正作者與主要分類。 | Corrected the author list and primary category from the official arXiv record. | 已閉合 |
| Table callouts | <span style="color:red">Tables introduced without body callouts</span> | <span style="color:green">Every submission table label has an explicit `Table~\\ref{...}` callout before the float</span> | 投稿版目前共有 Tables 1--7；舊 Table 8 已合併進 Appendix A.6／Table 6 契約，不再是獨立浮動表。 | All seven current submission tables have explicit callouts; the former Table 8 contract is merged into Appendix A.6/Table 6 rather than remaining a separate float. | 已閉合 |
| Float placement | <span style="color:red">Tables 7/8 float into the References section</span> | <span style="color:green">`placeins` + `\\FloatBarrier` before bibliography; Table 7 renders before References</span> | 浮動表在 bibliography 前被清空；PDF 文字座標亦確認 Table 7 位於 References 標題之前。 | Floats are flushed before the bibliography, and PDF coordinates confirm Table 7 precedes the References heading. | 已閉合 |

本補遺的「已閉合」只適用於論文敘述、metadata、callout 與版面契約。RT1--RT7 的實際執行結果仍為 `pending`；若投稿系統沒有 companion 附件或有效匿名連結，artifact availability 仍不得標為已驗證。

---

## R. Conditional Fail 最終修正判定／Final Remediation Verdict

| 原判定缺口 | 紅色刪除／Removed | 綠色新增／Added | 最終判定 |
|---|---|---|---:|
| Split 無法執行 | <span style="color:red">每個 10-run stratum 套用 20-run 10/4/3/3 cycle，導致非 train partitions 為空</span> | <span style="color:green">每個 card-by-mode stratum 依 hash rank 執行 5/2/1/2；train/development/calibration/locked-test 全部非空</span> | PASS |
| Formation metrics 恆為零 | <span style="color:red">fragmentation/over-merge 使用 one-to-one assigned edges</span> | <span style="color:green">coverage/fragmentation/over-merge 使用 unassigned threshold-qualified graph；one-to-one assignment 只計 episode F1</span> | PASS |
| Late event 雙重 dispatch | <span style="color:red">先 start/attach/merge open candidate，再檢查 revisable lineage</span> | <span style="color:green">先查 revisable/closed indexes；命中後產生唯一 successor/side record 並 return；無命中才處理 open candidates</span> | PASS |
| Closed lineage 未定義 | <span style="color:red">無 lookup key、retention 或過期行為</span> | <span style="color:green">保存 canonical relation keys 與 latest revision 至 deadline+86400 s；過期 ingress 進 RT7 且不得新建 episode</span> | PASS |
| Health snapshot ownership | <span style="color:red">Assembler 需要 health，但 Table 1/Figure 1 無完整輸入</span> | <span style="color:green">Table 1 加入 Assembler consumer；Figure 1 畫出 referenced SourceCoverage path；snapshot 只能 dereference SupportDecision references</span> | PASS |
| Health/provenance predicates | <span style="color:red">degraded 與 required/optional 未凍結</span> | <span style="color:green">30 s heartbeat、120/600 s lag、miss-count/down 規則，以及 required membership/link/score/coverage/version roots 全部固定</span> | PASS |
| Assembly schema | <span style="color:red">deadline、failure enum、types、nullability、digest sets 不完整</span> | <span style="color:green">watermark+120 s、七個 failure codes、closed types/maps、P/group-key nullability、三種 record digest include sets</span> | PASS |
| Figure 2 outcomes | <span style="color:red">只畫 r 與 r+2 outcome</span> | <span style="color:green">r、r+1、r+2、r+3 各自具有 immutable terminal AssemblyOutcome</span> | PASS |
| Stream survivorship bias | <span style="color:red">C_stream 只包含 AuditRecord，decision cohort 排除 OOS/failure</span> | <span style="color:green">C_dec_all 包含 supported/OOS AuditRecord 與 AssemblyFailureRecord；C_dec_score 僅供 score metrics；C_stream 保留所有 revision outcomes</span> | PASS |
| Labels/matching | <span style="color:red">A_cov、contamination 與 label precedence 未閉合</span> | <span style="color:green">action-token formulas、zero-denominator handling、mixed→positive→negative→ambiguous precedence</span> | PASS |
| Replay/outage/cost | <span style="color:red">RP operators、PO1 timestamps、RT6 measurement 不完整</span> | <span style="color:green">RP0--RP7 exact operators；t_stop/t_detect/t_restore/t_h1/t_h2/t_ready/t_stable；1/2/4/8 workers、warm-up+5 repeats</span> | PASS |
| Group calibration | <span style="color:red">fold assignment 與 improvement sign 不明，單純 hash modulo 5 也不能保證 class-balanced folds</span> | <span style="color:green">完整 run 保持不可分；依 binary class counts 排序後，以 seed/hash tie-break 的 greedy normalized-load assignment；Delta Brier/NLL = global minus group</span> | PASS |
| Serialization claim/references | <span style="color:red">machine-readable claim 超過 PDF 證據；RFC 8785/Draft 2020-12 無正式引用</span> | <span style="color:green">改為 schema-ready in-PDF contract；新增 RFC 8785 與 JSON Schema Draft 2020-12 references</span> | PASS |
| AI 尾段 | <span style="color:red">Use of Generative AI paragraph</span> | <span style="color:green">依本次稿件決策完全移除；PDF 文字層掃描無命中</span> | 已移除 |

### R.1 最終總判定

| 範圍 | 原判定 | 最終判定 | 證據 |
|---|---:|---:|---|
| Agentic RAG／CTI 移除 | Pass | **PASS** | 僅存在 scope exclusion，不在架構或方法 path |
| Section 3 | 4 Pass / 4 Partial | **8 Pass / 0 Partial / 0 Fail** | Ownership、late dispatch、closed index、health、assembly、calibration 均閉合 |
| Section 4 | 2 Pass / 4 Partial / 2 Fail | **8 Pass / 0 Partial / 0 Fail** | Split 與 formation metrics 兩個 P0 已修正；其餘 protocols 完整化 |
| Appendix A.1--A.6 | Partial | **PASS** | A.1 schema-ready contract；A.6 executable split/metrics/interventions/cost |
| References | Partial | **PASS** | CALDERA、OCSF、Ref. [14]、RFC 8785、JSON Schema 已核對或補齊 |
| PDF 視覺與交叉引用 | Pass | **PASS** | 12/12 頁檢查；4 figures；7 tables；0 hbox/undefined/out-of-page；1.17pt final output vbox 無裁切 |
| Empirical results | pending，不扣分 | **pending，不扣分** | RT1--RT7 未填入虛構數據 |

**最終判定：PASS。** 原本造成 Conditional Fail 的兩個 Section 4 P0，以及 Section 3、Appendix、references 的 partial 缺口均已關閉。此 PASS 表示投稿稿件的 specification 與 PDF 完整性通過，不表示 empirical evaluation 已執行。

---

## S. D/C、Denominator、Label、RP 與 Schema 最終閉合／Final Closure Addendum

| 項目 | <span style="color:red">紅色刪除／Removed</span> | <span style="color:green">綠色新增／Added</span> | 中文說明 | English explanation | 判定 |
|---|---|---|---|---|---:|
| Detector registry | <span style="color:red">D/C 僅有概念式定義；detector IDs、方向、合法值與 tie 未固定</span> | <span style="color:green">三個 EDR + 三個 NDR IDs；finite binary64 [0,1]；higher-more-suspicious；mid-rank CDF；top-min(3,n)；exact dedup key</span> | 不同實作者對同一 detector stream 會得到相同 normalized D。 | Independent implementations now derive the same normalized D from the same detector stream. | PASS |
| Raw scorer | <span style="color:red">Eq. (7) 只有未封閉的線性 logit 與一般 NLL 敘述，且可能把 intercept 一併限制為非負</span> | <span style="color:green">lambda=1e-4 L2 objective；b in R、w_D/w_C nonnegative；deterministic L-BFGS-B；tolerances、cohort、iteration cap、artifact digest</span> | Training 已從敘述性公式變成唯一可重現的 frozen model artifact，且不再強制所有 logits 非負。 | Training is uniquely reproducible and no longer forces all logits to be nonnegative. | PASS |
| Decision denominator | <span style="color:red">C_dec 只收 decision-eligible AuditRecord，OOS/failure 可從母體消失；mixed/ambiguous 可能污染 binary metrics</span> | <span style="color:green">C_dec_all 收所有 outcomes；C_dec_score 收可評分 records；C_dec_binary 只收 post-outcome joined positive/negative labels</span> | OOS/failure 不會結構性為零，AUPRC/AUROC/Brier/NLL 不再使用 mixed/ambiguous。 | OOS/failure remain visible, while binary metrics exclude mixed and ambiguous labels. | PASS |
| Labels and coverage | <span style="color:red">g* 無 no-edge 定義；ID tie、truth conflict、run aggregation 與空分母未封閉</span> | <span style="color:green">UTF-8 ordering；g*=null；三種 iff conflict；run max-coverage mean；defined-contamination mean + undefined count；empty=undefined</span> | Ground truth 與 run summaries 對所有邊界條件只有一種結果。 | Ground truth and run summaries have one result for every boundary case. | PASS |
| RP0--RP7 | <span style="color:red">只有 seeded/level 敘述；Figure 4 殘留 M8、stochastic lag、stop-or-isolate</span> | <span style="color:green">canonical base order；HMAC child seed；domain-separated U；每個 object/source/interval/permutation/duplicate mapping；Figure 4 同步 RP0--RP7 + PO1</span> | Paired replay children 可由 base run 唯一重建。 | Every paired-replay child can be uniquely reconstructed from its base run. | PASS |
| Support/schema ownership | <span style="color:red">SupportDecision 沒有 exact health references；reference/input/failure/version/number 規則不完整</span> | <span style="color:green">coverage_ref_ids + health_snapshot_digest；canonical reference/input order；failure precedence；closed VersionSet；LateEvidence reason enum；finite-number rejection</span> | Assembler 不可自行重選 health，且同一輸入衝突只會得到一個 terminal outcome。 | The Assembler cannot reselect health, and identical conflicts yield one terminal outcome. | PASS |

**本輪最終判定：PASS。** Detector、baseline、scenario、perturbation 與 schema contracts 已納入 17-entry manifest；`main.pdf` 為 12 頁、4 figures、7 tables，12/12 頁最終視覺檢查已通過。Empirical RT1--RT7 仍維持 `pending`，不在此 specification-completion PASS 中偽裝為已執行結果。

---

## T. n=0、Binary Metrics、Executable Cards 與 Digest 最終補遺／Final Addendum

| 項目 | <span style="color:red">紅色刪除／Removed</span> | <span style="color:green">綠色新增／Added</span> | 中文說明 | English explanation | 判定 |
|---|---|---|---|---|---:|
| `n=0` eligibility | <span style="color:red">`no_detection` could yield supported kappa even when no legal detector value existed.</span> | <span style="color:green">`n=0` has precedence: kappa=out_of_support, e=false, reason=no_eligible_detector_value, and P=null.</span> | 沒有合法 detector value 時絕不進入 score cohort，無論 resolved state 是否為 `no_detection`。 | A revision with no legal detector value can never enter the score cohort, even when its resolved state is `no_detection`. | PASS |
| Eq. (7) intercept | <span style="color:red">`b,w_D,w_C >= 0`, which implied every raw logit was nonnegative.</span> | <span style="color:green">`b in R`; only `w_D,w_C >= 0`; the fixed L2 objective and solver contract remain.</span> | intercept 可為負，因此模型不再被迫輸出 sigmoid 至少 0.5。 | The intercept may be negative, so the model is no longer forced to emit a sigmoid score of at least 0.5. | PASS |
| Binary metric population | <span style="color:red">Class metrics used all scorable records and could include mixed/ambiguous labels.</span> | <span style="color:green">C_dec_binary contains only positive/negative records after terminal-outcome label join.</span> | AUPRC、AUROC、Brier、NLL 與 reliability 只在 binary cohort 計算。 | All class-dependent ranking and calibration metrics use only the binary cohort. | PASS |
| Failure-bias audit | <span style="color:red">Offline labels joined only successful AuditRecords.</span> | <span style="color:green">Labels join by EpisodeRevision digest after every terminal AssemblyOutcome, including AssemblyFailureRecord.</span> | RT1 可檢查 positive/negative 的 assembly failure rate 是否不同。 | RT1 can detect class-dependent assembly-failure bias. | PASS |
| Lab cards | <span style="color:red">M1--M7/B1--B8 listed names and expected observations without a unique executor contract.</span> | <span style="color:green">Each card binds image keys, exact ability/command templates, offsets, marker preimage, success/failure predicates, cleanup, and mode matrix.</span> | 相同 card 現在只能導出一種可執行 run definition。 | Each card now derives one executable run definition. | PASS |
| Baselines | <span style="color:red">EB1/EB2/SB1/SB2 were named but their event grouping, severity parsing, cohort, and optimizer were open.</span> | <span style="color:green">A frozen baseline registry fixes 300-second bins, within-bin entity components, root-deduplicated native severity, and SB2 training.</span> | Baseline 比較不再依實作者自行猜測。 | Baseline results no longer depend on implementer interpretation. | PASS |
| RP source×dose | <span style="color:red">Seeded perturbations omitted the RP3 index, RP5 width, RP7 ID preimage, and complete source×dose matrix.</span> | <span style="color:green">RP2--RP7 use a full source×dose Cartesian design; RP3/RP5/RP7 mappings and byte preimages are exact.</span> | 每個 replay child 可由 base run、source、dose 與 seed 唯一重建。 | Every replay child is uniquely reconstructed from its base run, source, dose, and seed. | PASS |
| PO1 and balanced folds | <span style="color:red">Outage anchor/readiness/censoring and group-fold balance were underspecified.</span> | <span style="color:green">PO1 fixes anchor through censor timestamps and 1800-second follow-up; group folds use deterministic greedy normalized class/run loads.</span> | Outage latency與 group gate 都有唯一且不漏 class 的計算方式。 | Outage latency and group gating now have unique, class-aware procedures. | PASS |
| Digest and ordering | <span style="color:red">Audit digest omitted detector observation; LateEvidence digest, sentinel, VersionSet, and array order were incomplete.</span> | <span style="color:green">Audit digest includes o_det/count/reason; LateEvidence has its own digest and ordered refs; every version has a digest; optional absence uses a closed sentinel.</span> | 應用層先按明定 key 排 reference arrays，再執行 JCS；不能假設 RFC 8785 會重排 array。 | The application sorts reference arrays by the specified keys before JCS; RFC 8785 is not assumed to reorder arrays. | PASS |
| Required companion | <span style="color:red">The PDF claimed machine-readable completeness without binding the exact submitted files.</span> | <span style="color:green">The PDF binds the required ZIP SHA-256 `6298bd2e...c81205`; missing or mismatched supplementary material invalidates the claim.</span> | 本機 contract 驗證完成不等於投稿完成；實際上傳是最後人工 gate。 | Local validation is not submission delivery; uploading the exact ZIP remains a mandatory human gate. | PASS in repository; upload pending |

**T 節判定：repository specification PASS。** 唯一仍需投稿者執行的非程式工作，是在 submission system 上傳完全相同的 companion ZIP；唯一仍未完成的研究工作，是使用這些 frozen contracts 執行真實 experiments 並取代 `pending`。
