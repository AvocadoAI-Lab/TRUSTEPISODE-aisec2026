# DELIVERY REPORT — TrustEpisode DFRWS P0 (2026-07-21)

## Verdict target
**Weak Accept** (after P0 compliance fixes)

## P0 completed
| Item | Result |
|---|---|
| DFRWS format | `elsarticle` **5p / 10pt** two-column (Elsevier template) |
| M7 status | **Supplemental boundary-stress only**; removed from primary Table 4 |
| L1–L4 evidence classes | Per-path: live base / offline ablation / controlled inject / wall-clock |
| Wall-clock status | Within **2/2 pass**; beyond **2 sealed, 0/2 LateEvidence**; limitations aligned |
| Boundary fixtures | **299/300/301** + **3599/3600/3601/3900** all pass |
| Clean-room | `CLEANROOM_REPRODUCTION_REPORT_20260721.md` + derived JSON |
| Related-work table | **No / Not reported** (no undocumented inference) |
| EB1–EB4 | 60/60 ties on M1–M6; Δ=0; no observed difference |
| Primary Table-4 | M1–M6 only; sealed cells not overwritten |

## Artifact digests (final)
- Companion ZIP SHA-256: `ef2081c2a04c3bda0efe518f824ad28ffb0793a15ca6aeb6d08053b0ec57829b`
- Format: Elsevier `elsarticle` 5p / 10pt / two-column (DFRWS)
- PDF pages: 10
- `verify_claims.py`: ok
- Clean-room: PASS (`CLEANROOM_REPRODUCTION_REPORT_20260721.md`)
- Boundary fixtures: 7/7 including 3900 s


## Scripts (P0)
- `scripts/run_temporal_boundary_fixtures.py`
- `scripts/run_cleanroom_reproduction.py`
- `scripts/verify_claims.py` (boundary / M7-not-primary / wall-clock checks)
- `scripts/pack_companion.py`
