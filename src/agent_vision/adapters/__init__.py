"""Agent integration adapters.

Each adapter knows how to detect, backup, patch, apply and roll back the
config of a specific AI coding agent. Codex and OpenCode support automatic
patch; Claude Code and Cursor are detected and guided because they either
speak a different protocol or expose no stable public config key.
"""

from .base import AgentAdapter
from .claude import ClaudeAdapter
from .codex import CodexAdapter
from .cursor import CursorAdapter
from .opencode import OpenCodeAdapter

ADAPTERS = {
    "codex": CodexAdapter,
    "claude": ClaudeAdapter,
    "cursor": CursorAdapter,
    "opencode": OpenCodeAdapter,
}


def get_adapter(agent_id: str, **kwargs) -> AgentAdapter:
    try:
        adapter_cls = ADAPTERS[agent_id]
    except KeyError:
        raise ValueError(f"unsupported agent: {agent_id}") from None
    return adapter_cls(**kwargs)


__all__ = [
    "ADAPTERS",
    "AgentAdapter",
    "ClaudeAdapter",
    "CodexAdapter",
    "CursorAdapter",
    "OpenCodeAdapter",
    "get_adapter",
]
