from __future__ import annotations

import copy
import hashlib
import hmac
import math
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable

from .canonical import canonical_bytes, parse_timestamp, sha256_digest, timestamp, utf8_key


SEED_KEY = b"20260710"


@dataclass
class ReplayChild:
    intervention_id: str
    source_family: str | None
    level: Any
    events: list[dict[str, Any]]
    seed_hex: str
    valid: bool = True
    invalid_reason: str | None = None

    @property
    def child_key(self) -> str:
        source = self.source_family or "none"
        return f"{self.intervention_id}:{source}:{self.level}"

    def manifest(self, base_events: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "child_key": self.child_key,
            "intervention_id": self.intervention_id,
            "source_family": self.source_family,
            "level": self.level,
            "seed_hex": self.seed_hex,
            "valid": self.valid,
            "invalid_reason": self.invalid_reason,
            "base_event_count": len(base_events),
            "child_event_count": len(self.events),
            "base_digest": sha256_digest(base_events),
            "child_digest": sha256_digest(self.events),
        }


def canonical_base_order(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (copy.deepcopy(item) for item in events),
        key=lambda event: (
            parse_timestamp(event["event_time"]),
            parse_timestamp(event["ingest_time"]),
            utf8_key(event["source_instance"]),
            utf8_key(event["event_id"]),
        ),
    )


def child_seed(
    base_run_id: str,
    intervention_id: str,
    source_family: str | None,
    level: Any,
) -> bytes:
    message = (
        base_run_id.encode("utf-8")
        + b"\x1f"
        + intervention_id.encode("utf-8")
        + b"\x1f"
        + (source_family or "none").encode("utf-8")
        + b"\x1f"
        + canonical_bytes(level)
    )
    return hmac.new(SEED_KEY, message, hashlib.sha256).digest()


def uniform(seed: bytes, domain: str, key: str) -> float:
    message = domain.encode("utf-8") + b"\x1f" + key.encode("utf-8")
    value = int.from_bytes(hmac.new(seed, message, hashlib.sha256).digest()[:8], "big")
    return value / 2**64


def generate_replay_children(
    base_run_id: str,
    events: Iterable[dict[str, Any]],
) -> list[ReplayChild]:
    base = canonical_base_order(events)
    children: list[ReplayChild] = []
    children.append(_unchanged(base_run_id, base))
    for level in ("EDR_only", "NDR_only"):
        children.append(_source_mask(base_run_id, base, level))
    for source in ("EDR", "NDR"):
        for level in (0.05, 0.10, 0.25):
            children.append(_event_drop(base_run_id, base, source, level))
        for level in (30, 120, 300):
            children.append(_burst_drop(base_run_id, base, source, level))
        for level in (30, 120, 600):
            children.append(_fixed_delay(base_run_id, base, source, level))
        for level in (30, 120, 600):
            children.append(_reorder(base_run_id, base, source, level))
        for level in (-120, -30, 30, 120):
            children.append(_clock_skew(base_run_id, base, source, level))
        for level in (0.05, 0.10, 0.25):
            children.append(_duplicate(base_run_id, base, source, level))
    if len(children) != 41:
        raise AssertionError(f"replay design must contain 41 children, got {len(children)}")
    return children


def _new_child(
    base_run_id: str,
    intervention: str,
    source: str | None,
    level: Any,
    events: list[dict[str, Any]],
    *,
    valid: bool = True,
    invalid_reason: str | None = None,
) -> ReplayChild:
    seed = child_seed(base_run_id, intervention, source, level)
    return ReplayChild(
        intervention,
        source,
        level,
        events,
        seed.hex(),
        valid,
        invalid_reason,
    )


def _unchanged(base_run_id: str, base: list[dict[str, Any]]) -> ReplayChild:
    return _new_child(base_run_id, "RP0", None, "control", copy.deepcopy(base))


def _source_mask(base_run_id: str, base: list[dict[str, Any]], level: str) -> ReplayChild:
    retained = level.removesuffix("_only")
    events = [copy.deepcopy(item) for item in base if item["source_family"] == retained]
    return _new_child(base_run_id, "RP1", None, level, events)


def _event_drop(
    base_run_id: str,
    base: list[dict[str, Any]],
    source: str,
    level: float,
) -> ReplayChild:
    seed = child_seed(base_run_id, "RP2", source, level)
    events = [
        copy.deepcopy(item)
        for item in base
        if item["source_family"] != source
        or uniform(seed, "drop", f"{source}\x1f{item['event_id']}") >= level
    ]
    return ReplayChild("RP2", source, level, events, seed.hex())


def _burst_drop(
    base_run_id: str,
    base: list[dict[str, Any]],
    source: str,
    level: int,
) -> ReplayChild:
    seed = child_seed(base_run_id, "RP3", source, level)
    if not base:
        return ReplayChild("RP3", source, level, [], seed.hex(), False, "empty_base")
    run_end = max(parse_timestamp(item["event_time"]) for item in base)
    candidates = sorted(
        {
            parse_timestamp(item["event_time"])
            for item in base
            if item["source_family"] == source
            and parse_timestamp(item["event_time"]) + timedelta(seconds=level) <= run_end
        }
    )
    if not candidates:
        return ReplayChild(
            "RP3",
            source,
            level,
            copy.deepcopy(base),
            seed.hex(),
            False,
            "candidate_count_zero",
        )
    index = math.floor(uniform(seed, "interval", "start") * len(candidates))
    start = candidates[index]
    end = start + timedelta(seconds=level)
    events = [
        copy.deepcopy(item)
        for item in base
        if item["source_family"] != source
        or not (start <= parse_timestamp(item["event_time"]) < end)
    ]
    return ReplayChild("RP3", source, level, events, seed.hex())


