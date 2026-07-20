"""Mega Bracelet tab — force-unlock and force-complete Mega Stone MVP requirements."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from .widgets import LightScrollFrame
from ..sprite_loader import load_sprite

GameState = dict[str, Any]


def _unlock_bracelet_js() -> str:
    return (
        "(function(){"
        "try{"
        "if(typeof isMegaBraceletUnlocked==='function'&&isMegaBraceletUnlocked())return true;"
        "if(typeof saveHallOfFameEntry==='function'){"
        "saveHallOfFameEntry([],0,false,true,6,null,false,null);return true;}"
        "return false;"
        "}catch(e){return false;}"
        "})();"
    )


def _bump_stone_js(species: int, delta: int) -> str:
    # Adjusts mvpCounts for `species` by `delta` (never below 0). Only
    # auto-unlocks the bracelet on a positive bump, so a -1 correction
    # doesn't unexpectedly unlock it.
    return (
        "(function(species,delta){"
        "try{"
        "var stats=JSON.parse(localStorage.getItem('poke_challenge_stats')||'{}');"
        "if(!stats.mvpCounts||typeof stats.mvpCounts!=='object')stats.mvpCounts={};"
        "stats.mvpCounts[species]=Math.max(0,(stats.mvpCounts[species]||0)+delta);"
        "localStorage.setItem('poke_challenge_stats',JSON.stringify(stats));"
        "if(delta>0&&typeof isMegaBraceletUnlocked==='function'&&!isMegaBraceletUnlocked()"
        "&&typeof saveHallOfFameEntry==='function'){"
        "saveHallOfFameEntry([],0,false,true,6,null,false,null);}"
        "return true;"
        "}catch(e){return false;}"
        f"}})({species},{delta});"
    )


def _complete_stone_js(species: int, required: int) -> str:
    # Tops up mvpCounts for `species` just enough that the game's own
    # megaLineMvpCount() (summed across the whole evolution line) reaches
    # `required` — instead of overwriting, so it respects whatever MVP
    # progress already exists anywhere in the line.
    return (
        "(function(species,req){"
        "try{"
        "var stats=JSON.parse(localStorage.getItem('poke_challenge_stats')||'{}');"
        "if(!stats.mvpCounts||typeof stats.mvpCounts!=='object')stats.mvpCounts={};"
        "var current=typeof megaLineMvpCount==='function'"
        "?megaLineMvpCount({species:species})"
        ":(stats.mvpCounts[species]||0);"
        "var needed=req-current;"
        "if(needed>0){"
        "stats.mvpCounts[species]=(stats.mvpCounts[species]||0)+needed;"
        "localStorage.setItem('poke_challenge_stats',JSON.stringify(stats));}"
        "if(typeof isMegaBraceletUnlocked==='function'&&!isMegaBraceletUnlocked()"
        "&&typeof saveHallOfFameEntry==='function'){"
        "saveHallOfFameEntry([],0,false,true,6,null,false,null);}"
        "return true;"
        "}catch(e){return false;}"
        f"}})({species},{required});"
    )


class MegaSection(ctk.CTkFrame):
    """Mega Bracelet tab: unlock status + one row per Mega Stone."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        evaluate: Callable[[str], object],
        fetch_mega: Callable[[Callable[[dict], None]], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self._evaluate   = evaluate
        self._fetch_mega = fetch_mega
        self._rows: list[_StoneRow] = []

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))

        self._status_label = ctk.CTkLabel(top, text="Bracelet : —")
        self._status_label.pack(side="left")

        ctk.CTkButton(top, text="↻ Sync", width=70, height=28, command=self.refresh).pack(
            side="right"
        )
        ctk.CTkButton(
            top, text="Débloquer bracelet", height=28, command=self._unlock_bracelet
        ).pack(side="right", padx=(0, 6))
        ctk.CTkButton(top, text="Tout compléter", height=28, command=self._complete_all).pack(
            side="right", padx=(0, 6)
        )

        self._scroll = LightScrollFrame(self)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self._fetch_mega(lambda data: self.after(0, lambda: self.apply(data)))

    def apply(self, data: dict) -> None:
        unlocked = bool(data.get("unlocked"))
        self._status_label.configure(
            text=f"Bracelet : {'débloqué ✅' if unlocked else 'verrouillé 🔒'}"
        )

        stones = data.get("stones") or []
        if len(stones) != len(self._rows):
            for row in self._rows:
                row.destroy()
            self._rows = [
                _StoneRow(self._scroll.inner, self._on_complete, self._on_bump)
                for _ in stones
            ]

        for row, s in zip(self._rows, stones):
            row.apply(s)

    def update(self, state: GameState) -> None:
        pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_complete(self, species: int, required: int) -> None:
        try:
            self._evaluate(_complete_stone_js(species, required))
        except Exception:
            return
        self.refresh()

    def _on_bump(self, species: int, delta: int) -> None:
        try:
            self._evaluate(_bump_stone_js(species, delta))
        except Exception:
            return
        self.refresh()

    def _complete_all(self) -> None:
        for row in self._rows:
            if row.species is not None and not row.owned:
                try:
                    self._evaluate(_complete_stone_js(row.species, row.required))
                except Exception:
                    pass
        self.refresh()

    def _unlock_bracelet(self) -> None:
        try:
            self._evaluate(_unlock_bracelet_js())
        except Exception:
            pass
        self.refresh()


