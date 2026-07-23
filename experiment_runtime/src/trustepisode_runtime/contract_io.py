from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator

import jsonschema

from .canonical import assert_finite
from .firewall import enforce


class ContractSet:
    def __init__(self, contracts_dir: Path) -> None:
        self.root = contracts_dir.resolve()
        self.schema = self.load_json("trustepisode_online.v1.schema.json")
        self.thresholds = self.load_json("thresholds.v1.json")
        self.detectors = self.load_json("detector_registry.v1.json")
        self.result_registry = self.load_json("result_registry.v1.json")
        self.validator = jsonschema.Draft202012Validator(
            self.schema,
            format_checker=jsonschema.FormatChecker(),
        )

    def load_json(self, name: str) -> Any:
        path = self.root / name
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=self._reject_constant)

    @staticmethod
    def _reject_constant(token: str) -> None:
        raise ValueError(f"non-JSON number: {token}")

    def validate_online(self, record: dict[str, Any]) -> None:
        assert_finite(record)
        enforce(record)
        self.validator.validate(record)


def iter_ndjson(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: object required")
            yield value


def load_online_records(
    paths: Iterable[Path],
    contracts: ContractSet,
    *,
    object_types: set[str] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        for record in iter_ndjson(path):
            contracts.validate_online(record)
            if object_types is None or record["object_type"] in object_types:
                records.append(record)
    return records


def write_ndjson(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
