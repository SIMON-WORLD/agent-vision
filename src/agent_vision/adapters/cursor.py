"""Cursor adapter: detect config and guide the official base URL override.

Cursor exposes the OpenAI base URL override through its Settings UI, not a
stable public JSON key. Writing unknown keys into Cursor's internal state
could corrupt it, so this adapter detects the local installation and gives
exact manual steps instead of guessing at private config fields.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from .base import AgentAdapter

PROXY_BASE_URL = "http://127.0.0.1:19100/v1"


class CursorAdapter(AgentAdapter):
    id = "cursor"
    name = "Cursor"

    def __init__(self, config_dir: Path | None = None, home: Path | None = None, appdata: str | None = None):
        self.home = Path(home) if home is not None else Path.home()
        appdata = os.environ.get("APPDATA") if appdata is None else appdata
        if config_dir is not None:
            self.config_dir = Path(config_dir)
        else:
            candidates = [Path(appdata) / "Cursor" if appdata else None, self.home / ".config" / "Cursor"]
            candidates = [path for path in candidates if path is not None]
            self.config_dir = next((path for path in candidates if path.exists()), candidates[0])
        self.state_path = self.config_dir / ".agent-vision-state.json"

    def _cursor_in_path(self) -> bool:
        return shutil.which("cursor") is not None

    def detect(self) -> dict[str, object]:
        config_dir_exists = self.config_dir.exists()
        state = self.read_json(self.state_path)
        return {
            "agent": self.id,
            "name": self.name,
            "installed": config_dir_exists or self._cursor_in_path(),
            "config_path": str(self.config_dir),
            "config_exists": config_dir_exists,
            "model": "",
            "model_provider": "",
            "base_url": "",
            "patched": bool(state),
            "backup_path": str(state.get("backup_path", "")) if state else "",
            "upstream": str(state.get("upstream", "")) if state else "",
        }

    @staticmethod
    def manual_steps() -> list[str]:
        return [
            "Cursor has no stable public config key for the OpenAI base URL override.",
            "Open Cursor -> Settings -> Models and enable Override OpenAI Base URL.",
            f"Set the base URL to {PROXY_BASE_URL} (the local agent-vision proxy).",
            "Keep the model set to your text-only model, for example deepseek-v4-flash.",
        ]

    def plan(self, upstream: str | None = None) -> dict[str, object]:
        return {
            "agent": self.id,
            "detection": self.detect(),
            "files": [],
            "manual_steps": self.manual_steps(),
            "upstream": "",
        }

    def apply(self, upstream: str | None = None) -> dict[str, object]:
        raise NotImplementedError(
            "Cursor has no stable public config key; agent-vision does not auto-patch Cursor internals. "
            "Run `agent-vision setup --agent cursor --dry-run` for the manual steps."
        )

    def rollback(self) -> dict[str, object]:
        raise FileNotFoundError("agent-vision does not patch Cursor config; nothing to roll back")
