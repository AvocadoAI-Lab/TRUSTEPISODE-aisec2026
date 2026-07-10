<!-- 本文件逐段對應 sections/arch.tex；僅翻譯為繁體中文並轉換成 Markdown，未改變方法內容。 -->

# 3 TrustEpisode 方法

TrustEpisode 將端點偵測與回應（endpoint detection and response, EDR）以及網路偵測與回應（network detection and response, NDR）的遙測資料，轉換為確定性的候選事件集修訂版本（candidate-episode revisions）與具版本範圍的證據紀錄。線上路徑對標籤不可知（label blind）：Evidence Fabric 將事件與收集器健康狀態觀測正規化；只有 Episode Synthesis 擁有事件成員資格與不可變修訂版本的控制權；無狀態評分器將兩個明確的證據特徵映射為原始 logit；而且當目前修訂版本符合受支援的 manifest 時，affine calibrator 是惡意機率的唯一產生者。另一個獨立的確定性評估器會回報結構化的證據充分性 profile，但不會改變該機率。每個修訂版本只會產生一筆 append-only AuditRecord，其中包含原始分數、可為空值的校準機率、充分性狀態、版本、provenance references 與 canonical digest。Ground truth 僅在推論完成後，為了 fitting 或 evaluation 才進行 join。因此，本方法估計的是：在所觀測到的 EDR/NDR 收集邊界內，一個凍結的候選修訂版本是否包含惡意活動；本方法不估計企業整體風險、營運影響、回應優先級，或未留下可觀測軌跡的攻擊。圖 1 總結了這些 ownership 與 trust boundaries。

## 3.1 問題範圍、輸出契約與所有權

令 $\mathcal C$ 表示由凍結的 formation policy 所產生的所有 EpisodeRevision。令

<a id="eq-supported-population"></a>

$$
\mathcal C_{\mathrm{sup}}=
\left\{\epsilon^{(r)}\in\mathcal C:
\kappa_{\epsilon^{(r)}}\in
\{\kappa_G,\kappa_g\}\right\}.
\tag{1}
$$

其中，$\kappa_G$ 與 $\kappa_g$ 分別表示 `supported_global` 與 `supported_group`。這是 calibration manifest 能夠支援機率輸出的子集合。監督式目標 $Y_{\epsilon^{(r)}}\in\{0,1\}$ 表示：在凍結的時間與實體重疊政策下，修訂版本 $\epsilon^{(r)}$ 的不可變成員集合是否包含惡意活動。只有在該修訂版本完成線上推論後，標籤才會於離線階段進行 join。首次在修訂版本 $r+1$ 中觀測到的惡意動作，不能回溯性地重新標記修訂版本 $r$。正例與負例修訂版本構成主要的監督式 cohort；mixed 與 ambiguous 修訂版本會分開回報，且只進入預先註冊的敏感度分析。

對每個 $\epsilon^{(r)}\in\mathcal C$，runtime 會輸出一個原始 logit $z_{\epsilon^{(r)}}$、一個校準狀態 $\kappa_{\epsilon^{(r)}}$、一個可為空值的校準機率 $P_{\epsilon^{(r)}}$、一個結構化充分性 profile $U_{\epsilon^{(r)}}$，以及恰好一筆不可變 AuditRecord。當 $P$ 有定義時，它是以候選事件為條件且具有版本範圍的：

<a id="eq-scoped-probability"></a>

$$
P_{\epsilon^{(r)}} =
\Pr\!\left(Y_{\epsilon^{(r)}}=1\mid
\epsilon^{(r)},v_{\mathrm{episode}},v_{\mathrm{feature}},
v_{\mathrm{model}},v_{\mathrm{cal}}\right).
\tag{2}
$$

它不是組織正在遭受攻擊的無條件機率。

