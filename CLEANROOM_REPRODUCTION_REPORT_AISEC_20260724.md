# Clean-room reproduction report (AISec revision)

- Generated (UTC): `2026-07-23T18:49:06.165111+00:00`
- Companion ZIP: `TrustEpisode_reproducibility_companion_v1.zip`
- Companion SHA-256: `cc4d451b50f975fdd7ab07c263a8ce2044ab771126808e485faac4033852a730`
- Clean-room root: isolated extraction (local path omitted)
- Overall: **PASS**

## Checks

### `validate_contracts.py` — PASS (exit 0)

```
TrustEpisode contract validation: PASS
```

### `verify_runtime_origin.py` — PASS (exit 0)

```
{"ok": true, "runtime_origin": "experiment_runtime/src/trustepisode_runtime/__init__.py"}
```

### `experiment_runtime/tests` — PASS (exit 0)

```
......................................                                   [100%]
```

### `run_audit_conformance_a12.py` — PASS (exit 0)

```
{"pass": 18, "fail": 0}
```

### `run_taxonomy_ag.py` — PASS (exit 0)

```
{"pass": 8, "fail": 0}
```

### `run_audit_baselines_ab.py` — PASS (exit 0)

```
{"builders": ["AB0_MUTABLE_RECORD", "AB1_NONCANONICAL_APPEND", "AB2_SILENT_FAILURE", "AB3_TRUSTEPISODE"], "properties": 4}
```

### `run_agent_boundary_conformance.py` — PASS (exit 0)

```
{"pass_count": 8, "fail_count": 0, "all_pass": true}
```

### `run_targeted_cards.py` — PASS (exit 0)

```
{"pass": 8, "fail": 0}
```

### `run_temporal_boundary_fixtures.py` — PASS (exit 0)

```
{"all_pass": true, "n_cases": 7, "output": null, "sha256": null, "check_only": true, "pytest_tail": ".......                                                                  [100%]"}
```

### `generate_tables.py` — PASS (exit 0)

```
{"n_runs": 60, "d1_pass": 60, "d1_exec": 600, "audit_pass": 18, "audit_fail_codes": 7, "tax_pass": 8, "tax_total": 8, "agent_boundary_pass": 8, "agent_boundary_total": 8, "llm_pilot_exact": 9, "llm_pilot_total": 20, "gemma_pilot_exact": 0, "gemma_pilot_total": 20}
```

### `verify_claims.py` — PASS (exit 0)

```
{
  "ok": true,
  "failures": [],
  "n_failures": 0
}
```

## Interpretation

Every command above executed with the extracted archive as its working directory.
The companion validates contracts and the imported runtime's extracted-archive origin;
then runs all 38 packaged reference-runtime tests;
re-executes A1--A12, A--G, AB0--AB3, AI0--AI7, T1--T8, and temporal boundary
fixtures; regenerates tables; and checks sealed
determinism, baseline, M2, supplemental, and local-model summaries.
It byte-compares both frozen local-model raw/derived files without re-running Ollama.
It does not re-execute live collection or cohort re-synthesis from omitted raw lab bundles.

Machine-readable: `results/derived/cleanroom_reproduction.json` (sha256 `ed78037f1f80b810dd7851d18166b4a4d442ec39c0bc4566a8af20dd5c5a9f90`).
