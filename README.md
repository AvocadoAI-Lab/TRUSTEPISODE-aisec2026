# TrustEpisode - AISec 2026 Paper

TrustEpisode 是一份使用 ACM `sigconf` 雙欄格式撰寫的匿名論文稿，研究重點是：為 AI-assisted EDR/NDR 調查建立 deterministic、immutable、可稽核的 evidence contract，使下游 AI 或分析介面只能消費帶有來源、缺漏狀態與重播證據的案件物件，而不能憑空補寫 canonical evidence。

論文標題：

> **TrustEpisode: Auditable Evidence Contracts for AI-Assisted EDR/NDR Investigation**

## 目前輸出版本

| 檔案 | 頁數 | 圖數 | 用途 |
|---|---:|---:|---|
| `main.pdf` | 11 | 3 | AISec 投稿 PDF；Conclusion 與明確標示的 Appendix 於第 10 頁銜接，References 位於第 10–11 頁，GenAI disclosure 在最後 |

`main_full.pdf` 只屬於可選的內部審查輸出，不是投稿交付物，也不再封裝於 reproducibility companion。

`main.pdf` 將 `TrustEpisode_reproducibility_companion_v1.zip` 定義為必要 supplementary artifact；正式投稿時必須上傳與論文及 `.sha256` sidecar 相同的 ZIP。缺件或 hash 不符均使 machine-readable contract 主張失效。

Companion 以白名單封裝倉庫內固定的 reference runtime、可重跑 synthetic checks、sealed／匿名化結果副本、contracts、generated tables 與 claim-to-evidence matrix；投稿原始碼留在外部正式交付，避免在 ZIP 內嵌「ZIP 自身 SHA-256」造成必然過期的自我參照。`requirements.txt` 會以 editable local package 安裝封包內的 runtime，並列出其餘測試依賴。ZIP 會先驗證 Python 實際載入的 `trustepisode_runtime.__file__` 位於解壓目錄，再執行全部 38 項 implementation tests，並重跑 A1–A12、A–G、AB0–AB3、AI0–AI7、T1–T8 與 temporal fixtures；D1–D5、fair baselines、live／supplemental 與模型結果只從封存 JSON 驗證，不會假裝重跑未附的 raw lab bundles、live collection 或 Ollama。封裝器若找不到本倉庫的 `experiment_runtime/` 會直接失敗，不會從其他 checkout 靜默取用版本。

[ACM AISec 2026 官方 CFP](https://aisec.cc/) 規定：主文最多 10 頁，不含 bibliography 與明確標示的 appendix；bibliography/appendix 最多再使用 2 頁，PDF 全文最多 12 頁。`main.pdf` 目前為 11 頁，主文 Conclusion 與明確標示的 Appendix 在第 10 頁銜接，References 位於第 10–11 頁；`Generative AI Use Disclosure` 已置於 references/appendix 之後，不計入頁數。

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
main.tex                         # 預設編譯 11 頁 AISec 投稿版
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

本 Windows／MiKTeX 工作站已驗證的 PowerShell 指令：

```powershell
cd C:\Users\admin\Desktop\aisec\TRUSTEPISODE-aisec2026

$BuildDir = Join-Path (Get-Location) 'tmp\build-submission'
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

pdflatex -interaction=nonstopmode -halt-on-error -file-line-error `
  -output-directory="$BuildDir" main.tex
bibtex "$BuildDir\main"
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error `
  -output-directory="$BuildDir" main.tex
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error `
  -output-directory="$BuildDir" main.tex

Copy-Item "$BuildDir\main.pdf" .\main.pdf -Force
```

本機的 `latexmk` 需要額外安裝 Perl；目前不要把它當成已驗證路徑。

## 編譯完整重現版

```powershell
cd C:\Users\admin\Desktop\aisec\TRUSTEPISODE-aisec2026

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
main.pdf       11 pages, 3 figures, 16 tables, no overfull hbox/undefined reference
               (all pages visually and geometrically in bounds)
```

目前 PDF SHA-256：

```text
main.pdf       69b5f49da8191d47b708bafafc15ef1b34aab30fcfefe524f36c538342efa6cb
companion zip  cc4d451b50f975fdd7ab07c263a8ce2044ab771126808e485faac4033852a730
```

## 結果與投稿狀態

目前主文只報告已封存且可由 companion 驗證的結果：70 個 M1--M7 malicious runs、40 個 standalone-benign runs、60 個 M1--M6 determinism runs、18 個 audit-conformance fixtures、8 個 downstream canonical-record boundary cards、兩次各 20 張 held-out 本地模型卡，以及一個唯讀的部署案件物化 trace。AI0–AI7 包含一個刻意接受的 resealed allowed-field negative control，用來證明 unkeyed digest 不等於 writer authentication。Qwen2.5-7B 為 exact answer 15/20、exact citation set 15/20、fully exact 9/20；在看到 Qwen 結果後、下載前才鎖定的部署設定預設 Gemma3-1B replication 則為 7/20、0/20、0/20，並產生 18 個 invalid pointer。這是探索性 transfer failure，不是預先註冊的模型比較。案件畫面中的 98% 是下游 case engine 的 operational confidence，不是 TrustEpisode 的 calibrated probability，也不是 AI 效能結果。

正式投稿前仍需完成：

1. 由所有作者確認匿名資訊、利益衝突、作者名單與 GenAI disclosure。
2. 依 AISec 2026 CFP 在 HotCRP 完成 metadata 與 topics；官方鼓勵提供匿名 repository
   連結，ZIP 則只在登入後表單有對應 supplementary 欄位時上傳。
3. 若要主張跨模型或實務 AI/LLM 效能，仍須擴充到更多模型、多次重跑、真實案件 ground truth 與人工評分；目前兩個 once-run 20-card audit 只支撐受限的介面行為觀察。

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

- `AISEC_WEAK_ACCEPT_REVISION_REPORT_20260724_zh-TW.md`：AISec fit、誠信邊界、風險與投稿檢查。
- `AISEC_HOTCRP_SUBMISSION_PACKET_20260724.md`：HotCRP 標題、展開後摘要、topics、GenAI disclosure 與上傳雜湊。
- `CLEANROOM_REPRODUCTION_REPORT_AISEC_20260724.md`：companion 隔離解壓與重現驗證。
- `FRESH_ENV_COMPANION_AUDIT_20260724.md`：全新 Python venv 安裝依賴後的獨立重跑證據。
- `ANONYMOUS_ARTIFACT_PUBLISHING_CHECKLIST_20260724_zh-TW.md`：避免以作者 GitHub
  remote 破壞匿名性的 artifact 發布流程。
- `changereport/AISEC_PAGE_LIMIT_OPTIMIZATION_REPORT.md`：投稿版的頁數與合規證據；最終 PDF 已進一步壓縮為 11 頁。
- `AISEC_CITATION_AUDIT_20260724.md`：25 筆實際引用的 DOI／官方來源稽核與修正紀錄。
- `HTML_REVIEW_REMEDIATION_REPORT.md`：`preview.html` 的逐項修正與驗證矩陣。
- `SECTION3_SECTION4_DETAILED_COMPARISON_REPORT.md`：Section 3/4 紅刪綠增中英比較。
- `TRUSTEPISODE_V2_COMPLETION_REPORT.md`：v2 計畫需求矩陣與驗證結果。
- `TRUSTEPISODE_EXPERIMENT_ENVIRONMENT_PLAN.md`：兩個 Linux EDR containers、一個 NDR gateway 與四專案整合的實驗落地路線圖。
- `trustepisode_figures/README_zh-TW.md`：九張來源圖的語意、位置與限制。
