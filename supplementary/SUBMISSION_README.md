# TrustEpisode AISec 2026 reproducibility companion

This archive accompanies the amended 100-run live formation evaluation.

## Scope

- Primary live cohort: 40 B1--B8 standalone-benign runs plus 60 M1--M6 malicious runs.
- Repetitions: five per M1--M6 family/mode.
- Reported metrics: action coverage, fragmentation, over-merge, contamination, and episode F1.
- Temporal evidence: deterministic production-path conformance at 299/300/301 seconds and
  3599/3600/3601 seconds.
- Not reported: fitted calibration, held-out evaluation, perturbation, physical outage,
  production generalization, or completed live M7 results.

Four sealed M7 attack-only traces remain outside the primary estimator as audit evidence. They
are not included in this archive because the paper makes no live M7 result claim.

The machine contracts preserve the original 10-repetition M1--M7 registration as an immutable
audit trail. `evidence/table4/PROTOCOL_AMENDMENT_5_REPETITIONS.md` supersedes only the primary
reporting cohort and repetition count; it does not rewrite the original contract files or relabel
any run.

## Archive layout

- `artifacts/contracts/`: frozen machine-readable schemas, registries, examples, and validator.
- `evidence/table4/`: amended protocol, cell CSV, complete per-run JSON, and formal report.
- `evidence/table2/`: deterministic sufficiency-rule conformance report.
- `evidence/boundary/`: temporal boundary conformance report.
- `scripts/`: amended Table 4 aggregation script.
- `tests/`: production runtime conformance tests used for Table 2 and temporal boundaries.

## Verification

Run the contract validator from the archive root:

```text
python artifacts/contracts/validate_contracts.py
```

The archive includes the tested reference runtime package:

```text
cd runtime
python -m pytest tests/test_formation.py tests/test_pipeline.py -q
```

All hashes in the evidence files are SHA-256. No synthetic performance rows are included.
