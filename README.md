# TrustEpisode - AISec 2026 Paper

TrustEpisode 是一份使用 ACM `sigconf` 雙欄格式撰寫的匿名論文稿，研究重點是：將 EDR/NDR 異質遙測轉換成 deterministic、immutable episode revisions，並對每個 revision 產生 manifest-supported calibrated maliciousness probability、獨立的 evidence-sufficiency profile，以及 append-only terminal assembly outcome。

論文標題：

> **TrustEpisode: Deterministic Episode Formation and Manifest-Scoped Calibration for Partial EDR/NDR Telemetry**

## 目前輸出版本

| 檔案 | 頁數 | 圖數 | 用途 |
|---|---:|---:|---|
| `main.pdf` | 12 | 4 | AISec 唯一投稿 PDF；Conclusion 於第 9 頁，References 位於第 11--12 頁 |

`main_full.pdf` 只屬於可選的內部審查輸出，不是投稿交付物，也不再封裝於 reproducibility companion。

`main.pdf` 將 `TrustEpisode_reproducibility_companion_v1.zip` 定義為必要 supplementary artifact；正式投稿時必須上傳與論文及 `.sha256` sidecar 相同的 ZIP。缺件或 hash 不符均使 machine-readable contract 主張失效。

[ACM AISec 2026 官方 CFP](https://aisec.cc/) 規定：主文最多 10 頁，不含 bibliography 與明確標示的 appendix；bibliography/appendix 最多再使用 2 頁，PDF 全文最多 12 頁。`main.pdf` 目前為 12 頁，正文 Conclusion 位於第 9 頁；`Use of Generative AI` 尾段已依本次稿件決策移除，正式投稿前仍應由作者依當時 submission policy 自行確認 disclosure 欄位或文字要求。

## 方法範圍

正式的 v2 方法契約固定為：

```text
EDR + NDR telemetry
  -> Evidence Fabric
  -> deterministic Episode Synthesis
  -> health-independent [D, C, m, detector observation]
  -> compact stateless scorer
  -> Scope Resolver [resolved availability, kappa, group key, eligibility]
  -> manifest-scoped affine calibrator
  -> nullable calibrated probability P

SourceCoverage + EpisodeRevision + provenance + calibration status
  -> deterministic Sufficiency Evaluator
  -> structured five-axis U

P + U + independently owned inputs
  -> exactly one terminal AssemblyOutcome per revision
  -> AuditRecord or AssemblyFailureRecord

Beyond-horizon evidence
  -> LateEvidenceRecord in late store only

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
- 每個 EpisodeRevision 只能產生一個 immutable、append-only terminal AssemblyOutcome：完整 AuditRecord 或明確 AssemblyFailureRecord。
- Feature Extractor 不讀取 health；resolved detector availability 與 `decision_eligible` 只由 Scope Resolver 產生。
- `eligible_detector_count=0` 必定產生 out-of-support、`decision_eligible=false` 與 JSON-null `P`；`no_detection` 不得繞過此規則。
- Raw scorer 使用 $b\in\mathbb R$、$w_D,w_C\ge0$；intercept 不受非負限制。
- Beyond-horizon evidence 只產生 LateEvidenceRecord，不能回寫既有 revision、`U` 或 AuditRecord。

## 專案結構

```text
main.tex                         # 預設編譯 12 頁 AISec 投稿版
main_full.tex                    # 啟用完整 Appendix A--F
main.pdf                         # 已驗證投稿版
main_full.pdf                    # 已驗證完整重現版
section3.md                      # Section 3 繁體中文 Markdown 對照版
section4.md                      # Section 4 繁體中文 Markdown 對照版

artifacts/contracts/             # Frozen JSON schema、threshold、split、scenario、RT contracts
TrustEpisode_reproducibility_companion_v1.zip
TrustEpisode_reproducibility_companion_v1.sha256

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
TRUSTEPISODE_EXPERIMENT_ENVIRONMENT_PLAN.md
```

## 圖片使用方式

投稿版實際引用以下四張向量 PDF：

```text
trustepisode_figures/pdf/fig01_final_architecture.pdf
trustepisode_figures/pdf/fig02_episode_revision_lifecycle.pdf
trustepisode_figures/pdf/fig05_ground_truth_firewall.pdf
trustepisode_figures/pdf/fig07_partial_telemetry_perturbations.pdf
```

完整版另外引用以下五張 companion figures：

```text
trustepisode_figures/pdf/fig03_calibration_and_sufficiency.pdf
trustepisode_figures/pdf/fig04_lab_topology.pdf
trustepisode_figures/pdf/fig06_split_and_freeze_workflow.pdf
trustepisode_figures/pdf/fig08_episode_linking_decision.pdf
trustepisode_figures/pdf/fig09_calibration_validity_state_machine.pdf
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
main.pdf       12 pages, 4 figures, 7 tables, no overfull hbox/undefined reference
               (1.17 pt final-page output vbox; visually and geometrically in bounds)
```

目前 PDF SHA-256：

```text
main.pdf       aca9399f0a2721ef6d69111eacbf27d590f3b1bc1d9eebf5ee6542a6eeac5f3b
companion zip  45c191952c48411e0de534c2d99762c451e44f56f031277ceb8354715e1949ef
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
3. 依 AISec 2026 CFP 完成最終匿名檢查與 artifact link 決策。
4. 以真實 locked outputs 重新編譯並逐頁複核最終 PDF。

## 協作規則

- 一次修改一個 `sections/*.tex`，降低 merge conflicts。
- 修改 `sections/arch.tex` 時，同步更新一對一中文對照 `section3.md`。
- 修改 `sections/exps.tex` 時，同步更新一對一中文對照 `section4.md`。
- 新增 citation 時同步更新 `bib/references.bib`。
- 修改主文引用的 appendix label 時，必須同步更新 `appendix.tex` 與 `appendix_submission.tex`。
- 正式圖片只從 `trustepisode_figures/svg/` 維護，並輸出到 `trustepisode_figures/pdf/`。
- 不提交 `tmp/`、build directories、LaTeX intermediate files 或本機工具鏈。
- `main.pdf` 是投稿交付物；`main_full.pdf` 是完整重現與內部審查文件，不應誤當投稿 PDF。

## 詳細報告

- `AISEC_PAGE_LIMIT_OPTIMIZATION_REPORT.md`：12 頁投稿版的頁數與合規證據。
- `HTML_REVIEW_REMEDIATION_REPORT.md`：`preview.html` 的逐項修正與驗證矩陣。
- `SECTION3_SECTION4_DETAILED_COMPARISON_REPORT.md`：Section 3/4 紅刪綠增中英比較。
- `TRUSTEPISODE_V2_COMPLETION_REPORT.md`：v2 計畫需求矩陣與驗證結果。
- `TRUSTEPISODE_EXPERIMENT_ENVIRONMENT_PLAN.md`：兩個 Linux EDR containers、一個 NDR gateway 與四專案整合的實驗落地路線圖。
- `trustepisode_figures/README_zh-TW.md`：九張來源圖的語意、位置與限制。
