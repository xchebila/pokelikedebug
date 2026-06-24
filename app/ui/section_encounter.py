"""Encounter tab — full-space panel with a native Listbox for performance."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

import customtkinter as ctk

from ..pokemon_data import ALL_IDS, POKEMON_NAMES, get_name
from ..sprite_loader import load_sprite

GameState = dict[str, Any]

_OVERRIDE_JS = """
(function(id) {{
    window._forcedEncounterId = id;
    if (!window._getCatchChoicesPatched) {{
        const _orig = window.getCatchChoices;
        window.getCatchChoices = async function(...args) {{
            if (window._forcedEncounterId != null) {{
                const forcedId = window._forcedEncounterId;
                window._forcedEncounterId = null;
                const s = await fetchPokemonById(forcedId);
                if (s) return [s, s, s];
            }}
            return _orig.apply(this, args);
        }};
        window._getCatchChoicesPatched = true;
    }}
}})({pid})
"""

_CLEAR_JS = "window._forcedEncounterId = null;"

# Pre-build the full list once
_ALL_ENTRIES: list[tuple[int, str]] = [(pid, POKEMON_NAMES[pid]) for pid in ALL_IDS]


class EncounterSection(ctk.CTkFrame):
    """Fills the entire Rencontre tab."""

    def __init__(self, parent: ctk.CTkBaseClass, evaluate: Callable[[str], object]) -> None:
        super().__init__(parent, fg_color="transparent")
        self._evaluate    = evaluate
        self._selected_id: int | None = None
        self._lang: str = "en"
        self._filtered    = _ALL_ENTRIES  # current visible subset

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Search
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(
            self,
            textvariable=self._search_var,
            placeholder_text="Rechercher un Pokémon...",
            height=34,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        # Native Listbox — single widget regardless of list length
        list_frame = tk.Frame(self, bg="#1e1e1e")
        list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self._listbox = tk.Listbox(
            list_frame,
            bg="#1e1e1e",
            fg="#ffffff",
            selectbackground="#1f6aa5",
            selectforeground="#ffffff",
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            font=("Helvetica", 12),
        )
        self._listbox.grid(row=0, column=0, sticky="nsew")
        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        sb = tk.Scrollbar(list_frame, orient="vertical", command=self._listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._listbox.configure(yscrollcommand=sb.set)

        self._populate_listbox(_ALL_ENTRIES)

        # Bottom controls
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

        # Sprite + selection info side by side
        info_row = ctk.CTkFrame(bottom, fg_color="transparent")
        info_row.pack(fill="x", pady=(0, 4))

        self._sprite_label = ctk.CTkLabel(info_row, text="", image=None, width=72, height=72)
        self._sprite_label.pack(side="left", padx=(0, 10))
        self._sprite_ref: object = None  # keep PhotoImage alive

        info_text = ctk.CTkFrame(info_row, fg_color="transparent")
        info_text.pack(side="left", fill="x", expand=True)

        self._selection_label = ctk.CTkLabel(
            info_text, text="Aucun Pokémon sélectionné", text_color="#aaa", anchor="w"
        )
        self._selection_label.pack(fill="x")

        self._status_label = ctk.CTkLabel(
            info_text, text="Aucun override actif", text_color="#666", anchor="w"
        )
        self._status_label.pack(fill="x", pady=(4, 0))

        btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_row.pack(fill="x")

        self._apply_btn = ctk.CTkButton(
            btn_row,
            text="Appliquer pour la prochaine rencontre",
            height=32,
            state="disabled",
            command=self._apply,
        )
        self._apply_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Annuler", width=80, height=32,
            fg_color="#555", hover_color="#444",
            command=self._cancel,
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Listbox helpers
    # ------------------------------------------------------------------

    def _populate_listbox(self, entries: list[tuple[int, str]]) -> None:
        self._filtered = entries
        self._listbox.delete(0, tk.END)
        for pid, name in entries:
            self._listbox.insert(tk.END, f"  #{pid:03d}  {name}")

    def _all_entries_for_lang(self) -> list[tuple[int, str]]:
        return [(pid, get_name(pid, self._lang)) for pid in ALL_IDS]

    def _apply_filter(self) -> None:
        q = self._search_var.get().strip().lower()
        filtered = [
            (pid, get_name(pid, self._lang)) for pid in ALL_IDS
            if not q
            or q in get_name(pid, self._lang).lower()
            or q in POKEMON_NAMES.get(pid, "").lower()
            or q == str(pid)
        ]
        self._populate_listbox(filtered)

    def set_language(self, lang: str) -> None:
        self._lang = lang
        self._apply_filter()

    def _on_listbox_select(self, _: tk.Event) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        pid, _ = self._filtered[sel[0]]
        self._selected_id = pid
        self._selection_label.configure(
            text=f"Sélectionné : #{pid:03d}  {get_name(pid, self._lang)}", text_color="#fff"
        )
        self._apply_btn.configure(state="normal")
        load_sprite(
            pid,
            lambda img: self.after(0, lambda: self._set_sprite(img)),
            size=(72, 72),
        )

    def _set_sprite(self, pil_img: object) -> None:
        try:
            ctk_img = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=(72, 72)
            )
            self._sprite_ref = ctk_img  # prevent GC
            self._sprite_label.configure(image=ctk_img, text="")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # State sync
    # ------------------------------------------------------------------

    def update(self, state: GameState) -> None:
        pending = state.get("forcedPending", False)
        if pending and self._selected_id is not None:
            name = get_name(self._selected_id, self._lang)
            self._status_label.configure(
                text=f"En attente — prochaine rencontre : {name}", text_color="#2ecc71"
            )
        else:
            self._status_label.configure(text="Aucun override actif", text_color="#666")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _apply(self) -> None:
        if self._selected_id is None:
            return
        try:
            self._evaluate(_OVERRIDE_JS.format(pid=self._selected_id))
            name = get_name(self._selected_id, self._lang)
            self._status_label.configure(
                text=f"En attente — prochaine rencontre : {name}", text_color="#2ecc71"
            )
        except Exception:
            pass

    def _cancel(self) -> None:
        try:
            self._evaluate(_CLEAR_JS)
        except Exception:
            pass
        self._status_label.configure(text="Aucun override actif", text_color="#666")
