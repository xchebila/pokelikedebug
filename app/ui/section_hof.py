"""Hall of Fame Index tab — manage evoLineRoots, eggLegendaries, eggLegendaryShinies, shinySpecies."""

from __future__ import annotations

import tkinter.messagebox as mb
from typing import Callable

import customtkinter as ctk

from ..pokemon_data import ALL_IDS, GENERATIONS, LEGENDARY_IDS, get_name
from ..sprite_loader import load_sprites_batch
from .widgets import PokemonCanvasList

_SPRITE_SZ = (28, 28)

_KEYS = ["evoLineRoots", "eggLegendaries", "eggLegendaryShinies", "shinySpecies"]
_LABELS = {
    "evoLineRoots":        "Starters",
    "eggLegendaries":      "Œufs Légend.",
    "eggLegendaryShinies": "Œufs Légend. ✨",
    "shinySpecies":        "Espèces Shiny",
}
_IDS_FOR_KEY: dict[str, list[int]] = {
    "evoLineRoots":        ALL_IDS,
    "eggLegendaries":      LEGENDARY_IDS,
    "eggLegendaryShinies": LEGENDARY_IDS,
    "shinySpecies":        ALL_IDS,
}
_KEY_BY_LABEL = {v: k for k, v in _LABELS.items()}


def _add_js(key: str, pid: int) -> str:
    return (
        f"(function(){{var h=JSON.parse(localStorage.getItem('poke_hof_index')||'{{}}');"
        f"if(!Array.isArray(h['{key}']))h['{key}']=[];"
        f"if(!h['{key}'].includes({pid}))h['{key}'].push({pid});"
        f"localStorage.setItem('poke_hof_index',JSON.stringify(h));}})();"
    )


def _remove_js(key: str, pid: int) -> str:
    return (
        f"(function(){{var h=JSON.parse(localStorage.getItem('poke_hof_index')||'{{}}');"
        f"if(!Array.isArray(h['{key}']))return;"
        f"h['{key}']=h['{key}'].filter(function(x){{return x!=={pid};}});"
        f"localStorage.setItem('poke_hof_index',JSON.stringify(h));}})();"
    )


def _set_all_js(key: str, ids: list[int]) -> str:
    arr = ",".join(str(p) for p in ids)
    return (
        f"(function(){{var h=JSON.parse(localStorage.getItem('poke_hof_index')||'{{}}');"
        f"h['{key}']=[{arr}];"
        f"localStorage.setItem('poke_hof_index',JSON.stringify(h));}})();"
    )


def _clear_js(key: str) -> str:
    return (
        f"(function(){{var h=JSON.parse(localStorage.getItem('poke_hof_index')||'{{}}');"
        f"h['{key}']=[];"
        f"localStorage.setItem('poke_hof_index',JSON.stringify(h));}})();"
    )


