# Fresh-environment companion audit (AISec 2026)

- Date: 2026-07-24
- Artifact: `TrustEpisode_reproducibility_companion_v1.zip`
- SHA-256: `cc4d451b50f975fdd7ab07c263a8ce2044ab771126808e485faac4033852a730`
- Host test interpreter: Python 3.14.4
- Isolation: a newly created `venv` without inherited site packages
- Setup command: `python -m pip install -r requirements.txt`
- Verification command: `python scripts/run_companion_checks.py`
- Overall result: **PASS**
- Final-pack rerun: **PASS** after packaged-runtime origin enforcement

## Executed checks

| Check | Result |
|---|---:|
| Machine-readable contract validation | PASS |
| Runtime import origin | PASS: `experiment_runtime/src/trustepisode_runtime/__init__.py` |
| Packaged reference-runtime implementation tests | 38 pass / 0 fail |
| A1--A12 audit conformance | 18 pass / 0 fail |
| A--G evidence-loss taxonomy | 8 pass / 0 fail |
| AB0--AB3 contract isolation | PASS |
| AI0--AI7 downstream boundary conformance | 8 specified outcomes pass / 0 fail |
| T1--T8 mechanism conformance | 8 pass / 0 fail |
| Temporal boundaries 299/300/301 and 3599/3600/3601/3900 | 7 pass / 0 fail |
| Table/macro regeneration | PASS |
| Fail-closed claim verifier | `ok=true`, 0 failures |

All commands used the extracted archive as the working tree. No package from the author's active
Python environment was inherited. The archive still does not claim to re-run live collection,
raw-lab cohort re-synthesis, or Ollama inference.

An earlier fresh `r4` environment correctly exposed that the ZIP contained the runtime source but
did not install it. The packer was fixed to declare `-e ./experiment_runtime`. A subsequent
artifact-evaluator audit found that the host/root clean-room path could still import an editable
package from a different checkout. The final artifact therefore prepends its own runtime source
to every subprocess `PYTHONPATH` and fails closed unless `trustepisode_runtime.__file__` is the
copy beside the extracted scripts. The final `r6` environment installed
`trustepisode-experiment-runtime 0.1.0` from the ZIP and passed all 11 checks. Earlier audit
directories are retained as remediation evidence and are not part of the submitted artifact.

## Resolved dependency versions

`jsonschema 4.26.0`, `numpy 2.5.1`, `psutil 7.2.2`, `pytest 9.1.1`,
`rfc8785 0.1.4`, `scipy 1.18.0`, and the local
`trustepisode-experiment-runtime 0.1.0` were installed from the archive's declared requirements.
