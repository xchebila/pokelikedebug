"""Shared reusable UI components."""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import customtkinter as ctk


class CollapsibleSection(ctk.CTkFrame):
    """A labeled frame whose body can be toggled visible/hidden."""

    def __init__(self, parent: ctk.CTkBaseClass, title: str, **kwargs: object) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)  # type: ignore[arg-type]

        self._expanded = True

        self._toggle_btn = ctk.CTkButton(
            self,
            text=f"  {title}",
            anchor="w",
            height=34,
            corner_radius=8,
            fg_color=("#2b2b2b", "#2b2b2b"),
            hover_color=("#3a3a3a", "#3a3a3a"),
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._toggle,
        )
        self._toggle_btn.pack(fill="x", pady=(6, 0))
        self._update_arrow()

        self.body = ctk.CTkFrame(self, fg_color=("#1e1e1e", "#1e1e1e"), corner_radius=8)
        self.body.pack(fill="x", padx=2, pady=(2, 6))

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._update_arrow()
        if self._expanded:
            self.body.pack(fill="x", padx=2, pady=(2, 6))
        else:
            self.body.pack_forget()

    def _update_arrow(self) -> None:
        arrow = "▼" if self._expanded else "▶"
        current = self._toggle_btn.cget("text")
        # Replace leading arrow (or prepend if none)
        text = current.lstrip("▼▶ ")
        self._toggle_btn.configure(text=f"{arrow}  {text}")


class LabeledEntry(ctk.CTkFrame):
    """A compact label + entry on one row."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        label: str,
        width: int = 80,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)  # type: ignore[arg-type]
        ctk.CTkLabel(self, text=label, width=90, anchor="w").pack(side="left")
        self.entry = ctk.CTkEntry(self, width=width)
        self.entry.pack(side="left", padx=(4, 0))

    @property
    def value(self) -> str:
        return self.entry.get()

    def set(self, text: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, text)


class SearchableList(ctk.CTkFrame):
    """
    A search entry + scrollable list of (id, label) items.
    Calls on_select(item_id) when an item is clicked.
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        items: list[tuple[int, str]],
        on_select: object,
        height: int = 200,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)  # type: ignore[arg-type]
        self._all_items  = items
        self._on_select  = on_select
        self._selected   = ctk.StringVar(value="")
        self._buttons: dict[int, ctk.CTkButton] = {}

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter())

        ctk.CTkEntry(
            self, textvariable=self._search_var, placeholder_text="Rechercher..."
        ).pack(fill="x", pady=(0, 4))

        self._scroll = ctk.CTkScrollableFrame(self, height=height)
        self._scroll.pack(fill="both", expand=True)

        self._render(items)

    def _render(self, items: list[tuple[int, str]]) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        self._buttons.clear()
        for pid, name in items:
            label = f"#{pid:03d}  {name}"
            btn = ctk.CTkButton(
                self._scroll,
                text=label,
                anchor="w",
                height=26,
                corner_radius=4,
                fg_color="transparent",
                hover_color=("#3a3a3a", "#3a3a3a"),
                command=lambda p=pid, n=name: self._select(p, n),
            )
            btn.pack(fill="x", pady=1)
            self._buttons[pid] = btn

    def _filter(self) -> None:
        q = self._search_var.get().lower()
        filtered = [
            (pid, name)
            for pid, name in self._all_items
            if q in name.lower() or q == str(pid)
        ]
        self._render(filtered)

    def _select(self, pid: int, name: str) -> None:
        self._selected.set(f"#{pid:03d}  {name}")
        if self._on_select:
            self._on_select(pid)  # type: ignore[call-arg]

    @property
    def selected_label(self) -> str:
        return self._selected.get()


class Checkbox(tk.Canvas):
    """Canvas-drawn checkbox — consistent size and style on all platforms."""

    SZ           = 20
    _BOX_OFF     = "#2a2a2a"
    _BOX_ON      = "#1f6aa5"
    _BORDER_OFF  = "#666666"
    _BORDER_ON   = "#1f6aa5"

    def __init__(
        self,
        parent: tk.Widget,
        var: tk.BooleanVar,
        command: object,
        bg: str,
    ) -> None:
        super().__init__(
            parent,
            width=self.SZ, height=self.SZ,
            bg=bg, bd=0, highlightthickness=0,
        )
        self._var     = var
        self._command = command
        self._draw()
        var.trace_add("write", lambda *_: self.after(0, self._draw))
        self.bind("<Button-1>", self._click)

    def _draw(self) -> None:
        self.delete("all")
        on   = self._var.get()
        fill = self._BOX_ON    if on else self._BOX_OFF
        bdr  = self._BORDER_ON if on else self._BORDER_OFF
        m    = 2
        self.create_rectangle(m, m, self.SZ - m, self.SZ - m,
                              fill=fill, outline=bdr, width=1.5)
        if on:
            self.create_line(4, 10, 8, 15,  fill="white", width=2.5,
                             capstyle="round", joinstyle="round")
            self.create_line(8, 15, 16, 5, fill="white", width=2.5,
                             capstyle="round", joinstyle="round")

    def _click(self, _: tk.Event) -> None:
        self._var.set(not self._var.get())
        if self._command:
            self._command()  # type: ignore[call-arg]


