# TrustEpisode Table 2 與 Table 4 正式實驗報告

日期：2026-07-21  
版本：AISec 2026 amended submission cohort  
資料範圍：Table 2 deterministic sufficiency conformance、Table 4 M1--M6 CALDERA live cohort、temporal boundary conformance

## 1. 執行摘要

本次完成兩種性質不同、不可混為一談的驗證：

1. **Table 2** 是 evidence-sufficiency 的規範性 first-match 規則表。其完成標準是 production implementation 是否依輸入條件產生正確狀態，而不是計算平均準確率。直接測試結果為 **16 passed**，reference runtime 全套回歸為 **37 passed**。
2. **Table 4** 是 amended CALDERA BAS 情境矩陣。正式 cohort 共 **100 個 sealed runs**：40 個 B1--B8 standalone-benign runs，以及 60 個 M1--M6 malicious runs。每個 M1--M6 在 attack-only 與 concurrent-benign 模式各執行 5 次，共 12 個 malicious cells；每格均為 **5 achieved、0 failed**。

主要數據結論如下：

- M1、M3、M4、M5、M6 的 action coverage 為 **1.000**；M2 為 **0.750**。
- 60 個 malicious runs 的 fragmentation 與 over-merge 全部為 **0**。
- 12 個 malicious cells 的 episode assignment F1 全部為 **1.000**。
- attack-only contamination 為 **0**；concurrent-benign 平均 contamination 為 **0.356**。
- 299/300/301 秒與 3599/3600/3601 秒的六個 temporal boundary cases 全部符合預期；完整 formation test command 為 **7 passed**。

這些結果支持受控 Linux lab 中的 deterministic episode formation 與時間邊界實作，但不支持 calibration、held-out generalization、physical outage、perturbation robustness 或 completed live M7 的宣稱。

## 2. Table 2：Deterministic Evidence-Sufficiency Conformance

### 2.1 Table 2 的性質

Table 2 定義五個互相獨立的 sufficiency axes 及其 first-match precedence。它是 production contract，不是需要填入 mean、SD 或 F1 的經驗結果表。驗證方式是將邊界輸入送入 `ReferencePipeline._sufficiency`，比較 expected state 與 emitted state。

### 2.2 已驗證規則

| Axis | 輸入條件 | 預期狀態 | 實際狀態 | 判定 |
|---|---|---|---|---|
| coverage | health 缺失或互相衝突 | `unknown` | `unknown` | Pass |
| coverage | parser invalid | `unavailable` | `unavailable` | Pass |
| coverage | authenticated health degraded | `degraded` | `degraded` | Pass |
| coverage | health 正常且 parser valid | `complete` | `complete` | Pass |
| provenance | 所有 required references 均為有效 object | `complete` | `complete` | Pass |
| provenance | 任一 required reference 為 sentinel | `missing` | `missing` | Pass |
| lateness | revision horizon 內接受的 late evidence | `late_accepted` | `late_accepted` | Pass |
| lateness | episode 為 open 或 finalized | `revisable` | `revisable` | Pass |
| lateness | episode 已 closed | `stable` | `stable` | Pass |
| calibration | Scope Resolver 產生既有 `kappa` | 精確複製 | 精確複製 | Pass |

`provenance=partial` 是 schema 保留值，production v1 不會輸出；因此論文中的 precedence 已修正為 `missing > complete`。Contradiction 的 CR1--CR3 行為由既有 production pipeline 與 schema regression 覆蓋；本次新增的 Table 2 direct cases 聚焦 coverage、provenance、lateness 與 calibration。

### 2.3 測試統計

| 測試層級 | 結果 | 解讀 |
|---|---:|---|
| Table 2 direct pipeline tests | 16 passed | 已列條件與既有 pipeline cases 均符合 production contract |
| Reference runtime full regression | 37 passed | 本次規則修正沒有破壞其他 runtime 行為 |

### 2.4 Table 2 數據分析

Table 2 的結果應解讀為**規則一致性**，不能解讀為 live cohort 中各狀態的出現比例。直接測試顯示四項重要特性：

- **來源故障不會被當成 benign zero。** 缺失或矛盾 health 會得到 `unknown`，parser failure 會得到 `unavailable`。
- **Coverage 有明確降級路徑。** 正常、降級、不可用與未知是可重現的離散狀態。
- **Late evidence 不會覆寫既有 revision。** `late_accepted`、`revisable`、`stable` 依 episode lifecycle 決定。
- **Calibration state 不由 sufficiency evaluator 自行推導。** Evaluator 精確複製 Scope Resolver 的 `kappa`，維持 producer ownership。

目前沒有 fitted runtime artifact，因此不能從本次資料報告 Table 2 五軸在 100-run cohort 中的 empirical counts、transition matrix 或比例。論文應把 Table 2 保持為 deterministic contract，不能填入虛構的狀態分布。

## 3. Table 4：CALDERA BAS 實驗設計

### 3.1 Cohort 組成

