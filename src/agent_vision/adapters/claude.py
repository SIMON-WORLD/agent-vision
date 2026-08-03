"""Claude Code adapter: detect config and guide protocol-compatible setup.

Claude Code speaks the Anthropic Messages API, while the bundled proxy
speaks OpenAI chat completions. Auto-patching ANTHROPIC_BASE_URL to the
bundled proxy would break Claude Code, so this adapter detects the local
configuration and provides exact manual steps instead of writing a config
that cannot work.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .base import AgentAdapter


class ClaudeAdapter(AgentAdapter):
    id = "claude"
    name = "Claude Code"

    def __init__(self, config_path: Path | None = None, home: Path | None = None):
        self.home = Path(home) if home is not None else Path.home()
        self.config_path = Path(config_path) if config_path is not None else self.home / ".claude" / "settings.json"
        self.state_path = self.config_path.with_name(".agent-vision-state.json")

    def _claude_in_path(self) -> bool:
        return shutil.which("claude") is not None

    def _read_settings(self) -> dict[str, object]:
        if not self.config_path.exists():
            return {}
        try:
            import json

            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def detect(self) -> dict[str, object]:
        settings = self._read_settings()
        env = settings.get("env")
        env = env if isinstance(env, dict) else {}
        config_exists = self.config_path.exists()
        state = self.read_json(self.state_path)
        return {
            "agent": self.id,
            "name": self.name,
            "installed": config_exists or self._claude_in_path(),
            "config_path": str(self.config_path),
            "config_exists": config_exists,
            "model": "",
            "model_provider": "",
            "base_url": str(env.get("ANTHROPIC_BASE_URL") or ""),
            "patched": bool(state),
            "backup_path": str(state.get("backup_path", "")) if state else "",
            "upstream": str(state.get("upstream", "")) if state else "",
        }

    @staticmethod
    def manual_steps() -> list[str]:
        return [
            "Claude Code speaks the Anthropic Messages API; the bundled proxy speaks OpenAI chat completions.",
            "Point Claude Code at an Anthropic-compatible gateway or a protocol-converting router.",
            "When using a compatible gateway, add or update the env block in ~/.claude/settings.json:",
            '  "env": {"ANTHROPIC_BASE_URL": "<gateway-url>", "ANTHROPIC_AUTH_TOKEN": "<your-key>"}',
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
            "Claude Code uses the Anthropic protocol; agent-vision does not auto-patch Claude settings. "
            "Run `agent-vision setup --agent claude --dry-run` for the manual steps."
        )

    def rollback(self) -> dict[str, object]:
        raise FileNotFoundError("agent-vision does not patch Claude Code settings; nothing to roll back")
