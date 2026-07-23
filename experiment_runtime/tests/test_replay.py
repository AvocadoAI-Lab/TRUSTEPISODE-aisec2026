from __future__ import annotations

from collections import Counter

from trustepisode_runtime.replay import generate_po1_cells, generate_replay_children


def test_replay_design_has_exact_41_deterministic_children(sample_stream) -> None:
    events, _ = sample_stream
    first = generate_replay_children("base-001", events)
    second = generate_replay_children("base-001", events)
    assert len(first) == 41
    assert [item.manifest(events) for item in first] == [item.manifest(events) for item in second]
    assert first[0].intervention_id == "RP0"
    assert first[0].events == sorted(
        first[0].events,
        key=lambda item: (item["event_time"], item["ingest_time"], item["source_instance"], item["event_id"]),
    )


def test_po1_has_40_balanced_locked_test_cells() -> None:
    cells = generate_po1_cells()
    assert len(cells) == 40
    assert Counter(item["allocated_card_id"] for item in cells) == {
        "M1": 10,
        "M3": 10,
        "M4": 10,
        "M7": 10,
    }
    assert all(item["partition"] == "locked_test" for item in cells)
    assert len({item["po1_cell_id"] for item in cells}) == 40
