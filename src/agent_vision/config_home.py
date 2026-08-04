"""Unified user-level configuration directory for agent-vision.

All user-owned state (API keys, provider presets, runtime state and logs)
lives in one directory so the package works identically from a source
checkout and from a pip install. The directory can be overridden with the
``AGENT_VISION_HOME`` environment variable.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ENV_VAR = "AGENT_VISION_HOME"
LEGACY_MARKERS = ("pyproject.toml", "vision_bridge.py")


def agent_vision_home() -> Path:
    """Return the user-level config home, honoring AGENT_VISION_HOME."""
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".agent-vision"


def ensure_home() -> Path:
    """Create the config home and its subdirectories."""
    root = agent_vision_home()
    for name in ("", "state", "logs", "backups"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def env_file() -> Path:
    return agent_vision_home() / ".env"


def providers_file() -> Path:
    return agent_vision_home() / "providers.json"


def runtime_state_file() -> Path:
    return agent_vision_home() / "runtime.json"


def runtime_log_file() -> Path:
    return agent_vision_home() / "logs" / "runtime.log"


def state_dir() -> Path:
    return agent_vision_home() / "state"


def backups_dir() -> Path:
    return agent_vision_home() / "backups"


def legacy_source_root() -> Path | None:
    """Detect a source checkout root, or None when running from site-packages."""
    candidate = Path(__file__).resolve().parent.parent.parent
    if any((candidate / marker).exists() for marker in LEGACY_MARKERS):
        return candidate
    return None


def migrate_legacy_config() -> dict[str, Path]:
    """Copy legacy source-tree config into the user home if the target is absent."""
    root = legacy_source_root()
    if root is None:
        return {}
    ensure_home()
    moves = {
        root / ".env": env_file(),
        root / "providers.json": providers_file(),
        root / ".agent-vision-runtime.json": runtime_state_file(),
    }
    migrated: dict[str, Path] = {}
    for source, target in moves.items():
        if source.exists() and not target.exists():
            shutil.copy2(source, target)
            migrated[str(source)] = target
    return migrated


def initialize() -> dict[str, Path]:
    """Ensure the user home exists and import any legacy config found."""
    ensure_home()
    return migrate_legacy_config()
