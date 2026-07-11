<!-- 本文件逐段對應 sections/exps.tex；僅翻譯為繁體中文並轉換成 Markdown，未改變評估內容。 -->

# 4 評估

本評估是一份凍結的 protocol，而不是已完成實驗的結果報告。在存取 locked test 之前，母體、資料切分、manifest、門檻、gate、intervention、matching、metrics、resampling，以及空白的 RT1--RT7 schema 均已固定。所有尚未執行的欄位均標示為 `pending`；本文不回報任何合成數值、曲線或區間。

## 4.1 研究問題與母體

**RQ1 - formation。** 相較於 time-only 與 time-plus-entity comparators，label-blind builder 是否能提高惡意 action coverage，同時降低 fragmentation 與 over-merge？

**RQ2 - ranking/calibration。** 相較於 severity 與僅使用 $D$ 的 comparators，$D+C$ 是否能改善 AUPRC 與 fixed-budget recall？獨立的 affine calibration 是否能改善 Brier、NLL 與 reliability？

**RQ3 - partial telemetry。** 在 paired replay 與獨立的 physical outage 下，formation、$z$、support、$U$、revisions 與 eligibility 會如何改變？

**RQ4 - replay/cost。** Canonical outputs 是否能達到 byte-identical？實際量測的 throughput、latency、memory、storage 與 replay time 為何？

這些母體是相同 registered runs 的彼此分離視圖。$\mathcal C_{form}$ 在

$$
T_{form}=t_{run\_end}+L_{wm}+W_{rev}=t_{run\_end}+1020\ \mathrm{s}
$$

時，對每條仍存續的 episode lineage 僅包含一個 terminal revision；已合併的 parent 會被移除。$\mathcal C_{dec}^{all}$ 對每條 terminal lineage 包含第一個 `finalized` revision 的 AssemblyOutcome，涵蓋 supported/OOS AuditRecord 與 AssemblyFailureRecord。$\mathcal C_{dec}^{score}$ 是其中 decision-eligible 且 $P\in[0,1]$ 的 AuditRecord。每個 terminal outcome 插入後，offline harness 才依 EpisodeRevision digest join $L(o)\in\{positive,negative,mixed,ambiguous\}$，AssemblyFailureRecord 也必須被標記。$\mathcal C_{dec}^{binary}=\{o\in\mathcal C_{dec}^{score}:L(o)\in\{positive,negative\}\}$ 是所有 class-dependent ranking/calibration metrics 的唯一 population。每個 partition/run 以 $|\mathcal C_{dec}^{all}|$ 回報 outcome/failure counts 與 rates，並按四種 labels 分解 failures；scorable 與 binary coverage 分別使用 $C_{dec}^{score}$ 與 $C_{dec}^{binary}$。

## 4.2 受控實驗室與凍結切分

所有正式主張只使用受控的 Caldera v5.3.0 laboratory `\cite{caldera}`；公開的 provenance datasets 只作為 related-work context，不構成 evaluation tier。實驗室包含隔離的 Windows/Linux targets、benign service、EDR/NDR collectors、Health Monitor、production-like online pipeline、獨立的 Ground Truth Store，以及 offline Evaluation Harness。Release 固定為 annotated tag object `dd22d543...`，其 peeled commit 為 `b24f6e7a...`；每個正式 run 另會記錄 target、collector、configuration、topology、parser 與 schema digests。缺少 manifest 欄位時會 fail closed，只能進入 RT1。

表 3 固定所有結果共同使用的 split unit、deterministic assignment、descendant inheritance 與 fail-closed registry fields。

**表：凍結的 campaign split 與 descendant inheritance。**

| 項目 | 唯一規則 | Fail-closed invariant |
|---|---|---|
| Independent unit | Base campaign，依 scenario family 與 benign mode 進行 stratification | 不允許 event/episode random split |
| Order | 在每個 stratum 內，依 `20260710:base_campaign_id` 的 SHA-256 升冪排序 | 在 label release 前凍結 IDs |
| 10-run cycle | Rank 0--4 為 train；5--6 為 development；7 為 calibration；8--9 為 locked test | 精確比例 50/20/10/20；每個 partition 都非空 |
| Descendants | Replay/outage children 繼承 partition 與 bootstrap cluster | 任何不一致都會使完整 cluster 失效 |
| Registry | Run、base/parent/pair IDs、scenario、benign mode、seed、partition、cluster、role、manifest digest | 缺少任何欄位時排除於 RT2--RT7 |

