from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable

from .canonical import (
    digest_fields,
    parse_timestamp,
    sha256_digest,
    sort_references,
    timestamp,
    utf8_key,
)


RELATION_PRECEDENCE = {
    "process_causal": 4,
    "authenticated_session": 3,
    "endpoint_connection": 2,
    "specific_entity": 1,
}
LATE_DIGEST_FIELDS = (
    "object_type",
    "schema_version",
    "episode_id",
    "latest_revision",
    "latest_revision_digest",
    "event_id",
    "arrival_time",
    "revision_deadline",
    "reason",
    "raw_pointer",
    "dependency_group",
    "ordered_lineage_references",
    "versions",
)


@dataclass(frozen=True)
class LinkCandidate:
    episode_id: str
    relation_classes: tuple[str, ...]
    primary_reason: str
    rho: int
    delta_seconds: float
    start_time: datetime

    def open_sort_key(self) -> tuple[Any, ...]:
        return (
            -self.rho,
            -len(self.relation_classes),
            self.delta_seconds,
            self.start_time,
            utf8_key(self.episode_id),
        )


@dataclass
class Lineage:
    episode_id: str
    event_ids: set[str]
    reason_by_event: dict[str, str]
    start_event_id: str
    parent_episode_ids: tuple[str, ...] = ()
    revision: int = -1
    state: str = "open"
    first_finalized_at: datetime | None = None
    revision_deadline: datetime | None = None
    latest_record: dict[str, Any] | None = None


@dataclass
class SynthesisResult:
    revisions: list[dict[str, Any]] = field(default_factory=list)
    late_records: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    event_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def first_finalized(self) -> list[dict[str, Any]]:
        seen: set[str] = set()
        output: list[dict[str, Any]] = []
        for record in self.revisions:
            if record["state"] != "finalized" or record["episode_id"] in seen:
                continue
            seen.add(record["episode_id"])
            output.append(record)
        return output


