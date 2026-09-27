"""Ollama and LM Studio both expose an OpenAI-compatible /v1 API; this adapter uses only that."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from nfbench.domain.errors import BackendError
from nfbench.domain.models import BackendStatus, ChatRequest, StreamChunk

OLLAMA_URL = "http://localhost:11434/v1"
LM_STUDIO_URL = "http://localhost:1234/v1"

_REASONING_KEYS = ("reasoning_content", "reasoning")


def parse_sse_line(line: str) -> list[StreamChunk]:
    """Decode one server-sent-events line into zero or more chunks.

    Raises ``BackendError`` when the stream carries an error object.
    """
    line = line.strip()
    if not line.startswith("data:") or line.endswith("[DONE]"):
        return []
    try:
        payload = json.loads(line[5:])
    except json.JSONDecodeError as exc:
        raise BackendError(f"malformed stream event: {line[:80]}") from exc
    if not isinstance(payload, dict):
        return []
    if "error" in payload:
        raise BackendError(f"server error: {payload['error']}")
    chunks: list[StreamChunk] = []
    usage = payload.get("usage")
    if isinstance(usage, dict):
        chunks.append(
            StreamChunk(
                completion_tokens=usage.get("completion_tokens"),
                prompt_tokens=usage.get("prompt_tokens"),
            )
        )
    for choice in payload.get("choices") or []:
        delta = choice.get("delta") or {}
        if choice.get("finish_reason"):
            chunks.append(StreamChunk(finish_reason=str(choice["finish_reason"])))
        if delta.get("content"):
            chunks.append(StreamChunk(text=delta["content"]))
        for key in _REASONING_KEYS:
            if delta.get(key):
                chunks.append(StreamChunk(text=delta[key], is_reasoning=True))
                break
    return chunks


def _chat_body(request: ChatRequest) -> dict[str, Any]:  # Any: JSON body
    messages: list[dict[str, str]] = []
    if request.system:
        messages.append({"role": "system", "content": request.system})
    messages.append({"role": "user", "content": request.prompt})
    return {
        "model": request.model,
        "stream": True,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "stream_options": {"include_usage": True},
        "messages": messages,
    }


@dataclass(frozen=True, slots=True)
class OpenAICompatibleBackend:
    """A local server speaking the OpenAI chat-completions protocol."""

    name: str
    base_url: str

    def check(self, timeout: float = 3.0) -> BackendStatus:
        """Connectivity and model list; failures are returned, never raised."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/models", timeout=timeout) as response:
                data = json.load(response)
            models = tuple(str(m["id"]) for m in data["data"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return BackendStatus(self.name, self.base_url, False, error=str(exc))
        return BackendStatus(self.name, self.base_url, True, models)

    def stream_chat(self, request: ChatRequest) -> Iterator[StreamChunk]:
        """Stream a completion; transport and HTTP errors raise ``BackendError``."""
        http_request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            json.dumps(_chat_body(request)).encode(),
            {"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(http_request, timeout=request.timeout_s) as response:
                for raw in response:
                    yield from parse_sse_line(raw.decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise BackendError(f"HTTP {exc.code}: {detail}") from exc
        except OSError as exc:  # URLError, timeouts, connection resets
            raise BackendError(f"{type(exc).__name__}: {exc}") from exc


def default_backends() -> dict[str, OpenAICompatibleBackend]:
    """The two supported local servers, keyed by name."""
    return {
        "ollama": OpenAICompatibleBackend("ollama", OLLAMA_URL),
        "lmstudio": OpenAICompatibleBackend("lmstudio", LM_STUDIO_URL),
    }