此契約依賴三項假設。**可觀測軌跡假設（observable-trace assumption）** 將推論限制在已宣告 EDR/NDR 範圍內可見的軌跡。**收集器邊界假設（collector-boundary assumption）** 將收集器身分與傳輸 metadata 視為已驗證，同時明確表示 outage、delay 與 parser failure。**線上標籤不可知假設（label-blind online assumption）** 禁止任何線上物件包含標籤、scenario identifiers、split assignments 與 ground-truth windows。因此，TrustEpisode 無法保證偵測到未留下相關可觀測軌跡的活動。

**表 2：單一所有者線上物件契約。**

| 物件 | 唯一產生者 | 使用者 | 禁止行為 |
|---|---|---|---|
| NormalizedEvent | Evidence Fabric | Episode Synthesis | 包含 label、split 或 scenario 欄位 |
| SourceCoverage | Health Monitor | Scope Resolver；Sufficiency Evaluator | 從事件沉默推論 outage |
| EpisodeRevision | Episode Synthesis | Feature Extractor；audit path | 由 scorer 端改變 membership |
| FeatureVector $[D,C]$ | Feature Extractor | Stateless Scorer | 包含 health、$U$ 或 label 欄位 |
| Raw logit $z$ | Stateless Scorer | Calibrator；AuditRecord | 使用 probability 用語 |
| CalibrationStatus $\kappa$ | Scope Resolver | Calibrator；Sufficiency Evaluator；audit path | 由 test 選擇 status |
| 可為空值的校準 $P$ | Calibrator | AuditRecord；downstream review | 被 $U$ 修改；unsupported 時仍提供數值 |
| 結構化 $U$ | Sufficiency Evaluator | AuditRecord；downstream review | 取代或重新計算 $P$ |
| AuditRecord | Append-only audit store | Replay；evaluation；review | 更新較早修訂版本的紀錄 |

**表 3：核心符號。**

| 符號 | 意義 |
|---|---|
| $e_i$ | 正規化事件 |
| $\epsilon^{(r)}$ | 不可變事件集修訂版本 |
| $m_{\epsilon,s}$ | 已觀測 source-family mask |
| $h_\epsilon$ | 收集器健康狀態快照 |
| $q_{\epsilon,s}$ | 獨立偵測支援 |
| $D_\epsilon$ | 正規化 detector-deviation 特徵 |
| $C_\epsilon$ | EDR/NDR corroboration 特徵 |
| $z_\epsilon$ | 原始 logit |
| $P_\epsilon$ | 可為空值的校準惡意機率 |
| $\kappa_\epsilon$ | 校準支援狀態 |
| $U_\epsilon$ | 結構化證據充分性 profile |

<a id="figure-1"></a>

![TrustEpisode 線上與離線邊界](trustepisode_figures/png/fig01_final_architecture.png)

**圖 1：TrustEpisode 的線上與離線邊界。** 實線的主要候選路徑只包含 EDR/NDR。Evidence Fabric、Episode Synthesis、Feature Extractor、Stateless Scorer、Scope Resolver、Calibrator 與 Sufficiency Evaluator 分別唯一擁有 NormalizedEvent、EpisodeRevision、$[D,C]$、$z$、$\kappa$、$P$ 與 $U$。Identity 不是線上輸入，而且 $U$ 沒有任何數值路徑進入 scorer 或 calibrator。

## 3.2 Evidence Fabric 與獨立來源健康狀態

Evidence Fabric 將每筆來源紀錄映射為一個 NormalizedEvent，其中包含 stable ID、event time、ingest time、source family 與 instance、canonical entities 與 action、不可變 raw pointer，以及 root dependency group。Event time 描述來源何時觀測到某個動作；ingest time 描述 pipeline 何時收到它。這項區分是確定性 late-data handling 所必需的 `\cite{akidau2015dataflow}`。轉送或衍生的副本會繼承相同的 root dependency group，因此不能產生額外證據。正規化 artifacts（包括 source-specific parsers 與 empirical transforms）會使用 training data 進行 fitting 或 selection，並在 runtime 維持唯讀。OCSF v1.8.0 提供的是欄位名稱對齊目標，而不是跨廠商語意等價的主張 `\cite{ocsf2026}`。

