# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('C:\\Users\\hiroma-ito.NGKNTK\\Documents\\PlatformIO\\Projects\\m5stamp_bme688_poc\\pc_logger\\.venv\\Lib\\site-packages\\PySide6\\plugins', 'PySide6/plugins')],
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
        'serial_protocol'
    ],
    hookspath=[
        'C:\\Users\\hiroma-ito.NGKNTK\\Documents\\PlatformIO\\Projects\\m5stamp_bme688_poc\\pc_logger\\.venv\\Lib\\site-packages\\PyInstaller\\hooks',
        'C:\\Users\\hiroma-ito.NGKNTK\\Documents\\PlatformIO\\Projects\\m5stamp_bme688_poc\\pc_logger\\.venv\\Lib\\site-packages\\pyinstaller_hooks_contrib'
    ],
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
