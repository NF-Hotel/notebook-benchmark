"""Run one streamed request and measure it (TTFT, total time, tokens, tokens/s)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from nfbench.application.ports import ChatBackend
from nfbench.domain.errors import BackendError
from nfbench.domain.metrics import compute_metrics
from nfbench.domain.models import ChatRequest, RunMetrics


@dataclass(frozen=True, slots=True)
class RawRun:
    """Outcome of one request: text and metrics, or an error message."""

    text: str
    metrics: RunMetrics
    error: str | None = None
    finish_reason: str | None = None


def run_request(
    backend: ChatBackend,
    request: ChatRequest,
    clock: Callable[[], float] = time.perf_counter,
) -> RawRun:
    """Stream ``request`` through ``backend``; backend failures become ``RawRun.error``.

    Reasoning text counts for TTFT and token throughput but is not part of ``text``.
    """
    start = clock()
    first: float | None = None
    text: list[str] = []
    chunks = 0
    completion_tokens: int | None = None
    prompt_tokens: int | None = None
    finish_reason: str | None = None
    error: str | None = None
    try:
        for chunk in backend.stream_chat(request):
            if chunk.completion_tokens is not None:
                completion_tokens = chunk.completion_tokens
            if chunk.prompt_tokens is not None:
                prompt_tokens = chunk.prompt_tokens
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
            if chunk.text:
                if first is None:
                    first = clock()
                chunks += 1
                if not chunk.is_reasoning:
                    text.append(chunk.text)
    except BackendError as exc:
        error = str(exc)
    end = clock()
    metrics = compute_metrics(start, first, end, completion_tokens, chunks, prompt_tokens)
    return RawRun("".join(text), metrics, error, finish_reason)
