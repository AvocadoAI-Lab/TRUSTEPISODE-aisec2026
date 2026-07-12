# TrustEpisode 論文圖包

本圖包只涵蓋已確認的修改範圍：Section 3 Method、Section 4 Evaluation/Lab 與相關附錄。圖中未加入 CTI、Agent/RAG、impact/priority 或 autonomous response，也未虛構任何實驗結果。

## 檔案格式

- `pdf/`：向量 PDF，建議直接由 LaTeX `\includegraphics` 插入。
- `svg/`：可編輯向量原稿，可用 Inkscape、Illustrator 或 Figma 修改。
- `png/`：由正式向量 PDF rasterize 的高解析 PNG，適合 Word、簡報或預覽。
- `preview/contact_sheet.png`：九張圖的總覽。
- `figures.tex`：可直接複製的 LaTeX figure、caption 與 label。

## 建議放置順序

| 圖檔 | 建議位置 | LaTeX label | 用途 |
|---|---|---|---|
| `fig01_final_architecture` | Section 3.1，架構與 assumptions 後 | `fig:method-architecture` | 最終 online/offline 架構、ownership、P/U 分離與 audit boundary |
| `fig02_episode_revision_lifecycle` | Section 3.3，episode/revision policy 後 | `fig:episode-revision-lifecycle` | event time、ingest time、watermark、revision horizon 與 append-only revision |
| `fig03_calibration_and_sufficiency` | Section 3.5-3.6，calibration 與 U 定義後 | `fig:probability-sufficiency-boundary` | calibrator 只產生 P；U 為獨立五軸 profile，且不修改 P |
| `fig04_lab_topology` | Appendix E，Lab manifest 後 | `fig:lab-topology-companion` | Caldera control plane、isolated targets、EDR/NDR、Identity online exclusion 與 offline evaluation |
| `fig05_ground_truth_firewall` | Section 4.3，forbidden fields/schema policy 後 | `fig:ground-truth-firewall` | Ground Truth Firewall、online schema check 與 inference 後 label join |
| `fig06_split_and_freeze_workflow` | Section 4.5-4.6；頁數不足可移 Appendix G | `fig:run-split-freeze` | campaign/run-level split、artifact freeze、calibration split 與 locked test |
| `fig07_partial_telemetry_perturbations` | Section 4.8；頁數不足可移 Appendix H | `fig:telemetry-perturbation-design` | paired replay perturbations 與 separate physical collector outage |
| `fig08_episode_linking_decision` | Appendix B；主文 Section 3.3 引用 | `fig:episode-linking-decision` | frozen label-blind attach/merge/start decision procedure |
| `fig09_calibration_validity_state_machine` | Appendix D 或 J；Section 3.5 引用 | `fig:calibration-validity` | manifest match、group gate、out-of-support、U status 與 invalidation |

所有圖皆為橫向設計。ACM 雙欄版面建議使用 `figure*` 與 `width=\textwidth`，不要硬縮成單欄，否則內文會過小。

## 已鎖定的方法語意

- Primary telemetry scope 為 `S* = {EDR, NDR}`、`K = 2`；Identity 不存在 online path，只能作為 inference 後的 M5-ID offline annotation。
- Episode Synthesis 是 episode membership 與 revision 的唯一 owner；scorer 不得決定 attach/merge。
- Late evidence 若在固定 revision horizon 內，產生新的 immutable EpisodeRevision 與 terminal AssemblyOutcome；不得覆寫舊 revision，也不得延長 deadline。
- Beyond-horizon evidence 只產生 LateEvidenceRecord 並進入 late store，不得建立 revision 或回寫既有 AuditRecord。
- Raw scorer 為 stateless，source health 不進入 raw scorer，也不能由「沒有事件」推論 collector health。
- Affine calibrator 是 calibrated probability P 的唯一 producer。
- U 是 coverage、provenance、lateness、contradiction、calibration support 五軸結構；不是 scalar confidence，也不乘、減、gate 或重標 P。
- Ground-truth fields 僅在 inference 完成後由 offline evaluation harness join；不得進入 online schema。
- Campaign/run 是 split 與 bootstrap cluster 的基本單位；同一 run 的 episodes、revisions 與 replay variants 不得跨 split。
- Replay perturbation 與 physical collector outage 為不同實驗，不得合併成同一 intervention。

## 尚未生成的結果圖

下列圖必須等真實 locked-test 結果後再畫，本圖包刻意不放假曲線、假樣本數或假 confidence interval：

1. Raw sigmoid vs calibrated reliability diagram。
2. Reliability by supported telemetry regime。
3. Decision coverage under source loss。
4. Episode-builder fragmentation/contamination comparison。
5. Experimental revision behavior under delay/out-of-order evidence。

待實驗資料完成後，應以 campaign-level cluster bootstrap、預先註冊的 bins/metrics 與 frozen analysis procedure 生成以上結果圖。

## 匯出驗證

九張 PDF 均已重新渲染成 PNG 並完成文字層／總覽檢查；未發現截字、重疊、破圖或缺字。線條語意統一為：實線表示 online/within-procedure data flow，橘色虛線表示 offline-only flow，紫色表示 calibration scope/status，紅色表示 forbidden/out-of-support/invalidation path。
