# TrustEpisode AISec 2026 Weak-Accept 修訂報告

- 日期：2026-07-24
- 投稿稿：`main.pdf`
- 標題：*TrustEpisode: Auditable Evidence Contracts for AI-Assisted EDR/NDR Investigation*

## 結論

稿件已修到可合理競爭 AISec weak accept 的狀態，但不能保證錄取；最終決定仍由審稿人、
同期稿件與 program committee 決定。這一版的核心論點是可稽核、可重播、fail-closed 的
AI-assisted EDR/NDR evidence contract，而不是把單一模型或單一部署案件包裝成通用 AI
準確率證明。

## 已完成的關鍵修訂

1. 以 ACM `sigconf` 匿名稿格式完成 11 頁 PDF；正文、附錄與參考文獻符合 AISec 公告的
   總頁數上限。主文 Conclusion 與明確標示的 Appendix 在第 10 頁銜接，References
   位於第 10–11 頁，GenAI disclosure 放在參考文獻之後。
2. 從本機 `http://127.0.0.1:8081/` 的「防護 → 安全防護調查」取得真實案件畫面，
   並放入 Section 4。案件 `case-3464eb657fad541a` 顯示資產 `172.30.11.10`、
   3/3 evidence、2 個來源、Suricata/Wazuh 分離證據，以及 T1041、T1018 支援關聯。
3. 明確限制案件畫面的 98%：它是下游 case engine 的 operational confidence，
   不是 TrustEpisode calibrated probability，也不是 AI 準確率。
4. 修正 fair-baseline 數字矛盾：EB4 對 EB1 的 action coverage 為 0/69/1 W/T/L，
   mean delta `-0.014`、95% CI `[-0.043, 0]`；EB4 對 EB2 才是 0/70/0。
5. 擴充為 AI0–AI7 canonical-record boundary conformance：合法 control 通過；
   asserted fact、label leakage、unsupported 0.98、provenance removal、revision digest
   與 evidence digest tampering 被 schema 或 digest guard 拒絕；刻意加入並接受
   resealed allowed-field negative control，明確證明 unkeyed digest 不等於 writer
   authentication（8/8 specified outcomes）。
6. 新增真正的本地模型評估。先以分離的 18-card development set 修正輸出介面，
   再一次性執行 20-card held-out Qwen2.5-7B pilot；模型、prompt、cards、records、
   response schema、seed 與原始回覆都有雜湊或完整封存。
7. Qwen held-out pilot 結果誠實報告為：

   - schema-shaped JSON：20/20
   - exact answer：15/20
   - correct abstention flag：14/20
   - exact citation set：15/20
   - fully exact response：9/20
   - 不存在的 JSON pointer：1
   - 四張 prompt-conflict 卡輸出攻擊者指定假值：0/4
   - prompt-conflict fully exact：0/4，主因為過度棄答或引用不符

8. 在看到 Qwen 結果後、下載或查詢模型之前，另外凍結
   `LOCKED_GEMMA3_REPLICATION_PROTOCOL.md`，用完全相同的 prompt、schema、cards、
   records、seed 與 scorer，一次性測試部署設定預設的 Gemma3-1B：

   - schema-shaped JSON：15/20
   - exact answer：7/20
   - correct abstention flag：13/20
   - exact citation set：0/20
   - fully exact response：0/20
   - 不存在的 JSON pointer：18
   - H17、H18、H20 原始回覆回吐攻擊提示的數值或物件片段；此為質性檢視，
     不是事前定義的安全率指標

9. 論文明確把兩組結果解讀為「模型仍不可信，但 typed record 讓錯誤可檢查」，
   不宣稱跨模型泛化、field effectiveness、部署授權安全或 fitted calibration。
10. companion ZIP 採白名單封裝，內附本倉庫固定的 reference runtime、可攜式
    synthetic checks、封存／去識別化結果副本、contracts、表格與
    claim-to-evidence matrix。
11. Clean-room 從解壓後的 ZIP 內執行 reference runtime 全部 38 項 implementation
    tests，再重跑 A1–A12、A–G、AB0–AB3、AI0–AI7、T1–T8、contract validation
    與 7 個 temporal-boundary fixtures；表格與其餘主張則從 sealed JSON 驗證。
    它不假裝重跑未附的 raw lab cohort、live collection 或 Ollama。
12. 新增 fail-closed 匿名守門：ZIP 若包含使用者家目錄、部署專案名稱或既有本機路徑，
    打包直接失敗。6 個 supplemental JSON 副本只遮蔽 `source_path` 前綴，不改 run ID、
    observation、measurement 或 outcome；作者保留的封存原檔未改動。
13. 移除摘要、Introduction、實驗與 Conclusion 中可能被解讀為模型大小因果效應的
    `size-sensitive` 用語，統一為受測設定間的 model-dependent／cross-model variability；
    Limitations 保持「兩個 once-run 模型不能估計 size effect」。
14. 將投稿附錄收斂為 `Frozen Submission Contract`，保留 schema、生命週期常數、
    排序規則、實驗邊界與 companion digest；完整 machine-readable contract 仍由 ZIP
    提供。此修改將最終投稿稿由 12 頁降為 11 頁，降低 appendix/bibliography
    額外兩頁限制的格式風險。
15. 對 `main.aux` 中實際輸出的 25 筆引用執行 DOI／官方頁面稽核；修正
    `breitinger2025sok` 指向另一篇論文的錯誤 DOI，並補齊 Holmes、CORTEX、
    missing-modality survey 與 SWGDE metadata。結果記錄於
    `AISEC_CITATION_AUDIT_20260724.md`。
