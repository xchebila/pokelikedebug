"""
Chrome DevTools Protocol client — pure WebSocket implementation.

Replaces Playwright with websocket-client (pure Python, trivially bundleable).
All JS evaluation runs on a dedicated worker thread; callers use evaluate()
which queues the request and blocks until the worker executes it.
"""

from __future__ import annotations

import json
import logging
import platform
import queue
import subprocess
import threading
import time
from concurrent.futures import Future
from pathlib import Path
from typing import Any

import requests as _http
import websocket

# Log to file — visible even from a .app bundle where there's no console
_LOG_DIR = Path.home() / ".pokelike-debugger"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(_LOG_DIR / "debugger.log"),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cdp")

GAME_URL  = "https://pokelike.xyz"
CDP_PORT  = 9222
CDP_BASE  = f"http://localhost:{CDP_PORT}"
_RECONNECT_DELAY = 3.0


def _chrome_path() -> str:
    system = platform.system()
    if system == "Darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            )
            path, _ = winreg.QueryValueEx(key, "")
            return path
        except Exception:
            return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    return "google-chrome"


def _profile_dir() -> str:
    return str(Path.home() / ".pokelike-debugger" / "chrome-profile")


class CDPClient:
    """
    Thread-safe CDP bridge using raw WebSocket + CDP JSON protocol.

    One worker thread owns the WebSocket; all other threads submit JS via
    evaluate(), which queues the request and blocks until the result is back.
    """

    def __init__(self) -> None:
        self._cmd_queue: queue.Queue[tuple[str, Future[Any]]] = queue.Queue()
        self.status      = "disconnected"
        self.on_status_change: list[Any] = []
        self._chrome: subprocess.Popen | None = None  # type: ignore[type-arg]
        self._stop   = threading.Event()
        self._wake   = threading.Event()   # poke to retry connection immediately

        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name="cdp-worker"
        )
        self._worker.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, js: str, timeout: float = 15.0) -> Any:
        """Execute JS (blocking). Raises on error or timeout."""
        fut: Future[Any] = Future()
        self._cmd_queue.put((js, fut))
        return fut.result(timeout=timeout)

    def connect(self) -> None:
        """Signal the worker to retry connection immediately."""
        self._wake.set()

    def disconnect(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        ws: websocket.WebSocket | None = None
        pending: dict[int, Future[Any]] = {}
        pending_lock = threading.Lock()
        recv_dead    = threading.Event()
        msg_id       = 0

        while not self._stop.is_set():

            # ── Connect ──────────────────────────────────────────────────
            if ws is None:
                self._set_status("connecting")
                try:
                    log.info("Attempting connection...")
                    self._launch_chrome()
                    ws = self._open_ws()
                    recv_dead.clear()
                    threading.Thread(
                        target=self._recv_loop,
                        args=(ws, pending, pending_lock, recv_dead),
                        daemon=True,
                        name="cdp-recv",
                    ).start()
                    log.info("Connected to CDP")
                    self._set_status("connected")
                except Exception as exc:
                    # 403 = Chrome running without --remote-allow-origins=*
                    # Kill it and relaunch with the correct flag on next iteration
                    if "403" in str(exc):
                        log.warning(
                            "403 Forbidden: Chrome lacks --remote-allow-origins=*. "
                            "Killing process on port %d and relaunching.", CDP_PORT
                        )
                        self._kill_cdp_port()
                        self._chrome = None
                    else:
                        log.error("Connection failed: %s", exc, exc_info=True)
                        self._drain(pending, pending_lock)
                        self._wake.wait(timeout=_RECONNECT_DELAY)
                        self._wake.clear()
                    ws = None
                    self._set_status("disconnected")
                    continue

            # ── Detect dead receive thread ────────────────────────────────
            if recv_dead.is_set():
                log.warning("Receive thread died — reconnecting")
                ws = None
                self._set_status("disconnected")
                continue

            # ── Process one command ───────────────────────────────────────
            try:
                js_code, fut = self._cmd_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            msg_id += 1
            mid = msg_id
            with pending_lock:
                pending[mid] = fut
            try:
                ws.send(json.dumps({
                    "id": mid,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression":   js_code,
                        "awaitPromise": True,
                        "returnByValue": True,
                    },
                }))
            except Exception as exc:
                with pending_lock:
                    pending.pop(mid, None)
                if not fut.done():
                    fut.set_exception(exc)
                ws = None
                self._set_status("disconnected")

        if ws:
            try:
                ws.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Receive loop (background thread)
    # ------------------------------------------------------------------

    @staticmethod
    def _recv_loop(
        ws: websocket.WebSocket,
        pending: dict[int, Future[Any]],
        lock: threading.Lock,
        dead: threading.Event,
    ) -> None:
        try:
            while True:
                raw = ws.recv()
                if not raw:
                    break
                msg = json.loads(raw)
                mid = msg.get("id")
                if mid is None:
                    continue
                with lock:
                    fut = pending.pop(mid, None)
                if fut and not fut.done():
                    if "error" in msg:
                        fut.set_exception(RuntimeError(msg["error"]["message"]))
                    else:
                        # returnByValue: value is nested under result.result.value
                        r = msg.get("result", {}).get("result", {})
                        fut.set_result(r.get("value"))
        except Exception:
            pass
        dead.set()
        with lock:
            for f in pending.values():
                if not f.done():
                    f.set_exception(RuntimeError("CDP WebSocket closed"))
            pending.clear()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _open_ws(self) -> websocket.WebSocket:
        """Find or create the game tab and return a connected WebSocket."""
        tabs = _http.get(f"{CDP_BASE}/json", timeout=3).json()
        log.info("CDP tabs: %s", [t.get("url", "?") for t in tabs])

        game_tab = next(
            (t for t in tabs
             if "pokelike" in t.get("url", "").lower()
             or "pokelike" in t.get("title", "").lower()),
            None,
        )

        if game_tab is None:
            log.info("No game tab found — opening one")
            new_tab = _http.get(f"{CDP_BASE}/json/new", timeout=3).json()
            ws_url  = new_tab["webSocketDebuggerUrl"]
            ws      = websocket.create_connection(ws_url, timeout=10, origin="")
            ws.send(json.dumps({
                "id": 1,
                "method": "Page.navigate",
                "params": {"url": GAME_URL},
            }))
            deadline = time.time() + 5
            while time.time() < deadline:
                raw = ws.recv()
                if raw and json.loads(raw).get("id") == 1:
                    break
        else:
            ws_url = game_tab["webSocketDebuggerUrl"]
            log.info("Connecting to tab: %s", ws_url)
            ws = websocket.create_connection(ws_url, timeout=10, origin="")

        return ws

    def _launch_chrome(self) -> None:
        if self._cdp_available():
            log.info("CDP already available, reusing existing Chrome")
            return
        if self._chrome and self._chrome.poll() is None:
            log.info("Our Chrome process still running, waiting for CDP...")
            self._wait_for_cdp(timeout=12.0)
            return
        chrome = _chrome_path()
        profile = _profile_dir()
        log.info("Launching Chrome: %s  profile: %s", chrome, profile)
        args = [
            chrome,
            f"--remote-debugging-port={CDP_PORT}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile}",
        ]
        try:
            self._chrome = subprocess.Popen(
                args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            log.info("Chrome PID: %s", self._chrome.pid)
        except FileNotFoundError:
            log.error("Chrome not found at: %s", chrome)
            raise
        self._wait_for_cdp(timeout=12.0)

    def _kill_cdp_port(self) -> None:
        """Kill whatever process is listening on the CDP port."""
        log.info("Killing process(es) on port %d...", CDP_PORT)
        try:
            if platform.system() == "Windows":
                out = subprocess.check_output(
                    ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL
                )
                for line in out.splitlines():
                    if f":{CDP_PORT}" in line and "LISTENING" in line:
                        pid = line.split()[-1]
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                        log.info("Killed PID %s (Windows)", pid)
            else:
                out = subprocess.check_output(
                    ["lsof", "-t", f"-i:{CDP_PORT}"],
                    text=True, stderr=subprocess.DEVNULL,
                ).strip()
                for pid in out.split():
                    subprocess.run(["kill", "-9", pid], check=False)
                    log.info("Killed PID %s (Mac/Linux)", pid)
            time.sleep(1.0)
        except Exception as exc:
            log.warning("Could not kill process on port %d: %s", CDP_PORT, exc)

    def _cdp_available(self) -> bool:
        try:
            _http.get(f"{CDP_BASE}/json/version", timeout=1)
            return True
        except Exception:
            return False

    def _wait_for_cdp(self, timeout: float = 12.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._cdp_available():
                log.info("CDP port ready")
                return
            time.sleep(0.25)
        raise RuntimeError(f"Chrome CDP did not open within {timeout}s")

    def _drain(self, pending: dict[int, Future[Any]], lock: threading.Lock) -> None:
        with lock:
            for f in pending.values():
                if not f.done():
                    f.set_exception(RuntimeError("Not connected"))
            pending.clear()
        while not self._cmd_queue.empty():
            try:
                _, fut = self._cmd_queue.get_nowait()
                if not fut.done():
                    fut.set_exception(RuntimeError("Not connected"))
            except queue.Empty:
                break

    def _set_status(self, status: str) -> None:
        self.status = status
        for cb in self.on_status_change:
            try:
                cb(status)
            except Exception:
                pass
