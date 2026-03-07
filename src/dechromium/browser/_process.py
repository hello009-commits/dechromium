from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from dechromium._exceptions import BrowserError, BrowserNotInstalledError, BrowserTimeoutError

logger = logging.getLogger(__name__)

_SINGLETON_FILES = ("SingletonLock", "SingletonCookie", "SingletonSocket")


@dataclass(slots=True)
class BrowserInfo:
    profile_id: str
    pid: int
    debug_port: int
    ws_endpoint: str
    cdp_url: str


class BrowserProcess:
    __slots__ = ("_info", "_proc", "args", "debug_port", "env", "profile_id")

    def __init__(
        self,
        profile_id: str,
        args: list[str],
        env: dict[str, str],
        debug_port: int,
    ):
        self.profile_id = profile_id
        self.args = args
        self.env = env
        self.debug_port = debug_port
        self._proc: subprocess.Popen | None = None
        self._info: BrowserInfo | None = None

    def start(self, timeout: float = 15.0) -> BrowserInfo:
        full_args = [
            *self.args,
            f"--remote-debugging-port={self.debug_port}",
            "--remote-allow-origins=*",
            "--no-sandbox",
        ]

        self._clean_singleton_locks()

        popen_kwargs: dict = {
            "env": {**os.environ, **self.env},
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        try:
            self._proc = subprocess.Popen(full_args, **popen_kwargs)
        except FileNotFoundError:
            binary = full_args[0] if full_args else "chrome"
            raise BrowserNotInstalledError(
                f"Chromium binary not found: {binary}\nInstall it with: dechromium install"
            ) from None

        cdp_url = f"http://127.0.0.1:{self.debug_port}"

        try:
            ws = self._wait_cdp(cdp_url, timeout)
        except (BrowserTimeoutError, BrowserError):
            self.stop()
            raise

        self._info = BrowserInfo(
            profile_id=self.profile_id,
            pid=self._proc.pid,
            debug_port=self.debug_port,
            ws_endpoint=ws,
            cdp_url=cdp_url,
        )
        return self._info

    def stop(self, timeout: float = 5.0):
        if not self._proc:
            return
        if self._proc.poll() is not None:
            self._proc = None
            self._info = None
            self._clean_singleton_locks()
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=3)
        self._proc = None
        self._info = None
        self._clean_singleton_locks()

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def info(self) -> BrowserInfo | None:
        if self.is_running:
            return self._info
        return None

    def _user_data_dir(self) -> Path | None:
        for arg in self.args:
            if arg.startswith("--user-data-dir="):
                return Path(arg.split("=", 1)[1])
        return None

    def _clean_singleton_locks(self):
        data_dir = self._user_data_dir()
        if not data_dir or not data_dir.exists():
            return
        for name in _SINGLETON_FILES:
            lock = data_dir / name
            if lock.exists() or lock.is_symlink():
                try:
                    lock.unlink()
                    logger.debug("Removed stale %s from %s", name, data_dir)
                except OSError:
                    pass

    def _wait_cdp(self, cdp_url: str, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        last_err: Exception | None = None
        while time.monotonic() < deadline:
            if self._proc and self._proc.poll() is not None:
                raise BrowserError(f"Browser exited with code {self._proc.returncode}")
            try:
                resp = urlopen(f"{cdp_url}/json/version", timeout=2)
                data = json.loads(resp.read())
                return data.get("webSocketDebuggerUrl", "")
            except (URLError, OSError, json.JSONDecodeError) as exc:
                last_err = exc
                time.sleep(0.3)
        raise BrowserTimeoutError(
            f"CDP not ready after {timeout}s on port {self.debug_port}: {last_err}"
        )
