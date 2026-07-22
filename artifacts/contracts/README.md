# TrustEpisode 凍結契約

本目錄是論文方法與實驗的 machine-readable contract。它定義 schema、演算法常數、實驗卡、資料切分、擾動、結果欄位與失敗規則，但不代表正式實驗已完成。未執行的結果必須保持 `pending`，不能填零或虛構數值。

## 檔案

| 檔案 | 用途 |
|---|---|
| `trustepisode_online.v1.schema.json` | 八種 online objects、欄位型別、enum、nullability、digest 與 fail-closed 規則 |
| `detector_registry.v1.json` | 六個 detector、合法值、方向、empirical CDF、top-k、D/C 與去重規則 |
| `baseline_registry.v1.json` | EB1/EB2/SB1/SB2 的唯一實作、排序、缺值、solver 與 artifact digest 契約 |
| `thresholds.v1.json` | Formation、detector availability、contradiction、assembly、matching、calibration gate、ranking budget 與 bootstrap 常數 |
| `scenario_cards.v1.json` | Linux-only M1--M7 與 B1--B8 的 image、ability、command、timing、receipt、failure、cleanup 與 mode 契約 |
| `lab_manifest.v1.json` | 兩個 EDR target、一個 inline NDR、Caldera control plane、label firewall、sensor conformance 與正式收集 gate |
| `split_policy.v1.json` | 每個 10-run stratum 的 deterministic 50/20/10/20 split，以及獨立 locked-test PO1 population |
| `perturbations.v1.json` | RP0--RP7 deterministic replay 與 40-trace PO1 physical-outage protocol |
| `result_registry.v1.json` | RT1--RT7 的 rows、columns、population、denominators、`pending` 與 `N/A` 規則 |
| `run_registry.template.csv` | 正式 run、receipt、firewall、raw bundle 與 PO1 欄位；只有 header，沒有虛構 runs |
| `examples/*.json` | Supported/OOS AuditRecord、AssemblyFailureRecord、LateEvidenceRecord 與 leakage rejection examples |
| `validate_contracts.py` | Schema、canonical digest、Linux cards、40-cell PO1、split、registry 與 manifest 驗證器 |
| `manifest.v1.json` | Companion 交付檔案的 byte count 與 SHA-256 清單 |

## 正式實驗邊界

1. Compose 必須只解析出 `caldera`、`target-linux`、`target-linux-02`、`ndr-gateway` 四個服務。
2. 兩個 Ubuntu 22.04 target 各自保存 generic process start/exit 事件與可獨立停止的 EDR forwarder；一個 Suricata gateway 保存 raw EVE、NormalizedEvent 與 NDR health。
3. 正式 primary-evidence window 設定 `ENABLE_SANDCAT=false`。Host orchestrator 以 monotonic offsets 執行凍結的 `bash_no_profile` 卡片；Caldera 只保留版本與隔離 control-plane topology。
4. `run_id`、card/ability/operation/receipt IDs、split、label、attack window 及其值不得進入 online objects。Action receipts 只存在於 Ground Truth Store，且只能在 terminal AssemblyOutcome 寫入後 join。
5. Wazuh、`guacamole-ai`、`Aristaconnector-Control-Plane` 只能在 primary bundle seal 後讀取副本，不能改變 RT1--RT7 的輸入、denominator 或結果。
6. Base campaign 是 `7 x 2 x 10 + 8 x 1 x 10 = 220` runs；每個 stratum 固定 5 train、2 development、1 calibration、2 locked test。
7. RT4 僅使用 28 個 malicious locked-test roots。每個 root 產生 41 個 RP0--RP7 children，共 1,148 個 replay bundles；children 繼承 partition 與 bootstrap cluster。
8. PO1 與 base campaign 獨立，為 `2 sources x 2 durations x 10 = 40` 條 locked-test traces；M1/M3/M4/M7 各 10 條。TrustEpisode 與 OB1 必須重用同一 raw trace 與 SourceCoverage journal。
9. Class-dependent metrics 只使用 positive/negative `C_dec_binary`；failure/OOS rates 使用 `C_dec_all`。
10. JSON numbers 必須有限，禁止 NaN、Infinity 與 negative zero。RFC 8785 不會重排 arrays，因此 reference arrays 必須先依 schema 宣告的 application order 排序。

## 驗證

從論文根目錄執行：

```powershell
python artifacts\contracts\validate_contracts.py
```

驗證器會確認：

- Valid examples 通過 Draft 2020-12 schema，label-leakage example 必須被拒絕。
- Canonical digest 與 schema 宣告欄位一致。
- Cards 僅使用 Linux images 與 Bash executor，target command 不含 orchestrator-only values。
- Compose/service、Sandcat boundary、sensor conformance 與 optional mirror boundary 已凍結。
- PO1 精確展開 40 cells，M1/M3/M4/M7 各 10 cells。
- `manifest.v1.json` 的 byte count 與 SHA-256 全部吻合。
- 未執行結果保持 `pending`，不能以零或虛構數值取代。
