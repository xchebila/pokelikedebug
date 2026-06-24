"""Section — Force Shiny toggle."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from .widgets import CollapsibleSection

_JS_ON  = "rollShiny = () => true;"
_JS_OFF = "rollShiny = () => rng() < (hasShinyCharm() ? 0.02 : 0.01);"


class ShinySection(CollapsibleSection):
    def __init__(self, parent: ctk.CTkBaseClass, evaluate: Callable[[str], object]) -> None:
        super().__init__(parent, "✨  Force Shiny")
        self._evaluate = evaluate
        self._var = ctk.BooleanVar(value=False)

        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=12)

        ctk.CTkLabel(row, text="Activer pour la prochaine rencontre / starter").pack(side="left")
        ctk.CTkSwitch(
            row,
            text="",
            variable=self._var,
            onvalue=True,
            offvalue=False,
            command=self._on_toggle,
            width=44,
        ).pack(side="right")

    def _on_toggle(self) -> None:
        js = _JS_ON if self._var.get() else _JS_OFF
        try:
            self._evaluate(js)
        except Exception:
            pass
