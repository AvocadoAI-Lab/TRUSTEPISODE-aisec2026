#!/usr/bin/env bash
set -euo pipefail
echo "ERROR: held-out evaluation requires FreezeArtifacts + locked_test seals." >&2
exit 2
