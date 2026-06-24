"""First-launch setup screen — shown once until the user confirms the script is installed."""

from __future__ import annotations

import http.server
import os
import socketserver
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path

import customtkinter as ctk

_SETUP_FLAG = Path.home() / ".pokelike-debugger" / "setup_done"
_TM_FAQ_URL  = "https://www.tampermonkey.net/faq.php?q=Q209#Q209"


def is_setup_done() -> bool:
    return _SETUP_FLAG.exists()


def _userscript_path() -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.join(os.path.dirname(__file__), "..")
    return os.path.normpath(os.path.join(base, "pokelike_debugger.user.js"))


def _serve_userscript() -> str:
    """Serve the userscript over HTTP so Tampermonkey intercepts the .user.js URL."""
    with open(_userscript_path(), "rb") as f:
        content = f.read()

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_: object) -> None:
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.handle_request, daemon=True).start()
    return f"http://127.0.0.1:{port}/pokelike_debugger.user.js"


_TAMPERMONKEY_LINKS = [
    ("Chrome",  "https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo"),
    ("Firefox", "https://addons.mozilla.org/firefox/addon/tampermonkey/"),
    ("Edge",    "https://microsoftedge.microsoft.com/addons/detail/tampermonkey/iikmkjmpaadaobahmlepeloendndfphd"),
    ("Opera",   "https://addons.opera.com/extensions/details/tampermonkey-beta/"),
]


