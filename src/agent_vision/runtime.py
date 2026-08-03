"""Runtime manager: start/stop/restart the local vision proxy in the background."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from .version import VERSION

DEFAULT_LISTEN = "127.0.0.1:19100"


class RuntimeManager:
    """Manages the background vision proxy process and its PID/state file."""

    def __init__(
        self,
        state_file: Path | None = None,
        repo_root: Path | None = None,
        default_listen: str | None = None,
    ):
        self.repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parent.parent.parent
        self.state_file = Path(state_file) if state_file is not None else self.repo_root / ".agent-vision-runtime.json"
        self.log_file = self.repo_root / ".agent-vision-runtime.log"
        self.default_listen = default_listen or DEFAULT_LISTEN

    def state(self) -> dict[str, object]:
        if not self.state_file.exists():
            return {}
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write_state(self, data: dict[str, object]) -> None:
        self.state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def pid_alive(pid: int) -> bool:
        if os.name == "nt":
            try:
                import ctypes

                process_query_limited_information = 0x1000
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(process_query_limited_information, False, int(pid))
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
            except Exception:
                pass
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return str(pid) in result.stdout and "No tasks" not in result.stdout
            except (OSError, subprocess.SubprocessError):
                return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _terminate(pid: int) -> None:
        if os.name == "nt":
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
        else:
            os.kill(pid, signal.SIGTERM)

    def status(self) -> dict[str, object]:
        state = self.state()
        pid = state.get("pid")
        listen = str(state.get("listen") or self.default_listen)
        running = bool(pid) and self.pid_alive(int(pid))
        if not running and self.port_open(listen):
            running = True
            pid = None
        return {
            "running": running,
            "ready": running and self.port_open(listen),
            "pid": int(pid) if running and pid else None,
            "listen": listen,
            "upstream": str(state.get("upstream") or ""),
            "state_file": str(self.state_file),
        }

    def is_running(self) -> bool:
        return bool(self.status()["running"])

    @staticmethod
    def port_open(listen: str) -> bool:
        host, _, port = listen.rpartition(":")
        try:
            with socket.create_connection((host or "127.0.0.1", int(port)), timeout=1):
                return True
        except OSError:
            return False

    def wait_ready(self, listen: str, timeout: float = 8.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.port_open(listen):
                return True
            time.sleep(0.25)
        return False

    def start(self, upstream: str, listen: str = DEFAULT_LISTEN) -> dict[str, object]:
        state = self.state()
        if state.get("pid") and self.pid_alive(int(state["pid"])):
            return {**self.status(), "status": "already_running"}
        if self.port_open(listen):
            return {
                "running": True,
                "ready": True,
                "pid": None,
                "listen": listen,
                "upstream": upstream,
                "status": "already_running",
            }
        cmd = [sys.executable, "-m", "agent_vision", "proxy", "--listen", listen, "--upstream", upstream]
        flags = 0
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        log_handle = open(self.log_file, "ab")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=log_handle,
                stdin=subprocess.DEVNULL,
                creationflags=flags,
                close_fds=True,
            )
        finally:
            log_handle.close()
        state = {
            "pid": proc.pid,
            "listen": listen,
            "upstream": upstream,
            "started_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "version": VERSION,
        }
        self._write_state(state)
        ready = self.wait_ready(listen)
        return {**state, "ready": ready, "status": "started"}

    def stop(self) -> dict[str, object]:
        state = self.state()
        pid = state.get("pid")
        stopped = True
        if pid and self.pid_alive(int(pid)):
            self._terminate(int(pid))
            for _ in range(20):
                if not self.pid_alive(int(pid)):
                    break
                time.sleep(0.25)
            if self.pid_alive(int(pid)):
                stopped = False
        if self.state_file.exists():
            self.state_file.unlink()
        return {
            "status": "stopped" if stopped else "stop_failed",
            "pid": pid,
            "listen": str(state.get("listen") or DEFAULT_LISTEN),
            "upstream": str(state.get("upstream") or ""),
        }

    def restart(self, upstream: str | None = None, listen: str | None = None) -> dict[str, object]:
        old = self.status()
        stop_result = self.stop()
        if stop_result.get("status") == "stop_failed":
            raise RuntimeError(f"failed to stop runtime pid {stop_result.get('pid')}")
        resolved_upstream = upstream or str(old.get("upstream") or "")
        if not resolved_upstream:
            raise ValueError("no upstream configured; pass --upstream")
        resolved_listen = listen or str(old.get("listen") or DEFAULT_LISTEN)
        return self.start(upstream=resolved_upstream, listen=resolved_listen)
