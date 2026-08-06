import argparse
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import agent_vision.cli as vb


class AutostartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.startup = Path(self.tmp.name) / "Startup"
        self.startup.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _args(self, **overrides):
        defaults = {
            "enable": False,
            "disable": False,
            "status": False,
            "upstream": None,
            "startup_dir": str(self.startup),
        }
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def test_render_contains_python_and_start_command(self):
        content = vb.render_autostart_vbs(r"D:\py\python.exe", "https://api.deepseek.com")
        self.assertIn("-m agent_vision start", content)
        self.assertIn("--upstream", content)
        self.assertIn("https://api.deepseek.com", content)
        self.assertIn("python.exe", content)

    def test_enable_writes_vbs(self):
        args = self._args(enable=True, upstream="https://api.deepseek.com")
        with mock.patch.object(vb, "resolve_proxy_upstream", return_value="https://api.deepseek.com"):
            code = vb.cmd_autostart(args)
        self.assertEqual(code, 0)
        target = self.startup / vb.AUTOSTART_FILENAME
        self.assertTrue(target.exists())
        content = target.read_text(encoding="utf-8-sig")
        self.assertIn("-m agent_vision start --upstream", content)

    def test_source_tree_injects_pythonpath(self):
        src_root = Path(self.tmp.name) / "repo"
        args = self._args(enable=True, upstream="https://api.deepseek.com")
        with mock.patch.object(vb, "resolve_proxy_upstream", return_value="https://api.deepseek.com"), mock.patch.object(
            vb.config_home, "legacy_source_root", return_value=src_root
        ):
            code = vb.cmd_autostart(args)
        self.assertEqual(code, 0)
        content = (self.startup / vb.AUTOSTART_FILENAME).read_text(encoding="utf-8-sig")
        self.assertIn("PYTHONPATH", content)
        self.assertIn("src", content)

    def test_disable_removes_file(self):
        target = self.startup / vb.AUTOSTART_FILENAME
        target.write_text("x", encoding="utf-8")
        args = self._args(disable=True)
        self.assertEqual(vb.cmd_autostart(args), 0)
        self.assertFalse(target.exists())

    def test_status_reports_enabled(self):
        target = self.startup / vb.AUTOSTART_FILENAME
        target.write_text("x", encoding="utf-8")
        args = self._args(status=True)
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = vb.cmd_autostart(args)
        self.assertEqual(code, 0)
        self.assertIn("enabled", out.getvalue())

    def test_status_reports_disabled(self):
        args = self._args(status=True)
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = vb.cmd_autostart(args)
        self.assertEqual(code, 0)
        self.assertIn("disabled", out.getvalue())

    def test_enable_without_upstream_errors(self):
        args = self._args(enable=True)
        with mock.patch.object(vb, "resolve_proxy_upstream", return_value=""):
            code = vb.cmd_autostart(args)
        self.assertNotEqual(code, 0)
        self.assertFalse((self.startup / vb.AUTOSTART_FILENAME).exists())

    def test_env_override_for_startup_dir(self):
        args = self._args(enable=True, upstream="https://api.deepseek.com", startup_dir=None)
        with mock.patch.object(vb, "resolve_proxy_upstream", return_value="https://api.deepseek.com"), mock.patch.dict(
            os.environ, {"AGENT_VISION_AUTOSTART_DIR": str(self.startup)}
        ):
            code = vb.cmd_autostart(args)
        self.assertEqual(code, 0)
        self.assertTrue((self.startup / vb.AUTOSTART_FILENAME).exists())


if __name__ == "__main__":
    unittest.main()