# Section 3 / Section 4 Final Improvement Report

更新日期：2026-07-11  
審查基準：`C:\Users\admin\Downloads\preview.html`

## 1. 改稿結論

HTML 與後續 Conditional Fail 審查指出的 Section 3、Section 4、Appendix、figures、references 與全篇敘事問題已落實到 LaTeX、machine contracts 與最終 PDF。`main.pdf` 現為 12 頁，Conclusion 位於第 9 頁，符合 AISec 10-page main / 12-page total 限制。

Empirical runs 尚未執行，所以所有 result fields 保留 `pending`。本報告的「完成」只表示 specification 與可重現性契約完成。

## 2. Section 3 改善

### 2.1 Ownership

- Episode Synthesis 產生 immutable EpisodeRevision 與 LateEvidenceRecord。
- Feature Extractor 產生 health-independent $[D,C,m,o^{det}]$。
- Scope Resolver 單獨產生 $a^{det}$、$\kappa$、group key、`decision_eligible`、`coverage_ref_ids` 與 `health_snapshot_digest`。
- Calibrator 是 $P$ 的唯一 producer。
- Sufficiency Evaluator 是 $U$ 的唯一 producer。
- AuditRecord Assembler 對每個 revision 只產生一個 terminal AssemblyOutcome：AuditRecord 或 AssemblyFailureRecord。
- Append-only Store 只授予 insert/select，圖中明確標示 `SINK ONLY`。

### 2.2 Episode Formation

正式契約已固定：

```text
W_gap = 300 s
W_max = 3600 s
L_watermark = 120 s
W_revision = 900 s
relation precedence rho = (4,3,2,1)
hub = 25 distinct relations / 600 s
merge parents <= 3
component <= 500 events / 200 entities
event order = (event_time, ingest_time, source_instance, event_id)
candidate order = (-rho, -n_R, delta_t, start_time, episode_id)
```

Zero/one/multiple-candidate branch、merge fallback、canonical IDs、watermark、late successor、late-store 與 replay assertions 均已在正文與 Appendix B 實體定義。

### 2.3 Detector Missingness

新增五態：

```text
available
no_detection
collector_unavailable
parser_invalid
unknown
```

只有前兩者可支援 calibration。凍結的 detector registry 固定三個 EDR 與三個 NDR IDs；raw values 必須是有限 binary64 $[0,1]$ 且值越大越可疑。去重 key 為 `(source_family, detector_id, dependency_group)`；相同 retry 合併，衝突值或 reference 拒絕 FeatureVector。Empirical CDF 使用 mid-rank tie rule $(count_<+0.5count_=)/N$；$D$ 取前 $\min(3,n)$ 個 normalized values 平均。`D=0` 只在沒有 eligible value 時作 diagnostic placeholder，並強制 false eligibility；missing/nonfinite/out-of-range 絕不補零。$q_s=1$ 若且唯若 registered detector 同時具 `detected`、合法值與連至 core entity/selected edge 的去重 root。

`n=0` 現在具有最高優先級：即使 resolved detector state 是 `no_detection`，Scope Resolver 仍必須輸出 $\kappa=\kappa_\varnothing$、`decision_eligible=false`、`eligibility_reason=no_eligible_detector_value` 與 JSON-null $P$，因此不會污染 score cohort。

Raw scorer 的 Eq. (7) 已改為固定 $\lambda=10^{-4}$ 的 L2-regularized convex logistic objective，參數域明確為 $b\in\mathbb R$、$w_D,w_C\ge0$，不再誤把 intercept 限制為非負。Cohort 是每條 training lineage 的第一個 finalized、exact-supported、positive/negative revision；mixed、ambiguous、OOS 與 assembly failures 排除並計數。Solver 固定為 deterministic binary64 L-BFGS-B、zero initialization、stable `logaddexp`、projected-gradient tolerance $10^{-9}$、objective-change tolerance $10^{-12}$、最多 10,000 iterations。Model artifact digest 包含 ordered IDs/labels、registry/normalizer digests、matrix bytes、$\lambda$、solver contract 與 coefficients。

### 2.4 Calibration

- Global objective：natural-prevalence NLL + $10^{-6}(a^2+b^2)$，且 $a\ge10^{-6}$。
- Primary support：exact EDR/NDR mask `11`、允許的 health/detector states、valid parser、exact versions。
- Group gate：50 positives、50 negatives、10 independent runs、5 deterministic folds、seed 20260710。
- Brier/NLL mean improvement 均至少 .01，每 fold nonnegative，paired lower 95% bounds 均大於 0。
- Tie/undefined fallback 至 global；任何 support mismatch 產生 canonical-null $P$ 與 false eligibility。