class _StoneRow(ctk.CTkFrame):
    """One row per Mega Stone."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_complete: Callable[[int, int], None],
        on_bump: Callable[[int, int], None],
    ) -> None:
        super().__init__(parent, fg_color=("#2a2a2a", "#2a2a2a"), corner_radius=6)
        self.pack(fill="x", pady=2)
        self._on_complete = on_complete
        self._on_bump = on_bump
        self.species: int | None = None
        self.required: int = 1
        self.owned: bool = False
        self._sprite_ref: object = None
        self._last_species = -1

        self._sprite_lbl = ctk.CTkLabel(self, text="", image=None, width=32, height=32)
        self._sprite_lbl.pack(side="left", padx=(6, 6), pady=4)

        self._name_label = ctk.CTkLabel(self, text="—", anchor="w", width=160)
        self._name_label.pack(side="left")

        self._progress_label = ctk.CTkLabel(self, text="", width=80, text_color="#aaa")
        self._progress_label.pack(side="left", padx=(4, 0))

        self._btn = ctk.CTkButton(
            self, text="Compléter", width=80, height=26, command=self._complete
        )
        self._btn.pack(side="right", padx=6)

        self._plus_btn = ctk.CTkButton(
            self, text="+1", width=32, height=26, command=lambda: self._bump(1)
        )
        self._plus_btn.pack(side="right", padx=(0, 4))
        self._minus_btn = ctk.CTkButton(
            self, text="-1", width=32, height=26, fg_color="#555", hover_color="#444",
            command=lambda: self._bump(-1),
        )
        self._minus_btn.pack(side="right", padx=(0, 4))

    def apply(self, s: dict) -> None:
        self.species  = s.get("species")
        self.required = int(s.get("required") or 1)
        self.owned    = bool(s.get("owned"))
        current       = int(s.get("current") or 0)

        self._name_label.configure(text=str(s.get("name") or f"#{self.species}"))
        self._progress_label.configure(text=f"{current} / {self.required} MVP")
        self._btn.configure(
            state="disabled" if self.owned else "normal",
            text="Fait ✓" if self.owned else "Compléter",
        )

        if self.species and self.species != self._last_species:
            self._last_species = self.species
            load_sprite(
                self.species,
                lambda img: self.after(0, lambda: self._set_sprite(img)),
                size=(32, 32),
            )

    def _set_sprite(self, pil_img: object) -> None:
        try:
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
            self._sprite_ref = ctk_img
            self._sprite_lbl.configure(image=ctk_img)
        except Exception:
            pass

    def _complete(self) -> None:
        if self.species is not None:
            self._on_complete(self.species, self.required)

    def _bump(self, delta: int) -> None:
        if self.species is not None:
            self._on_bump(self.species, delta)