| Cohort | Families | 每個 family/mode 重複 | Runs |
|---|---|---:|---:|
| Standalone benign | B1--B8 | 5 | 40 |
| Attack-only | M1--M6 | 5 | 30 |
| Concurrent-benign | M1--M6 | 5 | 30 |
| **合計** | **B1--B8、M1--M6** |  | **100** |

原始 registry 保留 220-row audit trail；正式論文只採用上述 100-run amended live cohort。4 個已 sealed 的 M7 attack-only traces 保留作 audit evidence，但不納入 primary estimate，也不宣稱完成 live M7。

### 3.2 M1--M6 情境

| ID | Ordered CALDERA ability family | 主要壓力條件 |
|---|---|---|
| M1 | discovery → peer inventory → SSH write | lateral chain |
| M2 | stage → archive → SCP → delayed local action | weak-to-strong sequence |
| M3 | discovery → temporary-key SSH write | remote execution |
| M4 | five-request 60 s cadence → local action | sparse sequence |
| M5 | discovery → local configuration action | source-asymmetric case |
| M6 | matched-tool SSH → remote write | benign-tool overlap |

論文中的 Table 4 列出情境與 expected evidence；量測結果則列於後續的 formation-results table。這是表格功能不同，不是遺漏 Table 4 數字。

## 4. Table 4 正式數據

所有數值均為五次 repetitions 的 `mean ± sample SD`。每個 malicious cell 均為 achieved=5、failed=0，五項 formation metrics 均為 defined=5、undefined=0。

| Family | Mode | n | Action coverage | Fragmentation | Over-merge | Contamination | Episode F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| M1 | attack-only | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| M1 | concurrent-benign | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.300 ± 0.112 | 1.000 ± 0.000 |
| M2 | attack-only | 5 | 0.750 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| M2 | concurrent-benign | 5 | 0.750 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.350 ± 0.091 | 1.000 ± 0.000 |
| M3 | attack-only | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| M3 | concurrent-benign | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.350 ± 0.091 | 1.000 ± 0.000 |
| M4 | attack-only | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| M4 | concurrent-benign | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.367 ± 0.217 | 1.000 ± 0.000 |
| M5 | attack-only | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| M5 | concurrent-benign | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.433 ± 0.091 | 1.000 ± 0.000 |
| M6 | attack-only | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 |
| M6 | concurrent-benign | 5 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.333 ± 0.257 | 1.000 ± 0.000 |

### 4.1 Mode-level 彙整

| Mode | Malicious runs | Action coverage | Fragmentation | Over-merge | Contamination | Episode F1 |
|---|---:|---:|---:|---:|---:|---:|
| Attack-only | 30 | 0.958 | 0.000 | 0.000 | 0.000 | 1.000 |
| Concurrent-benign | 30 | 0.958 | 0.000 | 0.000 | 0.356 | 1.000 |

### 4.2 Family-level 彙整

以下為每個 family 合併兩種模式後的 10-run 平均值。

| Family | Runs | Action coverage | Fragmentation | Over-merge | Contamination | Episode F1 |
|---|---:|---:|---:|---:|---:|---:|
| M1 | 10 | 1.000 | 0.000 | 0.000 | 0.150 | 1.000 |
| M2 | 10 | 0.750 | 0.000 | 0.000 | 0.175 | 1.000 |
| M3 | 10 | 1.000 | 0.000 | 0.000 | 0.175 | 1.000 |
| M4 | 10 | 1.000 | 0.000 | 0.000 | 0.183 | 1.000 |
| M5 | 10 | 1.000 | 0.000 | 0.000 | 0.217 | 1.000 |
| M6 | 10 | 1.000 | 0.000 | 0.000 | 0.167 | 1.000 |

## 5. Table 4 數據分析

### 5.1 Episode grouping 穩定，但不等於 action detection 完美

60 個 malicious runs 的 fragmentation=0、over-merge=0、episode F1=1.0，表示在這批 runs 中，builder 沒有把單一 attack group 拆成多個競爭 episodes，也沒有把不同 attack groups 錯誤合併；正確 attack group 皆能與一個 predicted episode 完成一對一 assignment。

這不代表每個 required action 都被收進 episode。M2 的 episode F1 雖為 1.0，action coverage 仍只有 0.75；正確解讀是「找到了正確主要 episode，但四個 required actions 中穩定只涵蓋三個」。

### 5.2 M2 是可重現的 completeness 限制

M2 在 attack-only 與 concurrent-benign 的十次 runs 均為 action coverage=0.75、SD=0。這不是偶發失敗，而是高度可重現的系統性缺口。由於加入 benign workload 後沒有進一步下降，問題較可能位於 delayed local action 的 membership、entity linkage、matching window 或 action attribution，而不是 concurrent workload 干擾。

因此論文可主張五個 families 達到完整 coverage，但必須保留 M2=0.75，不能用 episode F1=1.0 將它描述成 action-level 100% detection。

### 5.3 Concurrent benign workload 的主要代價是 purity

