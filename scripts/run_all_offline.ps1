# PowerShell fail-closed wrappers for Windows hosts.
param(
  [ValidateSet("native","formation","calibration","heldout","perturbations","outage","replay","tables","figures","all-offline")]
  [string]$Action = "all-offline"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Lab = if ($env:LAB_ROOT) { $env:LAB_ROOT } else { Join-Path (Split-Path -Parent $Root) "sensel-caldera-linux-lab" }
$RuntimeSrc = if ($env:RUNTIME_SRC) { $env:RUNTIME_SRC } else { "c:\Users\admin\Desktop\coreAPP\TRUSTEPISODE-aisec2026\experiment_runtime\src" }
$env:PYTHONPATH = $RuntimeSrc

function Invoke-FailClosed([string]$Message) {
  Write-Error $Message
  exit 2
}

switch ($Action) {
  "calibration" { Invoke-FailClosed "Fitted calibration / cal partition seals missing; refusing to invent results." }
  "heldout" { Invoke-FailClosed "Held-out evaluation requires FreezeArtifacts + locked_test seals." }
  "perturbations" { Invoke-FailClosed "Formal RP0-RP7 cohort not sealed (smoke-only)." }
  "outage" { Invoke-FailClosed "Formal PO1 cohort not sealed (smoke-only)." }
  "native" {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "results\raw\table4_amended") | Out-Null
    python (Join-Path $Lab "scripts\aggregate_table4_amended.py") --root $Lab --contracts (Join-Path $Root "artifacts\contracts") --output (Join-Path $Root "results\raw\table4_amended")
    python (Join-Path $Root "scripts\generate_tables.py")
  }
  "formation" {
    python (Join-Path $Root "scripts\run_formation_baselines.py") --lab-root $Lab --contracts (Join-Path $Root "artifacts\contracts") --output-root (Join-Path $Root "results")
    python (Join-Path $Root "scripts\generate_tables.py")
  }
  "replay" {
    python (Join-Path $Root "scripts\run_formation_baselines.py") --lab-root $Lab --contracts (Join-Path $Root "artifacts\contracts") --output-root (Join-Path $Root "results") --skip-sensitivity
    python -c "import json,pathlib; d=json.loads(pathlib.Path(r'$Root\results\derived\formation_replay_equality.json').read_text(encoding='utf-8')); assert d['byte_equal_fail_count']==0; print('ok', d['byte_equal_pass_count'])"
  }
  "tables" { python (Join-Path $Root "scripts\generate_tables.py") }
  "figures" { python (Join-Path $Root "scripts\generate_figures.py") }
  "all-offline" {
    & $PSCommandPath -Action formation
    & $PSCommandPath -Action tables
    & $PSCommandPath -Action figures
  }
}
