# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for THEA

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all submodules of pdf2image and PIL
hiddenimports = collect_submodules('pdf2image') + collect_submodules('PIL')

a = Analysis(
    ['thea.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports + ['pdf2image', 'PIL', 'PIL.Image', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Determine the platform-specific executable name and icon
import platform
system = platform.system().lower()

if system == 'windows':
    exe_name = 'thea.exe'
    icon_file = None  # Add 'thea.ico' if you have an icon
    console = True
elif system == 'darwin':  # macOS
    exe_name = 'thea-macos'
    icon_file = None  # Add 'thea.icns' if you have an icon
    console = True
else:  # Linux and others
    exe_name = 'thea-linux'
    icon_file = None
    console = True

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)