SourceCoverage 是由已驗證的 heartbeat、lag、parser 與 transport observations 所產生的獨立健康狀態串流。沒有事件永遠不代表收集器已停止運作。對 source family $s\in\mathcal S^\star=\{\mathrm{EDR},\mathrm{NDR}\}$，定義

<a id="eq-source-mask"></a>

$$
m_{\epsilon,s}=\mathbb{1}\!left[
\epsilon\text{ 包含一筆來自 }s\text{ 的已觀測事件}\right].
\tag{3}
$$

向量 $m_\epsilon$ 是已觀測 source mask；replay event masking 可以改變 $m$，但不改變 health。快照 $h_\epsilon$ 由與 episode interval 重疊的 SourceCoverage intervals 解析而得。最後，只有當 $s$ 包含與 episode 核心實體或邊相連、且經 lineage 去重的 supporting detection evidence 時，$q_{\epsilon,s}=1$。因此，一個健康但沉默的來源 family 可以是 $m=0$ 且 health 為 `healthy`；一個有觀測事件但沒有 supporting detection 的 family 可以是 $m=1,q=0$。$m$ 或 $q$ 單獨存在時都不能診斷 collector failure。Scope Resolver 會聯合使用 $(m_\epsilon,h_\epsilon)$ 與凍結的 pipeline versions 來決定 $\kappa_\epsilon$。契約完整的 schema registry、canonical serialization 與 firewall rules 定義於附錄 A.1。

## 3.3 確定性 Episode Synthesis 與不可變修訂版本

Episode Synthesis 是唯一可以 attach、merge 或 revise membership 的元件。對一筆新事件 $e_i$ 與一個 open episode $E$，其 eligibility 為

<a id="eq-link-eligibility"></a>

$$
\begin{aligned}
\ell(e_i,E)=\mathbb{1}\!\big[ 
&\Delta_t(e_i,E)\le W_{\mathrm{gap}}
\land R(e_i,E)=1\\
&{}\land \operatorname{span}(E\cup\{e_i\})\le W_{\max}
\land H(e_i,E)=0
\big].
\end{aligned}
\tag{4}
$$

其中，$\Delta_t$ 是 event-time inactivity gap；$R$ 表示至少存在一個凍結的 process-causal、authenticated-session、endpoint-mapped connection 或 specific-entity relation；$H$ 則標記禁止的 hub-only link。僅有時間接近並不足以建立關聯。

若沒有 eligible candidate，則開始新的 episode；若只有一個 candidate，該 candidate 接收此事件；若有多個 candidates，則依照附錄 A.2 的凍結 total order 與 merge guard 處理。該附錄也固定 canonical episode IDs、merge lineage、inclusive boundaries 與 event ordering。Event time 決定 relation eligibility，ingest time 則推進 watermark。在 revision horizon 內被接受的證據會產生 revision $r+1$ 與一筆新的 AuditRecord；超過 horizon 的證據則依循凍結的 late-store 或 drop policy。任何路徑都不能覆寫較早的修訂版本或其紀錄。這些控制採納 alert-correlation 與 provenance systems 中 causal-context 的經驗，同時保留一個可稽核且刻意精簡的 candidate generator `\cite{ning2002attackscenarios,holmes2019,nodlink2024,kairos2024}`。

### Algorithm 1：Label-blind episode update

1. 將輸入事件正規化，並依 dependency 去重。
2. 擷取符合 inclusive temporal bounds 的 open candidates。
3. 評估允許的 non-temporal relations 與禁止的 hub links。
4. 套用凍結政策中的 giant-component 與 merge guards。
5. 依凍結的零／一／多 candidate 分支與 total order 執行。
6. 推進 ingest-time watermark，並套用 revision-horizon rule。
7. 產生一個不可變 EpisodeRevision，以及恰好一筆新的 AuditRecord。