### 2.5 U 與 AuditRecord

`U` 的 coverage、provenance、lateness、contradiction、calibration 五軸都有完整 enum、precedence 與 first-match predicate。`U` 不 scalarize，也沒有數值路徑修改 $P$。

Draft 2020-12 schema 已固定八種 online objects、nested required types、closed properties、canonical digest include/exclude set、nullable condition 與 leakage rejection。SupportDecision 必須帶 EDR/NDR coverage references 與 health snapshot digest；AuditRecord digest 已納入 $o^{det}$、eligible count/reason；LateEvidenceRecord 另有自己的 digest、latest revision digest、ordered lineage references 與完整 VersionSet。所有 VersionSet component 都是 `{version,digest}` binding。Reference arrays 由應用層依 relation、dependency group、object/sentinel、ID、digest 排序後才執行 JCS；RFC 8785 不替應用層重排 array。Optional absence 使用 closed sentinel，required reference 缺失則 assembly failure。LateEvidenceRecord reason 是三值 closed enum；所有 JSON numbers 拒絕 NaN、Infinity、negative zero 與 binary64 overflow。Supported/OOS/late/failure examples 驗證通過，含 `malicious_label` 的 example 驗證失敗。

## 3. Section 4 改善

### 3.1 Populations

- $\mathcal C_{form}$：run end + 1020 s 時，每個 surviving lineage 一個 terminal revision。
- $\mathcal C_{dec}^{all}$：每條 terminal lineage 第一個 finalized revision 的 AssemblyOutcome，包含 supported/OOS AuditRecord 與 AssemblyFailureRecord。
- $\mathcal C_{dec}^{score}$：`C_dec_all` 中具有 finite $P$ 且 decision-eligible 的 AuditRecord；RQ2 唯一 score population。
- $\mathcal C_{dec}^{binary}$：`C_dec_score` 中 offline terminal-outcome join 後標記為 positive/negative 的 records；AUPRC、AUROC、Brier、NLL 與 reliability 只使用此 population。
- $\mathcal C_{stream}$：全部 revision-level terminal AssemblyOutcomes；只用於 RQ3/RQ4 transitions/cost。

Offline label 必須在每個 terminal AssemblyOutcome 形成後，以 EpisodeRevision digest join，AssemblyFailureRecord 也不得漏掉；RT1 依 positive/negative/other 回報 outcome 與 failure count/rate，從而檢查 class-dependent assembly bias。每個 partition/run 都以 $|\mathcal C_{dec}^{all}|$ 回報 supported-global、supported-group、OOS 與 failure counts/rates；score coverage 使用 $|\mathcal C_{dec}^{score}|$，class-dependent score metrics 使用 $|\mathcal C_{dec}^{binary}|$。

### 3.2 Lab and Split

正式評估只使用 controlled Caldera v5.3.0 Lab，不再把 DARPA provenance data 當 formal tier。CALDERA pin 同時記錄 annotated tag object `dd22...` 與 peeled release commit `b24f...`。

Split 是 base-campaign level：依 scenario family / benign mode stratify，按 SHA-256(`20260710:id`) 排序，每個 10-run stratum 分配 5/2/1/2 至 train/development/calibration/locked test，確保所有 partitions 非空。所有 descendants 繼承 partition 與 bootstrap cluster。

### 3.3 Labels and Matching

Primary values：

```text
temporal IoU >= .10
entity Jaccard >= .50
exact harmless marker or registered action
w = .5 A_cov + .3 J_entity + .2 IoU_time
theta_match = .50
theta_mal = .50
theta_contam = .25
```

Assignment 在單一 run 內執行 maximum-weight bipartite matching；tie 依 entity overlap、absolute time difference、ASCII/UTF-8 `(episode_id,group_id)`。$g^*$ 依 coverage 降冪、edge weight 降冪、group ID 升冪決定；沒有 edge 時 $g^*=null$、coverage=0、contamination undefined。Truth conflict 有三個 iff predicates，任何 conflict 都在 assignment 前強制 ambiguous。Run coverage 是每 group 最大 coverage 的平均；run contamination 只平均 defined values並回報 undefined count；空分母永遠是 undefined，不得序列化為零。

### 3.4 Scenarios and Interventions

