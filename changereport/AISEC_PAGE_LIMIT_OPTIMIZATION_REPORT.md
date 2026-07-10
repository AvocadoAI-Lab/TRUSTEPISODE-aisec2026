# TrustEpisode AISec 2026 頁數優化與合規報告

更新日期：2026-07-10  
驗證基準：專案根目錄 `main.pdf` 與 `main_full.pdf`  
官方規則：[AISec 2026 Call for Papers](https://aisec.cc/)

## 結論

AISec 2026 規定主文最多 10 頁；bibliography 與明確標示的 appendix 最多再使用 2 頁，因此投稿 PDF 全文最多 12 頁。官方另要求在 references/appendices 之後放置 Generative AI 使用聲明，且該段不計頁限。

| 版本 | 頁數 | 圖數 | 用途 | 判定 |
|---|---:|---:|---|---|
| `main.pdf` | 12 | 4 | AISec 投稿版 | 通過；主文於第 10 頁結束，AI 使用聲明位於第 12 頁 |
| `main_full.pdf` | 20 | 5 | 完整重現與內部審查版 | 非投稿 PDF；保留完整 Appendix A--F |

## 本輪問題與處理

| 審查問題 | 原狀態 | 最終處理 | 狀態 |
|---|---|---|---:|
| A.1--A.6 只有摘要 | 正文聲稱附錄有 schemas、invalidation matrix、formulas、matching、RQ matrix、R3a/R3b shells，但投稿版未提供 | `appendix_submission.tex` 改為可稽核的 schema registry、episode total order、parameter/threshold registry、invalidation matrix、matching/metric formulas、RQ matrix 與 R3a/R3b shells | 關閉 |
| 完整 scenario cards 與 CORP 無法塞入 12 頁 | 正文把所有細節都指向投稿附錄 | 投稿附錄保留 family-level admission/failure contract；正文將逐卡 ordered actions/cleanup 與 CORP decomposition 明確指向 companion reproducibility appendix | 關閉 |
| Figure 1 與 ownership table 不一致 | 圖中缺 Feature Extractor/Scope Resolver，且資料流 owner 不明 | Figure 1 依 Table 2 重畫：NormalizedEvent、EpisodeRevision、`[D,C]`、`z`、`kappa`、`P`、`U` 與 AuditRecord 均有唯一 owner | 關閉 |
| Identity 位於 primary solid path | Identity 可能改變 candidate universe | Identity 從 Telemetry 與所有 solid primary paths 移除；正文與兩版附錄明定它不進 NormalizedEvent、Episode Synthesis、candidate IDs/membership、features 或 calibrator manifest | 關閉 |
| AISec 2026 新增 AI 聲明 | 舊稿沒有聲明 | `main.tex` 在 bibliography 後加入實際使用範圍與「未生成實驗資料/結果」聲明 | 關閉 |

## 投稿版附錄內容

投稿版 A.1--A.6 現在實際包含：

1. 五個 canonical online schemas、types、canonical JSON/null、SHA-256、append-only 與 firewall 規則。
2. Inclusive eligibility、candidate total order、start/merge IDs、membership order、late revision 與 replay equality。
3. Scorer/calibrator/formation/feature/runtime/evaluation 的 owner、fit data 與 freeze point，以及單一 threshold registry。
4. Calibrator manifest、group support gate、fallback/out-of-support 行為與八列 invalidation matrix。
5. Run manifest、M1--M7/B1--B8 family-level failure handling、offline label join 與 Identity exclusion contract。
6. Frozen matching、ActionCoverage、Fragmentation、Brier、NLL、supported coverage、fixed-budget recall、2,000-run bootstrap、完整 RQ matrix 與 R3a/R3b `pending` shells。

完整逐場景操作卡、完整 perturbation grid、完整 sufficiency rule table 與其他重現細節仍保留在 `sections/appendix.tex`，由 `main_full.tex` 編譯；投稿版不再假稱已收錄這些高體積內容。

## 頁面配置

| 頁碼 | 主要內容 | 頁限分類 |
|---:|---|---|
| 1--9 | Abstract、Sections 1--4、Figures 1--4 | 主文 |
| 10 | Section 4 結尾、Conclusion、Appendix A.1--A.2 起點 | 主文在本頁結束 |
| 11 | Schema registry、A.3--A.6、References 起點 | appendix / bibliography |
| 12 | Parameter registry、invalidation matrix、RQ/R3 shells、References 結尾、AI 使用聲明 | appendix / bibliography；AI 聲明不計頁限 |

未修改 ACM 全域字級、頁邊界或雙欄格式，也未填入假實驗數值。表格使用 ACM 文件既有的 `\scriptsize`，正文仍維持 class 預設字級。

## 驗證結果

| 項目 | 投稿版 | 完整版 |
|---|---:|---:|
| 編譯 | 通過 | 通過 |
| 頁數 | 12 | 20 |
| 有文字頁面 | 12/12 | 20/20 |
| undefined references/citations | 0 | 0 |
| overfull hbox | 0 | 0 |
| overfull vbox | 0 | bibliography balancing `1.09pt` |
| 視覺檢查 | 12/12 通過；Figures/Appendix/References/AI statement 無裁切或重疊 | Appendix E/F 與末頁通過 |

### 檔案雜湊

| 檔案 | Bytes | SHA-256 |
|---|---:|---|
| `main.pdf` | 405,076 | `4391e962257d673d2e61b23615a434af08d4936ae26e9aafca719c6f94f38a75` |
| `main_full.pdf` | 460,365 | `41e91b49750855cf9a7d7c37d04273401226063c52ecc2e7f0eed735dcbfe3cd` |

## 剩餘投稿風險

| 等級 | 風險 | 必要行動 |
|---|---|---|
| 高 | 實驗結果仍為 `pending` | 執行 frozen locked-test pipeline，以真實數值與 intervals 取代結果殼 |
| 高 | 全篇敘事仍不一致 | Title、Abstract、Sections 1/2/5 仍有 CTI/RAG/Agentic/impact 舊敘事，須另輪統一 |
| 中 | Appendix 不保證由 reviewer 閱讀 | 主文必須維持自足；不可把核心 method definition 或主要結果只放附錄 |
| 中 | Artifact/匿名審查尚未完成 | 依 AISec 2026 CFP 決定匿名 repository 與 artifact link，檢查 metadata/URL 洩漏 |
| 低 | 完整版 bibliography balance | `1.09pt` 微量警告不影響投稿版，視覺檢查未見裁切 |

## 編譯方式

```powershell
# AISec 投稿版
.\tmp\tools\tectonic\tectonic.exe --keep-logs --keep-intermediates --outdir tmp\build-submission main.tex

# 完整重現版
.\tmp\tools\tectonic\tectonic.exe --keep-logs --keep-intermediates --outdir tmp\build-full main_full.tex
```

頁數、附錄完整性與 Figure 1/Identity 邊界問題已解決；這不代表尚未執行的 empirical evaluation 已完成。
