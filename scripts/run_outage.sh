#!/usr/bin/env bash
set -euo pipefail
echo "ERROR: formal PO1 physical-outage cohort not sealed (smoke-only artifacts exist)." >&2
exit 2