Identity 永遠不是 online source。M5 是一張 EDR/NDR endpoint card；M5-ID 是獨立標示的 post-inference annotation，只有在其 timestamp/provenance/health/support pilot 通過後才會採用。它不能改變 $\mathcal S^\star$、$K=2$、candidates、features、manifests 或 primary RQs。

## 4.3 Ground Truth、Matching 與 Labels

Allowlist schemas 會拒絕所有 online objects 中的 evaluation-only fields。每個 ground-truth group $g$ 註冊 required action tokens $A_g$，每個 run 註冊 benign tokens $B_r$；$A_{cov}(p,g)=|A_p\cap A_g|/|A_g|$。Offline matching 先建立 threshold-qualified edge graph $E_q$：temporal IoU $\ge0.10$、entity Jaccard $\ge0.50$，且至少一個完全相符的 marker/action，再計算 edge weight：

<a id="eq-match-weight"></a>

$$
w=0.5A_{cov}+0.3J_{entity}+0.2\operatorname{IoU}_{time};
\qquad w\ge\theta_{match}=0.50.
\tag{1}
$$

Maximum-weight one-to-one assignment 只用於 episode precision/recall/F1；action coverage、fragmentation 與 over-merge 一律使用尚未 assignment 的 $E_q$。Assignment ties 依 entity overlap、absolute time difference，再依 `(episode_id,group_id)` 的 ASCII/UTF-8 bytes 升冪決定。

對每個 revision，依 $A_{cov}$ 降冪、$w$ 降冪、UTF-8 group ID 升冪選擇 incident edge 的 $g^*$；沒有 edge 時 $g^*=\texttt{null}$、$A_{cov}=0$ 且 $B_{cont}$ undefined。否則 $B_{cont}=|A_p\cap B_r|/|(A_p\cap A_{g^*})\cup(A_p\cap B_r)|$，分母為零時 undefined。Truth conflict 若且唯若 overlapping registered groups 將同一 root/action token 指派給不同 group IDs、同一 root 同時為 malicious 與 benign，或 duplicate marker IDs 對 card/window 的定義不一致；任何 conflict 都會在 assignment 前強制產生 `ambiguous`。其餘 label 採 first-match precedence：`mixed`、`positive`、`negative`、`ambiguous`。Label join 只在 terminal AssemblyOutcome 插入後發生，且必須獨立解析成功或 failure 的 EpisodeRevision；無法解析時為 ambiguous。

<a id="figure-3"></a>

![Ground Truth Firewall](trustepisode_figures/png/fig05_ground_truth_firewall.png)

**圖 3：Ground Truth Firewall。** Schema tests 會在 inference 之前拒絕 evaluation-only fields；labels 只會在 offline Evaluation Harness 中 join 至 immutable outputs。

## 4.4 Scenario 與 Benign Cards

表 4 定義七個 malicious families；其數量是 protocol 要求，不是已完成的 observations。

**表：凍結的惡意 scenario families；protocol 要求每張 card 在每個 mode 下有 10 次 valid repetitions；實際達成數量為 `pending`。**

| ID | 有序的 family | Stressor | Primary evidence |
|---|---|---|---|
| M1 | Windows discovery $\rightarrow$ share $\rightarrow$ remote marker | Lateral chain | EDR lineage + NDR connection |
| M2 | Script $\rightarrow$ marker transfer $\rightarrow$ temporary task | Weak-to-strong | EDR lineage + NDR transfer |
| M3 | Linux discovery $\rightarrow$ test SSH $\rightarrow$ file marker | Cross-platform | Linux EDR + NDR session |
| M4 | Low-rate connections $\rightarrow$ local marker | Sparse sequence | NDR cadence + EDR action |
| M5 | Test-account endpoint action $\rightarrow$ endpoint marker | Identity-independent primary card | 僅 EDR/NDR |
| M6 | Dual-use admin tool $\rightarrow$ remote marker | Tool-name shortcut | Contextual EDR/NDR |
| M7 | Discovery $\rightarrow$ fixed pauses $\rightarrow$ remote marker | 300/3600 s boundaries | Fragmentation/stabilization |

B1--B8 分別涵蓋 inventory、patching、file synchronization、vulnerability scanning、helpdesk administration、log collection、configuration management，以及已宣告的 unscheduled maintenance。每張 M/B card 都是 closed execution tuple：image key/digest、ordered ability IDs、executor 與 exact command template、monotonic offsets、marker path/content/hash preimage、success/failure predicates、cleanup commands/post-cleanup digest，以及 allowed mode。Malicious modes 是 attack-only 或由 hash 唯一選出的 B1--B8 workload 提前 60 s 啟動；benign cards 另有 standalone mode。任何 unresolved variable、command/image digest mismatch、offset error $>1$ s 或 cleanup failure 都使 run 無效。

