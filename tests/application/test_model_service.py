from __future__ import annotations

from collections.abc import Callable

import pytest

from nfbench.application.model_service import ModelService
from nfbench.domain.errors import (
    BackendError,
    InvalidModelNameError,
    ModelAlreadyInstalledError,
    ModelInUseError,
    ModelNotFoundError,
    PullActiveError,
    PullNotFoundError,
)
from nfbench.domain.service import MAX_KEPT_PULLS, PullState
from tests.service_fakes import FakeCatalog, FakeGuard, FakeModelAdmin


class _Parts:
    """A model service whose pulls wait in ``pending`` until the test runs them."""

    def __init__(self, *installed: str, guard: FakeGuard | None = None) -> None:
        self.catalog = FakeCatalog(*installed)
        self.admin = FakeModelAdmin(self.catalog)
        self.guard = guard or FakeGuard()
        self.pending: list[Callable[[], None]] = []
        ids = iter(f"pull-{n}" for n in range(1, 1000))
        self.service = ModelService(
            self.catalog,
            self.admin,
            self.guard,
            start=self.pending.append,
            new_id=lambda: next(ids),
        )

    def run_pending(self) -> None:
        while self.pending:
            self.pending.pop(0)()


def test_start_pull_returns_a_queued_pull_at_once() -> None:
    parts = _Parts("m1:latest")

    status = parts.service.start_pull("phi4-mini")

    assert (status.pull_id, status.model, status.state) == ("pull-1", "phi4-mini", PullState.QUEUED)
    assert status.percent is None
    assert parts.admin.pulled == []  # nothing ran yet: the API did not wait for the pull


def test_start_pull_trims_the_name() -> None:
    parts = _Parts()

    assert parts.service.start_pull("  phi4-mini:latest ").model == "phi4-mini:latest"


def test_a_pull_that_succeeds_ends_done_with_a_hundred_percent_and_the_model_is_listed() -> None:
    parts = _Parts()
    status = parts.service.start_pull("phi4-mini")

    parts.run_pending()

    done = parts.service.pull_status(status.pull_id)
    assert (done.state, done.percent, done.error) == (PullState.DONE, 100, None)
    assert "phi4-mini" in parts.catalog.installed_models()


def test_a_pull_that_fails_ends_failed_with_the_reason_and_lists_no_model() -> None:
    parts = _Parts()
    parts.admin.fail_with = "pull model manifest: file does not exist"
    parts.admin.progress_before_failing = 40
    status = parts.service.start_pull("no-such-model")

    parts.run_pending()

    failed = parts.service.pull_status(status.pull_id)
    assert failed.state is PullState.FAILED
    assert failed.error == "pull model manifest: file does not exist"
    assert failed.percent == 40
    assert "no-such-model" not in parts.catalog.installed_models()


def test_a_defect_in_a_pull_ends_it_failed_and_does_not_leave_it_pulling() -> None:
    parts = _Parts()
    parts.admin.defect = RuntimeError("boom")
    status = parts.service.start_pull("phi4-mini")

    parts.run_pending()

    failed = parts.service.pull_status(status.pull_id)
    assert failed.state is PullState.FAILED
    assert "boom" in (failed.error or "")


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
        "../etc/passwd",
        "a b",
        "a;b",
        "a/b/c/d",
        "x" * 101,
        "-start",
        "name:",
        ":tag",
        "a//b",
    ],
)
def test_start_pull_a_name_that_is_not_an_ollama_model_name_is_refused(name: str) -> None:
    parts = _Parts()

    with pytest.raises(InvalidModelNameError):
        parts.service.start_pull(name)

    assert parts.pending == []


@pytest.mark.parametrize(
    "name", ["phi4-mini", "llama3.2:3b", "hf.co/user/model:Q4_K_M", "library/gemma2:9b", "x" * 100]
)
def test_start_pull_valid_names_are_accepted(name: str) -> None:
    assert _Parts().service.start_pull(name).model == name


