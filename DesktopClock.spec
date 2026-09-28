# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

av_datas, av_binaries, av_hiddenimports = collect_all('av')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=av_binaries,
    datas=[('assets/desktop-clock.ico', 'assets')] + av_datas,
    hiddenimports=av_hiddenimports,
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
    name='DesktopClock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir='.',
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/desktop-clock.ico'],
)
