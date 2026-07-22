#!/usr/bin/env bash
# Fair sliding-gap baselines (EB0–EB4) + paired bootstrap.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python "$ROOT/scripts/run_fair_baselines.py" "$@"
python "$ROOT/scripts/generate_tables.py"
