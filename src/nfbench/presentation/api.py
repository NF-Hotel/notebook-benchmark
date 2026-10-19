"""HTTP API of the benchmark service (openapi/benchmark-contract.yaml, tag benchmark-service).

Controllers only: they check the token, turn JSON into a ``StartRunRequest`` or a ``RunStatus``
into JSON, and map domain errors to status codes. The rules live in ``RunService``.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import asdict
from typing import Any

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from nfbench.application.run_service import RunService
from nfbench.domain.errors import (
    InvalidRunRequestError,
    ModelNotInstalledError,
    QueueFullError,
    RunNotFoundError,
)
from nfbench.domain.service import RunStatus, StartRunRequest

RETRY_AFTER_S = 30
_BEARER = "Bearer "

Lifespan = Callable[[Starlette], AbstractAsyncContextManager[None]]


def _problem(status: int, code: str, message: str = "") -> JSONResponse:
    body: dict[str, str] = {"code": code}
    if message:
        body["message"] = message
    return JSONResponse(body, status_code=status)


def _authorized(request: Request, token: str) -> bool:
    header = request.headers.get("authorization", "")
    if not header.startswith(_BEARER) or not token:
        return False
    return hmac.compare_digest(header[len(_BEARER) :].encode(), token.encode())


def _status_json(status: RunStatus) -> dict[str, Any]:  # Any: JSON body
    body = asdict(status)
    body["models"] = list(status.models)
    return body


def _parse_start(body: object) -> StartRunRequest:
    """Strict reading of the body; anything that is not the contract is an invalid request."""
    if not isinstance(body, Mapping):
        raise InvalidRunRequestError("the body must be a JSON object")
    models = body.get("models")
    if not isinstance(models, list) or not all(isinstance(m, str) and m for m in models):
        raise InvalidRunRequestError("models must be a list of model names")
    hotel = body.get("hotel_analysis", True)
    tasks = body.get("deterministic_tasks", False)
    runs = body.get("runs", 1)
    if not isinstance(hotel, bool) or not isinstance(tasks, bool):
        raise InvalidRunRequestError("hotel_analysis and deterministic_tasks must be booleans")
    if not isinstance(runs, int) or isinstance(runs, bool):
        raise InvalidRunRequestError("runs must be an integer")
    return StartRunRequest(tuple(models), hotel, tasks, runs)


def create_app(service: RunService, token: str, lifespan: Lifespan | None = None) -> Starlette:
    """The ASGI application; ``/health`` is open, every other path needs the bearer token."""

    async def health(_: Request) -> Response:
        return JSONResponse({"status": "ok"})

    async def models(request: Request) -> Response:
        if not _authorized(request, token):
            return _problem(401, "unauthorized")
        installed = await run_in_threadpool(service.installed_models)
        return JSONResponse({"models": list(installed)})

    async def start_run(request: Request) -> Response:
        if not _authorized(request, token):
            return _problem(401, "unauthorized")
        try:
            run_request = _parse_start(await request.json())
            status = await run_in_threadpool(service.start, run_request)
        except ValueError:
            return _problem(400, "invalid_request", "the body is not valid JSON")
        except ModelNotInstalledError as error:
            return _problem(400, "model_not_installed", str(error))
        except InvalidRunRequestError as error:
            return _problem(400, "invalid_request", str(error))
        except QueueFullError as error:
            response = _problem(429, "queue_full", str(error))
            response.headers["Retry-After"] = str(RETRY_AFTER_S)
            return response
        return JSONResponse(_status_json(status), status_code=202)

    async def get_run(request: Request) -> Response:
        if not _authorized(request, token):
            return _problem(401, "unauthorized")
        try:
            status = await run_in_threadpool(service.status, request.path_params["run_id"])
        except RunNotFoundError:
            return _problem(404, "run_not_found")
        return JSONResponse(_status_json(status))

    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/models", models, methods=["GET"]),
        Route("/runs", start_run, methods=["POST"]),
        Route("/runs/{run_id}", get_run, methods=["GET"]),
    ]
    return Starlette(routes=routes, lifespan=lifespan)
