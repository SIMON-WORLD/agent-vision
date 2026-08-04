#!/usr/bin/env python3
"""agent-vision (deprecated compatibility entry).

This file used to be the single-file implementation. It is now a thin
re-export of the ``agent-vision`` package so the old entry point keeps
working without maintaining two copies of the same code.

Use the packaged command instead::

    python -m agent_vision
    agent-vision see ...
"""

from __future__ import annotations

import sys
from pathlib import Path

_src = Path(__file__).resolve().parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from agent_vision import cli as _cli  # noqa: E402

globals().update({k: v for k, v in vars(_cli).items() if not k.startswith("__")})

if __name__ == "__main__":
    print(
        "DEPRECATED: vision_bridge.py is kept for compatibility; use `agent-vision` instead.",
        file=sys.stderr,
    )
    sys.exit(main())
