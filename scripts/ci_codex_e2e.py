#!/usr/bin/env python3
"""CI end-to-end simulation of the Codex adapter on a clean machine.

Creates a fake Codex config.toml plus a cc-switch-style model catalog in a
temporary directory, then verifies the full detect -> plan -> apply -> rollback
cycle without touching a real Codex installation.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from agent_vision.adapters import CodexAdapter
from agent_vision.adapters.codex import PROXY_BASE_URL
from agent_vision import config_home

CONFIG_TOML = """model_provider = "deepseek"
model = "deepseek-v4-flash"
model_catalog_json = "cc-switch-model-catalog.json"

[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com"
wire_api = "responses"
env_key = "DEEPSEEK_API_KEY"
experimental_bearer_token = "sk-test-key"

[features]
enabled = true
"""

CATALOG = {
    "models": [
        {"slug": "deepseek-v4-flash", "input_modalities": ["text"]},
        {"slug": "deepseek-v4-pro", "input_modalities": ["text"]},
    ]
}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        codex_dir = Path(tmp) / ".codex"
        codex_dir.mkdir(parents=True)
        config_path = codex_dir / "config.toml"
        catalog_path = codex_dir / "cc-switch-model-catalog.json"
        config_path.write_text(CONFIG_TOML, encoding="utf-8")
        catalog_path.write_text(json.dumps(CATALOG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        os.environ["AGENT_VISION_HOME"] = str(Path(tmp) / "av-home")
        config_home.ensure_home()

        adapter = CodexAdapter(codex_dir=codex_dir)
        detection = adapter.detect()
        assert detection["config_exists"] is True
        assert detection["base_url"] == "https://api.deepseek.com"
        assert detection["catalog_patched"] is False

        plan = adapter.plan()
        assert plan["catalog_updated"] is True

        applied = adapter.apply()
        assert applied["catalog_updated"] is True
        patched_text = config_path.read_text(encoding="utf-8")
        assert PROXY_BASE_URL in patched_text
        assert "https://api.deepseek.com" not in patched_text
        patched_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        flash = next(item for item in patched_catalog["models"] if item["slug"] == "deepseek-v4-flash")
        assert "image" in flash["input_modalities"]

        rolled_back = adapter.rollback()
        assert config_path.read_text(encoding="utf-8") == CONFIG_TOML
        restored_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        restored_flash = next(item for item in restored_catalog["models"] if item["slug"] == "deepseek-v4-flash")
        assert restored_flash["input_modalities"] == ["text"]

    print("codex e2e simulation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
