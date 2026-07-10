# TrustEpisode v2 論文改稿完成報告

## 1. 執行範圍與結論

本次依據 `TrustEpisode_論文撰寫計畫_更新版_v2.md` 完成計畫授權範圍內的改稿：

- Section 3 Method：完成重寫。
- Section 4 Evaluation：完成重寫，結果欄位依計畫維持 `pending`，未填入假資料。
- Appendix A--F：完成新增與主文契約對齊。
- References：補齊方法、校準、資料洩漏、統計與工具版本引用。
- 投稿版 Figures 1--4：由 `trustepisode_figures` 精選納入並完成視覺檢查；第五張 linking decision 圖保留於完整重現版。
- `main.pdf`：12 頁 AISec 投稿版；`main_full.pdf`：20 頁完整 Appendix A--F 重現版。

結論：**v2 計畫授權的 Section 3、Section 4、Appendix、References 與圖表整合項目已全部完成。**

## 2. Section 3 完成矩陣

| 要求 | 完成狀態 | 實作位置 |
|---|---|---|
| EDR/NDR primary scope，固定 `K=2` | 通過 | Section 3.1、3.4 |
| `C`、`C_sup`、revision-specific offline labels | 通過 | Section 3.1 |
| 單一 producer ownership 與唯一 `AuditRecord` | 通過 | Table 2、Section 3.6 |
| Figure 1 與 ownership table 同一組 owner | 通過 | Figure 1、Table 2 |
| Identity 完全排除於 primary candidate universe | 通過 | Figure 1、Section 3.4、Appendix A.5/E |
| `m`、`h`、`q` 分離，source health 不進 raw scorer | 通過 | Section 3.2 |
| deterministic 0/1/multiple-candidate episode synthesis | 通過 | Section 3.3、Appendix B |
| immutable revisions、watermark 與 late-evidence 規則 | 通過 | Section 3.3、Appendix B |
| `D` top-three CDF、`C=q_EDR q_NDR` | 通過 | Section 3.4、Appendix C |
| stateless scorer `z=b+w_D D+w_C C` | 通過 | Section 3.4 |
| global primary affine calibration、conditional group mapping | 通過 | Section 3.5、Appendix D |
| out-of-support 時 `P=NA`、`decision_eligible=false` | 通過 | Section 3.5、Appendix A/D |
| 五軸 structured `U`，不修改或取代 `P` | 通過 | Section 3.6、Appendix C |
| method boundary 排除 CTI/RAG/Agent/impact/response | 通過 | Section 3.7 |
| Section 3 開場 150--220 words | 通過 | 實測 167 words |

## 3. Section 4 完成矩陣

| 要求 | 完成狀態 | 實作位置 |
|---|---|---|
| RQ1--RQ4 claim boundary | 通過 | Section 4.1 |
| 僅保留 Tier 1 DARPA TC 與 Tier 2 controlled Caldera | 通過 | Section 4.2、Table 5 |
| online ground-truth firewall 與 offline-only join | 通過 | Section 4.3、Appendix A/E |
| M1--M7 malicious scenario families | 通過 | Section 4.4、Appendix E |
| B1--B8 benign/hard-negative families | 通過 | Section 4.4、Appendix E |
| campaign/run-level mutually exclusive splits | 通過 | Section 4.5、Appendix F |
| natural-prevalence calibration 與 support gate | 通過 | Section 4.6、Appendix D |
| formation baselines EB1/EB2/EB3/EB3-H | 通過 | Section 4.7、Appendix F |
| scoring/calibration baselines SB1--SB7 | 通過 | Section 4.7、Appendix F |
| paired replay 與 physical outage 分離 | 通過 | Section 4.8、Appendix F |
| metrics、run-cluster bootstrap 與 fixed seed | 通過 | Section 4.9、Appendix F |
| 結果 shell 保留 pending，不製造數值 | 通過 | Section 4.10、Appendix F |
| limitations 與 claim safety | 通過 | Section 4.11 |

## 4. Appendix 與圖表

Appendix 已具備六個完整區塊：

- A：Online data contracts、canonical null/JSON、firewall examples。
- B：episode eligibility、total order、IDs、watermark、deterministic replay。
- C：feature、structured U、parameter taxonomy、single threshold registry。
- D：calibrator manifest、group resolver、invalidation matrix。
- E：lab manifest、M1--M7、B1--B8、Identity gate、offline join、leakage tests。
- F：split/freeze、baseline registry、perturbation grid、outage SOP、metrics、bootstrap、result registry。

投稿版保留四張非重複圖：整體架構、revision lifecycle、Ground Truth Firewall，以及 partial-telemetry/physical-outage design。Figure 1 已補齊 Feature Extractor、Scope Resolver 與唯一 owner，並把 Identity 移出 primary solid path。完整重現版另保留附錄 linking decision。圖庫仍保留九張來源圖；舊 `ScoreRecord` 用語已改成唯一的 immutable `AuditRecord`，圖說與內文一致。

投稿版 A.1--A.6 不再是摘要：現已內含 schema registry、episode total order、parameter/threshold registry、calibrator invalidation matrix、matching/metric formulas、RQ matrix 與 R3a/R3b result shells。逐場景操作卡與 CORP decomposition 明確保留於 companion reproducibility appendix，不再由投稿版過度承諾。

## 5. 自動與視覺驗證

| 驗證項目 | 結果 |
|---|---:|
| 投稿版 `main.pdf` | 12 頁；405,076 bytes |
| 投稿版 SHA-256 | `4391e962257d673d2e61b23615a434af08d4936ae26e9aafca719c6f94f38a75` |
| 完整版 `main_full.pdf` | 20 頁；460,365 bytes |
| 完整版 SHA-256 | `41e91b49750855cf9a7d7c37d04273401226063c52ecc2e7f0eed735dcbfe3cd` |
| 投稿版圖檔解析 | 4/4 |
| Figure 1--4 出現在投稿版 PDF | 通過 |
| duplicate labels | 0 |
| missing refs | 0 |
| duplicate BibTeX keys | 0 |
| missing citations | 0 |
| undefined references/citations | 0 |
| `ScoreRecord` / `K=3` / three-source / Tier 3 / SB8 / A8 | 全部 0 命中 |
| 投稿版全 12 頁視覺檢查 | 通過；無空白頁、裁切、重疊或圖表破版 |
| AISec 2026 Generative AI 使用聲明 | 通過；位於第 12 頁 bibliography 後 |

兩個版本均由 Tectonic 編譯成功。投稿版沒有 overfull 警告；完整版僅有平衡參考文獻欄位時的 `1.09pt` 垂直微量警告，視覺檢查未見裁切或重疊。

## 6. 明確保留事項

1. 實驗尚未執行，因此所有結果 shell 保持 `pending`；這是 v2 計畫明定行為，不是缺漏。
2. v2 計畫明定不修改 Section 1、Section 2、Section 5；標題與摘要也未列入本次方法改寫範圍。這些既有段落仍保留 CTI/RAG/Agentic/impact 敘事，與新版 Section 3 方法邊界存在全篇敘事風險。
3. 因此「全部完成」的判定只適用於 v2 明確授權的 Section 3、Section 4、Appendix、References 與 figures 範圍，不能延伸解讀為實驗結果已完成或全篇所有章節已統一改寫。
