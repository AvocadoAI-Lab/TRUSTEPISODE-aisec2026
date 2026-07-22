#!/usr/bin/env bash
# Calibration / held-out / perturbation / outage formal runners fail closed until prerequisites exist.
set -euo pipefail
echo "ERROR: fitted calibration and locked-test cohorts are not sealed in this submission." >&2
echo "Refusing to invent results. Seal calibration+locked partitions, then FitArtifacts." >&2
exit 2
