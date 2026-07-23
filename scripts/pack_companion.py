#!/usr/bin/env python3
"""Rebuild TrustEpisode_reproducibility_companion_v1.zip and update digests."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = "TrustEpisode_reproducibility_companion_v1.zip"
BUILD = ROOT / "tmp" / "supplementary-build-aisec-v2"

INCLUDE_DIRS = [
    "results/derived",
    "results/raw",
    "results/tables",
    "artifacts",
]
INCLUDE_SCRIPTS = [
    "classify_evidence_loss.py",
    "generate_tables.py",
    "run_agent_boundary_conformance.py",
    "run_audit_baselines_ab.py",
    "run_audit_conformance_a12.py",
    "run_companion_checks.py",
    "run_fair_baselines.py",
    "run_llm_grounding_pilot.py",
    "run_targeted_cards.py",
    "run_taxonomy_ag.py",
    "run_temporal_boundary_fixtures.py",
    "verify_runtime_origin.py",
    "verify_claims.py",
]
INCLUDE_FILES = [
    "CLAIM_EVIDENCE_MATRIX.md",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def locate_runtime_source() -> Path:
    local = ROOT / "experiment_runtime"
    if local.is_dir():
        return local
    raise FileNotFoundError(
        f"vendored TrustEpisode experiment_runtime not found: {local}"
    )


def sanitize_build() -> None:
    replacements = {
        "guacamole" + "-ai": "deployed-investigation-system",
        "Arista" + "connector-Control-Plane": "downstream-control-plane",
        "sensel" + "-caldera-linux-lab": "isolated-edr-ndr-lab",
    }
    text_suffixes = {
        ".csv",
        ".json",
        ".md",
        ".py",
        ".tex",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    for path in BUILD.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")

    def redact_local_paths(value: object) -> object:
        if isinstance(value, dict):
            return {key: redact_local_paths(item) for key, item in value.items()}
        if isinstance(value, list):
            return [redact_local_paths(item) for item in value]
        if not isinstance(value, str):
            return value
        normalized = value.replace("\\", "/")
        if not re.match(r"(?i)^[a-z]:/users/[^/]+/", normalized):
            return value
        marker = "/experiment-data/"
        if marker in normalized:
            return "<ANONYMIZED_LAB_ROOT>" + normalized[normalized.index(marker) :]
        return "<ANONYMIZED_LOCAL_PATH>/" + normalized.rsplit("/", 1)[-1]

    for path in BUILD.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        if not re.search(r"(?i)[a-z]:\\\\+users\\\\+", text):
            continue
        payload = redact_local_paths(json.loads(text))
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    contracts = BUILD / "artifacts" / "contracts"
    (contracts / "README.md").write_text(
        """# TrustEpisode machine-readable contracts

These files define the frozen schemas, thresholds, registries, scenario cards, examples, and
validation rules used by the paper. They are method and audit artifacts; pending protocols are
not represented as completed experiments.

Run `python artifacts/contracts/validate_contracts.py` from the companion root.
Operational dashboard/control-plane mirrors are downstream consumers of sealed copies and are
excluded from the primary RT1--RT7 inputs, denominators, and results.
""",
        encoding="utf-8",
    )

    manifest_path = contracts / "manifest.v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        target = contracts / entry["path"]
        content = target.read_bytes()
        entry["bytes"] = len(content)
        entry["sha256"] = hashlib.sha256(content).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def assert_anonymous_build() -> None:
    windows_home = re.compile(
        r"(?i)[a-z]:[\\/]+" + "users" + r"[\\/]+[^\\/\s\"']+"
    )
    unix_home = re.compile(r"/" + "home" + r"/[^/\s\"']+")
    forbidden = (
        "guacamole" + "-ai",
        "Arista" + "connector-Control-Plane",
        "sensel" + "-caldera-linux-lab",
    )
    text_suffixes = {
        ".csv",
        ".json",
        ".md",
        ".py",
        ".tex",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
    failures = []
    for path in BUILD.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        label = path.relative_to(BUILD).as_posix()
        if windows_home.search(text) or unix_home.search(text):
            failures.append(f"user-home path in {label}")
        lowered = text.lower()
        for value in forbidden:
            if value.lower() in lowered:
                failures.append(f"deployment label in {label}")
    if failures:
        raise SystemExit("companion anonymity scan failed:\n- " + "\n- ".join(failures))


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)

    readme = BUILD / "README.md"
    readme.write_text(
        """# TrustEpisode reproducibility companion (AISec 2026)

This anonymous archive contains a portable reference runtime, executable synthetic checks,
sealed results, contracts, generated tables, and a claim-to-evidence matrix. The manuscript
source is intentionally excluded because embedding a source file that states the archive's own
SHA-256 would create a self-referential stale digest. The submitted PDF's
**Artifact Digest** paragraph records the authoritative SHA-256 of this archive.

