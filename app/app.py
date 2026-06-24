"""Main application window."""

from __future__ import annotations

import threading

import customtkinter as ctk

from .ws_server import WSServer
from .pokemon_data import ALL_IDS
from .sprite_loader import preload_all
from .setup_screen import SetupScreen, is_setup_done
from .state_poller import GameState, StatePoller
from .ui.header import StatusHeader
from .ui.section_encounter import EncounterSection
from .ui.section_hof import HofSection
from .ui.section_money import MoneySection
from .ui.section_pokedex import PokedexSection
from .ui.section_shiny import ShinySection
from .ui.section_team import TeamSection
from .ui.widgets import LightScrollFrame


class DebuggerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Pokelike Debugger")
        self.geometry("600x820")
        self.minsize(520, 500)
        self.resizable(True, True)

        self._client = WSServer()
        self._client.on_status_change.append(self._on_status_change)

        self._poller = StatePoller(self._client, on_update=self._on_game_state)
        self._poller.start()
        self._game_was_loaded = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_sprite_preload()

        if not is_setup_done():
            self.after(200, lambda: SetupScreen(self))

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        evaluate = self._client.evaluate

        # Persistent header above the tabs
        self._header = StatusHeader(
            self,
            on_reconnect=self._reconnect,
            on_setup=self._open_setup,
            on_language_change=self._on_language_change,
        )
        self._header.pack(fill="x", padx=10, pady=(10, 4))

        # Root tab view — Contrôles | Pokédex
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ── Tab 1: controls ───────────────────────────────────────────
        ctrl_tab = tabs.add("Contrôles")
        ctrl_tab.grid_rowconfigure(0, weight=1)
        ctrl_tab.grid_columnconfigure(0, weight=1)

        scroll = LightScrollFrame(ctrl_tab)
        scroll.grid(row=0, column=0, sticky="nsew")

        self._shiny  = ShinySection(scroll.inner, evaluate)
        self._team   = TeamSection(scroll.inner, evaluate, on_refresh=self._poller.refresh_now)
        self._money  = MoneySection(scroll.inner, evaluate)

        for section in (self._shiny, self._team, self._money):
            section.pack(fill="x", pady=2)

        # ── Tab 2: Pokédex ────────────────────────────────────────────
        dex_tab = tabs.add("Pokédex")
        dex_tab.grid_rowconfigure(0, weight=1)
        dex_tab.grid_columnconfigure(0, weight=1)

        self._pokedex = PokedexSection(dex_tab, evaluate, self._poller.fetch_dex)
        self._pokedex.grid(row=0, column=0, sticky="nsew")

        # ── Tab 3: Hall of Fame ───────────────────────────────────────
        hof_tab = tabs.add("Hall of Fame")
        hof_tab.grid_rowconfigure(0, weight=1)
        hof_tab.grid_columnconfigure(0, weight=1)

        self._hof = HofSection(hof_tab, evaluate, self._poller.fetch_hof)
        self._hof.grid(row=0, column=0, sticky="nsew")

        # ── Tab 4: Rencontre ──────────────────────────────────────────
        enc_tab = tabs.add("Rencontre")
        enc_tab.grid_rowconfigure(0, weight=1)
        enc_tab.grid_columnconfigure(0, weight=1)

        self._encounter = EncounterSection(enc_tab, evaluate)
        self._encounter.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    # Callbacks — always re-dispatched to the Tkinter thread via after()
    # ------------------------------------------------------------------

    def _on_status_change(self, status: str) -> None:
        if status == "disconnected":
            self._game_was_loaded = False
        self.after(0, lambda: self._header.update_status(status))

    def _on_game_state(self, state: GameState) -> None:
        def _update() -> None:
            if not state.get("gameLoaded"):
                self._header.update_status("waiting_login")
                return

            self._header.update_status("in_run" if state.get("inRun") else "waiting_for_run")

            if not self._game_was_loaded:
                self._game_was_loaded = True
                self._poller.fetch_dex(
                    lambda dex: self.after(0, lambda: self._pokedex.apply_dex(dex))
                )
                self._poller.fetch_hof(
                    lambda hof: self.after(0, lambda: self._hof.apply_hof(hof))
                )

            self._team.update(state)
            self._money.update(state)
            self._encounter.update(state)

        self.after(0, _update)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _reconnect(self) -> None:
        self._header.update_status(self._client.status)

    def _open_setup(self) -> None:
        SetupScreen(self)

    def _on_language_change(self, lang: str) -> None:
        self._pokedex.set_language(lang)
        self._hof.set_language(lang)
        self._encounter.set_language(lang)

    def _start_sprite_preload(self) -> None:
        def _progress(done: int, total: int) -> None:
            self.after(0, lambda: self._header.update_download_progress(done, total))

        def _done() -> None:
            self.after(0, lambda: self._header.update_download_progress(1, 1))

        preload_all(ALL_IDS, on_progress=_progress, on_done=_done)

    def _on_close(self) -> None:
        self._poller.stop()
        self._client.disconnect()
        self.destroy()
