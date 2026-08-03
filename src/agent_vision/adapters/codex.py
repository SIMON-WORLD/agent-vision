"""Codex adapter: detect, backup, patch, apply and roll back config.toml."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from ..version import VERSION
from .base import AgentAdapter

PROVIDER_ID = "agent-vision"
PROVIDER_NAME = "Agent Vision Bridge"
PROXY_BASE_URL = "http://127.0.0.1:19100/v1"
WIRE_API = "chat"

_KEY_RE = re.compile(r'^\s*([A-Za-z0-9_.-]+)\s*=\s*"([^"]*)"\s*$')
_SECTION_RE = re.compile(r"^\[(.+)]\s*$")


class CodexAdapter(AgentAdapter):
    id = "codex"
    name = "Codex"

    def __init__(self, codex_dir: Path | None = None, home: Path | None = None):
        self.home = Path(home) if home is not None else Path.home()
        env_home = os.environ.get("CODEX_HOME")
        self.codex_dir = Path(codex_dir) if codex_dir is not None else Path(env_home or self.home / ".codex")
        self.config_path = self.codex_dir / "config.toml"
        self.state_path = self.codex_dir / "agent-vision-state.json"

    def _codex_in_path(self) -> bool:
        return shutil.which("codex") is not None

    @staticmethod
    def _top_level(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                break
            if not stripped or stripped.startswith("#"):
                continue
            match = _KEY_RE.match(line)
            if match:
                result[match.group(1)] = match.group(2)
        return result

    @staticmethod
    def _provider_table(text: str, provider: str) -> dict[str, str]:
        target = f"model_providers.{provider}"
        result: dict[str, str] = {}
        inside = False
        for line in text.splitlines():
            stripped = line.strip()
            section = _SECTION_RE.match(stripped)
            if section:
                inside = section.group(1).strip() == target
                continue
            if inside:
                match = _KEY_RE.match(line)
                if match:
                    result[match.group(1)] = match.group(2)
        return result

    def _current_model_config(self) -> dict[str, str]:
        if not self.config_path.exists():
            return {}
        text = self.config_path.read_text(encoding="utf-8")
        top = self._top_level(text)
        provider = top.get("model_provider", "")
        return {
            "model": top.get("model", ""),
            "model_provider": provider,
            "base_url": self._provider_table(text, provider).get("base_url", "") if provider else "",
        }

    def detect(self) -> dict[str, object]:
        config_exists = self.config_path.exists()
        model = self._current_model_config()
        state = self.read_json(self.state_path)
        return {
            "agent": self.id,
            "name": self.name,
            "installed": config_exists or self._codex_in_path(),
            "config_path": str(self.config_path),
            "config_exists": config_exists,
            "model": model.get("model", ""),
            "model_provider": model.get("model_provider", ""),
            "base_url": model.get("base_url", ""),
            "patched": bool(state),
            "backup_path": str(state.get("backup_path", "")) if state else "",
            "upstream": str(state.get("upstream", "")) if state else "",
        }

    def backup(self) -> Path:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Codex config not found: {self.config_path}")
        backup_path = self.unique_backup_path(self.config_path, "agent-vision")
        backup_path.write_text(self.config_path.read_text(encoding="utf-8"), encoding="utf-8")
        return backup_path

    def _detected_upstream(self, explicit: str | None) -> str:
        if explicit:
            return explicit.strip()
        base_url = self._current_model_config().get("base_url", "")
        if base_url and "127.0.0.1" not in base_url and "localhost" not in base_url:
            return base_url
        return ""

    @classmethod
    def render_patched_config(
        cls,
        text: str,
        *,
        provider_id: str = PROVIDER_ID,
        base_url: str = PROXY_BASE_URL,
        wire_api: str = WIRE_API,
        name: str = PROVIDER_NAME,
    ) -> str:
        """Return config.toml content with the agent-vision provider wired in."""
        lines = text.splitlines()
        out: list[str] = []
        replaced_top = False
        for line in lines:
            stripped = line.strip()
            is_top_key = not stripped.startswith("[") and _KEY_RE.match(line)
            key = line.split("=", 1)[0].strip() if is_top_key else None
            if key == "model_provider":
                out.append(f'model_provider = "{provider_id}"')
                replaced_top = True
            else:
                out.append(line)
        if not replaced_top:
            insert_at = len(out)
            for index, line in enumerate(out):
                stripped = line.strip()
                if _KEY_RE.match(stripped) and line.split("=", 1)[0].strip() == "model":
                    insert_at = index + 1
            out.insert(insert_at, f'model_provider = "{provider_id}"')

        target = f"model_providers.{provider_id}"
        block = [
            f"[{target}]",
            f'name = "{name}"',
            f'base_url = "{base_url}"',
            f'wire_api = "{wire_api}"',
        ]
        result: list[str] = []
        in_target = False
        replaced = False
        index = 0
        while index < len(out):
            line = out[index]
            stripped = line.strip()
            section = _SECTION_RE.match(stripped)
            if section:
                in_target = section.group(1).strip() == target
            if in_target and not replaced:
                index += 1
                while index < len(out) and not out[index].strip().startswith("["):
                    index += 1
                result.extend(block)
                replaced = True
                continue
            result.append(line)
            index += 1
        if not replaced:
            insert_at = len(result)
            for index, line in enumerate(result):
                if line.strip().startswith("["):
                    insert_at = index
                    break
            result[insert_at:insert_at] = block
        return "\n".join(result).rstrip() + "\n"

    def plan(self, upstream: str | None = None) -> dict[str, object]:
        detection = self.detect()
        if not detection["config_exists"]:
            raise FileNotFoundError(f"Codex config not found: {self.config_path}")
        resolved_upstream = self._detected_upstream(upstream)
        backup_path = self.unique_backup_path(self.config_path, "agent-vision")
        files = [
            {
                "file": str(self.config_path),
                "action": "modify",
                "backup": str(backup_path),
                "summary": (
                    f'set model_provider = "{PROVIDER_ID}", add '
                    f'[model_providers.{PROVIDER_ID}] base_url = "{PROXY_BASE_URL}", '
                    f'wire_api = "{WIRE_API}"'
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
            raise FileNotFoundError(f"Codex config not found: {self.config_path}")
        resolved_upstream = self._detected_upstream(upstream)
        backup_path = self.backup()
        original = backup_path.read_text(encoding="utf-8")
        self.config_path.write_text(self.render_patched_config(original), encoding="utf-8")
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
            raise FileNotFoundError("no agent-vision patch found for Codex")
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
