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
import agent_vision.runtime as runtime_mod
from agent_vision.runtime import RuntimeManager


class FakeProc:
    pid = 4242


class FakeRuntime:
    log_file = Path("runtime.log")

    def __init__(self, running=True, start_result=None):
        self._running = running
        self._start_result = start_result or {
            "status": "started",
            "ready": True,
            "pid": 1,
            "listen": "127.0.0.1:19100",
            "upstream": "https://api.deepseek.com",
        }

    def state(self):
        return {"upstream": "https://api.deepseek.com"} if self._running else {}

    def status(self):
        return {
            "running": self._running,
            "ready": self._running,
            "pid": 1 if self._running else None,
            "listen": "127.0.0.1:19100",
            "upstream": "https://api.deepseek.com" if self._running else "",
        }

    def start(self, upstream, listen):
        return self._start_result

    def stop(self):
        return {"status": "stopped", "pid": 1}


class RuntimeLifecycleTests(unittest.TestCase):
    def test_start_writes_state_and_returns_started(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RuntimeManager(
                state_file=Path(tmp) / "runtime.json",
                repo_root=Path(tmp),
                default_listen="127.0.0.1:19999",
            )
            with mock.patch.object(runtime_mod.subprocess, "Popen", return_value=FakeProc()), mock.patch.object(
                RuntimeManager, "wait_ready", return_value=True
            ):
                result = manager.start(upstream="https://api.deepseek.com", listen="127.0.0.1:19999")
            self.assertEqual(result["status"], "started")
            self.assertTrue(result["ready"])
            state = json.loads((Path(tmp) / "runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(state["pid"], 4242)
            self.assertEqual(state["upstream"], "https://api.deepseek.com")
            self.assertEqual(state["listen"], "127.0.0.1:19999")

    def test_start_injects_src_pythonpath_from_source_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            src_root = Path(tmp) / "repo"
            manager = RuntimeManager(
                state_file=Path(tmp) / "runtime.json",
                repo_root=src_root,
                default_listen="127.0.0.1:19999",
            )
            captured = {}

            def fake_popen(cmd, **kwargs):
                captured["cmd"] = cmd
                captured["env"] = kwargs.get("env")
                return FakeProc()

            with mock.patch.object(runtime_mod.subprocess, "Popen", side_effect=fake_popen), mock.patch.object(
                RuntimeManager, "wait_ready", return_value=True
            ), mock.patch.object(runtime_mod.config_home, "legacy_source_root", return_value=src_root):
                manager.start(upstream="https://api.deepseek.com", listen="127.0.0.1:19999")
            self.assertIn("agent_vision", captured["cmd"])
            self.assertIn(str((src_root / "src").resolve()), captured["env"]["PYTHONPATH"])

    def test_start_when_already_running_does_not_spawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RuntimeManager(
                state_file=Path(tmp) / "runtime.json",
                repo_root=Path(tmp),
                default_listen="127.0.0.1:19999",
            )
            manager._write_state({"pid": 1, "listen": "127.0.0.1:19100", "upstream": "https://api.deepseek.com"})
            with mock.patch.object(RuntimeManager, "pid_alive", return_value=True), mock.patch.object(
                runtime_mod.subprocess, "Popen"
            ) as popen:
                result = manager.start(upstream="https://api.deepseek.com", listen="127.0.0.1:19100")
            self.assertEqual(result["status"], "already_running")
            popen.assert_not_called()

    def test_stop_terminates_and_clears_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RuntimeManager(
                state_file=Path(tmp) / "runtime.json",
                repo_root=Path(tmp),
                default_listen="127.0.0.1:19999",
            )
            manager._write_state({"pid": 4242, "listen": "127.0.0.1:19100", "upstream": "https://api.deepseek.com"})
            with mock.patch.object(RuntimeManager, "pid_alive", side_effect=[True, False, False]), mock.patch.object(
                RuntimeManager, "_terminate"
            ) as terminate:
                result = manager.stop()
            self.assertEqual(result["status"], "stopped")
            terminate.assert_called_once_with(4242)
            self.assertFalse((Path(tmp) / "runtime.json").exists())

    def test_stop_when_not_running_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RuntimeManager(
                state_file=Path(tmp) / "runtime.json",
                repo_root=Path(tmp),
                default_listen="127.0.0.1:19999",
            )
            with mock.patch.object(RuntimeManager, "_terminate") as terminate:
                result = manager.stop()
            self.assertEqual(result["status"], "stopped")
            terminate.assert_not_called()

    def test_restart_starts_with_existing_upstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = RuntimeManager(
                state_file=Path(tmp) / "runtime.json",
                repo_root=Path(tmp),
                default_listen="127.0.0.1:19999",
            )
            manager._write_state({"pid": 4242, "listen": "127.0.0.1:19999", "upstream": "https://api.deepseek.com"})
            terminated = {"done": False}

            def fake_terminate(pid):
                terminated["done"] = True

            with mock.patch.object(
                RuntimeManager, "pid_alive", side_effect=lambda pid: not terminated["done"]
            ), mock.patch.object(RuntimeManager, "_terminate", side_effect=fake_terminate), mock.patch.object(
                runtime_mod.subprocess, "Popen", return_value=FakeProc()
            ), mock.patch.object(RuntimeManager, "wait_ready", return_value=True):
                result = manager.restart()
            self.assertEqual(result["status"], "started")
            state = json.loads((Path(tmp) / "runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(state["upstream"], "https://api.deepseek.com")


class RuntimeCliTests(unittest.TestCase):
    def test_cmd_start_prints_started(self):
        with mock.patch.object(av, "make_runtime_manager", return_value=FakeRuntime()):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = av.cmd_start(argparse.Namespace(upstream="https://api.deepseek.com", listen=None))
            self.assertEqual(code, 0)
            self.assertIn("Runtime started", buffer.getvalue())

    def test_cmd_start_fails_when_not_ready(self):
        fake = FakeRuntime(start_result={"status": "started", "ready": False, "pid": 1})
        with mock.patch.object(av, "make_runtime_manager", return_value=fake):
            code = av.cmd_start(argparse.Namespace(upstream="https://api.deepseek.com", listen=None))
        self.assertEqual(code, 1)

    def test_cmd_stop_prints_stopped(self):
        with mock.patch.object(av, "make_runtime_manager", return_value=FakeRuntime()):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = av.cmd_stop(argparse.Namespace())
            self.assertEqual(code, 0)
            self.assertIn("Runtime stopped", buffer.getvalue())

    def test_resolve_upstream_prefers_explicit(self):
        with mock.patch.object(av, "cfg", return_value="https://env.example.com"):
            resolved = av.resolve_proxy_upstream("https://explicit.example.com")
        self.assertEqual(resolved, "https://explicit.example.com")

    def test_resolve_upstream_falls_back_to_env_and_runtime(self):
        fake = FakeRuntime(running=True)
        with mock.patch.object(av, "cfg", return_value=""):
            self.assertEqual(av.resolve_proxy_upstream(None, runtime=fake), "https://api.deepseek.com")


if __name__ == "__main__":
    unittest.main()
