#!/usr/bin/env bash
# Paired analysis is produced by run_fair_baselines.py; this wrapper regenerates tables.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python "$ROOT/scripts/run_fair_baselines.py" "$@"
python "$ROOT/scripts/generate_tables.py"
