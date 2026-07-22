#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python "$ROOT/scripts/run_targeted_cards.py" "$@"
python "$ROOT/scripts/generate_tables.py"
