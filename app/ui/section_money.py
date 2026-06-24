"""Section — Pokédollars editor."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from .widgets import CollapsibleSection

GameState = dict[str, Any]


class MoneySection(CollapsibleSection):
    def __init__(self, parent: ctk.CTkBaseClass, evaluate: Callable[[str], object]) -> None:
        super().__init__(parent, "💰  Pokédollars")
        self._evaluate = evaluate

        body = self.body

        # Current balance display
        balance_row = ctk.CTkFrame(body, fg_color="transparent")
        balance_row.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(balance_row, text="Solde actuel :").pack(side="left")
        self._balance_label = ctk.CTkLabel(
            balance_row, text="—", font=ctk.CTkFont(weight="bold"), text_color="#f1c40f"
        )
        self._balance_label.pack(side="left", padx=6)

        # Set row
        set_row = ctk.CTkFrame(body, fg_color="transparent")
        set_row.pack(fill="x", padx=12, pady=(0, 10))

        self._entry = ctk.CTkEntry(set_row, placeholder_text="Montant", width=120)
        self._entry.pack(side="left")

        ctk.CTkButton(set_row, text="Définir", width=80, height=28, command=self._set).pack(
            side="left", padx=(8, 0)
        )
        ctk.CTkButton(
            set_row, text="+1 000", width=80, height=28, command=self._add_1k
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            set_row, text="Max", width=60, height=28, command=self._set_max
        ).pack(side="left", padx=(8, 0))

    def update(self, state: GameState) -> None:
        dollars = state.get("dollars", 0)
        self._balance_label.configure(text=f"{dollars:,} ₽")

    def _set(self) -> None:
        try:
            amount = int(self._entry.get())
        except ValueError:
            return
        try:
            self._evaluate(f"setPokedollars({amount});")
        except Exception:
            pass

    def _add_1k(self) -> None:
        try:
            self._evaluate("addPokedollars(1000);")
        except Exception:
            pass

    def _set_max(self) -> None:
        try:
            self._evaluate("setPokedollars(9999999);")
        except Exception:
            pass
