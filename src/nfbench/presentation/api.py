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

from nfbench.application.model_service import ModelService
from nfbench.application.run_service import RunService
from nfbench.domain.errors import (
    BackendError,
    InvalidModelNameError,
    InvalidRunRequestError,
    ModelAlreadyInstalledError,
    ModelInUseError,
    ModelNotFoundError,
    ModelNotInstalledError,
    PullActiveError,
    PullNotFoundError,
    QueueFullError,
    ResultNotReadyError,
    RunNotFoundError,
)
from nfbench.domain.service import PullStatus, RunStatus, StartRunRequest

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


def _pull_json(status: PullStatus) -> dict[str, Any]:  # Any: JSON body
    return asdict(status)


def _parse_pull(body: object) -> str:
    """The model name of ``POST /models``; anything that is not the contract is an invalid name."""
    if not isinstance(body, Mapping) or not isinstance(body.get("name"), str):
        raise InvalidModelNameError("the body must be a JSON object with the string name")
    return str(body["name"])


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


def _model_routes(model_service: ModelService | None, token: str) -> list[Route]:
    """The routes that add, follow, list and delete models (ADR-0005, ADR-0006)."""

    async def start_pull(request: Request) -> Response:
        if not _authorized(request, token) or model_service is None:
            return _problem(401, "unauthorized")
        try:
            name = _parse_pull(await request.json())
            status = await run_in_threadpool(model_service.start_pull, name)
        except ValueError:
            return _problem(400, "invalid_request", "the body is not valid JSON")
        except InvalidModelNameError as error:
            return _problem(400, "invalid_model_name", str(error))
        except ModelAlreadyInstalledError as error:
            return _problem(409, "already_installed", str(error))
        except PullActiveError as error:
            return _problem(409, "pull_active", str(error))
        return JSONResponse(_pull_json(status), status_code=202)

    async def get_pull(request: Request) -> Response:
        if not _authorized(request, token) or model_service is None:
            return _problem(401, "unauthorized")
        try:
            status = await run_in_threadpool(
                model_service.pull_status, request.path_params["pull_id"]
            )
        except PullNotFoundError:
            return _problem(404, "pull_not_found")
        return JSONResponse(_pull_json(status))

    async def delete_model(request: Request) -> Response:
        if not _authorized(request, token) or model_service is None:
            return _problem(401, "unauthorized")
        try:
            await run_in_threadpool(model_service.delete, request.path_params["name"])
        except InvalidModelNameError as error:
            return _problem(400, "invalid_model_name", str(error))
        except ModelNotFoundError as error:
            return _problem(404, "model_not_found", str(error))
        except ModelInUseError as error:
            return _problem(409, "model_in_use", str(error))
        except BackendError as error:
            return _problem(502, "model_server_error", str(error))
        return Response(status_code=204)

    async def list_pulls(request: Request) -> Response:
        if not _authorized(request, token) or model_service is None:
            return _problem(401, "unauthorized")
        pulls = await run_in_threadpool(model_service.list_pulls)
        return JSONResponse({"pulls": [_pull_json(pull) for pull in pulls]})

    return [
        Route("/models", start_pull, methods=["POST"]),
        Route("/models/pulls", list_pulls, methods=["GET"]),
        Route("/models/pulls/{pull_id}", get_pull, methods=["GET"]),
        Route("/models/{name:path}", delete_model, methods=["DELETE"]),
    ]


def create_app(
    service: RunService,
    token: str,
    lifespan: Lifespan | None = None,
    model_service: ModelService | None = None,
) -> Starlette:
    """The ASGI application; ``/health`` is open, every other path needs the bearer token."""

    async def health(_: Request) -> Response:
        return JSONResponse({"status": "ok"})

    async def models(request: Request) -> Response:
        if not _authorized(request, token):
            return _problem(401, "unauthorized")
        installed = await run_in_threadpool(service.installed_models)
        return JSONResponse({"models": list(installed)})

    async def list_runs(request: Request) -> Response:
        if not _authorized(request, token):
            return _problem(401, "unauthorized")
        runs = await run_in_threadpool(service.list_runs)
        return JSONResponse({"runs": [_status_json(run) for run in runs]})

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

    async def get_summaries(request: Request) -> Response:
        if not _authorized(request, token):
            return _problem(401, "unauthorized")
        run_text = request.query_params.get("run")
        run: int | None = None
        if run_text is not None:
            if not run_text.isdecimal():
                return _problem(400, "invalid_request", "run must be a whole number from 0")
            run = int(run_text)
        try:
            comparison = await run_in_threadpool(
                service.summaries, request.path_params["run_id"], run
            )
        except RunNotFoundError:
            return _problem(404, "run_not_found")
        except ResultNotReadyError:
            return _problem(409, "result_not_ready", "the run has no result yet")
        return JSONResponse(comparison.to_dict())

    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/models", models, methods=["GET"]),
        *_model_routes(model_service, token),
        Route("/runs", start_run, methods=["POST"]),
        Route("/runs", list_runs, methods=["GET"]),
        Route("/runs/{run_id}", get_run, methods=["GET"]),
        Route("/runs/{run_id}/summaries", get_summaries, methods=["GET"]),
    ]
    return Starlette(routes=routes, lifespan=lifespan)
