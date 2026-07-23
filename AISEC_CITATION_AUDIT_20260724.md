# TrustEpisode AISec 2026 引用與逆向審稿稽核

- 稽核日期：2026-07-24
- 稽核基準：最新版 `main.pdf`、`main.aux`、`bib/references.bib`
- 實際引用數：25

## 結論

實際輸出到投稿 PDF 的 25 筆文獻均已對照 DOI、官方論文頁、標準頁或出版社資料。
本輪找到並修正一個會傷害審稿可信度的錯誤 DOI，以及數個不完整或不精確的 metadata。
修正後未發現引用到不存在的論文、未解析的 BibTeX key 或標題與 DOI 不符的文獻。

## 已修正項目

1. `breitinger2025sok`
   - 原 DOI `10.1016/j.fsidi.2025.301880` 實際指向另一篇論文。
   - 正確資訊為 *Forensic Science International: Digital Investigation* 53,
     article 301932，DOI `10.1016/j.fsidi.2025.301932`。
   - 同步修正 volume、article number 與作者顯示。
2. `auditableddos2026`
   - 補齊 Haodong Chen、Ziheng Zhang、Jinghui Jiang、Qiang Su、Qiao Xiang。
   - 補入 arXiv `2601.14601`、DOI `10.48550/arXiv.2601.14601` 與官方 URL。
3. `cortex2025`
   - 將錯誤的 arXiv primary class `cs.CR` 修正為官方的 `cs.CL`。
   - 補入 DOI `10.48550/arXiv.2510.00311`。
4. `missingmodality2024`
   - 補入 DOI `10.48550/arXiv.2409.07825`。
5. `swgde2018tooltesting`
   - 將只指向 SWGDE 首頁的 URL 改為指定文件 `18-Q-001-2.1` 的官方頁面。

## 論述與表格風險修正

- 移除 Related Work 比較表中證據不足的 `Live` 欄位；原欄位可能把離線資料集評估
  誤讀為 live validation。
- 明示 40 個 B1--B8 standalone benign runs 是 execution controls，不是 false-positive
  trials；本稿沒有 fitted scorer 或 detection decision rule，因此不宣稱 false-positive rate。
- 將 `110 sealed train runs` 改為 `110 sealed live executions`，避免讀者誤以為這是模型
  訓練集效果。

## 驗證方式

- 由 `main.aux` 取得實際引用 key，而不是稽核未被使用的 bibliography entries。
- DOI 使用內容協商取得標題 metadata，並與 BibTeX 標題正規化比對。
- arXiv 文獻使用官方摘要頁核對 title、authors、year、identifier 與 primary class。
- NIST、RFC、JSON Schema、SWGDE 使用各自的官方文件頁。
- Casey 與 Carrier 兩本書沒有 DOI，使用 Elsevier／InformIT 出版資料核對書名、作者、
  版本與出版年。
- DOI 端點的 HTTP 403/429 僅視為 publisher bot protection 或速率限制；必須已有
  DOI metadata 或官方出版頁的獨立核對，才列為通過。

## 本輪使用的主要官方來源

- Breitinger et al.:
  <https://www.sciencedirect.com/science/article/pii/S266628172500071X>
- Holmes:
  <https://arxiv.org/abs/2601.14601>
- CORTEX:
  <https://arxiv.org/abs/2510.00311>
- Missing-modality survey:
  <https://arxiv.org/abs/2409.07825>
- SWGDE 18-Q-001-2.1:
  <https://www.swgde.org/18-q-001/>
- Digital Evidence and Computer Crime, 3rd ed.:
  <https://shop.elsevier.com/books/digital-evidence-and-computer-crime/casey/978-0-08-092148-8>
- File System Forensic Analysis:
  <https://www.informit.com/store/file-system-forensic-analysis-9780134439556>

## 最終判定

`PASS`：25/25 實際引用可追溯；0 個 missing BibTeX key；0 個 title/DOI mismatch；
0 個未定義 citation；修正後 PDF bibliography 可讀且未溢位。
