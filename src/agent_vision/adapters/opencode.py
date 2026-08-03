"""OpenCode adapter: detect, backup, patch, apply and roll back opencode.json."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from ..version import VERSION
from .base import AgentAdapter

PROVIDER_ID = "agent-vision"
PROVIDER_NAME = "Agent Vision Bridge"
PROXY_BASE_URL = "http://127.0.0.1:19100/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
CONFIG_SCHEMA = "https://opencode.ai/config.json"


class OpenCodeAdapter(AgentAdapter):
    id = "opencode"
    name = "OpenCode"

    def __init__(
        self,
        config_path: Path | None = None,
        home: Path | None = None,
        appdata: str | None = None,
    ):
        self.home = Path(home) if home is not None else Path.home()
        appdata = os.environ.get("APPDATA") if appdata is None else appdata
        if config_path is not None:
            self.config_path = Path(config_path)
        else:
            candidates = [self.home / ".config" / "opencode" / "opencode.json"]
            if appdata:
                candidates.append(Path(appdata) / "opencode" / "opencode.json")
            self.config_path = next((path for path in candidates if path.exists()), candidates[0])
        self.state_path = self.config_path.with_name(".agent-vision-state.json")

    def _opencode_in_path(self) -> bool:
        return shutil.which("opencode") is not None

    def _read_config(self) -> dict[str, object]:
        if not self.config_path.exists():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _provider_table(data: dict[str, object]) -> dict[str, dict[str, object]]:
        raw = data.get("provider")
        return raw if isinstance(raw, dict) else {}

    def _current_model(self) -> str:
        return str(self._read_config().get("model") or "")

    def _active_provider_base_url(self) -> str:
        config = self._read_config()
        providers = self._provider_table(config)
        model = self._current_model()
        active_id = model.split("/", 1)[0] if "/" in model else ""

        def base_url_of(provider_id: str) -> str:
            provider = providers.get(provider_id)
            if not isinstance(provider, dict):
                return ""
            options = provider.get("options")
            if not isinstance(options, dict):
                return ""
            return str(options.get("baseURL") or "")

        if active_id and active_id in providers:
            candidate = base_url_of(active_id)
            if candidate and "127.0.0.1" not in candidate and "localhost" not in candidate:
                return candidate
        for provider_id, provider in providers.items():
            if provider_id == PROVIDER_ID or not isinstance(provider, dict):
                continue
            candidate = base_url_of(provider_id)
            if candidate and "127.0.0.1" not in candidate and "localhost" not in candidate:
                return candidate
        return ""

    def detect(self) -> dict[str, object]:
        config = self._read_config()
        config_exists = self.config_path.exists()
        providers = self._provider_table(config)
        provider = providers.get(PROVIDER_ID)
        base_url = ""
        if isinstance(provider, dict):
            options = provider.get("options")
            if isinstance(options, dict):
                base_url = str(options.get("baseURL") or "")
        state = self.read_json(self.state_path)
        return {
            "agent": self.id,
            "name": self.name,
            "installed": config_exists or self._opencode_in_path(),
            "config_path": str(self.config_path),
            "config_exists": config_exists,
            "model": self._current_model(),
            "base_url": base_url,
            "patched": bool(state),
            "backup_path": str(state.get("backup_path", "")) if state else "",
            "upstream": str(state.get("upstream", "")) if state else "",
        }

    def backup(self) -> Path:
        if not self.config_path.exists():
            raise FileNotFoundError(f"OpenCode config not found: {self.config_path}")
        backup_path = self.unique_backup_path(self.config_path, "agent-vision")
        backup_path.write_text(self.config_path.read_text(encoding="utf-8"), encoding="utf-8")
        return backup_path

    def _detected_upstream(self, explicit: str | None) -> str:
        if explicit:
            return explicit.strip()
        candidate = self._active_provider_base_url()
        return candidate if candidate and "127.0.0.1" not in candidate and "localhost" not in candidate else ""

    @classmethod
    def render_patched_config(
        cls,
        data: dict[str, object] | None = None,
        *,
        provider_id: str = PROVIDER_ID,
        base_url: str = PROXY_BASE_URL,
        name: str = PROVIDER_NAME,
        model: str = "",
    ) -> dict[str, object]:
        """Return opencode.json content with the agent-vision provider wired in."""
        config = dict(data or {})
        providers = cls._provider_table(config)
        providers = {key: value for key, value in providers.items()}
        model_id = model or DEFAULT_MODEL
        model_name = model_id.rsplit("/", 1)[-1] or DEFAULT_MODEL
        providers[provider_id] = {
            "npm": "@ai-sdk/openai-compatible",
            "name": name,
            "options": {"baseURL": base_url},
            "models": {model_name: {"name": model_name}},
        }
        config["provider"] = providers
        config["model"] = f"{provider_id}/{model_name}"
        if "$schema" not in config:
            config["$schema"] = CONFIG_SCHEMA
        return config

    def plan(self, upstream: str | None = None) -> dict[str, object]:
        detection = self.detect()
        resolved_upstream = self._detected_upstream(upstream)
        backup_path = self.unique_backup_path(self.config_path, "agent-vision")
        files = [
            {
                "file": str(self.config_path),
                "action": "modify",
                "backup": str(backup_path),
                "summary": (
                    f'add provider "{PROVIDER_ID}" (npm @ai-sdk/openai-compatible, '
                    f'baseURL "{PROXY_BASE_URL}") and set model to agent-vision'
                ),
            },
            {
                "file": str(self.state_path),
                "action": "write",
                "summary": "write agent-vision state: backup path, provider, upstream",
            },
        ]
        return {
            "agent": self.id,
            "detection": detection,
            "files": files,
            "upstream": resolved_upstream,
        }

    def apply(self, upstream: str | None = None) -> dict[str, object]:
        detection = self.detect()
        if not detection["config_exists"]:
            raise FileNotFoundError(f"OpenCode config not found: {self.config_path}")
        resolved_upstream = self._detected_upstream(upstream)
        backup_path = self.backup()
        original = self._read_config()
        patched = self.render_patched_config(original, model=str(detection["model"]))
        self.config_path.write_text(
            json.dumps(patched, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.write_json(
            self.state_path,
            {
                "agent": self.id,
                "version": VERSION,
                "config_path": str(self.config_path),
                "backup_path": str(backup_path),
                "model": str(detection["model"]),
                "model_provider": PROVIDER_ID,
                "upstream": resolved_upstream,
                "patched_at": self.timestamp(),
            },
        )
        return {
            "agent": self.id,
            "config_path": str(self.config_path),
            "backup_path": str(backup_path),
            "state_path": str(self.state_path),
            "upstream": resolved_upstream,
            "model": str(detection["model"]),
        }

    def rollback(self) -> dict[str, object]:
        state = self.read_json(self.state_path)
        if not state:
            raise FileNotFoundError("no agent-vision patch found for OpenCode")
        backup_path = Path(str(state["backup_path"]))
        if not backup_path.exists():
            raise FileNotFoundError(f"backup missing: {backup_path}")
        self.config_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
        self.state_path.unlink(missing_ok=True)
        return {
            "agent": self.id,
            "config_path": str(self.config_path),
            "restored_from": str(backup_path),
            "state_path": str(self.state_path),
        }
