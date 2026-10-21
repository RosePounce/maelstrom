# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe — identical on Windows and on Linux.

The graphics and the sound are drawn by the code. The bundled resources are
`assets/` (the font, its licence, the favicon) and the language files from
`maelstrom/locales/`; both are found again through `__file__`, which
PyInstaller points inside the package.
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), ".."))
PACKAGING = os.path.join(ROOT, "packaging")
WINDOWS = sys.platform.startswith("win")

icon = os.path.join(PACKAGING, "icon.ico" if WINDOWS else "icon.png")
if not os.path.exists(icon):
    icon = None

DATAS = [
    (os.path.join(ROOT, "assets"), "assets"),
    (os.path.join(ROOT, "maelstrom", "locales"),
     os.path.join("maelstrom", "locales")),
]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=DATAS,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "numpy", "matplotlib", "PIL", "pydoc", "doctest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Maelstrom",
    debug=False,
    strip=False,
    upx=False,
    console=False,          # no black window behind the game
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Maelstrom",
)
