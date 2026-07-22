#!/usr/bin/env bash
# Offline formation baselines/ablations/M2/sensitivity/replay digests on sealed cohort.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAB="${LAB_ROOT:-$ROOT/../sensel-caldera-linux-lab}"
RUNTIME_SRC="${RUNTIME_SRC:-$ROOT/../../coreAPP/TRUSTEPISODE-aisec2026/experiment_runtime/src}"
export PYTHONPATH="$RUNTIME_SRC${PYTHONPATH:+:$PYTHONPATH}"
python "$ROOT/scripts/run_formation_baselines.py" \
  --lab-root "$LAB" \
  --contracts "$ROOT/artifacts/contracts" \
  --output-root "$ROOT/results"
python "$ROOT/scripts/generate_tables.py" --results "$ROOT/results" --out "$ROOT/results/tables"
echo "run_formation_offline: ok"
