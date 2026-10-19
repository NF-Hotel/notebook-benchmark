from __future__ import annotations

import json
from pathlib import Path

from nfbench.adapters.pending_store import FilePendingStore


def test_save_writes_the_result_as_a_file_before_anything_else(tmp_path: Path) -> None:
    store = FilePendingStore(tmp_path)

    store.save("r1", {"run_id": "r1", "results": [1]})

    assert json.loads((tmp_path / "pending" / "r1.json").read_text("utf-8")) == {
        "run_id": "r1", "results": [1],
    }  # fmt: skip


def test_pending_lists_saved_results_and_survives_a_new_instance(tmp_path: Path) -> None:
    FilePendingStore(tmp_path).save("r1", {"run_id": "r1"})
    FilePendingStore(tmp_path).save("r2", {"run_id": "r2"})

    pending = FilePendingStore(tmp_path).pending()

    assert sorted(run_id for run_id, _ in pending) == ["r1", "r2"]


def test_mark_delivered_moves_the_file_out_of_pending(tmp_path: Path) -> None:
    store = FilePendingStore(tmp_path)
    store.save("r1", {"run_id": "r1"})

    store.mark_delivered("r1")

    assert store.pending() == []
    assert (tmp_path / "delivered" / "r1.json").is_file()


def test_mark_failed_keeps_the_file_for_a_manual_send(tmp_path: Path) -> None:
    store = FilePendingStore(tmp_path)
    store.save("r1", {"run_id": "r1"})

    store.mark_failed("r1")

    assert store.pending() == []
    assert (tmp_path / "failed" / "r1.json").is_file()


def test_pending_skips_a_file_that_is_not_valid_json(tmp_path: Path) -> None:
    store = FilePendingStore(tmp_path)
    store.save("good", {"run_id": "good"})
    (tmp_path / "pending" / "bad.json").write_text("{oops", encoding="utf-8")

    assert [run_id for run_id, _ in store.pending()] == ["good"]


def test_pending_empty_folder_is_empty(tmp_path: Path) -> None:
    assert FilePendingStore(tmp_path / "nothing").pending() == []


def test_mark_delivered_unknown_run_does_nothing(tmp_path: Path) -> None:
    FilePendingStore(tmp_path).mark_delivered("ghost")