## Portable one-command check

```bash
python -m pip install -r requirements.txt
python scripts/run_companion_checks.py
```

The command first fails closed unless Python imports the runtime from this extracted archive.
It then runs the packaged reference-runtime test suite and re-runs A1--A12, A--G, AB0--AB3,
AI0--AI7, T1--T8, the inclusive temporal boundary fixtures, contract validation, table
generation, and the claim verifier.

## Evidence modes

- **Re-executable from this archive:** packaged-runtime origin validation; the 38-test reference
  runtime suite; A1--A12 audit conformance; A--G taxonomy; AB0--AB3 contract isolation;
  AI0--AI7 agent-boundary mutations; T1--T8 mechanism cards; temporal boundary fixtures at
  299/300/301 and 3599/3600/3601/3900 seconds.
- **Regenerated from sealed JSON:** LaTeX macros and result tables.
- **Integrity/claim checked from sealed outputs:** D1--D5 determinism summaries, fair-baseline
  summaries, M2 waterfall, supplemental L1--L4 results, and both held-out local-model audits.
- **Not re-executed from this archive:** live collection, offline cohort re-synthesis requiring
  omitted raw lab bundles, or Ollama model inference. The two model raw/derived JSON files are
  byte-compared and their frozen digests and reported scores are checked.

For anonymous review, absolute local `source_path` values in supplemental live-result copies are
replaced with `<ANONYMIZED_LAB_ROOT>`; run IDs, observations, measurements, and outcome fields are
unchanged. The author-retained sealed originals are not modified.

Expected headline values include 0/69/1 EB4-vs-EB1 action-coverage W/T/L, 60/60 D1 canonical
replay, 8/8 AI0--AI7 specified outcomes, 9/20 fully exact Qwen responses, and 0/20 fully exact Gemma
responses. These are bounded artifact claims, not production-readiness or general model-accuracy
claims.

## Anonymous-review publication

If the venue requests an artifact URL, publish this exact ZIP through an anonymous repository
or other organizer-approved anonymous mechanism. Do not link an author-identifying source
repository. Reviewers can compare the downloaded ZIP with the SHA-256 printed in the submitted
paper before extracting and running it.
""",
        encoding="utf-8",
    )
    (BUILD / "requirements.txt").write_text(
        "\n".join(
            [
                "-e ./experiment_runtime",
                "jsonschema[format]>=4.21,<5",
                "numpy>=1.26,<3",
                "psutil>=5.9,<8",
                "pytest>=8,<10",
                "rfc8785>=0.1.4,<0.2",
                "scipy>=1.12,<2",
                "",
            ]
        ),
        encoding="utf-8",
    )

    for rel in INCLUDE_DIRS:
        src = ROOT / rel
        if not src.exists():
            continue
        dst = BUILD / rel
        if src.is_dir():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    "*.pyc",
                    ".pytest_cache",
                    "cleanroom_reproduction.json",
                ),
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    scripts_dst = BUILD / "scripts"
    scripts_dst.mkdir(parents=True, exist_ok=True)
    for name in INCLUDE_SCRIPTS:
        src = ROOT / "scripts" / name
        if not src.exists():
            raise FileNotFoundError(f"missing companion script: {src}")
        shutil.copy2(src, scripts_dst / name)

    runtime_source = locate_runtime_source()
    shutil.copytree(
        runtime_source,
        BUILD / "experiment_runtime",
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            "*.egg-info",
            "README_zh-TW.md",
        ),
    )

    for name in INCLUDE_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, BUILD / name)

    sanitize_build()
    assert_anonymous_build()

    zip_path = ROOT / ZIP_NAME
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(BUILD.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(BUILD).as_posix())

    digest = sha256_file(zip_path)
    side = ROOT / "TrustEpisode_reproducibility_companion_v1.sha256"
    side.write_text(f"{digest}  {ZIP_NAME}\n", encoding="utf-8")

    # Update appendix split hex (tolerate LaTeX \\ between halves)
    appendix = ROOT / "sections" / "appendix_submission.tex"
    text = appendix.read_text(encoding="utf-8")
    line1, line2 = digest[:32], digest[32:]
    pattern = (
        r"(\\begin\{flushleft\}\\scriptsize\\ttfamily\s*\n?)"
        r"[0-9a-fA-F]{32}(?:\\\\)?\s*"
        r"[0-9a-fA-F]{32}"
        r"(\s*\\end\{flushleft\})"
    )
    repl = rf"\g<1>{line1}\\\\\n{line2}\g<2>"
    new_text, n = re.subn(pattern, repl, text)
    if n != 1:
        raise SystemExit(f"failed to patch appendix digest (matches={n})")
    appendix.write_text(new_text, encoding="utf-8")
    print(json.dumps({"zip": ZIP_NAME, "sha256": digest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
