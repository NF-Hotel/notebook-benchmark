"""Results that are not yet in the web database, kept as JSON files on a volume."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from nfbench.application.ports import Payload

logger = logging.getLogger(__name__)


class FilePendingStore:
    """``pending/<run_id>.json`` until delivered (``delivered/``) or given up (``failed/``)."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, run_id: str, payload: Payload) -> None:
        """Write the result; the file is complete before the first attempt to send it."""
        folder = self._root / "pending"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{run_id}.json"
        partial = folder / f"{run_id}.json.part"
        partial.write_text(json.dumps(payload), encoding="utf-8")
        partial.replace(target)

    def pending(self) -> list[tuple[str, Payload]]:
        """Every readable result that is neither delivered nor failed."""
        folder = self._root / "pending"
        found: list[tuple[str, Payload]] = []
        for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
            try:
                found.append((path.stem, json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError):
                logger.warning("unreadable pending result %s skipped", path.name)
        return found

    def mark_delivered(self, run_id: str) -> None:
        """The web API has the result."""
        self._move(run_id, "delivered")

    def mark_failed(self, run_id: str) -> None:
        """Give up; the file stays for a manual send."""
        self._move(run_id, "failed")

    def _move(self, run_id: str, folder: str) -> None:
        source = self._root / "pending" / f"{run_id}.json"
        if not source.is_file():
            return
        target = self._root / folder
        target.mkdir(parents=True, exist_ok=True)
        source.replace(target / source.name)
