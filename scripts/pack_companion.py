#!/usr/bin/env python3
"""Rebuild TrustEpisode_reproducibility_companion_v1.zip and update digests."""
from __future__ import annotations

import hashlib
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = "TrustEpisode_reproducibility_companion_v1.zip"
BUILD = ROOT / "tmp" / "supplementary-build-dfrws-v2"

INCLUDE_DIRS = [
    "scripts",
    "results/derived",
    "results/raw",
    "results/tables",
    "artifacts",
    "sections",
    "bib",
]
INCLUDE_FILES = [
    "CLAIM_EVIDENCE_MATRIX.md",
    "DELIVERY_REPORT_DFRWS_20260721.md",
    "CLEANROOM_REPRODUCTION_REPORT_20260721.md",
    "README_COMPANION.md",
    "main.tex",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)

    readme = BUILD / "README.md"
    readme.write_text(
        """# TrustEpisode reproducibility companion (DFRWS revision)

## One-command checks (from this directory)

```
python scripts/generate_tables.py
python scripts/run_targeted_cards.py
python scripts/run_determinism_matrix_60.py
python scripts/run_audit_conformance_a12.py
python scripts/run_taxonomy_ag.py
python scripts/run_audit_baselines_ab.py
python scripts/verify_claims.py
```

## Expected

- fair_baselines.json: EB1--EB4 identical on M1--M6; 60/60 ties vs sliding-time
- fair_baselines_m1m7.json: offline 70-run M1--M7 re-synthesis (descriptive; no superiority claim)
- table4_amended: primary M1--M6 cells; M7 is supplemental boundary-stress only
- temporal_boundary_conformance.json: 299/300/301 and 3599/3600/3601/3900 all pass
- determinism_matrix.json: D1 60/60; D2 raw 0/60; D2 canon 60/60; D3/D4 60/60
- audit_conformance.json: A1--A12 pass; seven failure codes covered
- taxonomy_ag.json: A--G synthetic + M2 live D
- ab_contract_baselines.json: AB0--AB3 isolation study
- mechanism_cards.json: T1--T8 pass (conformance only)
- m2_waterfall.json: D_token_mapping_failure
- sealed primary Table-4 cells are NOT mutated by these scripts
- supplemental live L1--L4: see results/raw/supplemental_live/ (evidence classes per path)
""",
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
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for name in INCLUDE_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, BUILD / name)

    # Prefer 60-run script as default determinism entry in companion
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
    print(__import__("json").dumps({"zip": ZIP_NAME, "sha256": digest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