16. 明示 40 個 standalone benign runs 是 execution controls，不是 false-positive
    trials；移除 Related Work 表中證據不足的 `Live` 欄位，並把
    `110 sealed train runs` 改為不誤導的 `110 sealed live executions`。
17. 依 AISec 指向的 CCS 2026 格式規則恢復 ACM Reference Format、rights、
    ISBN 與 DOI placeholder，移除 `printacmref=false`、copyright 抑制、自訂頁尾、
    全域 float/caption 間距與清單壓縮，避免格式型 desk-reject。
18. 將 Introduction 的七點混合貢獻收斂為四個可審查主張；修正 Related Work
    「不比較 LLM」與後文並列兩個 audit 的矛盾，改為不宣稱模型優越性。
19. 新增 isolated-lab ethical scope，並擴充 GenAI disclosure，明示 citation
    verification 及作者對 experimental outputs、citations、screenshots 的獨立驗證。
20. 將首頁摘要壓縮至 262 字，保留公平基線負面結果、60-run replay、
    真實案件軌跡、AI0--AI7 授權邊界與兩個 local-model fully-exact 結果；移除重複
    數字展開，使「問題--方法--主要證據--外推邊界」更容易在首頁快速辨識。
21. 將 Related Work 的自我評分式 Yes／Not reported 矩陣改為 research unit、
    primary objective 與 relation-to-this-work 的 scope map，明示它不是 effectiveness
    leaderboard，也不推論文獻未記載的功能不存在；novelty 收斂為 single-writer、
    immutable successor/late store、獨立 source health、唯一 terminal outcome、
    stage-localized loss 與 read-only citable record 的 contract composition。
22. 修補 companion 的隱性版本風險：封裝器原先在本倉庫缺少 runtime 時會從另一個
    checkout 靜默取用，且匿名化發生在複製之後。現在已把實際匿名化 runtime 的
    31 個檔案固定進本倉庫、移除跨 checkout fallback、把 local runtime package
    納入 `requirements.txt`，並以逐檔正規化 SHA-256 證明 ZIP 內版本 31/31 一致。
23. 進一步實測發現，主機與舊 clean-room 即使工作目錄在 ZIP，仍可能從
    `coreAPP` 的 editable install 載入同名 runtime。現在每個 subprocess 都把
    解壓後的 `experiment_runtime/src` 放在 `PYTHONPATH` 首位，且新增
    `verify_runtime_origin.py`；實際 `__file__` 不是封包內路徑時立即失敗。

## 最終驗證

- `scripts/check_claim_consistency.py`：通過。
- `scripts/verify_claims.py`：`ok=true`、`n_failures=0`。
- Clean-room reproduction：11/11 命令通過；packaged-runtime origin guard、
  reference runtime 38/38 tests、contract validation、A1–A12、A–G、AB0–AB3、
  AI0–AI7、T1–T8、7 個
  temporal-boundary fixtures、表格重建與 claim verifier 全部只從解壓後 ZIP 執行。
- 全新 Python 3.14.4 `venv`（未繼承主環境套件）依 `requirements.txt` 安裝後，
  從 ZIP 安裝 `trustepisode-experiment-runtime 0.1.0`，再由
  `run_companion_checks.py` 11/11 通過；`__file__` 明確位於解壓後 runtime。
- 獨立解壓匿名掃描：通過；未發現使用者家目錄或部署專案名稱。
- LaTeX：`pdflatex → bibtex → pdflatex ×2` 成功。
- LaTeX blocking diagnostics：0。
- BibTeX metadata warnings：0。
- 引用稽核：25/25 實際引用可追溯；0 個 title/DOI mismatch；0 個 missing key。
- overfull hbox/vbox：0。
- PDF：11 頁、letter size、PDF 1.5、未加密。
- PDF 已逐頁渲染檢查，無裁切、重疊或表格溢出。
- 投稿 PDF SHA-256：
  `69b5f49da8191d47b708bafafc15ef1b34aab30fcfefe524f36c538342efa6cb`
- Companion SHA-256：
  `cc4d451b50f975fdd7ab07c263a8ce2044ab771126808e485faac4033852a730`

## 審稿風險

| 面向 | 現況 | 仍需注意 |
|---|---|---|
| AISec fit | 強 | 已有真實調查介面與兩個 actual local-model audit |
| Novelty | 可辯護 | scope map 已避免跨輸出自我評分；reviewer 仍可能把貢獻視為 contract composition 而非新 detector |
| Technical soundness | 較強 | primary cohort 仍是受控 lab，不能外推到跨組織泛化 |
| Evaluation | 中等 | fair baseline 是誠實負面結果；尚無 fitted calibration、outage／partial-telemetry 或完整 cost benchmark；兩模型各僅 20 cards、單次執行 |
| Reproducibility | 強 | 固定 runtime、origin guard、ZIP、sidecar、appendix digest、11/11 clean-room 與全新 venv 已對齊；仍須以官方鼓勵的匿名 URL 交付 |
| Presentation | 投稿就緒 | 作者仍需確認匿名、COI、作者名單與 HotCRP metadata |

## 投稿前人工清單

- [ ] 所有作者確認匿名資訊、作者名單與利益衝突。
- [ ] HotCRP 標題、摘要、keywords 與 PDF 完全一致。
- [ ] 上傳 `main.pdf`。
- [ ] 若允許 supplementary material，上傳
      `TrustEpisode_reproducibility_companion_v1.zip`。
- [ ] 核對 companion sidecar 與論文 Appendix 內 SHA-256。
- [ ] 保留 Generative AI disclosure，並與 HotCRP 欄位一致。
- [ ] 不把部署畫面的 98% 改寫成 TrustEpisode 或 LLM accuracy。