## 4.5 Calibration Protocol 與 Comparators

Training、calibration、AUPRC/AUROC、Brier、NLL 與 reliability 都只能使用 $\mathcal C_{dec}^{binary}$；mixed/ambiguous 只回報 coverage，不進入 class-dependent metrics。Conditional SB6 以完整 runs 做 deterministic balanced five-fold assignment，平衡 positive、negative 與 run loads，並 seal assignment digest。Global positive-slope mapping 必須在同一 binary population 維持 AUPRC/AUROC，否則觸發 implementation audit。

表 5 將每個 formation、ranking、calibration、replay 與 outage comparator 綁定至唯一 implementation 與 RT registry。

**表：已註冊的 comparisons；每個 ID 只有一個 implementation 與一個 result location。**

| ID | Scope | 唯一 implementation | Purpose / registry |
|---|---|---|---|
| EB1 | Formation | Non-overlapping 300 s event-time windows | Time-only / RT2 |
| EB2 | Formation | EB1 加上一個 specific shared entity | Time+entity / RT2 |
| EB3 | Formation | Proposed guarded temporal-causal builder | Reference / RT2 |
| EB3-H | Formation | 關閉 hub suppression 的 EB3 | Component ablation / RT2 |
| SB1 | Ranking | 最大的 normalized source-native severity | External rank / RT3a |
| SB2 | Ranking | Constrained $D$-only logit | Corroboration ablation / RT3a |
| SB3 | Ranking | Proposed $D+C$ logit | Raw rank / RT3a |
| SB4 | Score | Uncalibrated sigmoid score $\sigma(z)$ | Non-probability comparator / RT3b |
| SB5 | Calibration | Global affine mapping | Primary / RT3b |
| SB6 | Calibration | 已啟用且註冊的 group mapping | Conditional / RT3b |
| SB7 | Replay | 將 unavailable detector 強制設為零並忽略 support | Anti-pattern / RT4 |
| OB1 | Outage | Available-source denominator；健康 sources 少於 2 個時不提供 corroboration | 僅用於 outage / RT5 |

Baseline registry 固定完整實作：EB1 以 run start 錨定 300 s event-time bins；EB2 在每個 EB1 bin 內建立 exact shared-entity connected components，無 entity event 為 singleton。SB1 使用 manifest-pinned parser 產生的 root-deduplicated finite `source_native_severity` 最大值，missing 為 undefined 並計數。SB2 使用與 SB3 相同的 binary training cohort，$b\in\mathbb R$、$w_D\ge0$、$\lambda=10^{-4}$ 與相同 L-BFGS-B tolerances，並以 $b+w_DD$ 排名。IDs、tie、failure 與 artifact digest fields 全部凍結。

## 4.6 Replay Perturbations 與 Physical Outage

每個 M1--M7 base run 都有 deterministic children。RP2--RP7 建立完整 `EDR/NDR source × dose` Cartesian children；RP1 使用 explicit EDR-only/NDR-only，RP0 無 source。Child seed 將 base、RP、source 與 JCS(level) 納入 HMAC。RP3 以 $j=\lfloor U(\texttt{interval},\texttt{start})N\rfloor$ 選擇 ascending integer-microsecond valid starts，$N=0$ child 無效。RP5 的 width 精確等於 30/120/600 s dose，anchor 是完整 base stream 的 minimum ingest time。RP7 duplicate ID 的 byte preimage 是 `UTF8("RP7") || 0x1f || S_as_32_raw_bytes || 0x1f || UTF8(original_event_id) || 0x1f || uint32_be(1)`；ingest time 加 1 microsecond，collision 使 child 無效。其他 source 與 SourceCoverage 都不變。

PO1 對每個 base run 建立 `source × {120,600 s}` cells。$t_{anchor}$ 需要兩個 healthy heartbeats、parser valid、transport live、backlog $\le120$ s；連續健康 120 s 後 $t_{stop}=t_{anchor}+120$ s。$t_{ready}$ 是 restore 後開始兩個連續 parser-valid、transport-live、backlog-$\le120$ heartbeat intervals 的第一時間。沒有 $t_{detect}<t_{restore}$ 時 detection 在 restore 右設限；沒有 ready/stable 時 recovery 在 $t_{censor}=t_{restore}+1800$ s 右設限並記錄 reason。

<a id="figure-4"></a>

![Partial-telemetry perturbation design](trustepisode_figures/png/fig07_partial_telemetry_perturbations.png)

