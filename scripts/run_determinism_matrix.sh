#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python "$ROOT/scripts/run_determinism_matrix.py" "$@"
python "$ROOT/scripts/generate_tables.py"
