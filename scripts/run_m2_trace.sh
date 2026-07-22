#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python "$ROOT/scripts/run_m2_trace.py" "$@"
python "$ROOT/scripts/generate_tables.py"