class PokemonCanvasList(tk.Frame):
    """
    High-performance Pokémon list renderer using a single tk.Canvas.

    Instead of one Frame+Label+Canvas+Label per row (thousands of widgets),
    every row is drawn as lightweight canvas items — zero layout-engine overhead.
    Handles sprites, checkboxes, filtering, and language switching.

    on_toggle(pid, new_checked: bool) is called when the user clicks a row.
    """

    ROW_H    = 38
    N_COLS   = 2
    SPRITE   = 28
    CB_SZ    = 16
    PAD      = 6
    _BG      = "#1e1e1e"
    _CB_OFF  = ("#2a2a2a", "#666666")   # fill, outline
    _CB_ON   = ("#1f6aa5", "#1f6aa5")
    _FG      = "#cccccc"
    _FONT    = ("Helvetica", 12)

    def __init__(
        self,
        parent: tk.Widget,
        pids: list[int],
        lang: str,
        on_toggle: Callable[[int, bool], None],
        get_name: Callable[[int, str], str],
        bg: str = _BG,
    ) -> None:
        super().__init__(parent, bg=bg)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._all_pids  = list(pids)
        self._vis_pids  = list(pids)
        self._lang      = lang
        self._on_toggle = on_toggle
        self._get_name  = get_name
        self._checked:  dict[int, bool]   = {}
        self._sprites:  dict[int, object] = {}   # PhotoImage refs (keep-alive)
        self._img_ids:  dict[int, int]    = {}   # canvas item id for image
        self._row_pos:  dict[int, tuple[int, int]] = {}  # pid → (x0, y0)
        self._col_w     = 0
        self._pending_draw = False

        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._sb = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._sb.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._yscroll_cb)

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Enter>", lambda _: self._bind_wheel())
        self._canvas.bind("<Leave>", lambda _: self._unbind_wheel())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_checked(self, pid: int, value: bool) -> None:
        if self._checked.get(pid) == value:
            return
        self._checked[pid] = value
        if pid in self._row_pos:
            self._redraw_checkbox(pid)

    def apply_all(self, checked_set: "set[int]") -> None:
        """Bulk-update all checkbox states and redraw."""
        self._checked = {p: (p in checked_set) for p in self._all_pids}
        self._redraw_all()

    def set_sprite(self, pid: int, photo: object) -> None:
        self._sprites[pid] = photo
        img_id = self._img_ids.get(pid)
        if img_id:
            self._canvas.itemconfig(img_id, image=photo)  # type: ignore[arg-type]

    def apply_filter(self, q: str) -> None:
        q = q.strip().lower()
        if q:
            self._vis_pids = [
                p for p in self._all_pids
                if q in self._get_name(p, self._lang).lower()
                or q in self._get_name(p, "en").lower()
                or q == str(p)
            ]
        else:
            self._vis_pids = list(self._all_pids)
        self._redraw_all()

    def set_language(self, lang: str) -> None:
        self._lang = lang
        for pid in self._vis_pids:
            self._canvas.itemconfig(
                f"txt_{pid}",
                text=f"#{pid:03d}  {self._get_name(pid, lang)}",
            )

    # ------------------------------------------------------------------
    # Internal drawing
    # ------------------------------------------------------------------

    def _redraw_all(self) -> None:
        if self._col_w == 0:
            return
        self._canvas.delete("all")
        self._img_ids.clear()
        self._row_pos.clear()

        col_w   = self._col_w
        n       = len(self._vis_pids)
        n_rows  = max(1, (n + self.N_COLS - 1) // self.N_COLS)
        total_h = n_rows * self.ROW_H
        self._canvas.configure(scrollregion=(0, 0, col_w * self.N_COLS, total_h))

        for idx, pid in enumerate(self._vis_pids):
            col = idx % self.N_COLS
            row = idx // self.N_COLS
            x0  = col * col_w
            y0  = row * self.ROW_H
            self._row_pos[pid] = (x0, y0)
            self._draw_row(pid, x0, y0, col_w)

    def _draw_row(self, pid: int, x0: int, y0: int, col_w: int) -> None:
        cx = x0 + self.PAD + self.SPRITE // 2
        cy = y0 + self.ROW_H // 2

        img_id = self._canvas.create_image(cx, cy, anchor="center", tags=f"img_{pid}")
        self._img_ids[pid] = img_id
        if pid in self._sprites:
            self._canvas.itemconfig(img_id, image=self._sprites[pid])  # type: ignore[arg-type]

        self._redraw_checkbox(pid, x0, y0)

        tx = x0 + self.PAD + self.SPRITE + self.PAD + self.CB_SZ + self.PAD
        ty = y0 + self.ROW_H // 2
        self._canvas.create_text(
            tx, ty,
            text=f"#{pid:03d}  {self._get_name(pid, self._lang)}",
            fill=self._FG,
            font=self._FONT,
            anchor="w",
            tags=f"txt_{pid}",
        )

    def _redraw_checkbox(self, pid: int, x0: int = -1, y0: int = -1) -> None:
        if x0 < 0:
            pos = self._row_pos.get(pid)
            if pos is None:
                return
            x0, y0 = pos

        self._canvas.delete(f"cb_{pid}")
        cbx = x0 + self.PAD + self.SPRITE + self.PAD
        cby = y0 + (self.ROW_H - self.CB_SZ) // 2
        checked = self._checked.get(pid, False)
        fill, bdr = self._CB_ON if checked else self._CB_OFF
        self._canvas.create_rectangle(
            cbx, cby, cbx + self.CB_SZ, cby + self.CB_SZ,
            fill=fill, outline=bdr, width=1.5,
            tags=f"cb_{pid}",
        )
        if checked:
            self._canvas.create_line(
                cbx + 2, cby + 8, cbx + 6, cby + 12,
                fill="white", width=2, capstyle="round", joinstyle="round",
                tags=f"cb_{pid}",
            )
            self._canvas.create_line(
                cbx + 6, cby + 12, cbx + 13, cby + 3,
                fill="white", width=2, capstyle="round", joinstyle="round",
                tags=f"cb_{pid}",
            )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_resize(self, event: tk.Event) -> None:
        new_w = event.width // self.N_COLS
        if new_w == self._col_w:
            return
        self._col_w = new_w
        self._redraw_all()

    def _on_click(self, event: tk.Event) -> None:
        col_w = self._col_w
        if col_w == 0:
            return
        cy  = int(self._canvas.canvasy(event.y))
        cx  = int(self._canvas.canvasx(event.x))
        col = min(cx // col_w, self.N_COLS - 1)
        row = cy // self.ROW_H
        idx = row * self.N_COLS + col
        if 0 <= idx < len(self._vis_pids):
            pid = self._vis_pids[idx]
            new_val = not self._checked.get(pid, False)
            self._checked[pid] = new_val
            self._redraw_checkbox(pid)
            self._on_toggle(pid, new_val)

    def _yscroll_cb(self, first: str, last: str) -> None:
        if float(first) <= 0.0 and float(last) >= 1.0:
            self._sb.grid_remove()
        else:
            self._sb.grid()
        self._sb.set(first, last)

    def _bind_wheel(self) -> None:
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)
        self._canvas.bind_all("<Button-4>", lambda _: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind_all("<Button-5>", lambda _: self._canvas.yview_scroll(1, "units"))

    def _unbind_wheel(self) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event: tk.Event) -> None:
        delta = -1 * (event.delta // 120) if event.delta else 0
        self._canvas.yview_scroll(delta, "units")


class LightScrollFrame(tk.Frame):
    """
    Lightweight scrollable container — native tk.Canvas + tk.Scrollbar.
    Use everywhere instead of CTkScrollableFrame for smooth scrolling.
    Exposes `.inner` (tk.Frame) as the child container.
    """

    BG = "#1e1e1e"

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(parent, bg=self.BG, **kwargs)  # type: ignore[arg-type]
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, bg=self.BG, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._sb = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._sb.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._on_yscroll)

        self.inner = tk.Frame(self._canvas, bg=self.BG)
        self._win = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_resize)
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._canvas.bind("<Enter>", self._bind_wheel)
        self._canvas.bind("<Leave>", self._unbind_wheel)

    def _on_yscroll(self, first: str, last: str) -> None:
        if float(first) <= 0.0 and float(last) >= 1.0:
            self._sb.grid_remove()
        else:
            self._sb.grid()
        self._sb.set(first, last)

    def _on_inner_resize(self, _: tk.Event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_resize(self, event: tk.Event) -> None:
        self._canvas.itemconfig(self._win, width=event.width)

    def _bind_wheel(self, _: tk.Event) -> None:
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)
        self._canvas.bind_all("<Button-4>", lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind_all("<Button-5>", lambda e: self._canvas.yview_scroll(1, "units"))

    def _unbind_wheel(self, _: tk.Event) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event: tk.Event) -> None:
        delta = -1 * (event.delta // 120) if event.delta else 0
        self._canvas.yview_scroll(delta, "units")