`scenario_cards.v1.json` v2 為每張 M1--M7、offline-only M5-ID 與 B1--B8 card 固定 image key、ability/command template、整數秒 offset、marker preimage、success/failure predicate、cleanup command、cleanup assertion 與 mode matrix；concurrent-benign mode 固定早 60 秒啟動。任何 image、marker、timing 或 cleanup 不符都使 run invalid。實驗契約要求每個 mode 取得 10 次 valid repetitions；實際完成次數尚未產生，維持 `pending`。

`baseline_registry.v1.json` 封閉 EB1、EB2、SB1、SB2：EB1 是以 run start 為 anchor 的 300 秒 half-open bins；EB2 只在同一 EB1 bin 內依 exact shared-entity connected components 合併；SB1 使用 root-deduplicated finite source-native severity 的最大值；SB2 使用相同 binary cohort、$b\in\mathbb R$、$w_D\ge0$、$\lambda=10^{-4}$ 與相同 L-BFGS-B contract。

`perturbations.v1.json` v2 提供 RP0--RP7 的 canonical base order、包含 source 的 HMAC-SHA256 child seed，以及 RP2--RP7 的完整 source×dose Cartesian design。RP3 固定 valid-start candidate index，RP5 固定 buffer width/anchor/index，RP7 固定 duplicate-ID byte preimage。PO1 對每個 base×source×{120,600} 組合固定 anchor、stop、ready、stable、1800 秒 follow-up 與 detection/recovery right-censoring。Figure 4 已同步移除 M8、stochastic arrival lag 與 stop-or-isolate。

### 3.5 Metrics and Results

Over-merge 單位已修正為「同一 run 內被指派到多個 ground-truth action groups 的 terminal predicted episodes」，不再以 mutually exclusive run ID 計算。Primary summaries 使用 run-macro，intervals 使用 2,000 complete-run-cluster percentile resamples，seed 20260710。

RT1、RT2、RT3a、RT3b、RT4、RT5、RT6、RT7 的 row keys 與 columns 已固定；OB1 有唯一 ID 與 RT5 row。尚未執行欄位一律 `pending`，只有結構不適用才使用 `N/A`。

## 4. Appendix and Figures

投稿版 A.1--A.6 已提供 schema、algorithm、threshold/U table、calibration resolver、Lab/cards/labels、populations/split/interventions/metrics/RT registries，不再是摘要。

Figure 1 已修正 ownership。投稿版保留 Figures 1--4；完整版另加入 calibration--U、Lab topology、split/freeze、linking decision、calibration validity，共 9 figures。

## 5. References and Narrative

- Title、Abstract、Sections 1/2/5 已移除舊 CTI/RAG/Agentic/impact 主張。
- RQ1 已移除沒有 path metric 的 malicious-path claim。
- SB4 改為 `uncalibrated sigmoid score`。
- U enums 與 RT1--RT7 命名一致。
- Wen-tau Yih BibTeX 已修正。
- 無 citation 的 CORP sentence 已刪除。

## 6. Verification

| Gate | Result |
|---|---|
| `main.pdf` | 12 pages / 4 figures / 7 tables |
| `main_full.pdf` | 20 pages / 9 figures |
| Overfull hbox / undefined / multiply defined | 0 |
| Final-page output vbox | 1.17 pt；無文字越界或裁切 |
| U+22AE / U+FFFD | 0 / 0 |
| Out-of-page text blocks | 0 |
| Schema positive/OOS/rejection tests | PASS |
| Artifact manifest hashes | 17/17 PASS |
| Companion zip integrity | PASS |
| Extended remediation regression | 83/83 PASS |
| Visual inspection | 12/12 pages PASS |

`main.pdf` 已把 SHA-256 為 `5c226ba73667d628058538ede2adbbb174cdd9986b9e58ea2bf082b75bcf7e83` 的 companion ZIP 定義為 required supplementary artifact。本機驗證只證明封裝一致；正式投稿必須上傳完全相同的 ZIP，否則 machine-readable contract 主張不成立。

最完整的逐項 HTML requirement matrix 位於 `HTML_REVIEW_REMEDIATION_REPORT.md`；紅刪綠增中英對照位於 `SECTION3_SECTION4_DETAILED_COMPARISON_REPORT.md`。

## 7. Remaining

Locked-test empirical execution、真實 RT1--RT7、confidence intervals 與 plots 尚未完成。這些項目必須使用 frozen contracts 執行，不能以合成數值補齊。