兩種模式的 action coverage、fragmentation、over-merge 與 episode F1 完全相同；唯一明顯差異是 contamination 從 0 上升至 0.356。這表示 benign background 沒有破壞主要 attack episode 的一對一匹配，但部分 benign actions 會因時間、entity、session 或 tool context 接近而被納入 matched episode。

各 concurrent-benign cell 的 contamination mean 為 0.300--0.433。M5 平均最高（0.433），但 M4 與 M6 的 SD 分別為 0.217 與 0.257，顯示五次 runs 間變異較大。由於每格只有 n=5，本報告不做 family superiority ranking，也不進行 confirmatory significance claim。

### 5.4 Standalone-benign runs 的正確解讀

40 個 B1--B8 standalone-benign runs 均納入 sealed cohort。對 benign-only runs，required malicious action coverage、malicious-group fragmentation、contamination 與 episode F1 沒有適用 denominator，因此應保持 undefined/null，而不是錯誤填成 0。它們用於固定 benign workload 與 audit inventory，不應被當成 40 個 malicious formation measurements。

## 6. Deterministic Temporal Boundary Conformance

| Dimension | 測試值 | 預期 | 實際 | 判定 |
|---|---:|---|---|---|
| `W_gap` | 299 s | Eligible | Eligible | Pass |
| `W_gap` | 300 s | Eligible | Eligible | Pass |
| `W_gap` | 301 s | Ineligible | Ineligible | Pass |
| `W_max` | 3599 s | Eligible | Eligible | Pass |
| `W_max` | 3600 s | Eligible | Eligible | Pass |
| `W_max` | 3601 s | Ineligible | Ineligible | Pass |

結果證明 production `EpisodeSynthesizer._candidate` 使用 inclusive 300 s gap 與 3600 s span：邊界值仍允許連結，超過一秒即拒絕。這是 deterministic implementation conformance，不是 3900 秒 live M7 BAS result，也不能替代長時間服務穩定性測試。

## 7. 可回填論文的結論

下列文字受目前證據直接支持：

> In the amended 60-run M1--M6 malicious cohort, five families achieved complete required-action coverage and M2 achieved 0.75. No fragmentation or over-merge was observed, and episode assignment F1 was 1.0 in every cell. Concurrent benign activity preserved action coverage but increased mean contamination to 0.356. Deterministic production-path tests confirmed the inclusive 300-second gap and 3600-second span boundaries.

可支持的主張：

- M1--M6 controlled live executions 的 episode-formation 結果。
- attack-only 與 concurrent-benign 的 action coverage、fragmentation、over-merge、contamination 與 episode F1。
- Table 2 production rule conformance。
- 300/3600 秒 inclusive boundary semantics。

不可支持的主張：

- 100% action-level attack detection。
- calibrated probability、Brier、NLL、AUPRC 或 reliability performance。
- held-out、locked-test、production 或跨環境泛化。
- adversarial perturbation、partial telemetry 或 physical-outage resilience。
- completed live M7 或 3900 秒長時間 campaign。

## 8. 有效性限制

1. 每個 family/mode 只有五次 repetitions；mean 與 sample SD 應視為 descriptive statistics。
2. 結果來自 amended controlled-lab cohort，沒有獨立 held-out cohort。
3. Table 2 驗證規則輸出，不提供五軸 empirical distribution。
4. M7 未納入 primary cohort；boundary tests 只驗證 deterministic semantics。
5. Concurrent-benign contamination 平均為 0.356，episode purity 仍是主要改善方向。
6. 本實驗不代表 commercial EDR effectiveness 或 production enterprise base rate。

## 9. 證據完整性

| 證據 | SHA-256 |
|---|---|
| Table 2 conformance report | `118be5352c4cc8948bd247b0eb58c2cf8e77671d84ca54e20957c7000560646b` |
| Table 4 cell CSV | `e11abcc4c126aa433acbbf7dc2efd1e1c5905e4fc0b91e7f49bb0e8cc12a727b` |
| Table 4 per-run JSON | `1b16a2125e812dd20da9e05970d30a72d0cce4f0d761752930e7eddcbd8a7edb` |
| Temporal boundary report | `eaa38f296518a767ee1862c1b41ae9973a2e816a6f4910713bbdca590cfc6f15` |
| Five-repetition protocol amendment | `fbfa63a123f0b79a6304c0d22b7106fabede934a00831eddc14b8823044b0bef` |

## 10. 最終判定

Table 2 的 deterministic contract 與 Table 4 的 amended 100-run live cohort 均已有可稽核證據。最可信的結論是：**TrustEpisode 在觀察到的 M1--M6 情境中維持穩定的一對一 episode grouping，且 deterministic sufficiency 與 temporal rules 符合 production contract；但 M2 action completeness 與 concurrent-benign contamination 仍是明確限制。**

在論文明確揭露五次重複、M7 排除、沒有 held-out/calibration/robustness 結果的前提下，這些資料可以作為受限但真實的 live-system evidence 回填並投稿。
