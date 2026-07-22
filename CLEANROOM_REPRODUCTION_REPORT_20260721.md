# Clean-room reproduction report (DFRWS P0)

- Generated (UTC): `2026-07-21T14:12:41.240513+00:00`
- Companion ZIP: `TrustEpisode_reproducibility_companion_v1.zip`
- Companion SHA-256: `ef2081c2a04c3bda0efe518f824ad28ffb0793a15ca6aeb6d08053b0ec57829b`
- Clean-room root: `C:\Users\admin\Desktop\aisec\TRUSTEPISODE-aisec2026\tmp\cleanroom-dfrws-p0`
- Overall: **PASS**

## Checks

### `scripts/generate_tables.py` — PASS (exit 0)

```
{"n_runs": 60, "d1_pass": 60, "d1_exec": 600, "audit_pass": 18, "audit_fail_codes": 7, "tax_pass": 8, "tax_total": 8}
```

### `scripts/verify_claims.py` — PASS (exit 0)

```
{
  "ok": true,
  "failures": [],
  "n_failures": 0
}
```

### `C:\Users\admin\Desktop\aisec\TRUSTEPISODE-aisec2026\scripts\run_temporal_boundary_fixtures.py` — PASS (exit 0)

```
{"all_pass": true, "n_cases": 7, "output": "C:\\Users\\admin\\Desktop\\aisec\\TRUSTEPISODE-aisec2026\\results\\derived\\temporal_boundary_conformance.json", "sha256": "27aee2b801fec0e3ffc20d6901f3f51152d1910542409c327f4a64eaee51ae30", "pytest_tail": ".......                                                                  [100%]"}
```

## Interpretation

This clean-room extract verifies that the packed companion regenerates LaTeX macros,
passes `verify_claims.py`, and that temporal boundary fixtures
(299/300/301 and 3599/3600/3601/3900) pass against the production synthesizer.
It does not re-execute live CALDERA collection.

Machine-readable: `results/derived/cleanroom_reproduction.json` (sha256 `7c8e1f2189a4251c1098149d66033e51ff21ba71f0c54cec60405cf77cbaa96d`).
