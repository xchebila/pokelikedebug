"""Sprite loading and batch pre-caching.

Strategy
--------
* First launch : all sprites download in a background thread pool (~1300 files,
  a few MB total).  A progress callback lets the UI show status.
* Subsequent launches : instant load from disk.

Thread safety
-------------
load_sprite() calls back with a PIL Image (NOT a PhotoImage/CTkImage).
The caller must:
  1. Dispatch the callback onto the Tkinter main thread via widget.after().
  2. Convert to CTkImage *there* (Tk objects are not thread-safe).
"""

from __future__ import annotations

import concurrent.futures
import threading
import urllib.request
from pathlib import Path
from typing import Callable

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

_SPRITE_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
_CACHE = Path.home() / ".pokelike-debugger" / "sprites"
_CACHE.mkdir(parents=True, exist_ok=True)

_TIMEOUT = 10
_PRELOAD_WORKERS = 14


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_sprite(
    pid: int,
    callback: Callable[["Image.Image"], None],
    size: tuple[int, int] = (96, 96),
    shiny: bool = False,
) -> None:
    """Asynchronously load one sprite; call callback(pil_image) when ready.

    If the sprite is already on disk the callback fires almost instantly.
    Callback is called from a background thread — caller must dispatch to
    Tk main thread via widget.after().
    """
    if not PIL_OK:
        return
    threading.Thread(
        target=_load_one,
        args=(pid, callback, size, shiny),
        daemon=True,
        name=f"sprite-{pid}",
    ).start()


def preload_all(
    pids: list[int],
    on_progress: Callable[[int, int], None] | None = None,
    on_done: Callable[[], None] | None = None,
) -> None:
    """Download all missing sprites in a background thread pool.

    on_progress(done, total) is called after each completed download.
    on_done() is called when the batch finishes.
    Both callbacks fire from a background thread — dispatch to Tk via after().
    """
    if not PIL_OK:
        if on_done:
            on_done()
        return
    threading.Thread(
        target=_preload_worker,
        args=(pids, on_progress, on_done),
        daemon=True,
        name="sprite-preload",
    ).start()


def is_cached(pid: int, shiny: bool = False) -> bool:
    return _cache_path(pid, shiny).exists()


def load_sprites_batch(
    pids: list[int],
    callback: Callable[[int, "Image.Image"], None],
    size: tuple[int, int] = (32, 32),
) -> None:
    """Load a list of sprites sequentially in one background thread.

    callback(pid, pil_image) is called for each sprite as it loads.
    Caller must dispatch to the Tk main thread via widget.after().
    Cached sprites load from disk; missing ones are downloaded first.
    """
    if not PIL_OK:
        return
    threading.Thread(
        target=_batch_worker,
        args=(pids, callback, size),
        daemon=True,
        name="dex-sprite-batch",
    ).start()


def _batch_worker(
    pids: list[int],
    callback: Callable,
    size: tuple[int, int],
) -> None:
    for pid in pids:
        try:
            _download(pid, shiny=False)
            path = _cache_path(pid, False)
            if path.exists():
                img = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
                callback(pid, img)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _cache_path(pid: int, shiny: bool) -> Path:
    prefix = "shiny_" if shiny else ""
    return _CACHE / f"{prefix}{pid}.png"


def _download(pid: int, shiny: bool) -> None:
    """Download a single sprite to disk (no-op if already cached)."""
    path = _cache_path(pid, shiny)
    if path.exists():
        return
    suffix = f"shiny/{pid}.png" if shiny else f"{pid}.png"
    url = f"{_SPRITE_BASE}/{suffix}"
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
            path.write_bytes(resp.read())
    except Exception:
        pass


def _load_one(
    pid: int,
    callback: Callable,
    size: tuple[int, int],
    shiny: bool,
) -> None:
    try:
        _download(pid, shiny)
        path = _cache_path(pid, shiny)
        if not path.exists():
            return
        img = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
        callback(img)
    except Exception:
        pass


def _preload_worker(
    pids: list[int],
    on_progress: Callable[[int, int], None] | None,
    on_done: Callable[[], None] | None,
) -> None:
    todo = [pid for pid in pids if not _cache_path(pid, False).exists()]
    total = len(todo)
    if total == 0:
        if on_done:
            on_done()
        return

    done_count = 0

    def _task(pid: int) -> None:
        nonlocal done_count
        _download(pid, shiny=False)
        done_count += 1
        if on_progress:
            on_progress(done_count, total)

    with concurrent.futures.ThreadPoolExecutor(max_workers=_PRELOAD_WORKERS) as pool:
        pool.map(_task, todo)

    if on_done:
        on_done()
