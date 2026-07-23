# TrustEpisode AISec 2026 最終投稿預檢

- 預檢日期：2026-07-24（Asia/Taipei）
- 投稿稿：`main.pdf`
- 正式上傳目錄：`output/hotcrp-final-20260724/to-upload`
- 官方 CFP：<https://aisec.cc/>
- 投稿系統：<https://aisec26.hotcrp.com/>

## 結論

目前兩個準備檔案已通過論文欄位一致性、頁面與格式、逐位元雜湊、
claim-to-evidence、machine-readable contract、cleanroom reproduction 及匿名性預檢。
稿件已達可提交狀態；學術審查結果仍取決於評審判斷，不能由預檢保證接受。

## 官方格式與 front matter

- 英文、匿名、ACM `sigconf` 雙欄格式。
- PDF 為 Letter（612 × 792 pt）、未加密，共 11 頁。
- 保留 ACM Reference Format、rights、ISBN 與 DOI placeholder；沒有自訂頁首頁尾、
  全域 float/caption 間距或清單壓縮。
- 主文不超過 10 頁；Conclusion 與明確標示的 Appendix 在第 10 頁銜接，
  References 位於第 10–11 頁。
- `Generative AI Use Disclosure` 位於 appendix/references 之後。
- 官方頁首標示 2026-11-15，但 Important Dates 仍標示 `Workshop day: TBD`；
  因官方資訊互相矛盾，front matter 保留不過度斷言的 `November 2026`，
  地點為 `The Hague, Netherlands`。

## HotCRP 欄位一致性

以 `main.tex`、`results/tables/result_macros.tex` 與
`AISEC_HOTCRP_SUBMISSION_PACKET_20260724.md` 自動比對：

- Title：完全一致。
- Abstract：展開結果巨集後為 262 字，與 PDF 語意及數值完全一致。
- Keywords：完全一致。
- Generative AI disclosure：完全一致。
- 作者用 packet 與 `output/hotcrp-final-20260724/author-notes` 內副本完全一致。

編譯實際包含 17 個 TeX 輸入檔、3 張圖與 16 張表；README 中先前誤記的
17 張表已修正為 16 張。

## 交付檔案與雜湊

### Paper

- `TrustEpisode_AISec2026_submission_20260724.pdf`
- 大小：775657 bytes
- SHA-256：
  `69b5f49da8191d47b708bafafc15ef1b34aab30fcfefe524f36c538342efa6cb`

根目錄、`output/pdf` 與 `to-upload` 的三份 PDF 逐位元相同。

### Supplementary material

- `TrustEpisode_reproducibility_companion_v1.zip`
- 大小：475151 bytes
- SHA-256：
  `cc4d451b50f975fdd7ab07c263a8ce2044ab771126808e485faac4033852a730`

根目錄與 `to-upload` 的兩份 ZIP 逐位元相同。`to-upload` 內只有上述兩個檔案。

## HotCRP 實際介面邊界

2026-07-24 已唯讀檢查公開 HotCRP 頁面；公開狀態只顯示登入表單、投稿管理入口與
截止時間，實際投稿欄位必須登入後才可見。因此：

- Paper PDF 必須上傳至正式 paper 欄位。
- 只有登入後表單出現 supplementary material／file 類型欄位時，才上傳 ZIP。
- 若沒有對應欄位，不要把 ZIP 放入 paper 或其他不相干欄位；保留 ZIP，並依主辦方
  核准的匿名 artifact 管道處理。
- 本文件列出的 topics、paper type 與 disclosure 是準備內容，不宣稱已驗證為
  HotCRP 的逐字欄位名稱。
- 官方 CFP 鼓勵提供匿名 repository 連結。不得直接連結目前帶有作者／組織名稱的
  Git remote；必須依 `ANONYMOUS_ARTIFACT_PUBLISHING_CHECKLIST_20260724_zh-TW.md`
  先以未登入瀏覽器驗證匿名 URL 與下載後 ZIP 雜湊。

## 自動驗證

- `scripts/check_claim_consistency.py`：PASS
- `scripts/verify_claims.py`：PASS，0 failures
- `artifacts/contracts/validate_contracts.py`：PASS
- `scripts/run_cleanroom_reproduction.py`：PASS，11/11 checks；runtime-origin guard
  顯示 `experiment_runtime/src/trustepisode_runtime/__init__.py`，封包內 reference
  runtime 38/38 tests
- 全新 Python 3.14.4 venv：從 ZIP 安裝 local runtime 後 11/11 checks，且
  `__file__` 位於解壓後 runtime
- AI0–AI7：8/8 specified outcomes；AI7 的 schema-valid reseal 如預期被接受，
  明確保留「外部 writer authorization 尚未評估」的安全邊界。
- 合成驗證與 held-out record 重新封裝路徑已統一使用 RFC 8785/JCS，不再以一般
  `sort_keys` JSON 近似 canonicalization。
- 內文截圖、數值、引用與 companion 邊界已由既有 citation audit、
  weak-accept revision report、fresh-environment audit 與 anonymity scan 交叉驗證。

## 投稿前仍須作者本人完成

- 在 HotCRP 填入完整作者姓名、單位、國家與 Email。
- 完整勾選利益衝突。
- 確認沒有一稿多投或與既有 archival publication 實質重疊。
- 指定接受後的出席／報告作者。
- 確認機構要求的 funding 或 disclosure 欄位。
- 若表單有 artifact／repository URL 欄位，填入已完成匿名與下載雜湊驗證的 URL。
- 一定上傳 `to-upload` 內的 PDF；ZIP 僅在 HotCRP 有對應 supplementary 欄位時上傳。
- 不要上傳 `author-notes` 或 `.sha256` sidecar。
