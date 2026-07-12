# TrustEpisode AISec 2026 頁數優化與合規報告

驗證日期：2026-07-11  
驗證對象：專案根目錄 `main.pdf`、companion ZIP 與最新 submission LaTeX log

## 1. 結論

[AISec 2026 官方 CFP](https://aisec.cc/) 規定主文最多 10 頁，bibliography 與明確標示的 appendix 最多再使用 2 頁，投稿 PDF 最多 12 頁。最新投稿版為 **12 頁**，Conclusion 位於第 9 頁，符合主文與總頁數限制，但已無總頁數餘裕。

| 版本 | 頁數 | 圖數 | 用途 | 判定 |
|---|---:|---:|---|---|
| `main.pdf` | 12 | 4 | AISec 投稿版 | 通過（達上限） |

## 2. 投稿版頁面配置

| 頁面 | 主要內容 | 頁限分類 |
|---:|---|---|
| 1--8 | Abstract、Sections 1--4、Figures 1--3、Tables 1--6 | 主文 |
| 9 | Figure 4、Section 4 結尾與 Conclusion | 主文文字在本頁結束 |
| 10 | Submission appendix A.1--A.6 | Appendix |
| 11 | Table 7 與 References 起點 | Appendix / bibliography |
| 12 | References 結尾 | Bibliography |

主文 Conclusion 位於第 9 頁，submission appendix 位於第 10--11 頁，References 位於第 11--12 頁。PDF 已使用完整 12 頁上限；新增 locked-test 數值或 plots 後必須重新排版，不能再增加頁數。

## 3. 圖片策略

投稿版只保留四張回答核心契約的圖：

1. Figure 1：online/offline ownership 與 AuditRecord Assembler。
2. Figure 2：episode revision lifecycle。
3. Figure 3：Ground Truth Firewall。
4. Figure 4：paired replay 與 physical outage 的分離。

其餘 companion figures 不屬於投稿 PDF 的必要依賴。投稿版只保留能直接支撐 ownership、revision、ground-truth firewall 與 perturbation protocol 的四張圖。

## 4. Appendix 與本機 Companion

投稿版 A.1--A.6 已提供可直接稽核的內容：

- Draft 2020-12 八物件 schema、SupportDecision、AssemblyOutcome 與 canonical-null 規則。
- Episode total order、固定 revision deadline、LateEvidenceRecord 與 replay assertions。
- Numeric thresholds、health-independent detector observation、resolved availability、CR1--CR3 與五軸 `U` precedence。
- Global/group calibration objective、group key、final refit、exclusive resolver 與 invalidation。
- Caldera pin、M1--M7、M5-ID、B1--B8 與 offline labels。
- 三個 population、每個 10-run stratum 的 50/20/10/20 split、RP0--RP7、PO1 timestamps、graph metrics、RT6 cost protocol 與 RT1--RT7。

完整 machine contracts 位於本機 `artifacts/contracts/`，並封裝為：

```text
TrustEpisode_reproducibility_companion_v1.zip
SHA-256: 6298bd2e89bd50a78a890b62750dcca2bcee34906fd6dd73a4a77f2a19c81205
```

Zip integrity、17 個 manifest entries 與 sidecar hash 已在本機驗證。Bundle 只含 `contracts/`，不包含 `main_full.pdf`、虛構 run 或 result。投稿 PDF 已將此精確 ZIP/hash 定義為 required supplementary artifact；HotCRP 若未上傳或 hash 不符，即為投稿缺件。

## 5. 編譯與 PDF QA

| Gate | `main.pdf` |
|---|---|
| Tectonic build | PASS |
| Undefined / multiply defined | 0 |
| Overfull hbox | 0 |
| Final-page output vbox | 1.17 pt；頁框座標與視覺檢查均無裁切 |
| Figures | 1--4 |
| U+22AE / U+FFFD | 0 / 0 |
| Out-of-page text blocks | 0 |
| Visual render | 12/12 pages inspected |

Type3 entries reported by PDF extraction are TeX mathematical glyph resources；正文與數學符號均正常渲染。兩個 indicator 在文字層均抽取為 `1[...]`，不再是 U+22AE。

## 6. 最終檔案指紋

| 檔案 | Bytes | SHA-256 |
|---|---:|---|
| `main.pdf` | 263,278 | `aca9399f0a2721ef6d69111eacbf27d590f3b1bc1d9eebf5ee6542a6eeac5f3b` |
| companion ZIP | 36,235 | `6298bd2e89bd50a78a890b62750dcca2bcee34906fd6dd73a4a77f2a19c81205` |

## 7. 尚未完成的研究工作

頁數與契約完整性已通過，但 empirical evaluation 仍是 `pending`。正式投稿前仍需執行 frozen M1--M7/B1--B8、replay/outage、locked-test metrics、2,000-run-cluster bootstrap 與 reliability plots。不得把頁數合規解讀成實驗結果已完成。
