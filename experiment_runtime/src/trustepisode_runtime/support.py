from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .canonical import parse_timestamp, sha256_digest, sort_references, utf8_key


HEALTH_PRECEDENCE = {
    "healthy": 0,
    "degraded": 1,
    "not_applicable": 2,
    "down": 3,
    "unknown": 4,
}

COVERAGE_SELECTION_POINT = "EpisodeRevision.event_time_end"
COVERING_INTERVAL_CARDINALITY = (
    "exactly one content-distinct SourceCoverage interval for every expected source "
    "instance at the selection point; zero or multiple maps the family to unknown"
)


def support_contract_metadata(thresholds: dict[str, Any]) -> dict[str, str]:
    """Bind support semantics even when descriptive keys are omitted from the contract."""
    resolution = thresholds["detector_availability_resolution"]
    return {
        "coverage_selection_point": resolution.get(
            "coverage_selection_point", COVERAGE_SELECTION_POINT
        ),
        "covering_interval_cardinality": resolution.get(
            "covering_interval_cardinality", COVERING_INTERVAL_CARDINALITY
        ),
    }


@dataclass
class FamilyCoverage:
    family: str
    health: str
    parser_valid: bool
    transport_live: bool
    observed_lag_seconds: float
    reference_id: str
    references: list[dict[str, Any]]
    records: list[dict[str, Any]]
    missing_or_conflicting: bool


@dataclass
class SupportResolution:
    decision: dict[str, Any]
    health_snapshot: dict[str, str]
    family_coverage: dict[str, FamilyCoverage]