def _fixed_delay(
    base_run_id: str,
    base: list[dict[str, Any]],
    source: str,
    level: int,
) -> ReplayChild:
    events = copy.deepcopy(base)
    for event in events:
        if event["source_family"] == source:
            event["ingest_time"] = timestamp(
                parse_timestamp(event["ingest_time"]) + timedelta(seconds=level)
            )
    return _new_child(base_run_id, "RP4", source, level, events)


def _reorder(
    base_run_id: str,
    base: list[dict[str, Any]],
    source: str,
    level: int,
) -> ReplayChild:
    seed = child_seed(base_run_id, "RP5", source, level)
    if not base:
        return ReplayChild("RP5", source, level, [], seed.hex())
    anchor = min(parse_timestamp(item["ingest_time"]) for item in base)
    output = copy.deepcopy(base)
    positions_by_buffer: dict[int, list[int]] = {}
    for index, event in enumerate(base):
        if event["source_family"] != source:
            continue
        buffer_index = math.floor(
            (parse_timestamp(event["ingest_time"]) - anchor).total_seconds() / level
        )
        positions_by_buffer.setdefault(buffer_index, []).append(index)
    for positions in positions_by_buffer.values():
        permuted = sorted(
            (copy.deepcopy(base[index]) for index in positions),
            key=lambda event: (
                uniform(seed, "permute", f"{source}\x1f{event['event_id']}"),
                utf8_key(event["event_id"]),
            ),
        )
        for position, event in zip(positions, permuted, strict=True):
            output[position] = event
    return ReplayChild("RP5", source, level, output, seed.hex())


def _clock_skew(
    base_run_id: str,
    base: list[dict[str, Any]],
    source: str,
    level: int,
) -> ReplayChild:
    events = copy.deepcopy(base)
    for event in events:
        if event["source_family"] == source:
            event["event_time"] = timestamp(
                parse_timestamp(event["event_time"]) + timedelta(seconds=level)
            )
    return _new_child(base_run_id, "RP6", source, level, events)


def _duplicate(
    base_run_id: str,
    base: list[dict[str, Any]],
    source: str,
    level: float,
) -> ReplayChild:
    seed = child_seed(base_run_id, "RP7", source, level)
    selected_groups = {
        group
        for group in sorted(
            {item["dependency_group"] for item in base if item["source_family"] == source},
            key=utf8_key,
        )
        if uniform(seed, "duplicate", f"{source}\x1f{group}") < level
    }
    output: list[dict[str, Any]] = []
    seen_ids = {item["event_id"] for item in base}
    for event in base:
        output.append(copy.deepcopy(event))
        if event["source_family"] != source or event["dependency_group"] not in selected_groups:
            continue
        duplicate = copy.deepcopy(event)
        preimage = (
            b"RP7\x1f"
            + seed
            + b"\x1f"
            + event["event_id"].encode("utf-8")
            + b"\x1f"
            + (1).to_bytes(4, "big")
        )
        duplicate_id = hashlib.sha256(preimage).hexdigest()
        if duplicate_id in seen_ids:
            return ReplayChild(
                "RP7",
                source,
                level,
                copy.deepcopy(base),
                seed.hex(),
                False,
                "duplicate_id_collision",
            )
        duplicate["event_id"] = duplicate_id
        duplicate["ingest_time"] = timestamp(
            parse_timestamp(event["ingest_time"]) + timedelta(microseconds=1)
        )
        seen_ids.add(duplicate_id)
        output.append(duplicate)
    return ReplayChild("RP7", source, level, output, seed.hex())


def generate_po1_cells() -> list[dict[str, Any]]:
    cards = ("M1", "M3", "M4", "M7")
    cells: list[dict[str, Any]] = []
    for source_index, source in enumerate(("EDR", "NDR")):
        for duration_index, duration in enumerate((120, 600)):
            for repetition in range(10):
                card = cards[(repetition + 2 * source_index + duration_index) % 4]
                preimage = (
                    b"PO1-v3\x1f"
                    + source.encode("utf-8")
                    + b"\x1f"
                    + duration.to_bytes(4, "big")
                    + b"\x1f"
                    + repetition.to_bytes(4, "big")
                    + b"\x1f"
                    + card.encode("utf-8")
                )
                cells.append(
                    {
                        "po1_cell_id": hashlib.sha256(preimage).hexdigest(),
                        "source_family": source,
                        "duration_seconds": duration,
                        "repetition_index": repetition,
                        "allocated_card_id": card,
                        "partition": "locked_test",
                        "bootstrap_cluster_id": hashlib.sha256(preimage).hexdigest(),
                    }
                )
    counts = {card: sum(item["allocated_card_id"] == card for item in cells) for card in cards}
    if len(cells) != 40 or set(counts.values()) != {10}:
        raise AssertionError(f"invalid PO1 allocation: {counts}")
    return cells
