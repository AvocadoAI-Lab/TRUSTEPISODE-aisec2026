# Table 2 deterministic sufficiency conformance

## Conclusion

Paper Table 2 is a normative first-match rule table, not an empirical performance table. Direct
tests against `ReferencePipeline._sufficiency` confirm the production v1 implementation for
coverage, provenance, lateness, and calibration. Contradiction behavior remains covered by the
existing production pipeline and schema tests.

## Verified mappings

| Axis | Input condition | Expected/observed state |
|---|---|---|
| coverage | missing/conflicting health | `unknown` |
| coverage | invalid parser | `unavailable` |
| coverage | degraded health | `degraded` |
| coverage | healthy and parser-valid | `complete` |
| provenance | every required reference is an object | `complete` |
| provenance | any required reference is a sentinel | `missing` |
| lateness | accepted within revision horizon | `late_accepted` |
| lateness | open or finalized | `revisable` |
| lateness | closed | `stable` |
| calibration | Scope Resolver output | exact copied `kappa` value |

The schema value `provenance=partial` is reserved for a future version and is not emitted by
the production v1 implementation. The paper and submission appendix were corrected accordingly.

## Test evidence

- Command: `python -m pytest tests/test_pipeline.py -q`
- Result: `16 passed`
- Full runtime regression: `37 passed`.

This report verifies rule conformance only. It does not claim empirical Table 2 state
distributions for the amended live cohort because fitted runtime artifacts were not produced.
