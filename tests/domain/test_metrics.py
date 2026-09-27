from __future__ import annotations

import pytest

from nfbench.domain.metrics import compute_metrics


def test_compute_metrics_uses_api_token_count() -> None:
    m = compute_metrics(10.0, 10.5, 12.5, api_completion_tokens=100, streamed_chunks=7)
    assert m.ttft_s == pytest.approx(0.5)
    assert m.total_s == pytest.approx(2.5)
    assert m.completion_tokens == 100
    assert m.tokens_per_s == pytest.approx(50.0)  # 100 tokens / 2.0 s generation
    assert m.tokens_estimated is False


def test_compute_metrics_falls_back_to_chunk_count_when_usage_missing() -> None:
    m = compute_metrics(0.0, 1.0, 3.0, api_completion_tokens=None, streamed_chunks=20)
    assert m.completion_tokens == 20
    assert m.tokens_estimated is True
    assert m.tokens_per_s == pytest.approx(10.0)


def test_compute_metrics_without_first_token_has_no_ttft_or_rate() -> None:
    m = compute_metrics(0.0, None, 1.0, api_completion_tokens=None, streamed_chunks=0)
    assert m.ttft_s is None
    assert m.tokens_per_s is None
    assert m.total_s == pytest.approx(1.0)


def test_compute_metrics_zero_generation_time_gives_no_rate() -> None:
    m = compute_metrics(0.0, 1.0, 1.0, api_completion_tokens=5, streamed_chunks=5)
    assert m.tokens_per_s is None
