"""
Local WebSocket server — the Tampermonkey userscript connects here.

State updates are pushed by the browser; JS commands are sent on demand
and their results awaited (same blocking evaluate() API as the old CDPClient).
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Callable

_LOG_DIR = Path.home() / ".pokelike-debugger"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(_LOG_DIR / "debugger.log"),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ws_server")

PORT = 9223


class WSServer:
    """
    Replaces CDPClient: instead of connecting to Chrome, we listen and the
    browser's userscript connects to us.

    Public API is intentionally identical to CDPClient so the rest of the
    codebase (StatePoller, sections) needs no changes.
    """

    def __init__(self, port: int = PORT) -> None:
        self._port = port
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws: Any = None
        self._pending: dict[int, Future[Any]] = {}
        self._cmd_id = 0
        self._lock = threading.Lock()
        self.status = "disconnected"
        self.on_status_change: list[Callable[[str], None]] = []

        t = threading.Thread(target=self._run_loop, daemon=True, name="ws-server")
        t.start()

    # ------------------------------------------------------------------
    # Public API (same contract as CDPClient)
    # ------------------------------------------------------------------

    def evaluate(self, js: str, timeout: float = 15.0) -> Any:
        """Send JS to the browser and block until the result comes back."""
        if self._ws is None:
            raise RuntimeError("No browser connected")

        fut: Future[Any] = Future()
        with self._lock:
            self._cmd_id += 1
            cmd_id = self._cmd_id
            self._pending[cmd_id] = fut

        payload = json.dumps({"type": "eval", "id": cmd_id, "code": js})
        asyncio.run_coroutine_threadsafe(self._send(payload), self._loop)  # type: ignore[arg-type]
        return fut.result(timeout=timeout)

    def connect(self) -> None:
        """No-op — server is always listening; reconnection is automatic."""

    def disconnect(self) -> None:
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ------------------------------------------------------------------
    # Asyncio server (runs in its own thread)
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as exc:
            log.error("Server loop crashed: %s", exc, exc_info=True)

    async def _serve(self) -> None:
        # websockets 14+ uses websockets.asyncio.server; legacy API removed in v14
        from websockets.asyncio.server import serve as ws_serve  # noqa: PLC0415

        try:
            async with ws_serve(self._handler, "127.0.0.1", self._port):
                log.info("WS server listening on ws://127.0.0.1:%d", self._port)
                await asyncio.Future()  # run forever
        except OSError as exc:
            log.error("Cannot start WS server on port %d: %s", self._port, exc)

    async def _handler(self, websocket: Any) -> None:
        log.info("Browser connected")
        self._ws = websocket
        self._set_status("connected")
        try:
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if msg.get("type") == "result":
                    with self._lock:
                        fut = self._pending.pop(msg["id"], None)
                    if fut and not fut.done():
                        if "error" in msg:
                            fut.set_exception(RuntimeError(msg["error"]))
                        else:
                            fut.set_result(msg.get("value"))

        except Exception as exc:
            log.warning("Handler error: %s", exc)
        finally:
            self._ws = None
            self._set_status("disconnected")
            with self._lock:
                for f in self._pending.values():
                    if not f.done():
                        f.set_exception(RuntimeError("Browser disconnected"))
                self._pending.clear()
            log.info("Browser disconnected")

    async def _send(self, msg: str) -> None:
        if self._ws:
            try:
                await self._ws.send(msg)
            except Exception as exc:
                log.warning("Send error: %s", exc)

    def _set_status(self, status: str) -> None:
        self.status = status
        for cb in self.on_status_change:
            try:
                cb(status)
            except Exception:
                pass