class SupportResolver:
    version = "trustepisode.support.v1"

    def __init__(
        self,
        *,
        expected_instances: dict[str, list[str]],
        support_manifest_digest: str,
        enabled_group_keys: Iterable[str] = (),
    ) -> None:
        self.expected_instances = {
            family: tuple(sorted(expected_instances[family], key=utf8_key))
            for family in ("EDR", "NDR")
        }
        self.support_manifest_digest = support_manifest_digest
        self.enabled_group_keys = frozenset(enabled_group_keys)

    def resolve(
        self,
        revision: dict[str, Any],
        feature: dict[str, Any],
        coverage_records: Iterable[dict[str, Any]],
        *,
        group_key: str | None = None,
        versions_match: bool = True,
        calibration_available: bool = True,
    ) -> SupportResolution:
        point = parse_timestamp(revision["event_time_end"])
        records = list(coverage_records)
        families = {
            family: self._resolve_family(family, point, records)
            for family in ("EDR", "NDR")
        }
        resolved_state = {
            family: self._detector_state(
                families[family], feature["detector_observation"][family]
            )
            for family in ("EDR", "NDR")
        }
        eligible_count = int(feature["eligible_detector_count"])
        kappa = "out_of_support"
        selected_group: str | None = None
        reason = "source_out_of_support"

        if eligible_count == 0:
            reason = "no_eligible_detector_value"
        elif not versions_match:
            reason = "version_out_of_support"
        elif feature["source_mask"] != {"EDR": 1, "NDR": 1}:
            reason = "source_out_of_support"
        elif any(not families[item].parser_valid for item in ("EDR", "NDR")):
            reason = "parser_out_of_support"
        elif any(
            families[item].health in {"down", "unknown", "not_applicable"}
            or families[item].missing_or_conflicting
            for item in ("EDR", "NDR")
        ):
            reason = "source_out_of_support"
        elif not calibration_available:
            reason = "calibration_out_of_support"
        elif any(item in {"unknown", "collector_unavailable"} for item in resolved_state.values()):
            reason = "source_out_of_support"
        elif any(item == "parser_invalid" for item in resolved_state.values()):
            reason = "parser_out_of_support"
        else:
            reason = "eligible"
            if group_key is not None and group_key in self.enabled_group_keys:
                kappa = "supported_group"
                selected_group = group_key
            else:
                kappa = "supported_global"

        decision_eligible = eligible_count > 0 and kappa in {
            "supported_global",
            "supported_group",
        }
        snapshot_payload = {
            family: {
                "coverage_ref_id": families[family].reference_id,
                "health": families[family].health,
                "parser_valid": families[family].parser_valid,
                "lag": families[family].observed_lag_seconds,
            }
            for family in ("EDR", "NDR")
        }
        decision = {
            "object_type": "SupportDecision",
            "schema_version": "trustepisode.online.v1",
            "episode_id": revision["episode_id"],
            "revision": revision["revision"],
            "resolved_detector_state": resolved_state,
            "eligible_detector_count": eligible_count,
            "eligibility_reason": reason,
            "kappa": kappa,
            "calibration_group_key": selected_group,
            "decision_eligible": decision_eligible,
            "support_manifest_digest": self.support_manifest_digest,
            "coverage_ref_ids": {
                family: families[family].reference_id for family in ("EDR", "NDR")
            },
            "health_snapshot_digest": sha256_digest(snapshot_payload),
            "ordered_coverage_references": sort_references(
                reference
                for family in ("EDR", "NDR")
                for reference in families[family].references
            ),
        }
        return SupportResolution(
            decision=decision,
            health_snapshot={family: families[family].health for family in ("EDR", "NDR")},
            family_coverage=families,
        )

    def _resolve_family(
        self,
        family: str,
        point,
        records: list[dict[str, Any]],
    ) -> FamilyCoverage:
        selected: list[dict[str, Any]] = []
        references: list[dict[str, Any]] = []
        missing_or_conflicting = False
        for instance in self.expected_instances[family]:
            covering = [
                record
                for record in records
                if record["source_family"] == family
                and record["source_instance"] == instance
                and parse_timestamp(record["interval_start"]) <= point < parse_timestamp(record["interval_end"])
            ]
            unique = {sha256_digest(item): item for item in covering}
            if len(unique) != 1:
                missing_or_conflicting = True
                references.append(
                    {
                        "reference_kind": "sentinel",
                        "relation": "health",
                        "dependency_group": f"coverage:{family}:{instance}",
                        "sentinel_reason": "not_observed" if not unique else "unresolved_optional",
                        "expected_object_id": f"coverage:{family}:{instance}",
                    }
                )
                continue
            record_digest, record = next(iter(unique.items()))
            selected.append(record)
            references.append(
                {
                    "reference_kind": "object",
                    "raw_pointer": {
                        "object_id": f"coverage-object:{record_digest.split(':', 1)[1]}",
                        "content_digest": record_digest,
                        "locator": f"coverage:{family}:{instance}:{record['interval_start']}",
                        "storage_schema_version": "trustepisode.online.v1",
                    },
                    "dependency_group": f"coverage:{family}:{instance}",
                    "relation": "health",
                }
            )

        if missing_or_conflicting or len(selected) != len(self.expected_instances[family]):
            health = "unknown"
            parser_valid = False
            transport_live = False
            lag = max((float(item["observed_lag_seconds"]) for item in selected), default=0.0)
        else:
            health = max(
                (str(item["health"]) for item in selected),
                key=lambda item: HEALTH_PRECEDENCE[item],
            )
            parser_valid = all(bool(item["parser_valid"]) for item in selected)
            transport_live = all(bool(item["transport_live"]) for item in selected)
            lag = max(float(item["observed_lag_seconds"]) for item in selected)
        reference_id = "coverage:" + family + ":" + sha256_digest(
            {
                "family": family,
                "instances": list(self.expected_instances[family]),
                "records": [sha256_digest(item) for item in selected],
                "missing_or_conflicting": missing_or_conflicting,
            }
        ).split(":", 1)[1]
        return FamilyCoverage(
            family=family,
            health=health,
            parser_valid=parser_valid,
            transport_live=transport_live,
            observed_lag_seconds=lag,
            reference_id=reference_id,
            references=references,
            records=selected,
            missing_or_conflicting=missing_or_conflicting,
        )

    @staticmethod
    def _detector_state(coverage: FamilyCoverage, observation: str) -> str:
        if coverage.missing_or_conflicting:
            return "unknown"
        if coverage.health in {"down", "not_applicable"} or not coverage.transport_live:
            return "collector_unavailable"
        if not coverage.parser_valid:
            return "parser_invalid"
        if coverage.health == "unknown" or observation == "not_examined":
            return "unknown"
        if observation == "detected":
            return "available"
        if observation == "examined_none":
            return "no_detection"
        return "unknown"
