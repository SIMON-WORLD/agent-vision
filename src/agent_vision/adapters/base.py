"""Shared infrastructure for agent-specific adapters."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class AgentAdapter:
    """Base class for agent integration adapters."""

    id = "base"
    name = "Base"

    def detect(self) -> dict[str, object]:
        raise NotImplementedError

    def plan(self, **kwargs) -> dict[str, object]:
        raise NotImplementedError

    def apply(self, **kwargs) -> dict[str, object]:
        raise NotImplementedError

    def rollback(self) -> dict[str, object]:
        raise NotImplementedError

    @staticmethod
    def timestamp() -> str:
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    @staticmethod
    def unique_backup_path(path: Path, tag: str) -> Path:
        """Return a backup path that never overwrites an existing file."""
        stamp = AgentAdapter.timestamp()
        candidate = path.with_name(f"{path.name}.bak-{tag}-{stamp}")
        counter = 2
        while candidate.exists():
            candidate = path.with_name(f"{path.name}.bak-{tag}-{stamp}-{counter}")
            counter += 1
        return candidate

    @staticmethod
    def read_json(path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, data: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