class EpisodeSynthesizer:
    def __init__(
        self,
        formation: dict[str, Any],
        *,
        versions: dict[str, Any],
        entity_aliases: dict[str, str] | None = None,
    ) -> None:
        self.policy_version = "trustepisode.formation.v1"
        self.gap = float(formation["W_gap_seconds"])
        self.max_span = float(formation["W_max_seconds"])
        self.revision_horizon = float(formation["W_revision_seconds"])
        self.retention = float(formation["W_closed_lineage_retention_seconds"])
        self.watermark_lag = float(formation["L_watermark_seconds"])
        self.hub_window = float(formation["hub_window_seconds"])
        self.hub_cutoff = int(formation["hub_distinct_relation_cutoff"])
        self.max_events = int(formation["max_component_events"])
        self.max_entities = int(formation["max_component_entities"])
        self.max_parents = int(formation["max_merge_parents"])
        self.versions = versions
        self.aliases = entity_aliases or {}
        self.events: dict[str, dict[str, Any]] = {}
        self.event_to_lineage: dict[str, str] = {}
        self.open: dict[str, Lineage] = {}
        self.revisable: dict[str, Lineage] = {}
        self.closed: dict[str, Lineage] = {}
        self.max_ingest: datetime | None = None
        self.watermark: datetime | None = None
        self.result = SynthesisResult(event_by_id=self.events)

    def synthesize(self, events: Iterable[dict[str, Any]], *, flush: bool = True) -> SynthesisResult:
        # Input sequence is the authenticated arrival order. Base bundles are
        # canonicalized by the bundle builder; RP5 intentionally changes this
        # sequence while retaining event/ingest timestamps.
        ordered = list(events)
        for event in ordered:
            self._process(event)
        if flush and self.max_ingest is not None:
            self._advance(self.max_ingest + timedelta(seconds=self.watermark_lag + 1))
            self._advance(
                self.max_ingest
                + timedelta(seconds=self.watermark_lag + self.revision_horizon + 2)
            )
        return self.result

    @staticmethod
    def _ingest_sort_key(event: dict[str, Any]) -> tuple[Any, ...]:
        return (
            parse_timestamp(event["ingest_time"]),
            parse_timestamp(event["event_time"]),
            utf8_key(event["source_instance"]),
            utf8_key(event["event_id"]),
        )

    def _process(self, event: dict[str, Any]) -> None:
        event_id = event["event_id"]
        ingest = parse_timestamp(event["ingest_time"])
        event_time = parse_timestamp(event["event_time"])
        self._advance(ingest)

        previous = self.events.get(event_id)
        if previous is not None:
            if previous != event:
                raise ValueError(f"conflicting duplicate NormalizedEvent: {event_id}")
            lineage_id = self.event_to_lineage.get(event_id)
            if lineage_id and lineage_id in self.closed:
                self._emit_late(self.closed[lineage_id], event, "duplicate_after_terminal_outcome")
            return

        if self.max_ingest and (ingest - event_time).total_seconds() > self.retention:
            self.result.rejected.append(
                {"event_id": event_id, "reason": "closed_index_expired"}
            )
            return

        self.events[event_id] = event
        non_open = self._non_open_candidates(event)
        if non_open:
            _, lineage, candidate = non_open[0]
            if lineage.state == "finalized" and lineage.revision_deadline and ingest <= lineage.revision_deadline:
                self._attach(lineage, event, candidate.primary_reason, late=True)
            else:
                reason = (
                    "beyond_revision_horizon"
                    if lineage.revision_deadline and ingest > lineage.revision_deadline
                    else "closed_lineage_match"
                )
                self._emit_late(lineage, event, reason)
            self._observe_ingest(ingest)
            self._finalize_by_watermark(ingest)
            return

        candidates = sorted(
            (candidate for lineage in self.open.values() if (candidate := self._candidate(event, lineage))),
            key=LinkCandidate.open_sort_key,
        )
        if not candidates:
            self._start(event)
        elif len(candidates) == 1:
            lineage = self.open[candidates[0].episode_id]
            self._attach(lineage, event, candidates[0].primary_reason, late=False)
        elif self._merge_allowed(event, candidates):
            self._merge(event, candidates)
        else:
            selected = candidates[0]
            self._attach(self.open[selected.episode_id], event, selected.primary_reason, late=False)

        self._observe_ingest(ingest)
        self._finalize_by_watermark(ingest)

    def _observe_ingest(self, ingest: datetime) -> None:
        if self.max_ingest is None or ingest > self.max_ingest:
            self.max_ingest = ingest
        self.watermark = self.max_ingest - timedelta(seconds=self.watermark_lag)

    def _advance(self, now: datetime) -> None:
        self._observe_ingest(now)
        self._finalize_by_watermark(now)
        for episode_id, lineage in list(self.revisable.items()):
            if lineage.revision_deadline and now >= lineage.revision_deadline:
                lineage.state = "closed"
                self._emit_revision(lineage, now, late_reason=None)
                del self.revisable[episode_id]
                self.closed[episode_id] = lineage
        for episode_id, lineage in list(self.closed.items()):
            if (
                lineage.revision_deadline
                and now > lineage.revision_deadline + timedelta(seconds=self.retention)
            ):
                del self.closed[episode_id]

    def _finalize_by_watermark(self, now: datetime) -> None:
        if self.watermark is None:
            return
        for episode_id, lineage in list(self.open.items()):
            _, end = self._time_bounds(lineage)
            if end <= self.watermark:
                lineage.state = "finalized"
                lineage.first_finalized_at = now
                lineage.revision_deadline = now + timedelta(seconds=self.revision_horizon)
                self._emit_revision(lineage, now, late_reason=None)
                del self.open[episode_id]
                self.revisable[episode_id] = lineage

    def _start(self, event: dict[str, Any]) -> None:
        episode_id = "ep:" + sha256_digest(
            {
                "policy": self.policy_version,
                "start_event_id": event["event_id"],
            }
        ).split(":", 1)[1]
        lineage = Lineage(
            episode_id=episode_id,
            event_ids={event["event_id"]},
            reason_by_event={},
            start_event_id=event["event_id"],
        )
        self.open[episode_id] = lineage
        self.event_to_lineage[event["event_id"]] = episode_id
        self._emit_revision(lineage, parse_timestamp(event["ingest_time"]), late_reason=None)

    def _attach(
        self,
        lineage: Lineage,
        event: dict[str, Any],
        reason: str,
        *,
        late: bool,
    ) -> None:
        lineage.event_ids.add(event["event_id"])
        lineage.reason_by_event[event["event_id"]] = reason
        self.event_to_lineage[event["event_id"]] = lineage.episode_id
        if late:
            lineage.state = "finalized"
        self._emit_revision(
            lineage,
            parse_timestamp(event["ingest_time"]),
            late_reason="accepted_within_horizon" if late else None,
        )

    def _merge(self, event: dict[str, Any], candidates: list[LinkCandidate]) -> None:
        selected = candidates[: self.max_parents]
        parents = [self.open[item.episode_id] for item in selected]
        parent_ids = tuple(sorted((item.episode_id for item in parents), key=utf8_key))
        episode_id = "ep:" + sha256_digest(
            {
                "policy": self.policy_version,
                "parents": list(parent_ids),
                "event_id": event["event_id"],
            }
        ).split(":", 1)[1]
        event_ids: set[str] = set()
        reasons: dict[str, str] = {}
        for parent in parents:
            event_ids.update(parent.event_ids)
            reasons.update(parent.reason_by_event)
            del self.open[parent.episode_id]
        event_ids.add(event["event_id"])
        reasons[event["event_id"]] = selected[0].primary_reason
        lineage = Lineage(
            episode_id=episode_id,
            event_ids=event_ids,
            reason_by_event=reasons,
            start_event_id=min(event_ids, key=lambda item: self._event_sort_key(self.events[item])),
            parent_episode_ids=parent_ids,
        )
        self.open[episode_id] = lineage
        for member in event_ids:
            self.event_to_lineage[member] = episode_id
        self._emit_revision(lineage, parse_timestamp(event["ingest_time"]), late_reason=None)

    def _merge_allowed(self, event: dict[str, Any], candidates: list[LinkCandidate]) -> bool:
        if len(candidates) > self.max_parents:
            return False
        strong = {"process_causal", "authenticated_session", "endpoint_connection"}
        if any(not strong.intersection(item.relation_classes) for item in candidates):
            return False
        event_ids = {event["event_id"]}
        for item in candidates:
            event_ids.update(self.open[item.episode_id].event_ids)
        if len(event_ids) > self.max_events:
            return False
        entities = set()
        for event_id in event_ids:
            entities.update(self._entities(self.events[event_id]))
        return len(entities) <= self.max_entities

    def _non_open_candidates(
        self, event: dict[str, Any]
    ) -> list[tuple[int, Lineage, LinkCandidate]]:
        values: list[tuple[int, Lineage, LinkCandidate]] = []
        for priority, index in ((0, self.revisable), (1, self.closed)):
            for lineage in index.values():
                candidate = self._candidate(event, lineage)
                if candidate:
                    values.append((priority, lineage, candidate))
        values.sort(
            key=lambda item: (
                item[0],
                *item[2].open_sort_key(),
            )
        )
        return values

    def _candidate(self, event: dict[str, Any], lineage: Lineage) -> LinkCandidate | None:
        event_time = parse_timestamp(event["event_time"])
        times = [parse_timestamp(self.events[item]["event_time"]) for item in lineage.event_ids]
        delta = min(abs((event_time - item).total_seconds()) for item in times)
        if delta > self.gap:
            return None
        start, end = min([*times, event_time]), max([*times, event_time])
        if (end - start).total_seconds() > self.max_span:
            return None
        relations, shared_entities = self._relations(event, lineage)
        if not relations:
            return None
        if self._hub_only(shared_entities, event_time):
            return None
        primary = max(relations, key=lambda item: RELATION_PRECEDENCE[item])
        return LinkCandidate(
            episode_id=lineage.episode_id,
            relation_classes=tuple(sorted(relations, key=lambda item: -RELATION_PRECEDENCE[item])),
            primary_reason=primary,
            rho=RELATION_PRECEDENCE[primary],
            delta_seconds=delta,
            start_time=start,
        )

    def _relations(self, event: dict[str, Any], lineage: Lineage) -> tuple[set[str], set[str]]:
        relations: set[str] = set()
        event_entities = self._entities(event)
        shared_entities: set[str] = set()
        for event_id in lineage.event_ids:
            other = self.events[event_id]
            shared = event_entities.intersection(self._entities(other))
            shared_entities.update(shared)
            if event["dependency_group"] == other["dependency_group"]:
                relations.add("process_causal")
            if shared:
                relations.add("specific_entity")
                families = {event["source_family"], other["source_family"]}
                if families == {"EDR", "NDR"}:
                    relations.add("endpoint_connection")
                if self._session_like(event) and self._session_like(other):
                    relations.add("authenticated_session")
        return relations, shared_entities

    @staticmethod
    def _session_like(event: dict[str, Any]) -> bool:
        action = event["action"].lower()
        family = str((event.get("attributes") or {}).get("command_family") or "").lower()
        protocol = str((event.get("attributes") or {}).get("app_protocol") or "").lower()
        port = (event.get("attributes") or {}).get("destination_port")
        return (
            family in {"remote_session", "file_transfer"}
            or protocol in {"ssh", "smb", "nfs"}
            or port == 22
            or "session" in action
        )

    def _hub_only(self, shared_entities: set[str], event_time: datetime) -> bool:
        if not shared_entities:
            return False
        lower = event_time - timedelta(seconds=self.hub_window)
        counts: dict[str, set[str]] = {item: set() for item in shared_entities}
        for existing in self.events.values():
            existing_time = parse_timestamp(existing["event_time"])
            if not lower <= existing_time <= event_time:
                continue
            for entity in shared_entities.intersection(self._entities(existing)):
                counts[entity].add(existing["dependency_group"])
        return all(len(values) >= self.hub_cutoff for values in counts.values())

    def _entities(self, event: dict[str, Any]) -> set[str]:
        return {
            self.aliases.get(event["subject"], event["subject"]),
            self.aliases.get(event["object"], event["object"]),
        }

    def _time_bounds(self, lineage: Lineage) -> tuple[datetime, datetime]:
        times = [parse_timestamp(self.events[item]["event_time"]) for item in lineage.event_ids]
        return min(times), max(times)

    def _event_sort_key(self, event: dict[str, Any]) -> tuple[Any, ...]:
        return (
            parse_timestamp(event["event_time"]),
            parse_timestamp(event["ingest_time"]),
            utf8_key(event["source_instance"]),
            utf8_key(event["event_id"]),
        )

    def _emit_revision(
        self,
        lineage: Lineage,
        observed_at: datetime,
        *,
        late_reason: str | None,
    ) -> None:
        predecessor = lineage.revision if lineage.revision >= 0 else None
        lineage.revision += 1
        ordered = sorted(lineage.event_ids, key=lambda item: self._event_sort_key(self.events[item]))
        link_reasons = [
            lineage.reason_by_event.get(event_id, "specific_entity")
            for event_id in ordered[1:]
        ]
        start, end = self._time_bounds(lineage)
        watermark_value = self.watermark or observed_at - timedelta(seconds=self.watermark_lag)
        record = {
            "object_type": "EpisodeRevision",
            "schema_version": "trustepisode.online.v1",
            "episode_id": lineage.episode_id,
            "revision": lineage.revision,
            "state": lineage.state,
            "ordered_event_ids": ordered,
            "ordered_link_reasons": link_reasons,
            "parent_episode_ids": list(lineage.parent_episode_ids),
            "predecessor_revision": predecessor,
            "late_evidence_reason": late_reason,
            "first_finalized_at": timestamp(lineage.first_finalized_at) if lineage.first_finalized_at else None,
            "revision_deadline": timestamp(lineage.revision_deadline) if lineage.revision_deadline else None,
            "event_time_start": timestamp(start),
            "event_time_end": timestamp(end),
            "watermark": timestamp(watermark_value),
            "formation_policy_version": self.policy_version,
            "membership_digest": sha256_digest(ordered),
        }
        lineage.latest_record = record
        self.result.revisions.append(record)

    def _emit_late(self, lineage: Lineage, event: dict[str, Any], reason: str) -> None:
        if lineage.latest_record is None or lineage.revision_deadline is None:
            raise ValueError("late evidence requires a finalized lineage")
        references = sort_references(
            self._event_reference(self.events[event_id], "membership")
            for event_id in lineage.latest_record["ordered_event_ids"]
        )
        record = {
            "object_type": "LateEvidenceRecord",
            "schema_version": "trustepisode.online.v1",
            "episode_id": lineage.episode_id,
            "latest_revision": lineage.latest_record["revision"],
            "latest_revision_digest": sha256_digest(lineage.latest_record),
            "event_id": event["event_id"],
            "arrival_time": event["ingest_time"],
            "revision_deadline": timestamp(lineage.revision_deadline),
            "reason": reason,
            "raw_pointer": event["raw_pointer"],
            "dependency_group": event["dependency_group"],
            "ordered_lineage_references": references,
            "versions": self.versions,
        }
        record["canonical_digest"] = digest_fields(record, LATE_DIGEST_FIELDS)
        self.result.late_records.append(record)

    @staticmethod
    def _event_reference(event: dict[str, Any], relation: str) -> dict[str, Any]:
        return {
            "reference_kind": "object",
            "raw_pointer": event["raw_pointer"],
            "dependency_group": event["dependency_group"],
            "relation": relation,
        }