def test_start_pull_installed_model_is_refused_with_or_without_the_tag() -> None:
    parts = _Parts("phi3.5:latest", "llama3.2:3b")

    with pytest.raises(ModelAlreadyInstalledError):
        parts.service.start_pull("phi3.5")
    with pytest.raises(ModelAlreadyInstalledError):
        parts.service.start_pull("llama3.2:3b")


def test_start_pull_a_tag_that_is_not_installed_is_accepted_when_another_tag_is() -> None:
    parts = _Parts("llama3.2:3b")

    assert parts.service.start_pull("llama3.2:1b").state is PullState.QUEUED


def test_start_pull_second_pull_while_one_is_queued_is_refused() -> None:
    parts = _Parts()
    parts.service.start_pull("phi4-mini")

    with pytest.raises(PullActiveError):
        parts.service.start_pull("qwen2.5:7b")


def test_start_pull_after_the_first_ended_a_new_pull_is_accepted() -> None:
    parts = _Parts()
    parts.service.start_pull("phi4-mini")
    parts.run_pending()

    assert parts.service.start_pull("qwen2.5:7b").state is PullState.QUEUED


def test_start_pull_after_a_failed_pull_a_new_pull_is_accepted() -> None:
    parts = _Parts()
    parts.admin.fail_with = "disk full"
    parts.service.start_pull("phi4-mini")
    parts.run_pending()
    parts.admin.fail_with = None

    assert parts.service.start_pull("phi4-mini").state is PullState.QUEUED


def test_pull_status_unknown_id_raises_not_found() -> None:
    with pytest.raises(PullNotFoundError):
        _Parts().service.pull_status("nope")


def test_only_the_last_twenty_pulls_are_kept() -> None:
    parts = _Parts()
    for n in range(MAX_KEPT_PULLS + 1):
        parts.service.start_pull(f"model-{n}")
        parts.run_pending()

    with pytest.raises(PullNotFoundError):
        parts.service.pull_status("pull-1")
    assert parts.service.pull_status(f"pull-{MAX_KEPT_PULLS + 1}").state is PullState.DONE


def test_delete_an_installed_model_deletes_it_through_the_guard() -> None:
    parts = _Parts("phi3.5:latest", "llama3.2:3b")

    parts.service.delete("llama3.2:3b")

    assert parts.admin.deleted == ["llama3.2:3b"]
    assert parts.catalog.installed_models() == ("phi3.5:latest",)
    assert parts.guard.checked == ["llama3.2:3b"]


def test_delete_a_name_without_a_tag_deletes_the_latest_tag() -> None:
    parts = _Parts("phi3.5:latest")

    parts.service.delete("phi3.5")

    assert parts.admin.deleted == ["phi3.5:latest"]


def test_delete_a_model_that_is_not_installed_raises_not_found_and_deletes_nothing() -> None:
    parts = _Parts("llama3.2:3b")

    with pytest.raises(ModelNotFoundError):
        parts.service.delete("phi4-mini")

    assert parts.admin.deleted == []


def test_delete_a_model_that_a_run_uses_is_refused_and_stays_installed() -> None:
    parts = _Parts("llama3.2:3b", guard=FakeGuard(in_use={"llama3.2:3b"}))

    with pytest.raises(ModelInUseError):
        parts.service.delete("llama3.2:3b")

    assert parts.admin.deleted == []
    assert parts.catalog.installed_models() == ("llama3.2:3b",)


def test_delete_when_the_server_says_not_installed_raises_not_found() -> None:
    parts = _Parts("llama3.2:3b")
    parts.admin.delete_result = False

    with pytest.raises(ModelNotFoundError):
        parts.service.delete("llama3.2:3b")


def test_delete_a_backend_error_is_passed_on() -> None:
    parts = _Parts("llama3.2:3b")
    parts.admin.delete_error = BackendError("Ollama could not be reached")

    with pytest.raises(BackendError):
        parts.service.delete("llama3.2:3b")


@pytest.mark.parametrize("name", ["", "../x", "a b", "x" * 101])
def test_delete_an_invalid_name_is_refused(name: str) -> None:
    with pytest.raises(InvalidModelNameError):
        _Parts("llama3.2:3b").service.delete(name)
