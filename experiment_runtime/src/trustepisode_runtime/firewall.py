from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


FORBIDDEN_KEYS = frozenset(
    {
        "run_id",
        "card_id",
        "scenario_id",
        "scenario_class",
        "ability_id",
        "operation_id",
        "caldera_run_id",
        "campaign_id",
        "adversary_id",
        "adversary_profile",
        "receipt_id",
        "marker",
        "marker_id",
        "label",
        "malicious_label",
        "split",
        "partition",
        "attack_window",
    }
)


@dataclass(frozen=True)
class LeakageFinding:
    path: str
    kind: str
    value: str


class LabelLeakageError(ValueError):
    def __init__(self, findings: list[LeakageFinding]) -> None:
        self.findings = findings
        detail = "; ".join(f"{item.kind}@{item.path}={item.value!r}" for item in findings)
        super().__init__(f"label firewall rejected online object: {detail}")


def inspect(value: Any, forbidden_values: Iterable[str] = ()) -> list[LeakageFinding]:
    exact_values = {str(item) for item in forbidden_values if str(item)}
    findings: list[LeakageFinding] = []

    def walk(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text
                if key_text.lower() in FORBIDDEN_KEYS:
                    findings.append(LeakageFinding(child_path, "key", key_text))
                walk(child, child_path)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]")
        elif isinstance(item, str) and item in exact_values:
            findings.append(LeakageFinding(path, "value", item))

    walk(value, "")
    return findings


def enforce(value: Any, forbidden_values: Iterable[str] = ()) -> None:
    findings = inspect(value, forbidden_values)
    if findings:
        raise LabelLeakageError(findings)
