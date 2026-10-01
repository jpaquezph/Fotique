# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para Fotia (Windows, ejecutable de un solo archivo).

Uso:
    pyinstaller --noconfirm --clean fotia.spec
"""

from pathlib import Path

raiz = Path(SPECPATH)

# El esquema SQLite se lee con Path(__file__) y debe viajar junto al paquete.
datos = [(str(raiz / "fotia" / "db" / "schema.sql"), "fotia/db")]

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
    name="Fotia",
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
