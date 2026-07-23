#!/usr/bin/env python3
"""Fail closed unless the imported runtime is the copy packaged beside this script."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = (ROOT / "experiment_runtime" / "src").resolve()
EXPECTED_INIT = (RUNTIME_SRC / "trustepisode_runtime" / "__init__.py").resolve()


def main() -> int:
    if not EXPECTED_INIT.is_file():
        raise SystemExit(f"missing packaged runtime: {EXPECTED_INIT}")

    sys.path.insert(0, str(RUNTIME_SRC))
    importlib.invalidate_caches()
    runtime = importlib.import_module("trustepisode_runtime")
    actual = Path(runtime.__file__).resolve()
    if actual != EXPECTED_INIT:
        raise SystemExit(
            f"runtime origin mismatch: expected={EXPECTED_INIT} actual={actual}"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "runtime_origin": actual.relative_to(ROOT).as_posix(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
