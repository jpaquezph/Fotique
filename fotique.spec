# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para Fotique (Windows, ejecutable de un solo archivo).

Uso:
    pyinstaller --noconfirm --clean fotique.spec
"""

from pathlib import Path

raiz = Path(SPECPATH)

# El esquema SQLite y el logo se leen con Path(__file__) y deben viajar junto
# al paquete.
recursos = raiz / "fotique" / "ui" / "recursos"
datos = [(str(raiz / "fotique" / "db" / "schema.sql"), "fotique/db"),
         (str(recursos), "fotique/ui/recursos")]

analisis = Analysis(
    [str(raiz / "main.py")],
    pathex=[str(raiz)],
    binaries=[],
    datas=datos,
    hiddenimports=["darkdetect"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pyinstaller"],
    noarchive=False,
)

pyz = PYZ(analisis.pure)

exe = EXE(
    pyz,
    analisis.scripts,
    analisis.binaries,
    analisis.datas,
    [],
    name="Fotique",
    icon=str(recursos / "fotique.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
