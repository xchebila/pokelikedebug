"""
Receives game state pushed by the Tampermonkey userscript and fires callbacks.

The state is no longer polled from Python — the browser sends it every 3 s.
fetch_dex() and fetch_hof() still use evaluate() for on-demand heavy data.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

from .ws_server import WSServer

_STATE_JS = """
(function() {
    try {
        var gameLoaded = typeof getPokedollars === 'function';
        var inRun = gameLoaded
            && typeof state !== 'undefined'
            && state !== null
            && Array.isArray(state.team);
        return {
            gameLoaded: gameLoaded,
            inRun: inRun,
            team: inRun ? state.team.map(function(p) {
                var bs = p.baseStats || {};
                return {
                    name:      p.name      || '???',
                    level:     p.level     || 0,
                    currentHp: p.currentHp || 0,
                    maxHp:     p.maxHp     || 0,
                    isShiny:   !!p.isShiny,
                    speciesId: p.speciesId || 0,
                    baseStats: {
                        hp:      bs.hp      || 0,
                        atk:     bs.atk     || 0,
                        def:     bs.def     || 0,
                        speed:   bs.speed   || 0,
                        special: bs.special || 0,
                        spdef:   bs.spdef   || 0,
                    },
                };
            }) : [],
            dollars:       gameLoaded ? getPokedollars() : 0,
            forcedPending: typeof _forcedEncounterId !== 'undefined'
                           && _forcedEncounterId !== null,
        };
    } catch(e) {
        return { gameLoaded: false, inRun: false, error: e.message,
                 team: [], dollars: 0, forcedPending: false };
    }
})()
"""

_DEX_POLL_JS = """
(() => {
    try {
        return typeof getPokedex === 'function' ? getPokedex() : {};
    } catch(e) {
        return {};
    }
})()
"""

_HOF_POLL_JS = """
(() => {
    try {
        var raw = localStorage.getItem('poke_hof_index');
        return raw ? JSON.parse(raw) : {};
    } catch(e) {
        return {};
    }
})()
"""

_MEGA_POLL_JS = """
(() => {
    try {
        if (typeof MEGA_STONES === 'undefined') return { unlocked: false, stones: [] };
        var unlocked = typeof isMegaBraceletUnlocked === 'function' && isMegaBraceletUnlocked();
        var stones = MEGA_STONES.map(function(s) {
            var current  = typeof megaLineMvpCount === 'function' ? megaLineMvpCount(s) : 0;
            var required = s.tier || 1;
            var owned    = typeof ownsMegaStone === 'function' ? ownsMegaStone(s) : (current >= required);
            return {
                species:  s.species,
                name:     s.megaName || s.name,
                required: required,
                current:  current,
                owned:    !!owned,
            };
        });
        return { unlocked: unlocked, stones: stones };
    } catch(e) {
        return { unlocked: false, stones: [] };
    }
})()
"""

GameState = dict[str, Any]
StateCallback = Callable[[GameState], None]


class StatePoller:
    """
    Polls game state every N seconds via evaluate() and fires a callback.
    Also accepts on-demand refresh via refresh_now().
    """

    def __init__(
        self,
        client: WSServer,
        on_update: StateCallback,
        interval: float = 3.0,
    ) -> None:
        self._client   = client
        self._callback = on_update
        self._interval = interval
        self._wake     = threading.Event()
        self._running  = False
        self._thread   = threading.Thread(target=self._run, daemon=True, name="state-poller")

    def start(self) -> None:
        self._running = True
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._wake.set()

    def refresh_now(self) -> None:
        """Trigger an immediate poll without waiting for the interval."""
        self._wake.set()

    def _run(self) -> None:
        while self._running:
            if self._client.status == "connected":
                try:
                    state = self._client.evaluate(_STATE_JS)
                    if state:
                        self._callback(state)
                except Exception:
                    pass
            self._wake.wait(timeout=self._interval)
            self._wake.clear()

    def fetch_dex(self, on_result: Callable[[dict], None]) -> None:
        def _run() -> None:
            try:
                dex = self._client.evaluate(_DEX_POLL_JS)
                on_result(dex or {})
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True, name="dex-fetch").start()

    def fetch_hof(self, on_result: Callable[[dict], None]) -> None:
        def _run() -> None:
            try:
                hof = self._client.evaluate(_HOF_POLL_JS)
                on_result(hof or {})
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True, name="hof-fetch").start()

    def fetch_mega(self, on_result: Callable[[dict], None]) -> None:
        def _run() -> None:
            try:
                mega = self._client.evaluate(_MEGA_POLL_JS)
                on_result(mega or {})
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True, name="mega-fetch").start()
