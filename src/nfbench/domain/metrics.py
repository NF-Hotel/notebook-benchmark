"""Pure metric arithmetic for one streamed LLM request."""

from __future__ import annotations

from nfbench.domain.models import RunMetrics


def compute_metrics(
    start: float,
    first_token: float | None,
    end: float,
    api_completion_tokens: int | None,
    streamed_chunks: int,
    prompt_tokens: int | None = None,
) -> RunMetrics:
    """Derive TTFT, total time and tokens/s from timestamps (seconds) and token counts.

    Completion tokens come from the server's usage report; when it is missing the number of
    streamed chunks is used and ``tokens_estimated`` is set.
    tokens/s = completion tokens / (end - first_token); None without a first token or when
    the generation time is not positive.
    """
    estimated = api_completion_tokens is None
    tokens = streamed_chunks if api_completion_tokens is None else api_completion_tokens
    ttft = None if first_token is None else first_token - start
    generation = None if first_token is None else end - first_token
    tps = tokens / generation if generation is not None and generation > 0 and tokens > 0 else None
    return RunMetrics(
        ttft_s=ttft,
        total_s=end - start,
        completion_tokens=tokens,
        prompt_tokens=prompt_tokens,
        tokens_per_s=tps,
        tokens_estimated=estimated,
    )
