from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Any, Iterable

import rfc8785


def assert_finite(value: Any) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        if value == 0.0 and math.copysign(1.0, value) < 0:
            raise ValueError("negative zero is forbidden")
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            assert_finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            assert_finite(child)


def canonical_bytes(value: Any) -> bytes:
    assert_finite(value)
    return rfc8785.dumps(value)


def sha256_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def raw_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"timestamp must be UTC Z form: {value!r}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp timezone missing")
    return parsed.astimezone(timezone.utc)


def timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


RELATION_RANK = {
    "membership": 0,
    "link": 1,
    "feature": 2,
    "health": 3,
    "contradiction": 4,
}


def reference_sort_key(reference: dict[str, Any]) -> tuple[Any, ...]:
    pointer = reference.get("raw_pointer") or {}
    return (
        RELATION_RANK[reference["relation"]],
        utf8_key(reference["dependency_group"]),
        0 if reference["reference_kind"] == "object" else 1,
        utf8_key(str(pointer.get("object_id") or reference.get("expected_object_id") or "")),
        utf8_key(str(pointer.get("content_digest") or "")),
    )


def sort_references(references: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(references, key=reference_sort_key)


def digest_fields(record: dict[str, Any], fields: Iterable[str]) -> str:
    payload = {field: record[field] for field in fields}
    return sha256_digest(payload)
