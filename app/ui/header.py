"""Connection status header bar."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

_STATUS_COLORS = {
    "connected":       "#2ecc71",
    "in_run":          "#2ecc71",
    "waiting_for_run": "#f39c12",
    "waiting_login":   "#f39c12",
    "connecting":      "#f39c12",
    "disconnected":    "#e74c3c",
}
_STATUS_LABELS = {
    "connected":       "Connecté",
    "in_run":          "Partie en cours",
    "waiting_for_run": "En attente d'une partie",
    "waiting_login":   "Connectez-vous à Pokelike",
    "connecting":      "Connexion...",
    "disconnected":    "Déconnecté",
}


class StatusHeader(ctk.CTkFrame):
    """
    Top bar showing connection status and a reconnect button.
    Call update_status(status) from any thread via widget.after().
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_reconnect: object,
        on_setup: Callable[[], None] | None = None,
        on_language_change: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=("#1a1a1a", "#1a1a1a"), corner_radius=10, **kwargs)  # type: ignore[arg-type]

        self._on_language_change = on_language_change
        self._on_setup = on_setup
        self._lang = "en"

        # Left: dot + label
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=12, pady=8)

        self._dot = ctk.CTkLabel(left, text="⬤", font=ctk.CTkFont(size=14))
        self._dot.pack(side="left")

        self._label = ctk.CTkLabel(left, text="Déconnecté", font=ctk.CTkFont(size=13))
        self._label.pack(side="left", padx=(6, 0))

        # Right: lang toggle + title + reconnect button
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=12, pady=8)

        ctk.CTkLabel(
            right, text="Pokelike Debugger", font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left", padx=(0, 12))

        self._lang_btn = ctk.CTkButton(
            right,
            text="FR",
            width=40,
            height=28,
            fg_color="#444",
            hover_color="#555",
            command=self._toggle_lang,
        )
        self._lang_btn.pack(side="left", padx=(0, 8))

        self._reconnect_btn = ctk.CTkButton(
            right,
            text="Reconnecter",
            width=110,
            height=28,
            command=on_reconnect,  # type: ignore[arg-type]
        )
        self._reconnect_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right,
            text="⚙",
            width=28,
            height=28,
            fg_color="#333",
            hover_color="#444",
            command=lambda: on_setup() if on_setup else None,
        ).pack(side="left")

        # Download progress (hidden by default)
        self._dl_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#888",
        )

        self.update_status("disconnected")

    def _toggle_lang(self) -> None:
        self._lang = "fr" if self._lang == "en" else "en"
        self._lang_btn.configure(text="EN" if self._lang == "fr" else "FR")
        if self._on_language_change:
            self._on_language_change(self._lang)

    def update_download_progress(self, done: int, total: int) -> None:
        if done >= total:
            self._dl_label.pack_forget()
        else:
            self._dl_label.configure(text=f"⬇ Sprites {done}/{total}")
            self._dl_label.pack(side="bottom", pady=(0, 4))

    def update_status(self, status: str) -> None:
        color = _STATUS_COLORS.get(status, "#e74c3c")
        label = _STATUS_LABELS.get(status, status)
        self._dot.configure(text_color=color)
        self._label.configure(text=label)
        self._reconnect_btn.configure(
            state="disabled" if status in ("connected", "in_run", "waiting_for_run", "waiting_login") else "normal"
        )
