# AISec 2026 匿名 Artifact 發布檢查表

官方 CFP 鼓勵投稿時提供匿名 repository 連結。這是鼓勵項目，不代表公開 HotCRP
一定提供 ZIP 上傳欄位。為避免匿名性破壞，請依以下方式處理。

## 可發布檔案

- `TrustEpisode_reproducibility_companion_v1.zip`
- 檔名不可改成含作者、實驗室、公司或學校名稱的版本。
- ZIP 的 SHA-256 必須與投稿 PDF Appendix 的 **Artifact Digest** 完全一致。

## 禁止直接連結

- 不要連結目前的作者／組織 GitHub remote。
- 不要連結含作者帳號、commit history、issue、release author、Email 或機構名稱的頁面。
- 不要把 `output/hotcrp-final-20260724/author-notes`、本檢查表或 `.sha256` sidecar
  當成匿名研究 artifact。

## 建議流程

1. 使用 AISec CFP 建議的 `anonymous.4open.science`，或主辦方核准的其他匿名機制。
2. 匿名頁面至少提供最終 ZIP；不要從未匿名化的原始 repository 建立可追溯連結。
3. 在無痕／未登入瀏覽器中開啟匿名 URL，確認不會跳轉或顯示作者身分。
4. 下載 ZIP，重新計算 SHA-256，確認與投稿 PDF Appendix 一致。
5. 只將通過上述檢查的 URL 填入 HotCRP artifact／repository URL 欄位；若沒有對應
   欄位，依主辦方指示處理，不要塞入不相干欄位。

## 本地驗證命令（PowerShell）

```powershell
Get-FileHash -Algorithm SHA256 `
  .\TrustEpisode_reproducibility_companion_v1.zip
```

解壓後：

```powershell
python -m pip install -r requirements.txt
python scripts/run_companion_checks.py
```

預期結果為九項檢查全部通過。