<a id="figure-2"></a>

![確定性 episode 與 revision lifecycle](trustepisode_figures/png/fig02_episode_revision_lifecycle.png)

**圖 2：確定性 episode 與 revision lifecycle。** Event time 控制 $W_{\mathrm{gap}}$ 與 $W_{\max}$ 下的 linking；ingest time 控制 watermarks。被接受的 late evidence 會建立新的不可變 revision 與 AuditRecord，而超過 horizon 的證據不能重寫歷史。

## 3.4 精簡特徵語意與無狀態原始評分器

主要 feature contract 為

<a id="eq-feature-vector"></a>

$$
x_\epsilon=[D_\epsilon,C_\epsilon].
\tag{5}
$$

對每個 eligible source-native detector value $r_i$，凍結的轉換
$d_i=\widehat F^{\mathrm{train,benign}}_{s_i}(r_i)$ 會透過以該 source family 的 training-benign observations 所擬合的 empirical CDF 對數值進行映射。$D_\epsilon$ 是三個最大 eligible $d_i$ 值的平均；若少於三個，則使用全部數值。若完全不存在 eligible value，$D_\epsilon=0$ 只是一個確定性的 raw-model placeholder，同時 $u_{\mathrm{provenance}}=\texttt{missing}$。這不是 benign evidence；除非 calibration manifest 明確支援該 regime，否則 $P_\epsilon=\mathrm{NA}$。

主要範圍永久固定為

$$
\mathcal S^\star=\{\mathrm{EDR},\mathrm{NDR}\},\qquad K=2,
\tag{6}
$$

而 corroboration 為

<a id="eq-corroboration"></a>

$$
C_\epsilon =
q_{\epsilon,\mathrm{EDR}}q_{\epsilon,\mathrm{NDR}}.
\tag{7}
$$

Heartbeat、inventory 與 dependency-linked forwarded copies 都不會將 $q$ 設為 1。Identity 若在後續 pilot-gated study 中可用，仍只是離線 exploratory annotation：它不會進入 NormalizedEvent、Episode Synthesis、candidate IDs 或 membership、$D$、$C$、任何 calibrator manifest 或主要 research question。因此它無法改變 candidate universe，且 $\mathcal S^\star$ 與 $K=2$ 維持固定。

無狀態評分器為

<a id="eq-raw-logit"></a>

$$
z_\epsilon=b+w_DD_\epsilon+w_CC_\epsilon,
\qquad w_D,w_C\ge0.
\tag{8}
$$

其唯一的 learned coefficients 為 $(b,w_D,w_C)$。Training 最小化未加權的 candidate-level log loss；formation 與 feature settings 使用 training 與 development data 進行選擇，接著在 final train-only normalizer 與 scorer fitting 之前凍結。Campaign/run 是 split 與 uncertainty cluster。Health、$m$、$\kappa$、$U$、labels 與 outage status 永遠不會進入 $x_\epsilon$。$w_DD_\epsilon$ 與 $w_CC_\epsilon$ 是可重播的 logit decompositions，而不是 causal explanations。附錄 A.3 記錄 preprocessing artifacts、implementation settings、owners 與 freeze points。

## 3.5 Manifest-Scoped Affine Calibration

$z_\epsilon$ 與 $\sigma(z_\epsilon)$ 都不會被稱為已驗證機率。主要 calibrator 是一個斜率為正的 global affine mapping，使用具有自然候選事件盛行率的獨立 calibration split 進行 fitting，遵循 Platt scaling 的 score-to-probability 原則，並使用 proper scoring rules 進行評估 `\cite{platt1999probabilistic,gneiting2007proper}`：

<a id="eq-affine-calibration"></a>

