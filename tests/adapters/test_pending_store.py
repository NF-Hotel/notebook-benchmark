from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_find_reads_a_result_wherever_it_is(tmp_path: Path) -> None:
    store = FilePendingStore(tmp_path)
    for run_id in ("r1", "r2", "r3"):
        store.save(run_id, {"run_id": run_id})
    store.mark_delivered("r2")
    store.mark_failed("r3")

    assert [store.find(run_id) for run_id in ("r1", "r2", "r3")] == [
        {"run_id": "r1"},
        {"run_id": "r2"},
        {"run_id": "r3"},
    ]


def test_find_returns_none_for_an_unknown_run(tmp_path: Path) -> None:
    assert FilePendingStore(tmp_path).find("ghost") is None


@pytest.mark.parametrize("run_id", ["../secret", "a/b", "a\\b", "", "x" * 65])
def test_find_refuses_an_id_that_could_name_another_file(tmp_path: Path, run_id: str) -> None:
    (tmp_path / "secret.json").write_text('{"leak": true}', encoding="utf-8")

    assert FilePendingStore(tmp_path / "data").find(run_id) is None
    assert FilePendingStore(tmp_path).find(run_id) is None


def test_find_skips_a_file_that_cannot_be_read(tmp_path: Path) -> None:
    store = FilePendingStore(tmp_path)
    (tmp_path / "pending").mkdir()
    (tmp_path / "pending" / "bad.json").write_text("{not json", encoding="utf-8")

    assert store.find("bad") is None
