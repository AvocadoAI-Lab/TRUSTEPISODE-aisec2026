# Supplemental Live L1+L4 — frozen protocol (fast path)

Date: 2026-07-21  
Partition: `supplemental_mechanism`  
Primary M1–M6 / B1–B8: **untouched**

## Auth unblock status

- Caldera API key: `ADMIN123` (compose default) — `/api/v2/health` OK
- Agents restored via direct sandcat start (bootstrap re-download was hanging)
- Observed trusted agents on `edr-target-01` and `edr-target-02`

## Fast-path design (honest scope)

| ID | Live execution | Offline mechanism check | Not claimed |
|---|---|---|---|
| L1 | 3× `M3` ability sequence (`linux.discovery`→`linux.ssh_action`), `attack_only` | Full policy vs `no_session` ablation on same sealed stream | Field superiority over sliding-time |
| L4 | 3× short `M5` local sequence, `attack_only` | Controlled late ingest at +60s (within 900s) and +901s (beyond) on sealed stream | Wall-clock forwarder wait of 900s×N |

Rationale for offline late inject: D3 already proved horizon math on 60 sealed streams; L4 adds **new live-collected** bases under supplemental partition, then applies the same controlled ingest delays. Paper must say: live base + controlled late delivery (not raw wall-clock forwarder delay).

## Success criteria

### L1
- Receipt valid; sealed inputs present
- Full policy: ≥1 matched episode retaining remote_session / SSH-linked events across hosts
- `no_session` ablation: more fragments OR fewer cross-host merges than full (documented digests)

### L4
- Prior revision digest unchanged after late inject
- +60s: successor revision OR accepted late membership change per contract
- +901s: `LateEvidenceRecord` (or equivalent late store object), prior digest unchanged

## Run count

- Target: **3 valid** L1 + **3 valid** L4
- Failures are recorded; not zero-filled; primary estimates unchanged

## Run ID scheme

`run-supp-l1-{n}` / `run-supp-l4-{n}` with n=01..03
