from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .canonical import assert_finite, sha256_digest


MANIFEST_NAME = "bundle_manifest.json"


def json_bytes(value: Any) -> bytes:
    assert_finite(value)
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def ndjson_bytes(records: Iterable[dict[str, Any]]) -> bytes:
    lines: list[str] = []
    for record in records:
        assert_finite(record)
        lines.append(
            json.dumps(
                record,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    return (("\n".join(lines) + "\n") if lines else "").encode("utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


class BundleWriter:
    def __init__(self, root: Path, *, bundle_type: str, force: bool = False) -> None:
        self.root = root.resolve()
        self.bundle_type = bundle_type
        if self.root.exists() and any(self.root.iterdir()):
            if not force:
                raise FileExistsError(f"output bundle is not empty: {self.root}")
            for path in sorted(self.root.rglob("*"), reverse=True):
                if path.is_file() or path.is_symlink():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
        self.root.mkdir(parents=True, exist_ok=True)

    def write_json(self, relative_path: str, value: Any) -> None:
        self._write(relative_path, json_bytes(value))

    def write_ndjson(
        self, relative_path: str, records: Iterable[dict[str, Any]]
    ) -> None:
        self._write(relative_path, ndjson_bytes(records))

    def write_bytes(self, relative_path: str, value: bytes) -> None:
        self._write(relative_path, value)

    def _write(self, relative_path: str, value: bytes) -> None:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts or relative.name == MANIFEST_NAME:
            raise ValueError(f"invalid bundle path: {relative_path}")
        target = (self.root / relative).resolve()
        if self.root not in target.parents:
            raise ValueError(f"bundle path escapes root: {relative_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)

    def finalize(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        entries = _collect_entries(self.root)
        manifest = {
            "manifest_type": "trustepisode.bundle-manifest.v1",
            "bundle_type": self.bundle_type,
            "metadata": metadata or {},
            "files": entries,
            "bundle_digest": sha256_digest(entries),
        }
        (self.root / MANIFEST_NAME).write_bytes(json_bytes(manifest))
        return manifest


def validate_bundle(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = root / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_type") != "trustepisode.bundle-manifest.v1":
        raise ValueError("unsupported bundle manifest")
    expected = manifest.get("files")
    if not isinstance(expected, list):
        raise ValueError("manifest files must be an array")
    actual = _collect_entries(root)
    if actual != expected:
        raise ValueError("bundle file set, size, or SHA-256 differs from manifest")
    if manifest.get("bundle_digest") != sha256_digest(expected):
        raise ValueError("bundle digest mismatch")
    return manifest


def _collect_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file() and item.name != MANIFEST_NAME),
        key=lambda item: item.relative_to(root).as_posix().encode("utf-8"),
    ):
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    return entries
