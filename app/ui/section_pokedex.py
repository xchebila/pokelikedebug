"""Pokédex tab — canvas-based renderer for zero-lag scrolling."""

from __future__ import annotations

import tkinter.messagebox as mb
from typing import Callable

import customtkinter as ctk

from ..pokemon_data import ALL_IDS, GEN1_IDS, GENERATIONS, get_name
from ..sprite_loader import load_sprites_batch
from .widgets import PokemonCanvasList

_SPRITE_SZ = (28, 28)


class PokedexSection(ctk.CTkFrame):

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        evaluate: Callable[[str], object],
        fetch_dex: Callable[[Callable[[dict], None]], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self._evaluate  = evaluate
        self._fetch_dex = fetch_dex
        self._lang      = "en"
        self._cached_dex: dict = {}

        # One PokemonCanvasList per gen tab
        self._lists:    dict[str, PokemonCanvasList] = {}
        self._sprites:  dict[int, object] = {}   # PhotoImage refs shared across tabs
        self._built:    set[str] = set()

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text="Cocher/décocher = instantané sur la save  ·  'Tout décocher' = irréversible",
            font=ctk.CTkFont(size=11),
            text_color="#888",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(8, 0))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(
            self,
            textvariable=self._search_var,
            placeholder_text="Rechercher par nom ou #ID...",
            height=34,
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 6))

        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 4))

        for gen_label, _ in GENERATIONS:
            tab = self._tabs.add(gen_label)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)

        self._build_gen_tab(GENERATIONS[0][0])
        for i, (gen_label, _) in enumerate(GENERATIONS[1:], start=1):
            self.after(i * 50, lambda lbl=gen_label: self._build_gen_tab(lbl))
        self._tabs.configure(command=self._on_tab_change)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 10))

        ctk.CTkButton(btn_row, text="Unlock Gen 1", height=30,
                      command=self._unlock_gen1).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Unlock tout", height=30,
                      command=self._unlock_all).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Tout décocher", height=30,
                      fg_color="#555", hover_color="#444",
                      command=self._uncheck_all).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="↻ Sync", height=30,
                      command=self._refresh_dex).pack(side="left")

    def _build_gen_tab(self, gen_label: str) -> None:
        if gen_label in self._built:
            return
        self._built.add(gen_label)

        ids = next(ids for lbl, ids in GENERATIONS if lbl == gen_label)
        tab = self._tabs.tab(gen_label)

        cl = PokemonCanvasList(
            tab, ids, self._lang,
            on_toggle=self._on_toggle,
            get_name=get_name,
        )
        cl.grid(row=0, column=0, sticky="nsew")
        self._lists[gen_label] = cl

        # Apply already-known state
        if self._cached_dex:
            checked = {p for p in ids if self._cached_dex.get(str(p)) or self._cached_dex.get(p)}
            cl.apply_all(checked)

        # Apply already-loaded sprites
        for pid in ids:
            if pid in self._sprites:
                cl.set_sprite(pid, self._sprites[pid])

        load_sprites_batch(
            ids,
            lambda pid, img: self.after(0, lambda p=pid, i=img: self._set_sprite(p, i)),
            size=_SPRITE_SZ,
        )

    def _on_tab_change(self) -> None:
        self._build_gen_tab(self._tabs.get())

    # ------------------------------------------------------------------
    # Sprites
    # ------------------------------------------------------------------

    def _set_sprite(self, pid: int, pil_img: object) -> None:
        try:
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(pil_img)
            self._sprites[pid] = photo
            for cl in self._lists.values():
                cl.set_sprite(pid, photo)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Toggle → JS
    # ------------------------------------------------------------------

    def _on_toggle(self, pid: int, checked: bool) -> None:
        try:
            if checked:
                self._evaluate(f"markPokedexCaught({pid});")
            else:
                self._evaluate(
                    f"(function(){{var d=getPokedex();"
                    f"delete d[{pid}];delete d['{pid}'];"
                    f"localStorage.setItem('poke_dex',JSON.stringify(d));"
                    f"}})();"
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------

    def apply_dex(self, dex: dict) -> None:
        self._cached_dex = dex
        for gen_label, ids in GENERATIONS:
            cl = self._lists.get(gen_label)
            if cl is None:
                continue
            checked = {p for p in ids if dex.get(str(p)) or dex.get(p)}
            cl.apply_all(checked)

    def _refresh_dex(self) -> None:
        self._fetch_dex(self.apply_dex)

    def update(self, state: dict) -> None:
        pass

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _apply_filter(self) -> None:
        q = self._search_var.get()
        for cl in self._lists.values():
            cl.apply_filter(q)

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    def set_language(self, lang: str) -> None:
        self._lang = lang
        for cl in self._lists.values():
            cl.set_language(lang)

    # ------------------------------------------------------------------
    # Bulk actions
    # ------------------------------------------------------------------

    def _unlock_gen1(self) -> None:
        if mb.askyesno("Confirmation", "Débloquer les 151 Pokémon de la Gen 1 ?"):
            self._unlock_ids(GEN1_IDS)

    def _unlock_all(self) -> None:
        if mb.askyesno("Confirmation", "Débloquer les 649 Pokémon du Pokédex complet ?"):
            self._unlock_ids(ALL_IDS)

    def _unlock_ids(self, ids: list[int]) -> None:
        js = "".join(f"markPokedexCaught({pid});" for pid in ids)
        try:
            self._evaluate(js)
        except Exception:
            pass
        for gen_label, gen_ids in GENERATIONS:
            cl = self._lists.get(gen_label)
            if cl is None:
                continue
            to_set = set(ids) & set(gen_ids)
            if to_set:
                current = {p for p, v in cl._checked.items() if v}
                cl.apply_all(current | to_set)

    def _uncheck_all(self) -> None:
        if not mb.askyesno(
            "Confirmation",
            "Supprimer tous les Pokémon du Pokédex ?\nCette action est irréversible.",
        ):
            return
        try:
            self._evaluate("localStorage.setItem('poke_dex', JSON.stringify({}));")
        except Exception:
            pass
        for cl in self._lists.values():
            cl.apply_all(set())
