# Supplemental live + wall-clock L4 status

## Mechanism matrix

| ID | Result |
|---|---|
| L1 session | 3/3 |
| L2 endpoint | 3/3 |
| L3 hub | organic 0/3; controlled 3/3 |
| L4 controlled late inject | 3/3 |
| L4 wall-clock **within** (180s hold/release) | **2/2** sealed + pass |
| L4 wall-clock **beyond** (930s hold; 1080s quiet wait) | **2 sealed; 0/2 LateEvidenceRecord** (new membership instead) |

## Honesty

- Within-horizon wall-clock forwarder delay: **validated**
- Beyond-horizon wall-clock LateEvidenceRecord: **attempted, not observed** in this lab
- Beyond-horizon code path: still supported by controlled inject on live seals

Artifacts: `supplemental_live_l4_wallclock.json`, `supplemental_live_l4_wallclock_analysis.json`
