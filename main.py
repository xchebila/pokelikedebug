"""Entry point."""

import sys
import traceback
from pathlib import Path

# Startup log — written with stdlib only, before any other import.
# If the app crashes before cdp_client is loaded, this is the only trace.
_LOG = Path.home() / ".pokelike-debugger" / "debugger.log"
_LOG.parent.mkdir(parents=True, exist_ok=True)


def _log(msg: str) -> None:
    with open(_LOG, "a") as f:
        f.write(msg + "\n")


_log(f"--- startup (Python {sys.version}, frozen={getattr(sys, 'frozen', False)}) ---")

try:
    from app.app import DebuggerApp
    _log("imports OK")

    if __name__ == "__main__":
        _log("launching DebuggerApp")
        DebuggerApp().mainloop()
        _log("mainloop exited cleanly")

except Exception:
    err = traceback.format_exc()
    _log("CRASH:\n" + err)
    # Show a native error dialog so the user knows something went wrong
    try:
        import tkinter as tk
        import tkinter.messagebox as mb
        root = tk.Tk()
        root.withdraw()
        mb.showerror(
            "Pokelike Debugger — Erreur de démarrage",
            f"L'application a planté au démarrage.\n\nLog : {_LOG}\n\n{err[:800]}",
        )
        root.destroy()
    except Exception:
        pass
    sys.exit(1)