class HofSection(ctk.CTkFrame):
    """Hall of Fame Index: manage starter unlocks and legendary eggs."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        evaluate: Callable[[str], object],
        fetch_hof: Callable[[Callable[[dict], None]], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self._evaluate  = evaluate
        self._fetch_hof = fetch_hof
        self._lang      = "en"

        self._lists:   dict[str, PokemonCanvasList] = {}
        self._sprites: dict[int, object] = {}   # shared PhotoImage refs
        self._built:   set[str] = set()
        self._hof_data: dict[str, list[int]] = {k: [] for k in _KEYS}

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text="Cocher/décocher = instantané sur la save",
            font=ctk.CTkFont(size=11),
            text_color="#888",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 0))

        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 4))

        for key in _KEYS:
            tab = self._tabs.add(_LABELS[key])
            tab.grid_rowconfigure(1, weight=1)
            tab.grid_columnconfigure(0, weight=1)

        self._search_vars: dict[str, ctk.StringVar] = {}
        for key in _KEYS:
            sv = ctk.StringVar()
            sv.trace_add("write", lambda *_, k=key, v=sv: self._apply_filter(k, v.get()))
            self._search_vars[key] = sv

        self._build_tab(self._tabs.get())
        self._tabs.configure(command=lambda: self._build_tab(self._tabs.get()))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

        ctk.CTkButton(btn_row, text="Unlock Gen 1", height=30,
                      command=self._unlock_gen1).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Unlock tout", height=30,
                      command=self._unlock_all).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Tout décocher", height=30,
                      fg_color="#555", hover_color="#444",
                      command=self._clear_current).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="↻ Sync", height=30,
                      command=self._refresh).pack(side="left")

    def _build_tab(self, label: str) -> None:
        key = _KEY_BY_LABEL.get(label)
        if key is None or key in self._built:
            return
        self._built.add(key)

        tab  = self._tabs.tab(label)
        ids  = _IDS_FOR_KEY[key]
        sv   = self._search_vars[key]

        ctk.CTkEntry(
            tab, textvariable=sv,
            placeholder_text="Rechercher par nom ou #ID...", height=30,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        cl = PokemonCanvasList(
            tab, ids, self._lang,
            on_toggle=lambda pid, chk, k=key: self._on_toggle(k, pid, chk),
            get_name=get_name,
        )
        cl.grid(row=1, column=0, sticky="nsew")
        self._lists[key] = cl

        # Apply already-known state
        if self._hof_data[key]:
            cl.apply_all(set(self._hof_data[key]))

        # Apply already-loaded sprites
        for pid in ids:
            if pid in self._sprites:
                cl.set_sprite(pid, self._sprites[pid])

        load_sprites_batch(
            ids,
            lambda pid, img: self.after(0, lambda p=pid, i=img: self._set_sprite(p, i)),
            size=_SPRITE_SZ,
        )

    # ------------------------------------------------------------------
    # Sprites
    # ------------------------------------------------------------------

    def _set_sprite(self, pid: int, pil_img: object) -> None:
        try:
            from PIL import ImageTk
            if pid not in self._sprites:
                photo = ImageTk.PhotoImage(pil_img)
                self._sprites[pid] = photo
            else:
                photo = self._sprites[pid]  # type: ignore[assignment]
            for cl in self._lists.values():
                cl.set_sprite(pid, photo)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Toggle → JS
    # ------------------------------------------------------------------

    def _on_toggle(self, key: str, pid: int, checked: bool) -> None:
        try:
            if checked:
                self._evaluate(_add_js(key, pid))
            else:
                self._evaluate(_remove_js(key, pid))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Filter / Language
    # ------------------------------------------------------------------

    def _apply_filter(self, key: str, q: str) -> None:
        cl = self._lists.get(key)
        if cl:
            cl.apply_filter(q)

    def set_language(self, lang: str) -> None:
        self._lang = lang
        for cl in self._lists.values():
            cl.set_language(lang)

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------

    def apply_hof(self, hof: dict) -> None:
        self._hof_data = {k: list(hof.get(k) or []) for k in _KEYS}
        for key, cl in self._lists.items():
            cl.apply_all(set(self._hof_data[key]))

    def _refresh(self) -> None:
        self._fetch_hof(self.apply_hof)

    def update(self, state: dict) -> None:
        pass

    # ------------------------------------------------------------------
    # Bulk actions (scoped to active tab)
    # ------------------------------------------------------------------

    def _current_key(self) -> str | None:
        return _KEY_BY_LABEL.get(self._tabs.get())

    def _unlock_gen1(self) -> None:
        key = self._current_key()
        if not key:
            return
        tab_ids  = _IDS_FOR_KEY[key]
        gen1_set = set(next(ids for lbl, ids in GENERATIONS if lbl == "Gen 1 — Kanto"))
        ids_to_add = [p for p in tab_ids if p in gen1_set]
        if not ids_to_add:
            return
        if mb.askyesno("Confirmation", f"Unlock les Pokémon Gen 1 dans '{_LABELS[key]}' ?"):
            merged = list(set(self._hof_data[key]) | set(ids_to_add))
            try:
                self._evaluate(_set_all_js(key, merged))
            except Exception:
                pass
            self._hof_data[key] = merged
            cl = self._lists.get(key)
            if cl:
                cl.apply_all(set(merged))

    def _unlock_all(self) -> None:
        key = self._current_key()
        if not key:
            return
        ids = _IDS_FOR_KEY[key]
        if mb.askyesno("Confirmation", f"Unlock tous les Pokémon disponibles dans '{_LABELS[key]}' ?"):
            try:
                self._evaluate(_set_all_js(key, ids))
            except Exception:
                pass
            self._hof_data[key] = list(ids)
            cl = self._lists.get(key)
            if cl:
                cl.apply_all(set(ids))

    def _clear_current(self) -> None:
        key = self._current_key()
        if not key:
            return
        if mb.askyesno(
            "Confirmation",
            f"Supprimer tous les Pokémon de '{_LABELS[key]}' ?\nIrréversible.",
        ):
            try:
                self._evaluate(_clear_js(key))
            except Exception:
                pass
            self._hof_data[key] = []
            cl = self._lists.get(key)
            if cl:
                cl.apply_all(set())
