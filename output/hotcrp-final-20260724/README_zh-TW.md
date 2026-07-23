# AISec 2026 HotCRP 最終上傳目錄

投稿網站：<https://aisec26.hotcrp.com/>

## `to-upload` 內準備好的兩個檔案

1. 必傳 Paper：
   `to-upload/TrustEpisode_AISec2026_submission_20260724.pdf`
2. 條件式 Supplementary material：
   `to-upload/TrustEpisode_reproducibility_companion_v1.zip`

公開 HotCRP 頁面不會在未登入狀態顯示實際投稿欄位。只有登入後表單出現
supplementary material／file 類型欄位時，才上傳 ZIP；若沒有對應欄位，保留 ZIP
並依主辦方核准的匿名 artifact 管道處理，不要放入 paper 或其他不相干欄位。
AISec CFP 另鼓勵提供匿名 repository URL；請依
`author-notes/ANONYMOUS_ARTIFACT_PUBLISHING_CHECKLIST_20260724_zh-TW.md` 驗證，
不得直接連結帶作者或組織名稱的現有 Git remote。

不要把 `author-notes` 內的投稿欄位、稽核報告或 `.sha256` sidecar 當成
supplementary material 上傳。

## 最終雜湊

- PDF：
  `69b5f49da8191d47b708bafafc15ef1b34aab30fcfefe524f36c538342efa6cb`
- ZIP：
  `cc4d451b50f975fdd7ab07c263a8ce2044ab771126808e485faac4033852a730`

## 投稿前人工欄位

從 `author-notes/AISEC_HOTCRP_SUBMISSION_PACKET_20260724.md` 複製 title、abstract、
keywords、topics 與 Generative AI disclosure。作者姓名、單位、Email、利益衝突與
presenter 必須由作者本人確認。

## 禁止混用

`output/pdf/TrustEpisode_AISec2026_submission_20260723.pdf` 是舊版本，不得上傳。
本目錄 `to-upload` 的 20260724 PDF 才是完成引用稽核、benign-control 邊界修正及
ACM reference/rights/default-layout 合規修正與最終視覺檢查的版本。
