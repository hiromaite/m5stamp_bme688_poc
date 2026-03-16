# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

import PySide6


PROJECT_DIR = Path(SPECPATH).resolve().parent
PYSIDE_DIR = Path(PySide6.__file__).resolve().parent
PYSIDE_PLUGINS = PYSIDE_DIR / "plugins"


a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_DIR / 'src')],
    binaries=[],
    datas=[(str(PYSIDE_PLUGINS), 'PySide6/plugins')],
    hiddenimports=[
        'pyqtgraph',
        'pyqtgraph.Qt',
        'pyqtgraph.Qt.QtCore',
        'pyqtgraph.Qt.QtGui',
        'pyqtgraph.Qt.QtWidgets',
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'app_metadata',
        'serial_protocol',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
