#!/usr/bin/env bash
# Formation digest equality on sealed malicious runs (no fitted pipeline cost claim).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAB="${LAB_ROOT:-$ROOT/../sensel-caldera-linux-lab}"
RUNTIME_SRC="${RUNTIME_SRC:-$ROOT/../../coreAPP/TRUSTEPISODE-aisec2026/experiment_runtime/src}"
export PYTHONPATH="$RUNTIME_SRC${PYTHONPATH:+:$PYTHONPATH}"
python "$ROOT/scripts/run_formation_baselines.py" \
  --lab-root "$LAB" \
  --contracts "$ROOT/artifacts/contracts" \
  --output-root "$ROOT/results" \
  --skip-sensitivity
python -c "import json,pathlib; d=json.loads(pathlib.Path(r'$ROOT/results/derived/formation_replay_equality.json').read_text(encoding='utf-8')); assert d['byte_equal_fail_count']==0 and d['parallel_map_equal_to_sequential']; print('replay_benchmark_formation: ok', d['byte_equal_pass_count'])"
