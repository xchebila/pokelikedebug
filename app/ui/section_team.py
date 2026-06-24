"""Section — Team editor."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from .widgets import CollapsibleSection
from ..sprite_loader import load_sprite

GameState = dict[str, Any]


class TeamSection(CollapsibleSection):
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        evaluate: Callable[[str], object],
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, "⚔️  Équipe")
        self._evaluate    = evaluate
        self._on_refresh  = on_refresh
        self._rows: list[_PokemonRow] = []

        ctk.CTkButton(
            self.body,
            text="Rafraîchir l'équipe",
            height=28,
            command=self._request_refresh,
        ).pack(anchor="e", padx=12, pady=(8, 4))

        self._list_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self._list_frame.pack(fill="x", padx=8, pady=(0, 8))

    def update(self, state: GameState) -> None:
        team: list[dict] = state.get("team", [])

        # Rebuild rows only when team size changes
        if len(team) != len(self._rows):
            for row in self._rows:
                row.destroy()
            self._rows = [
                _PokemonRow(self._list_frame, i, self._evaluate)
                for i in range(len(team))
            ]

        for row, mon in zip(self._rows, team):
            row.refresh(mon)

    def _request_refresh(self) -> None:
        if self._on_refresh:
            self._on_refresh()


_STATS: list[list[tuple[str, str]]] = [
    [("HP",      "hp"),      ("ATK",     "atk"),     ("DEF",     "def")],
    [("VIT",     "speed"),   ("Atk Spé", "special"), ("Déf Spé", "spdef")],
]


class _PokemonRow(ctk.CTkFrame):
    """One row per Pokémon in the team."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        index: int,
        evaluate: Callable[[str], object],
    ) -> None:
        super().__init__(parent, fg_color=("#2a2a2a", "#2a2a2a"), corner_radius=6)
        self.pack(fill="x", pady=2)

        self._index      = index
        self._evaluate   = evaluate
        self._sprite_ref: object = None
        self._last_sid: int = -1

        # ── Top row : sprite | name | level | HP/maxHP | Apply ──────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=(6, 2))

        self._sprite_lbl = ctk.CTkLabel(top, text="", image=None, width=44, height=44)
        self._sprite_lbl.pack(side="left", padx=(0, 6))

        name_frame = ctk.CTkFrame(top, fg_color="transparent")
        name_frame.pack(side="left", fill="x", expand=True)

        self._name_label  = ctk.CTkLabel(name_frame, text="—", anchor="w", width=110)
        self._name_label.pack(side="left")
        self._shiny_label = ctk.CTkLabel(name_frame, text="", text_color="#f1c40f", width=20)
        self._shiny_label.pack(side="left")

        ctrl = ctk.CTkFrame(top, fg_color="transparent")
        ctrl.pack(side="right")

        ctk.CTkLabel(ctrl, text="Niv.", width=28).pack(side="left")
        self._lvl_entry = ctk.CTkEntry(ctrl, width=44)
        self._lvl_entry.pack(side="left", padx=2)

        ctk.CTkLabel(ctrl, text="HP", width=22).pack(side="left", padx=(6, 0))
        self._hp_entry = ctk.CTkEntry(ctrl, width=44)
        self._hp_entry.pack(side="left", padx=2)
        self._hp_max_label = ctk.CTkLabel(ctrl, text="/ —", width=40, anchor="w")
        self._hp_max_label.pack(side="left")

        ctk.CTkButton(ctrl, text="Apply", width=52, height=26,
                      command=self._apply).pack(side="left", padx=(8, 0))

        # ── Base stats (2 rows × 3 stats) ────────────────────────────────
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=6, pady=(0, 6))

        self._stat_entries: dict[str, ctk.CTkEntry] = {}
        for r, stat_row in enumerate(_STATS):
            for c, (label, key) in enumerate(stat_row):
                ctk.CTkLabel(stats_frame, text=label, width=52,
                             font=ctk.CTkFont(size=10), text_color="#aaa",
                             anchor="e").grid(row=r, column=c * 2, padx=(4, 2), pady=1, sticky="e")
                e = ctk.CTkEntry(stats_frame, width=52, height=24)
                e.grid(row=r, column=c * 2 + 1, padx=(0, 8), pady=1, sticky="w")
                self._stat_entries[key] = e

    def refresh(self, mon: dict) -> None:
        name   = mon.get("name", "???")
        shiny  = mon.get("isShiny", False)
        lvl    = mon.get("level", 0)
        hp     = mon.get("currentHp", 0)
        max_hp = mon.get("maxHp", 0)
        sid    = mon.get("speciesId", 0)
        bs     = mon.get("baseStats", {})

        self._name_label.configure(text=name)
        self._shiny_label.configure(text="★" if shiny else "")
        self._hp_max_label.configure(text=f"/ {max_hp}")

        self._lvl_entry.delete(0, "end")
        self._lvl_entry.insert(0, str(lvl))
        self._hp_entry.delete(0, "end")
        self._hp_entry.insert(0, str(hp))

        for key, entry in self._stat_entries.items():
            entry.delete(0, "end")
            entry.insert(0, str(bs.get(key, 0)))

        if sid and sid != self._last_sid:
            self._last_sid = sid
            load_sprite(
                sid,
                lambda img: self.after(0, lambda: self._set_sprite(img)),
                size=(44, 44),
                shiny=shiny,
            )

    def _set_sprite(self, pil_img: object) -> None:
        try:
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(44, 44))
            self._sprite_ref = ctk_img
            self._sprite_lbl.configure(image=ctk_img)
        except Exception:
            pass

    def _apply(self) -> None:
        try:
            lvl = int(self._lvl_entry.get())
            hp  = int(self._hp_entry.get())
        except ValueError:
            return

        i = self._index
        parts = [
            f"state.team[{i}].level = {lvl}",
            f"state.team[{i}].currentHp = {hp}",
        ]
        for key, entry in self._stat_entries.items():
            try:
                val = int(entry.get())
                parts.append(f"state.team[{i}].baseStats.{key} = {val}")
            except ValueError:
                pass
        parts.append("saveRun()")

        try:
            self._evaluate("; ".join(parts) + ";")
        except Exception:
            pass
