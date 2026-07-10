# TrustEpisode - AISec 2026 Paper

TrustEpisode 是一份使用 ACM `sigconf` 雙欄格式撰寫的匿名論文稿，研究重點是：將 EDR/NDR 異質遙測轉換成 deterministic、immutable episode revisions，並對每個 revision 產生 manifest-supported calibrated maliciousness probability、獨立的 evidence-sufficiency profile，以及 append-only audit record。

論文標題：

> **TrustEpisode: Calibrated Episode Risk Scoring with Evidence-Grounded Agentic RAG for Multi-Step Cyber Attacks**

> 注意：目前 Title、Abstract、Sections 1/2/5 仍保留較早期的 CTI/RAG/Agentic/impact 敘事；新版 Section 3 的正式方法邊界已排除這些模組。此全篇敘事一致性問題仍須在正式投稿前處理。

## 目前輸出版本

| 檔案 | 頁數 | 圖數 | 用途 |
|---|---:|---:|---|
| `main.pdf` | 12 | 4 | AISec 投稿版；主文於第 10 頁結束，附錄與 References 使用第 10--12 頁 |
| `main_full.pdf` | 20 | 5 | 完整重現與內部審查版；保留 Appendix A--F |

[ACM AISec 2026 官方 CFP](https://aisec.cc/) 規定：主文最多 10 頁，不含 bibliography 與明確標示的 appendix；bibliography/appendix 最多再使用 2 頁，PDF 全文最多 12 頁。投稿還必須在 references/appendices 後加入 Generative AI 使用聲明；該聲明不計頁限。`main.pdf` 已同時符合頁數與聲明要求。

## 方法範圍

正式的 v2 方法契約固定為：

```text
EDR + NDR telemetry
  -> Evidence Fabric
  -> deterministic Episode Synthesis
  -> compact stateless scorer
  -> manifest-scoped affine calibrator
  -> nullable calibrated probability P

SourceCoverage + EpisodeRevision + provenance + calibration status
  -> deterministic Sufficiency Evaluator
  -> structured five-axis U

P + U + versions + evidence references
  -> immutable append-only AuditRecord

Ground truth
  -> offline training / calibration / evaluation only
```

核心限制：

- Primary telemetry scope 固定為 `S* = {EDR, NDR}`、`K = 2`。
- Identity 只能是 pilot-gated、post-inference 的離線 exploratory annotation；不進入 NormalizedEvent、Episode Synthesis、candidate universe、primary features 或 calibrator manifest。
- Episode Synthesis 是 membership 與 revision 的唯一 owner。
- Scorer 只使用 `[D, C]`，source health、labels、`U` 不進入 raw scorer。
- Affine calibrator 是 calibrated probability `P` 的唯一 producer。
- Unsupported regime 必須輸出 canonical-null `P` 與 `decision_eligible=false`。
- `U` 是五軸 evidence-sufficiency profile，不是第二個 probability，也不修改 `P`。
- Ground truth、scenario IDs、attack windows 與 split assignments 不得進入 online objects。
- 每個 EpisodeRevision 只能產生一筆 immutable、append-only AuditRecord。

## 專案結構

```text
main.tex                         # 預設編譯 12 頁 AISec 投稿版
main_full.tex                    # 啟用完整 Appendix A--F
main.pdf                         # 已驗證投稿版
main_full.pdf                    # 已驗證完整重現版
section3.md                      # Section 3 繁體中文 Markdown 對照版

sections/
  intro.tex                      # Section 1: Introduction
  related.tex                    # Section 2: Related Work
  arch.tex                       # Section 3: TrustEpisode Method
  exps.tex                       # Section 4: Evaluation
  conc.tex                       # Section 5: Conclusion
  appendix_submission.tex        # 投稿版精簡契約附錄
  appendix.tex                   # 完整 Appendix A--F

bib/
  references.bib                 # BibTeX references

trustepisode_figures/
  svg/                           # 可編輯向量原稿
  pdf/                           # LaTeX 實際插入的向量 PDF
  png/                           # 預覽與簡報使用
  preview/contact_sheet.png      # 九張來源圖總覽
  figures.tex                    # Figure/caption/label 範例
  README_zh-TW.md                # 圖包語意與配置說明

figs/                            # 舊版 P/I/U 與 Agentic 圖，不被目前論文引用
tools/generate_eps_figures.py    # 只重建 figs/ 內的舊版 EPS/PDF

AISEC_PAGE_LIMIT_OPTIMIZATION_REPORT.md
SECTION3_SECTION4_DETAILED_COMPARISON_REPORT.md
TRUSTEPISODE_V2_COMPLETION_REPORT.md
```

## 圖片使用方式

投稿版實際引用以下四張向量 PDF：

```text
trustepisode_figures/pdf/fig01_final_architecture.pdf
trustepisode_figures/pdf/fig02_episode_revision_lifecycle.pdf
trustepisode_figures/pdf/fig05_ground_truth_firewall.pdf
trustepisode_figures/pdf/fig07_partial_telemetry_perturbations.pdf
```

完整版另外引用：

```text
trustepisode_figures/pdf/fig08_episode_linking_decision.pdf
```

LaTeX 插圖範例：

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{
    trustepisode_figures/pdf/fig01_final_architecture.pdf
  }
  \caption{TrustEpisode online and offline boundaries.}
  \label{fig:method-architecture}
\end{figure*}
```

ACM 雙欄橫向架構圖應使用 `figure*` 與 `width=\textwidth`；不要硬縮成單欄，否則圖中文字會過小。

### 從 SVG 匯出 PDF

若已安裝 Inkscape，可將修改後的 SVG 重新匯出成向量 PDF：

```powershell
inkscape trustepisode_figures\svg\fig01_final_architecture.svg `
  --export-type=pdf `
  --export-filename=trustepisode_figures\pdf\fig01_final_architecture.pdf
```

批次匯出全部九張來源圖：

```powershell
Get-ChildItem trustepisode_figures\svg\*.svg | ForEach-Object {
  $output = Join-Path "trustepisode_figures\pdf" ($_.BaseName + ".pdf")
  inkscape $_.FullName --export-type=pdf --export-filename=$output
}
```

`tools/generate_eps_figures.py` 只會產生 `figs/fig1_revised_architecture`、`fig2_piu_separation`、`fig3_assurance_protocol` 的 EPS/PDF。這些圖含舊版 P/I/U、Agentic Assurance 語意，**目前論文不引用，不能用來覆蓋正式圖包**。

## 編譯需求

建議環境：

- Windows 11 + PowerShell
- Python 3（產圖或驗證時使用）
- Tectonic，或含 `latexmk`、BibTeX 與 ACM packages 的完整 TeX distribution
- ACM `acmart` class

專案內的 `tmp/` 與本機 Tectonic binary 被 `.gitignore` 排除，不應提交到 GitHub。

## 編譯 AISec 投稿版

本工作站已驗證的 PowerShell 指令：

```powershell
cd C:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026

New-Item -ItemType Directory -Force tmp\build-submission | Out-Null

.\tmp\tools\tectonic\tectonic.exe `
  --keep-logs `
  --keep-intermediates `
  --outdir tmp\build-submission `
  main.tex

Copy-Item tmp\build-submission\main.pdf .\main.pdf -Force
```

使用系統安裝的 Tectonic：

```powershell
New-Item -ItemType Directory -Force build-submission | Out-Null
tectonic --keep-logs --keep-intermediates --outdir build-submission main.tex
Copy-Item build-submission\main.pdf .\main.pdf -Force
```

使用完整 TeX distribution：

```powershell
latexmk -pdf -bibtex -outdir=build-submission main.tex
Copy-Item build-submission\main.pdf .\main.pdf -Force
```

## 編譯完整重現版

```powershell
cd C:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026

New-Item -ItemType Directory -Force tmp\build-full | Out-Null

.\tmp\tools\tectonic\tectonic.exe `
  --keep-logs `
  --keep-intermediates `
  --outdir tmp\build-full `
  main_full.tex

Copy-Item tmp\build-full\main_full.pdf .\main_full.pdf -Force
```

`main_full.tex` 只定義 `\fullappendix`，然後載入 `main.tex`。因此投稿版與完整版共用相同 title、abstract、正文、bibliography 與方法來源，不需要維護兩套論文。

## 編譯與引用檢查

檢查目前引用的圖片：

```powershell
rg -n "\\includegraphics" main.tex sections
```

檢查 undefined references、citations 與 overfull：

```powershell
rg -n -i "undefined|multiply defined|Overfull \\hbox|Overfull \\vbox" `
  tmp\build-submission\main.log `
  tmp\build-full\main_full.log
```

檢查 PDF 頁數（需安裝 PyMuPDF）：

```powershell
python -m pip install pymupdf

$script = @'
import fitz
for filename in ["main.pdf", "main_full.pdf"]:
    document = fitz.open(filename)
    print(filename, len(document), "pages")
'@
$script | python -
```

目前驗證基準：

```text
main.pdf       12 pages, 4 figures, no overfull
main_full.pdf  20 pages, 5 figures, bibliography balance warning only
```

## 結果與投稿狀態

實驗結果目前仍維持 `pending`。這是刻意的研究誠信限制：

- 不填入假數據、假曲線、假 confidence intervals 或假樣本數。
- 不將未執行的 result-shell 欄位序列化成零。
- 正式投稿前必須用 frozen locked-test pipeline 的真實輸出取代 `pending`。
- 頁數合規不代表 empirical evaluation 已完成。

正式投稿前仍需完成：

1. 執行 M1--M7、B1--B8 與 paired replay／physical-outage protocol。
2. 產生 RQ1--RQ4 的 locked-test metrics、cluster-bootstrap intervals 與 reliability plots。
3. 統一 Title、Abstract、Sections 1/2/5 與新版 Section 3 method boundary。
4. 依 AISec 2026 CFP 完成匿名檢查、artifact link 決策與 Generative AI 聲明複核。
5. 重新編譯、檢查所有 references/citations，並逐頁渲染 PDF。

## 協作規則

- 一次修改一個 `sections/*.tex`，降低 merge conflicts。
- 修改 `sections/arch.tex` 時，同步更新一對一中文對照 `section3.md`。
- 新增 citation 時同步更新 `bib/references.bib`。
- 修改主文引用的 appendix label 時，必須同步更新 `appendix.tex` 與 `appendix_submission.tex`。
- 正式圖片只從 `trustepisode_figures/svg/` 維護，並輸出到 `trustepisode_figures/pdf/`。
- 不提交 `tmp/`、build directories、LaTeX intermediate files 或本機工具鏈。
- `main.pdf` 是投稿交付物；`main_full.pdf` 是完整重現與內部審查文件，不應誤當投稿 PDF。

## 詳細報告

- `AISEC_PAGE_LIMIT_OPTIMIZATION_REPORT.md`：12 頁投稿版的頁數與合規證據。
- `SECTION3_SECTION4_DETAILED_COMPARISON_REPORT.md`：Section 3/4 紅刪綠增中英比較。
- `TRUSTEPISODE_V2_COMPLETION_REPORT.md`：v2 計畫需求矩陣與驗證結果。
- `trustepisode_figures/README_zh-TW.md`：九張來源圖的語意、位置與限制。
