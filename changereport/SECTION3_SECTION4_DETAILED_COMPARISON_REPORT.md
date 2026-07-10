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
| Three-tier setting | <span style="color:red">Tier 1, Tier 2, Tier 3 all appear as empirical evaluation pillars</span> | <span style="color:green">Tier 1 is formation-only; Tier 2 is primary; Tier 3 is optional external-validity study if data exist</span> | 明確每個 tier 可回答與不可回答的問題。 | Each tier now has explicit allowed and forbidden claims. |
| Tier 1 | <span style="color:red">Attack reports and labels excluded from RAG corpus</span> | <span style="color:green">Labels joined only after episode revisions are emitted</span> | 因 RAG 已刪除，改成 ground-truth firewall 語意。 | Since RAG was removed, the text now focuses on label-leakage prevention. |
| Tier 2 | <span style="color:red">EDR, NDR, Syslog, identity, asset inventory, curated CTI, scoring service</span> | <span style="color:green">First frozen scope uses endpoint and network telemetry; identity is pilot-gated</span> | Lab 範圍縮小且可驗證。 | Lab scope is smaller and verifiable. |
| Implementation | <span style="color:red">normalization service, graph store, scoring service, retrieval index, analyst-facing case interface</span> | <span style="color:green">Caldera control plane separated from telemetry data plane; source-health monitoring; offline Ground Truth Store</span> | 從產品服務敘事改為實驗拓樸與資料隔離。 | Replaced product-service narrative with experiment topology and data isolation. |

---

## J. Section 4 Ground Truth, Scenarios, and Splits

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Ground truth | <span style="color:red">Attack reports and scenario labels used only as ground truth</span> | <span style="color:green">Forbidden fields: operation_id, ability_id, adversary_profile, technique_label, attack_marker, scenario_class, label, split</span> | 新增具體 forbidden-field list 和 integration test 要求。 | Added a concrete forbidden-field list and integration-test requirement. |
| Label policy | <span style="color:red">No explicit episode-level positive/negative/mixed/ambiguous policy</span> | <span style="color:green">positive, negative, mixed, ambiguous labels with versioned policy</span> | 補上 episode-level label semantics。 | Added episode-level label semantics. |
| Scenarios | <span style="color:red">Scenario families described broadly in prose</span> | <span style="color:green">M1--M7 malicious scenario table and B1--B8 benign/hard-negative suite; M8 is only a replay perturbation family</span> | 場景改成最小可執行目錄，且不把 replay intervention 誤列為第八個攻擊場景。 | Scenarios became an executable minimum catalogue without misclassifying replay interventions as an eighth attack family. |
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
| Result tables | <span style="color:red">Direct LLM/RAG triage row and trace-completeness column</span> | <span style="color:green">R2 formation shell for EB1/EB2/EB3/EB3-H plus R3a ranking and R3b supported-calibration shells for SB1--SB6</span> | 結果表拆開 formation、ranking 與 calibration，且所有未執行欄位明確為 pending。 | Result tables now separate formation, ranking, and calibration, with every unexecuted cell explicitly pending. |
| Case studies | <span style="color:red">APT lateral movement with contextual CTI; false positive reduced by assurance layer narrative</span> | <span style="color:green">Additional reporting artifacts: Table R1-R4, reliability plots, error-analysis taxonomy</span> | 刪除尚未支撐的 narrative case studies，改成預註冊結果表。 | Removed unsupported narrative case studies and added pre-registered reporting artifacts. |
| Discussion | <span style="color:red">Beyond adaptive provenance detection; Why Agentic RAG does not score; asset criticality and CTI quality limitations</span> | <span style="color:green">Limitations and Safety: controlled lab scope, Tier 1 formation limits, optional field deployment, non-destructive isolated emulation</span> | 討論改成範圍限制與安全邊界。 | Discussion now focuses on scope limits and safety boundaries. |

### L.1 Submission Appendix and Ownership Follow-up

| 位置 | 紅色刪除／Removed | 綠色新增／Added | 中文說明 | English explanation |
|---|---|---|---|---|
| Appendix A.1 | <span style="color:red">Prose summary claiming versioned objects</span> | <span style="color:green">Five-object schema registry plus types, canonical JSON/null, digest, append-only, and firewall rules</span> | 將摘要換成可核對的線上資料契約。 | Replaced the summary with an auditable online data contract. |
| Appendix A.2--A.4 | <span style="color:red">Narrative-only synthesis, parameter, and calibration summaries</span> | <span style="color:green">Candidate total order and IDs; parameter/threshold ownership; eight-row calibrator invalidation matrix</span> | 補齊正文逐項承諾的演算法與 matrix。 | Added the algorithm and matrix explicitly promised by the main text. |
| Appendix A.5 | <span style="color:red">Claim that every complete scenario card appears in the submission appendix</span> | <span style="color:green">Family-level admission/failure contract; complete ordered cards explicitly assigned to the companion appendix</span> | 不再以兩頁附錄假稱容納所有逐卡 SOP。 | The submission no longer claims to contain every full scenario SOP. |
| Appendix A.6 | <span style="color:red">Result-contract summary only</span> | <span style="color:green">Matching rule, formulas, bootstrap seed, full RQ matrix, and R3a/R3b pending shells</span> | 公式、matching 與結果殼現在確實存在。 | Formulas, matching, and result shells now actually appear. |
| Identity | <span style="color:red">Pilot-gated Identity could share the primary path</span> | <span style="color:green">Offline post-inference annotation only; EDR/NDR candidate universe is invariant</span> | gate passage 也不能改變 primary candidate。 | Even a passed gate cannot alter the primary candidate universe. |