**圖 4：Paired replay 會改變 events，但 health 保持固定；physical outage 會改變 authenticated health，並且分開評估。**

## 4.7 Metrics 與 Run-Level Uncertainty

對 run $r$，令 $E_{q,r}$ 為未 assignment 的 threshold-qualified graph，$n_g=|\{p:(p,g)\in E_{q,r}\}|$，$d_p=|\{g:(p,g)\in E_{q,r}\}|$。RQ1 使用 action coverage、fragmentation

$$
|G_r|^{-1}\sum_g\max(0,n_g-1),
$$

以及 over-merge $|P_r|^{-1}\sum_p\mathbf{1}[d_p>1]$。One-to-one assignment 只計算 episode F1，因此 fragmentation 與 over-merge 不會被 assignment 強制成零。

Run-level action coverage 定義為 $|G_r|^{-1}\sum_g\max_p A_{cov}(p,g)$；run contamination 是所有已定義 $B_{cont}$ 的平均，並另外回報 undefined count。任何空分母 metric 都是 undefined，絕不序列化為零。

RQ2 只使用 $\mathcal C_{dec}^{binary}$。Primary ranking metrics 是 AUPRC，以及每個 run 前

$$
\max\left(1,\left\lceil0.05|\mathcal C_{dec,r}^{binary}|\right\rceil\right)
$$

名 candidates 的 recall；Brier、NLL 與 ten-bin reliability 使用同一 positive/negative population。RT6 在 manifest-pinned host 對 RP0 使用 1/2/4/8 workers，每個組合先做一次不計入的 warm-up，再做五次 measured repeats；latency 使用 monotonic ingest-to-AssemblyOutcome、RSS 每 100 ms sampling、storage 加總 canonical bytes，且 throughput denominator 包含 failure outcomes。

所有 primary summaries 都以 runs 進行 macro-average；pooled micro results 僅作 supplemental。Intervals 使用 2,000 次 complete run clusters 的 percentile bootstrap resamples，seed 為 20260710 `\cite{field2007bootstrap}`；replay/outage 會 resample base-run pairs。未定義 class-dependent metric 的 resamples 會被計數並省略，絕不以零取代。Relative effects 僅作 supplemental。

## 4.8 RT1--RT7 Reporting Contract

表 6 是唯一 normative result registry；不假設 reviewers 另外取得 machine-readable registry。

**表：凍結的 result registries。所有尚未執行的欄位都序列化為 `pending`；只有結構上不適用的欄位才使用 `N/A`。**

| Registry | Rows | 凍結的 columns | State |
|---|---|---|---|
| RT1 | Partition $\times$ population | Runs；$C_{dec}^{all}$/$C_{dec}^{score}$/$C_{dec}^{binary}$；outcome/failure labels；supported/OOS/failure rates | pending |
| RT2 | EB1、EB2、EB3、EB3-H | Action coverage；fragmentation；over-merge；contamination；episode F1 | pending |
| RT3a | SB1、SB2、SB3 | all/score/binary denominators；binary coverage；AUPRC；recall@budget；AUROC；precision@$k$ | pending |
| RT3b | SB4、SB5、SB6 | all/score/binary denominators；Brier；NLL；reliability bins；OOS/failure rates | pending |
| RT4 | RP0--RP7 $\times$ level | Formation/$z$/Brier/NLL changes；coverage；$U$ transitions；revisions；stabilization | pending |
| RT5 | Source $\times$ duration $\times$ method/OB1 | Anchor/stop/detect/restore/ready/stable/censor；eligibility；OOS；recovery | pending |
| RT6 | Worker count 1/2/4/8 | Manifest；repeats；hash equality；throughput；p50/p95/p99；peak RSS；canonical bytes/event/outcome；replay time；failure fraction | pending |
| RT7 | Error category | Count；run/candidate fraction；representative revision；adjudication | pending |

Planned reliability 與 revision plots 會保持缺席，直到 locked outputs 確實存在。任何後續 machine-readable registry 都必須完整保留表 6 的 RT keys、rows、columns、`pending` 與 `N/A` 規則。

## 4.9 限制與安全性

受控實驗室無法證明 field generalization，也無法涵蓋所有 evasion 與 base rate。Calibration 只適用於完全相符且受支援的 manifests。Identity 維持 offline。所有正式 runs 都使用隔離 hosts、test accounts、harmless markers、cleanup gates 與已記錄的 failures。本評估不研究 CTI、agents、impact、priority、OT/ICS 或 autonomous response，而且在 locked pipeline 實際執行前不會回報任何 empirical result。
