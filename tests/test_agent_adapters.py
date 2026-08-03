import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import agent_vision.cli as av
from agent_vision.adapters import ClaudeAdapter, CursorAdapter, OpenCodeAdapter

OPENCODE_ORIGINAL = {
    "$schema": "https://opencode.ai/config.json",
    "provider": {
        "deepseek": {
            "npm": "@ai-sdk/deepseek",
            "options": {"baseURL": "https://api.deepseek.com"},
            "models": {"deepseek-v4-flash": {"name": "deepseek-v4-flash"}},
        }
    },
    "model": "deepseek/deepseek-v4-flash",
}


def make_opencode(tmp: str) -> OpenCodeAdapter:
    config_path = Path(tmp) / "opencode.json"
    config_path.write_text(json.dumps(OPENCODE_ORIGINAL, indent=2), encoding="utf-8")
    return OpenCodeAdapter(config_path=config_path)


def setup_args(**overrides):
    defaults = {
        "agent": None,
        "provider": "free",
        "api_key": "test-key",
        "base_url": None,
        "model": None,
        "cost": None,
        "dry_run": False,
        "yes": True,
        "proxy_upstream": None,
        "listen": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class OpenCodeAdapterTests(unittest.TestCase):
    def test_detect_reads_config_and_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = make_opencode(tmp)
            detection = adapter.detect()
            self.assertTrue(detection["installed"])
            self.assertTrue(detection["config_exists"])
            self.assertEqual(detection["model"], "deepseek/deepseek-v4-flash")
            self.assertFalse(detection["patched"])

    def test_plan_detects_upstream_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = make_opencode(tmp)
            plan = adapter.plan()
            self.assertEqual(plan["upstream"], "https://api.deepseek.com")
            self.assertEqual(len(plan["files"]), 2)
            self.assertFalse(Path(plan["files"][0]["backup"]).exists())
            self.assertFalse(adapter.state_path.exists())

    def test_apply_patches_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = make_opencode(tmp)
            result = adapter.apply(upstream="https://api.deepseek.com")
            config = json.loads(adapter.config_path.read_text(encoding="utf-8"))
            provider = config["provider"]["agent-vision"]
            self.assertEqual(provider["npm"], "@ai-sdk/openai-compatible")
            self.assertEqual(provider["options"]["baseURL"], "http://127.0.0.1:19100/v1")
            self.assertEqual(config["model"], "agent-vision/deepseek-v4-flash")
            self.assertEqual(config["provider"]["deepseek"]["options"]["baseURL"], "https://api.deepseek.com")
            self.assertTrue(Path(result["backup_path"]).exists())
            state = json.loads(adapter.state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["agent"], "opencode")
            self.assertEqual(state["upstream"], "https://api.deepseek.com")

    def test_render_patched_config_is_idempotent(self):
        first = OpenCodeAdapter.render_patched_config(OPENCODE_ORIGINAL)
        second = OpenCodeAdapter.render_patched_config(first)
        self.assertEqual(first, second)

    def test_rollback_restores_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = make_opencode(tmp)
            adapter.apply(upstream="https://api.deepseek.com")
            result = adapter.rollback()
            self.assertEqual(
                json.loads(adapter.config_path.read_text(encoding="utf-8")),
                OPENCODE_ORIGINAL,
            )
            self.assertFalse(adapter.state_path.exists())
            self.assertTrue(Path(result["restored_from"]).exists())


class ClaudeAdapterTests(unittest.TestCase):
    def test_detect_reads_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "settings.json"
            settings.write_text(
                json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://gateway.example.com"}}),
                encoding="utf-8",
            )
            adapter = ClaudeAdapter(config_path=settings)
            detection = adapter.detect()
            self.assertTrue(detection["installed"])
            self.assertEqual(detection["base_url"], "https://gateway.example.com")
            self.assertFalse(detection["patched"])

    def test_plan_returns_manual_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ClaudeAdapter(config_path=Path(tmp) / "settings.json")
            plan = adapter.plan()
            self.assertTrue(plan["manual_steps"])
            self.assertEqual(plan["files"], [])

    def test_apply_raises_not_implemented(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ClaudeAdapter(config_path=Path(tmp) / "settings.json")
            with self.assertRaises(NotImplementedError):
                adapter.apply()

    def test_setup_claude_dry_run_prints_manual_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "settings.json"
            adapter = ClaudeAdapter(config_path=settings)
            env_file = Path(tmp) / ".env"
            providers_file = Path(tmp) / "providers.json"
            with mock.patch.object(av, "make_adapter", return_value=adapter), mock.patch.object(
                av, "ENV_FILE", env_file
            ), mock.patch.object(av, "CUSTOM_PROVIDERS_FILE", providers_file):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = av.cmd_setup(setup_args(agent="claude", dry_run=True))
            self.assertEqual(code, 0)
            self.assertIn("Dry run", buffer.getvalue())
            self.assertIn("manual configuration required", buffer.getvalue())
            self.assertFalse(env_file.exists())
            self.assertFalse(settings.exists())

    def test_setup_claude_without_auto_patch_stops_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ClaudeAdapter(config_path=Path(tmp) / "settings.json")
            env_file = Path(tmp) / ".env"
            with mock.patch.object(av, "make_adapter", return_value=adapter), mock.patch.object(
                av, "ENV_FILE", env_file
            ):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = av.cmd_setup(setup_args(agent="claude"))
            self.assertEqual(code, 1)
            self.assertIn("not auto-patched", buffer.getvalue())
            self.assertFalse(env_file.exists())


class CursorAdapterTests(unittest.TestCase):
    def test_detect_config_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "Cursor"
            config_dir.mkdir()
            adapter = CursorAdapter(config_dir=config_dir)
            detection = adapter.detect()
            self.assertTrue(detection["installed"])
            self.assertTrue(detection["config_exists"])

    def test_plan_returns_manual_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = CursorAdapter(config_dir=Path(tmp) / "Cursor")
            plan = adapter.plan()
            self.assertTrue(plan["manual_steps"])
            self.assertEqual(plan["files"], [])

    def test_apply_raises_not_implemented(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = CursorAdapter(config_dir=Path(tmp) / "Cursor")
            with self.assertRaises(NotImplementedError):
                adapter.apply()


class SetupAutoDetectTests(unittest.TestCase):
    def test_setup_picks_opencode_when_codex_absent(self):
        class FakeAdapter:
            def __init__(self, found):
                self.found = found

            def detect(self):
                return {"config_exists": self.found, "installed": self.found, "name": "OpenCode"}

        with mock.patch.object(
            av, "make_adapter", side_effect=lambda agent_id: FakeAdapter(agent_id == "opencode")
        ):
            with mock.patch.object(av, "cmd_setup_full", return_value=7) as full:
                code = av.cmd_setup(setup_args(provider=None))
        self.assertEqual(code, 7)
        self.assertEqual(full.call_args.kwargs["agent_id"], "opencode")

    def test_make_adapter_dispatches(self):
        self.assertIsInstance(av.make_adapter("opencode"), OpenCodeAdapter)
        self.assertIsInstance(av.make_adapter("claude"), ClaudeAdapter)
        self.assertIsInstance(av.make_adapter("cursor"), CursorAdapter)


if __name__ == "__main__":
    unittest.main()