class SetupScreen(ctk.CTkToplevel):
    """Modal window shown on first launch (or reopened via ⚙ button)."""

    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        self.title("Pokelike Debugger — Configuration")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self._script_url: str | None = None
        self._build_ui()

        # Let tkinter compute natural size, then fix it
        self.update_idletasks()
        self.geometry(f"520x{self.winfo_reqheight()}")

    def _sep(self) -> None:
        ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x", padx=24, pady=10)

    def _build_ui(self) -> None:
        pad = {"padx": 24, "pady": 6}

        ctk.CTkLabel(
            self,
            text="Configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=(
                "Pour fonctionner avec n'importe quel navigateur, cette app\n"
                "utilise un script Tampermonkey plutôt qu'un Chrome dédié."
            ),
            text_color="#aaa",
            justify="center",
        ).pack(pady=(0, 4))

        self._sep()

        # ── Étape 1 ──────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Étape 1 — Installer Tampermonkey",
                     font=ctk.CTkFont(weight="bold"), anchor="w").pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Choisissez votre navigateur :",
                     text_color="#aaa", anchor="w").pack(fill="x", padx=24)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=4)
        for name, url in _TAMPERMONKEY_LINKS:
            ctk.CTkButton(btn_row, text=name, width=100, height=28,
                          fg_color="#333", hover_color="#444",
                          command=lambda u=url: webbrowser.open(u),
                          ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(self, text="Si Tampermonkey est déjà installé, passez à l'étape 2.",
                     text_color="#666", font=ctk.CTkFont(size=11), anchor="w",
                     ).pack(fill="x", padx=24)

        self._sep()

        # ── Étape 2 ──────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Étape 2 — Installer le script",
                     font=ctk.CTkFont(weight="bold"), anchor="w").pack(fill="x", **pad)

        ctk.CTkLabel(self,
                     text="Cliquez ci-dessous — Tampermonkey proposera l'installation.",
                     text_color="#aaa", anchor="w").pack(fill="x", padx=24)

        ctk.CTkButton(self, text="Installer le script Tampermonkey", height=34,
                      command=self._install_script,
                      ).pack(padx=24, pady=(6, 4), fill="x")

        self._status_label = ctk.CTkLabel(
            self, text="", text_color="#2ecc71", font=ctk.CTkFont(size=11), anchor="w"
        )
        self._status_label.pack(fill="x", padx=24)

        # URL fallback — always in layout, initially hidden
        self._url_outer = ctk.CTkFrame(self, fg_color="transparent")
        self._url_outer.pack(fill="x", padx=24, pady=(2, 0))

        self._url_inner = ctk.CTkFrame(self._url_outer, fg_color="transparent")
        # not packed yet — shown on first install click

        ctk.CTkLabel(self._url_inner,
                     text="Si rien ne s'affiche, copiez ce lien dans votre navigateur :",
                     text_color="#555", font=ctk.CTkFont(size=11), anchor="w",
                     ).pack(fill="x")

        entry_row = ctk.CTkFrame(self._url_inner, fg_color="transparent")
        entry_row.pack(fill="x", pady=(2, 0))

        self._url_entry = tk.Entry(
            entry_row, state="readonly", relief="flat",
            bg="#2b2b2b", fg="#aaaaaa", readonlybackground="#2b2b2b",
            font=("Courier", 10), bd=0,
        )
        self._url_entry.pack(side="left", fill="x", expand=True, ipady=4)

        ctk.CTkButton(entry_row, text="Copier", width=60, height=26,
                      command=self._copy_url,
                      ).pack(side="left", padx=(6, 0))

        self._sep()

        # ── Étape 3 ──────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Étape 3 — Autoriser les scripts dans Tampermonkey",
                     font=ctk.CTkFont(weight="bold"), anchor="w").pack(fill="x", **pad)

        note_frame = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=6)
        note_frame.pack(fill="x", padx=24, pady=(0, 6))

        ctk.CTkLabel(
            note_frame,
            text=(
                "Certains navigateurs (ex : Arc, Chrome récent) désactivent les\n"
                "userscripts par défaut. Si le badge \"🔌\" n'apparaît pas sur le jeu :"
            ),
            text_color="#aaa", font=ctk.CTkFont(size=11),
            justify="left", anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            note_frame,
            text="1. Ouvrez Tampermonkey → Tableau de bord → Paramètres\n"
                 "2. Passez le niveau de sécurité sur « Détendu » ou activez\n"
                 "    les scripts utilisateur dans les paramètres avancés.",
            text_color="#ccc", font=ctk.CTkFont(size=11),
            justify="left", anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkButton(
            note_frame,
            text="Voir l'aide officielle Tampermonkey →",
            height=26, fg_color="transparent", hover_color="#2a2a2a",
            text_color="#5b9bd5", font=ctk.CTkFont(size=11),
            anchor="w",
            command=lambda: webbrowser.open(_TM_FAQ_URL),
        ).pack(fill="x", padx=6, pady=(0, 6))

        self._sep()

        ctk.CTkButton(
            self,
            text="C'est fait, démarrer l'app →",
            height=36,
            fg_color="#1f6aa5", hover_color="#1a5a8f",
            command=self._finish,
        ).pack(padx=24, pady=(0, 20), fill="x")

    # ------------------------------------------------------------------

    def _install_script(self) -> None:
        try:
            url = _serve_userscript()
        except Exception as exc:
            self._status_label.configure(text=f"Erreur : {exc}", text_color="#e74c3c")
            return

        self._script_url = url

        self._url_entry.configure(state="normal")
        self._url_entry.delete(0, tk.END)
        self._url_entry.insert(0, url)
        self._url_entry.configure(state="readonly")

        # Show the URL row now that we have a URL
        if not self._url_inner.winfo_ismapped():
            self._url_inner.pack(fill="x")
            self.update_idletasks()
            self.geometry(f"520x{self.winfo_reqheight()}")

        webbrowser.open(url)
        self._status_label.configure(
            text="Lien ouvert — Tampermonkey devrait proposer l'installation.",
            text_color="#2ecc71",
        )

    def _copy_url(self) -> None:
        if self._script_url:
            self.clipboard_clear()
            self.clipboard_append(self._script_url)
            self._status_label.configure(text="Lien copié !", text_color="#2ecc71")

    def _finish(self) -> None:
        _SETUP_FLAG.parent.mkdir(parents=True, exist_ok=True)
        _SETUP_FLAG.touch()
        self.grab_release()
        self.destroy()
