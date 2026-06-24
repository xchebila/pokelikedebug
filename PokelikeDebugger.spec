# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Pokelike Debugger.
Build on each target platform:
  Mac:     pyinstaller PokelikeDebugger.spec
  Windows: pyinstaller PokelikeDebugger.spec
"""

import sys
from pathlib import Path
import customtkinter

# Path to the customtkinter package (themes, images, etc.)
CTK_PATH = Path(customtkinter.__file__).parent

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # customtkinter ships JSON themes and PNG assets — must be bundled
        (str(CTK_PATH), "customtkinter"),
        # Tampermonkey userscript — opened in browser on first launch
        ("pokelike_debugger.user.js", "."),
    ],
    hiddenimports=[
        "customtkinter",
        "PIL._tkinter_finder",
        "PIL.Image",
        "PIL.ImageTk",
        "PIL.ImageDraw",
        "PIL.ImageFilter",
        "websockets",
        "websockets.asyncio",
        "websockets.asyncio.server",
        "websockets.asyncio.connection",
        "websockets.asyncio.messages",
        "websockets.connection",
        "websockets.http11",
        "websockets.extensions",
        "websockets.extensions.permessage_deflate",
        "websockets.frames",
        "websockets.streams",
        "websockets.typing",
        "websockets.uri",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["playwright", "pytest", "numpy", "pandas", "matplotlib", "websocket"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == "darwin":
    # ── Mac: onedir mode → .app bundle ────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="PokelikeDebugger",
        debug=False,
        strip=False,
        upx=True,
        console=False,
        argv_emulation=False,
        icon="assets/icon.icns",
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        name="PokelikeDebugger",
    )
    app = BUNDLE(
        coll,
        name="PokelikeDebugger.app",
        icon="assets/icon.icns",
        bundle_identifier="com.pokelike.debugger",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
else:
    # ── Windows: single .exe ───────────────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="PokelikeDebugger",
        debug=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        icon="assets/icon.ico",
    )
