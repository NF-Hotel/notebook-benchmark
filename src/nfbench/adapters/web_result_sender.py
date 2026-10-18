"""Post a finished result to the NFHotel web API (openapi/benchmark-contract.yaml)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from nfbench.adapters.http_types import UrlOpen
from nfbench.application.ports import Payload
from nfbench.domain.service import DeliveryOutcome

logger = logging.getLogger(__name__)

RESULTS_PATH = "/api/benchmark/results"
_RETRY_CODES = frozenset({408, 429})
_DELIVERED_CODES = frozenset({200, 201})


class WebResultSender:
    """One attempt per call; every failure is an outcome, never an exception."""

    def __init__(
        self,
        base_url: str,
        token: str,
        urlopen: UrlOpen = urllib.request.urlopen,
        timeout_s: float = 30.0,
    ) -> None:
        self._url = base_url.rstrip("/") + RESULTS_PATH
        self._token = token
        self._urlopen = urlopen
        self._timeout_s = timeout_s

    def send(self, payload: Payload) -> DeliveryOutcome:
        """201 or 200 = delivered; 4xx other than 408 and 429 = rejected; anything else = retry."""
        request = urllib.request.Request(  # noqa: S310 - the base URL comes from the env file
            self._url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
        )
        try:
            with self._urlopen(request, timeout=self._timeout_s) as response:
                status = int(response.status)
        except urllib.error.HTTPError as error:
            return _from_error_status(error.code)
        except (urllib.error.URLError, OSError) as error:
            logger.warning("the web API could not be reached: %s", error)
            return DeliveryOutcome.RETRY
        return DeliveryOutcome.DELIVERED if status in _DELIVERED_CODES else DeliveryOutcome.RETRY


def _from_error_status(code: int) -> DeliveryOutcome:
    if 400 <= code < 500 and code not in _RETRY_CODES:
        return DeliveryOutcome.REJECTED
    return DeliveryOutcome.RETRY
