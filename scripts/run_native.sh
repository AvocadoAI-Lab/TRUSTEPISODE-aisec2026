#!/usr/bin/env bash
# Fail-closed wrapper: re-aggregate amended Table 4 and regenerate LaTeX macros.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAB="${LAB_ROOT:-$ROOT/../sensel-caldera-linux-lab}"
RUNTIME_SRC="${RUNTIME_SRC:-$ROOT/../../coreAPP/TRUSTEPISODE-aisec2026/experiment_runtime/src}"
export PYTHONPATH="$RUNTIME_SRC${PYTHONPATH:+:$PYTHONPATH}"
OUT="$ROOT/results/raw/table4_amended"
mkdir -p "$OUT" "$ROOT/results/tables" "$ROOT/manifests"
python "$LAB/scripts/aggregate_table4_amended.py" \
  --root "$LAB" \
  --contracts "$ROOT/artifacts/contracts" \
  --output "$OUT"
python "$ROOT/scripts/generate_tables.py" --results "$ROOT/results" --out "$ROOT/results/tables"
echo "run_native: ok"
