import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import agent_vision.cli as av
import agent_vision.config_home as config_home
import agent_vision.runtime as runtime_mod
from agent_vision.runtime import RuntimeManager


class FakeProc:
    pid = 4321


class HomeTests(unittest.TestCase):
    def test_env_override_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AGENT_VISION_HOME": tmp}, clear=False):
                self.assertEqual(config_home.agent_vision_home(), Path(tmp).resolve())

    def test_default_home_is_user_dot_dir(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            self.assertEqual(config_home.agent_vision_home(), Path.home() / ".agent-vision")

    def test_ensure_home_creates_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AGENT_VISION_HOME": tmp}, clear=False):
                root = config_home.ensure_home()
                self.assertEqual(root, Path(tmp).resolve())
                for name in ("state", "logs", "backups"):
                    self.assertTrue((root / name).is_dir())

    def test_path_helpers_live_under_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AGENT_VISION_HOME": tmp}, clear=False):
                home = Path(tmp).resolve()
                self.assertEqual(config_home.env_file(), home / ".env")
                self.assertEqual(config_home.providers_file(), home / "providers.json")
                self.assertEqual(config_home.runtime_state_file(), home / "runtime.json")
                self.assertEqual(config_home.runtime_log_file(), home / "logs" / "runtime.log")
                self.assertEqual(config_home.state_dir(), home / "state")
                self.assertEqual(config_home.backups_dir(), home / "backups")


class InstalledPathTests(unittest.TestCase):
    def test_legacy_root_none_when_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_site_packages = Path(tmp) / "site-packages"
            fake_module = fake_site_packages / "agent_vision" / "config_home.py"
            fake_module.parent.mkdir(parents=True)
            fake_module.write_text("", encoding="utf-8")
            original = config_home.__file__
            config_home.__file__ = str(fake_module)
            try:
                self.assertIsNone(config_home.legacy_source_root())
            finally:
                config_home.__file__ = original

    def test_legacy_root_found_in_source_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "agent-vision"
            module = root / "src" / "agent_vision" / "config_home.py"
            module.parent.mkdir(parents=True)
            module.write_text("", encoding="utf-8")
            (root / "pyproject.toml").write_text("", encoding="utf-8")
            original = config_home.__file__
            config_home.__file__ = str(module)
            try:
                self.assertEqual(config_home.legacy_source_root(), root.resolve())
            finally:
                config_home.__file__ = original

    def test_cli_paths_point_to_user_home_not_site_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_site_packages = Path(tmp) / "site-packages"
            fake_site_packages.mkdir()
            self.assertNotIn(str(fake_site_packages), str(av.ENV_FILE))
            self.assertNotIn(str(fake_site_packages), str(av.CUSTOM_PROVIDERS_FILE))
            self.assertEqual(av.ENV_FILE, config_home.env_file())
            self.assertEqual(av.CUSTOM_PROVIDERS_FILE, config_home.providers_file())

    def test_runtime_defaults_use_user_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with mock.patch.dict(os.environ, {"AGENT_VISION_HOME": str(home)}, clear=False):
                manager = RuntimeManager()
            self.assertEqual(manager.state_file, home.resolve() / "runtime.json")
            self.assertEqual(manager.log_file, home.resolve() / "logs" / "runtime.log")

    def test_runtime_start_writes_state_into_user_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            with mock.patch.dict(os.environ, {"AGENT_VISION_HOME": str(home)}, clear=False):
                manager = RuntimeManager(default_listen="127.0.0.1:19999")
                with mock.patch.object(runtime_mod.subprocess, "Popen", return_value=FakeProc()), mock.patch.object(
                    RuntimeManager, "wait_ready", return_value=True
                ):
                    result = manager.start(upstream="https://api.deepseek.com", listen="127.0.0.1:19999")
            self.assertEqual(result["status"], "started")
            state = json.loads((home / "runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(state["pid"], 4321)
            self.assertTrue((home / "logs" / "runtime.log").exists())


class MigrationTests(unittest.TestCase):
    def test_migrate_copies_legacy_config_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            (root / "src" / "agent_vision").mkdir(parents=True)
            (root / "pyproject.toml").write_text("", encoding="utf-8")
            (root / ".env").write_text("VISION_API_KEY=legacy-key\n", encoding="utf-8")
            (root / "providers.json").write_text("{}", encoding="utf-8")
            (root / ".agent-vision-runtime.json").write_text('{"pid": 1}', encoding="utf-8")

            original_file = config_home.__file__
            config_home.__file__ = str(root / "src" / "agent_vision" / "config_home.py")
            try:
                with mock.patch.dict(os.environ, {"AGENT_VISION_HOME": str(home)}, clear=False):
                    migrated = config_home.migrate_legacy_config()
                    self.assertEqual(len(migrated), 3)
                    self.assertEqual((home / ".env").read_text(encoding="utf-8"), "VISION_API_KEY=legacy-key\n")
                    self.assertEqual((home / "providers.json").read_text(encoding="utf-8"), "{}")
                    self.assertEqual((home / "runtime.json").read_text(encoding="utf-8"), '{"pid": 1}')

                    second = config_home.migrate_legacy_config()
                    self.assertEqual(len(second), 0)
            finally:
                config_home.__file__ = original_file

    def test_migrate_noop_outside_source_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_site_packages = Path(tmp) / "site-packages"
            fake_site_packages.mkdir()
            original_file = config_home.__file__
            config_home.__file__ = str(fake_site_packages / "agent_vision" / "config_home.py")
            try:
                with mock.patch.dict(os.environ, {"AGENT_VISION_HOME": str(Path(tmp) / "home")}, clear=False):
                    self.assertEqual(config_home.migrate_legacy_config(), {})
            finally:
                config_home.__file__ = original_file


class GitignoreTests(unittest.TestCase):
    def test_sensitive_patterns_ignored(self):
        gitignore = Path(__file__).resolve().parent.parent / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        for pattern in (".env", "providers.json", "runtime.json", "*.state.json", "*.log"):
            self.assertIn(pattern, content)


if __name__ == "__main__":
    unittest.main()
