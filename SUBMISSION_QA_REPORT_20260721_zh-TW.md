# TrustEpisode AISec 投稿前 QA 報告

日期：2026-07-21  
檢查範圍：投稿版論文、Table 2 實作一致性、Table 4/5 實驗證據、補充重現套件

## 結論

目前狀態為「技術內容可投稿，仍需作者完成投稿平台與政策層級的人工確認」。投稿版 PDF、五次重複的 amended live cohort、Table 2 決定性規則測試，以及補充重現套件已完成一致性與完整性校驗。Section 1 與 Section 2 已整合 `yuying-sec1-sec2` 的研究動機、相關工作與書目修訂，並依現行 Section 3 邊界移除未實作能力及未完成實驗宣稱。

本版論文只主張已完成的 M1--M6 live cohort 與 deterministic temporal boundary conformance；未將 calibration、held-out、perturbation、physical outage、deterministic replay 或 M7 寫成已完成結果。

## 已完成的正式證據

| 項目 | 結果 | 判定 |
|---|---:|---|
| 投稿版 PDF | 11 頁 | 通過 |
| Table 4 amended live cohort | 100 runs：M1--M6 共 60、B1--B8 共 40 | 通過 |
| M1--M6 每格重複 | attack-only 與 concurrent-benign 各 5 次 | 通過 |
| Table 4 失敗／未定義 cell | 每格 5 achieved、0 failed、0 undefined | 通過 |
| Table 2 直接規則測試 | 16 passed | 通過 |
| reference runtime 全套回歸 | 37 passed | 通過 |
| contract validator | PASS | 通過 |
| 補充 ZIP manifest | 64/64 非 manifest 檔案雜湊相符，無額外未登錄檔案 | 通過 |
| 從解壓套件執行 runtime 測試 | 37 passed | 通過 |
| PDF 未解析引用／LaTeX error | 0 | 通過 |

## Table 2 一致性判定

Table 2 是五個 evidence-sufficiency 軸的 deterministic first-match 規則表，不是另一組需要填入平均值與標準差的效能實驗表。

本次已直接對 production `ReferencePipeline._sufficiency` 增加並執行規則測試，涵蓋：

- coverage：`unknown`、`unavailable`、`degraded`、`complete`
- provenance：`missing`、`complete`
- lateness：`late_accepted`、`revisable`、`stable`
- calibration：精確複製既有 kappa 狀態

論文與程式現已一致：provenance v1 的實際優先序為 `missing > complete`；`partial` 僅為 schema 保留值，v1 不會產生該狀態。

## Table 4/5 結果解讀

M1、M3、M4、M5、M6 的 action coverage 均為 1.000；M2 為 0.750。所有十二個 malicious cells 的 fragmentation、over-merge 都為 0，episode F1 都為 1.000。這支持目前較窄的主張：在這組 live Linux BAS 情境中，episode formation 能穩定保留場景證據，且沒有觀察到 episode 分裂或跨 episode 誤合併。

Concurrent-benign 模式的 contamination 平均值介於 0.300 與 0.433；attack-only 均為 0。這是 benign activity 被納入 episode 的可觀察成本，因此論文不應將結果描述成「完全沒有污染」，而應如目前 Table 5 一樣透明報告。

五次重複適合支撐這次 amended cohort 的描述性結果，但不足以把尚未執行的 robustness、outage、calibration 或跨環境泛化宣稱為已證實。

## 全文宣稱稽核

已確認投稿版 PDF：

- 不含 `pending`、`TBD`、假雜湊或 simulated 數值。
- Table 3 對未完成分析明列 `not executed`。
- 擾動、斷線與完整統計流程均使用未來式或 prospective protocol 語氣。
- 不宣稱 live M7 已完成；4 條 sealed M7 traces 維持排除於 primary cohort。
- supplementary archive 名稱與 SHA-256 已寫入論文。
- AI 使用揭露位於第 11 頁。

PDF 仍有四個既存的 overfull hbox 警告，均位於架構／公式區；本次逐頁渲染檢查未見文字裁切、欄位互相覆蓋或表格越界。這些警告不構成目前的阻擋項。

## 投稿檔案與雜湊

| 檔案 | SHA-256 |
|---|---|
| `main.pdf` | `99710c375b5429982fd6b7a90873d0b94c008f13dfc3effacf15105bbdc767fc` |
| `TrustEpisode_reproducibility_companion_v1.zip` | `45c191952c48411e0de534c2d99762c451e44f56f031277ceb8354715e1949ef` |

補充 ZIP 內含 contracts、Table 4 CSV/JSON/正式報告、Table 2 conformance 報告、temporal boundary conformance、aggregation script、reference runtime 原始碼與測試，以及完整 SHA-256 manifest。

## 已知限制與禁止擴張的宣稱

- 不得宣稱 M7、physical collector outage、perturbation dose-response、calibration、held-out evaluation 或 deterministic replay benchmark 已完成。
- Table 6 的外部 comparator 是 secondary context，並非本研究重新執行的同條件基準。
- 100-run cohort 與每格五次重複應明確稱為 amended protocol；不可再稱為原始 220-run 設計已完成。
- 結果只直接支持目前受控的兩台 live Ubuntu targets 與 inline NDR sensor，不代表商用 EDR 產品或跨組織泛化效能。

## 投稿前最後人工關卡

1. 上傳本報告所列的精確 `main.pdf` 與補充 ZIP；若平台允許，一併保存 `.sha256` sidecar。
2. 依投稿會議最新規範確認頁數、匿名政策、supplementary 上傳方式與生成式 AI disclosure 是否應保留在主文、移至聲明欄或另行提交。
3. 檢查 PDF metadata、作者欄、致謝與補充檔內容是否符合 double-blind 要求。
4. 投稿後下載平台生成的預覽檔，再核對頁數與兩個 SHA-256，避免平台轉檔或誤傳舊版本。
