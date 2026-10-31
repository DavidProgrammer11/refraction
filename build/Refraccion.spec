# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Programación/GitH/refraction-main/refraction-main/run.py'],
    pathex=['C:/Programación/GitH/refraction-main/refraction-main/src'],
    binaries=[],
    datas=[('C:/Programación/GitH/refraction-main/refraction-main/src/refraccion/resources', 'refraccion/resources')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['ssl', '_ssl', '_hashlib', 'PySide6.QtNetwork', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Refraccion',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='C:/Programación/GitH/refraction-main/refraction-main/build/version_info.txt',
    icon=['C:/Programación/GitH/refraction-main/refraction-main/src/refraccion/resources/icons/app.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Refraccion',
)