---

## M. 最終一致性檢查／Final Consistency Check

| 檢查項 | 結果 | 中文說明 | English explanation |
|---|---:|---|---|
| Section 3/4 禁用詞掃描 | 通過 | 指定禁用詞與舊公式在 `sections/arch.tex`、`sections/exps.tex` 無命中。 | The forbidden-term and obsolete-formula scan has no hits in Section 3/4 files. |
| Citation key 存在性 | 通過 | Section 3/4 使用的 citation keys 均存在於 `bib/references.bib`。 | All Section 3/4 citation keys exist in `bib/references.bib`. |
| Scope Freeze | 通過 | 未修改 Section 1、Section 2、Title、Abstract、Conclusion。 | Section 1, Section 2, Title, Abstract, and Conclusion were not modified. |
| Submission appendix substance | 通過 | A.1--A.6 實際包含 schemas、total order、parameter registry、invalidation matrix、formulas/matching、RQ matrix 與 R3a/R3b shells。 | A.1--A.6 now contain the artifacts promised by the main text. |
| PDF compile | 通過 | 已用可攜 Tectonic 編譯 12 頁 `main.pdf` 投稿版與 20 頁 `main_full.pdf` 完整版；投稿版 12/12 頁均已渲染檢查。 | Portable Tectonic compiled the 12-page submission and 20-page full version; all 12 submission pages were rendered and inspected. |
| AISec page limit | 通過 | 投稿版主文於第 10 頁結束、全文 12 頁，符合 AISec 2026 的 10-page main / 12-page overall 規則。 | The submission body ends on page 10 and the PDF has 12 pages, satisfying the official AISec 2026 limit. |
| Generative AI declaration | 通過 | 依 AISec 2026 CFP 在 references/appendices 後加入使用範圍與責任聲明。 | The required disclosure appears after the references/appendices. |
| Submission figures | 通過 | 投稿版保留 Figures 1--4；完整重現版另保留 linking-decision Figure 5。 | The submission retains Figures 1--4, while the full reproducibility version additionally retains linking-decision Figure 5. |

---

## N. 殘留風險／Remaining Risk

| 風險 | 中文說明 | English explanation |
|---|---|---|
| Scope-locked old text | `main.tex`、`intro.tex`、`related.tex`、`conc.tex` 仍可能保留舊 CTI／Agent／impact 敘述；這是最終改稿計畫明確鎖定不改的範圍。 | `main.tex`, `intro.tex`, `related.tex`, and `conc.tex` may still contain older CTI/Agent/impact framing because the final plan explicitly froze those areas. |
| Figure assets | 舊 figure 檔仍存在，但新版 Section 3/4 不再引用含 removed-module 語意的圖。 | Old figure assets remain, but revised Section 3/4 no longer references figures that imply removed modules. |
| TeX build | 已用專案內可攜 Tectonic 完成；若要改用 `latexmk`，仍需另外安裝完整 TeX toolchain。 | Completed with the portable Tectonic binary in the project; using `latexmk` would still require a full TeX toolchain. |

---

## O. AISec 頁數改良補遺／AISec Page-Limit Addendum

| 階段 | 頁數／Figures | 中文說明 | English explanation |
|---|---:|---|---|
| 完整改稿初版 | 22 / 9 | 方法、實驗與完整附錄均在單一 PDF，超過 AISec 全文限制。 | Method, evaluation, and the full appendix were in one PDF and exceeded the AISec overall limit. |
| 圖量收斂版 | 18 / 5 | 刪除四張重複流程圖，但完整 Appendix A--F 仍占主要篇幅。 | Four redundant workflow figures were removed, but the full Appendix A--F still dominated the page count. |
| 最終投稿版 | 12 / 4 | `appendix_submission.tex` 不只保留 labels，也放入正文承諾的可稽核 artifacts；主文第 10 頁結束。 | The submission appendix now includes the promised auditable artifacts, and the body ends on page 10. |
| 完整重現版 | 20 / 5 | `main_full.tex` 保留完整 schema、threshold、scenario、formula 與 result-shell 資料。 | `main_full.tex` retains all schemas, thresholds, scenarios, formulas, and result-shell material. |

頁數合規已完成，但投稿成熟度仍受兩項高風險限制：locked-test 結果尚未產生，以及 scope-locked Title／Abstract／Sections 1、2、5 仍保留與新版方法邊界不完全一致的 CTI/RAG/Agentic/impact 敘事。
