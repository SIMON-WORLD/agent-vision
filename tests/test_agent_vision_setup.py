import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import agent_vision.cli as av


def setup_args(**overrides):
    defaults = {
        "provider": "free",
        "api_key": "test-key",
        "base_url": None,
        "model": None,
        "cost": None,
        "dry_run": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class AgentDetectionTests(unittest.TestCase):
    def test_detects_config_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir()
            (home / ".codex" / "config.toml").write_text("model = \"deepseek\"\n", encoding="utf-8")
            (home / ".claude.json").write_text("{}\n", encoding="utf-8")
            result = av.agent_evidence(home, appdata=None, which=lambda name: None)
            found = {item["id"]: item["found"] for item in result}
            self.assertTrue(found["codex"])
            self.assertTrue(found["claude"])
            self.assertFalse(found["cursor"])
            self.assertFalse(found["opencode"])

    def test_detects_executable_without_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = av.agent_evidence(
                Path(tmp),
                appdata=None,
                which=lambda name: "C:/bin/codex.exe" if name == "codex" else None,
            )
            codex = next(item for item in result if item["id"] == "codex")
            self.assertTrue(codex["found"])
            self.assertIn("codex", str(codex["evidence"][0]))

    def test_detects_none_when_no_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = av.agent_evidence(Path(tmp), appdata=None, which=lambda name: None)
            self.assertTrue(all(not item["found"] for item in result))


class ProviderSelectionTests(unittest.TestCase):
    def test_quality_preset_maps_to_builtin(self):
        preset = av.quality_preset("dashscope")
        self.assertEqual(preset["base_url"], av.PROVIDERS["dashscope"]["base_url"])
        self.assertEqual(preset["model"], av.PROVIDERS["dashscope"]["model"])

    def test_custom_preset_shape(self):
        preset = av.custom_preset(" https://api.example.com/v1 ", "vl-model", "paid")
        self.assertEqual(preset["id"], "custom")
        self.assertEqual(preset["base_url"], "https://api.example.com/v1")
        self.assertEqual(preset["model"], "vl-model")

    def test_choose_mode_defaults_to_free(self):
        with mock.patch("builtins.input", return_value=""):
            self.assertEqual(av.choose_setup_mode(None), "free")
        with mock.patch("builtins.input", return_value="2"):
            self.assertEqual(av.choose_setup_mode(None), "quality")
        with mock.patch("builtins.input", return_value="3"):
            self.assertEqual(av.choose_setup_mode(None), "custom")
        self.assertEqual(av.choose_setup_mode("custom"), "custom")

    def test_choose_quality_provider(self):
        with mock.patch("builtins.input", return_value="2"):
            self.assertEqual(av.choose_quality_provider(), "openai")
        with mock.patch("builtins.input", return_value="99"):
            self.assertEqual(av.choose_quality_provider(), "dashscope")


class ConfigGenerationTests(unittest.TestCase):
    def test_render_dotenv_preserves_comments_and_unrelated_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# comment\nVISION_API_KEY=old\nKEEP=1\nVISION_BASE_URL=old-url\n",
                encoding="utf-8",
            )
            content = av.render_dotenv(
                env_file,
                {"VISION_API_KEY": "new", "VISION_BASE_URL": "https://x", "VISION_MODEL": "m"},
            )
            self.assertIn("# comment", content)
            self.assertIn("KEEP=1", content)
            self.assertIn("VISION_API_KEY=new", content)
            self.assertIn("VISION_BASE_URL=https://x", content)
            self.assertIn("VISION_MODEL=m", content)
            self.assertNotIn("old-url", content)

    def test_render_dotenv_creates_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = av.render_dotenv(Path(tmp) / ".env", {"VISION_API_KEY": "k", "VISION_MODEL": "m"})
            self.assertIn("VISION_API_KEY=k", content)
            self.assertIn("VISION_MODEL=m", content)

    def test_render_providers_json_replaces_same_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            path.write_text(
                json.dumps({"providers": [{"id": "custom", "base_url": "old", "model": "old"}]}),
                encoding="utf-8",
            )
            content = av.render_providers_json(
                path,
                {"id": "custom", "base_url": "new", "model": "m", "cost": "paid"},
            )
            data = json.loads(content)
            self.assertEqual(len(data["providers"]), 1)
            self.assertEqual(data["providers"][0]["base_url"], "new")

    def test_render_providers_json_preserves_other_providers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            path.write_text(
                json.dumps({"providers": [{"id": "other", "base_url": "keep", "model": "keep"}]}),
                encoding="utf-8",
            )
            content = av.render_providers_json(
                path,
                {"id": "custom", "base_url": "new", "model": "m", "cost": "paid"},
            )
            data = json.loads(content)
            self.assertEqual(len(data["providers"]), 2)


class SetupCommandTests(unittest.TestCase):
    def test_dry_run_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            providers_file = Path(tmp) / "providers.json"
            with mock.patch.object(av, "ENV_FILE", env_file), mock.patch.object(
                av, "CUSTOM_PROVIDERS_FILE", providers_file
            ):
                code = av.cmd_setup(
                    setup_args(
                        provider="custom",
                        api_key="secret",
                        base_url="https://api.example.com/v1",
                        model="vl-model",
                        cost="paid",
                        dry_run=True,
                    )
                )
            self.assertEqual(code, 0)
            self.assertFalse(env_file.exists())
            self.assertFalse(providers_file.exists())

    def test_setup_writes_env_and_providers(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            providers_file = Path(tmp) / "providers.json"
            with mock.patch.object(av, "ENV_FILE", env_file), mock.patch.object(
                av, "CUSTOM_PROVIDERS_FILE", providers_file
            ):
                code = av.cmd_setup(
                    setup_args(
                        provider="custom",
                        api_key="secret",
                        base_url="https://api.example.com/v1",
                        model="vl-model",
                        cost="paid",
                    )
                )
            self.assertEqual(code, 0)
            env_text = env_file.read_text(encoding="utf-8")
            self.assertIn("VISION_API_KEY=secret", env_text)
            self.assertIn("VISION_BASE_URL=https://api.example.com/v1", env_text)
            self.assertIn("VISION_MODEL=vl-model", env_text)
            data = json.loads(providers_file.read_text(encoding="utf-8"))
            self.assertEqual(data["providers"][0]["id"], "custom")
            self.assertEqual(data["providers"][0]["model"], "vl-model")

    def test_setup_free_writes_only_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            providers_file = Path(tmp) / "providers.json"
            with mock.patch.object(av, "ENV_FILE", env_file), mock.patch.object(
                av, "CUSTOM_PROVIDERS_FILE", providers_file
            ):
                code = av.cmd_setup(setup_args(provider="free", api_key="secret"))
            self.assertEqual(code, 0)
            env_text = env_file.read_text(encoding="utf-8")
            self.assertIn("VISION_API_KEY=secret", env_text)
            self.assertEqual(av.PROVIDERS["zhipu"]["model"], "glm-4v-flash")
            self.assertFalse(providers_file.exists())


if __name__ == "__main__":
    unittest.main()