$$
P_\epsilon=
\begin{cases}
\sigma(a z_\epsilon+b_{\mathrm{cal}}),
& \kappa_\epsilon=\kappa_G,\\
\sigma(a_g z_\epsilon+b_g),
& \kappa_\epsilon=\kappa_g,\\
\mathrm{NA},
& \kappa_\epsilon=\kappa_\varnothing,
\end{cases}
\qquad a,a_g>0.
\tag{9}
$$

$\kappa_\varnothing$ 表示 `out_of_support`；$\kappa_G$ 與 $\kappa_g$ 保留公式（1）後所定義的狀態意義。Global mapping 會保留相同 candidate set 內的 ranking。Group mapping 只保留該 group 內的 ranking，不提出跨 group ranking 的主張。Group calibration 是有條件的：預先註冊的 gate 要求有足夠的 positive revisions、negative revisions 與 independent runs，並需要證據顯示 global mapping 不充分。Selection 與 fitting 使用 run-level cross-fitting 或 internal calibration holdout，絕不使用 locked test。

精確支援要求目前的 episode、feature、detector、raw-model、label-policy、candidate-selection 與 schema versions，以及 source mask，都與 calibrator manifest 相符。受支援的 group 使用 `supported_group`；僅因 group gate 失敗的受支援 revision，會退回主要 global mapping，並標記為 `supported_global`；manifest 或 regime mismatch 會標記為 `out_of_support`，將 $P$ 儲存為 canonical null，並設定 `decision_eligible=false`。系統保留 $z$ 供診斷使用，但任何未經驗證的 $[0,1]$ 數值都不能被稱為 probability。附錄 A.4 定義 resolver、manifest、gate 與 invalidation matrix。

## 3.6 獨立的結構化充分性與 Append-Only Audit

證據充分性是一個結構化狀態：

<a id="eq-sufficiency"></a>

$$
U_\epsilon=(u_{\mathrm{coverage}},u_{\mathrm{provenance}},
u_{\mathrm{lateness}},u_{\mathrm{contradiction}},
u_{\mathrm{calibration}}).
\tag{10}
$$

**表 4：確定性 Evidence Sufficiency Profile。**

| 軸 | 值集合 | 確定性線上輸入 |
|---|---|---|
| coverage | complete；degraded；unavailable；unknown | deployment manifest 與 SourceCoverage |
| provenance | complete；partial；missing | raw pointers 與 entity/edge traces |
| lateness | stable；revisable；late-accepted；horizon-exceeded | watermark 與 revision state |
| contradiction | none；present；unevaluable | 凍結的 online-only contradiction rules |
| calibration | supported-global；supported-group；out-of-support | Scope Resolver status $\kappa$ |

$U$ 不是 scalar confidence：它的各個軸永遠不會被加權、平均或 one-hot 排序。它不會修改、gate 或重新標記 $P$。Contradiction 軸只讀取線上證據，不能讀取 scenario、ability 或 label metadata。Downstream review 或 abstention policy 可以同時使用 $P$ 與 $U$，但該政策位於本方法範圍之外。

每個 EpisodeRevision 恰好產生一筆 insert-only AuditRecord，其中包含有序 membership 與 link reasons、$D$、$C$、$z$、可為空值的 $P$、$\kappa$、$U$、source-health snapshot、evidence references、policy/model/calibrator versions 與 canonical digest。被接受的 late evidence 會在 revision chain 中建立一筆完整的新紀錄。Canonical null、serialization、key 與 hashing rules 定義於附錄 A.1。

## 3.7 方法邊界與可重現性契約

本方法排除 CTI enrichment、RAG 或 agent components、impact 或 priority scoring、automated response、將 Identity 作為 primary source、OT/ICS generalization、ground-truth-assisted online inference，以及 downstream queue optimization。其 canonical replay payload 排除 wall-clock execution timestamps 與 machine-specific runtime metadata。本研究的貢獻僅限於：確定性的 candidate-episode construction、具版本範圍的精簡 probability calibration、獨立 evidence-sufficiency reporting，以及在 endpoint 與 network telemetry 下可重播的 append-only provenance。
