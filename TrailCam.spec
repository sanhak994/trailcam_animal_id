# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for TrailCam Animal ID macOS application.
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect data files for packages that need them
datas = [
    ('assets/logo.png', 'assets'),
]

# Don't bundle backend as binary - will copy it manually to Resources after build
binaries = []

# Collect hidden imports that PyInstaller might miss
hiddenimports = [
    'tkinter',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'PIL._tkinter_finder',
    'customtkinter',
    'darkdetect',
    'requests',
    'numpy',
]

# Binaries to exclude (reduce bundle size)
# Note: cv2 is excluded from GUI, it's only used by backend process
excludes = [
    'matplotlib',
    'scipy',
    'pytest',
    'IPython',
    'jupyter',
    'cv2',  # Not needed in GUI process
    'ultralytics',  # Not needed in GUI
    'torch',  # Not needed in GUI
]

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TrailCam Animal ID',
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
    mac_sdk_roots=["/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TrailCam Animal ID',
)

app = BUNDLE(
    coll,
    name='TrailCam Animal ID.app',
    icon='assets/icon.icns',
    bundle_identifier='com.sanhak994.trailcam-animal-id',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'TrailCam Animal ID',
        'CFBundleDisplayName': 'TrailCam Animal ID',
        'CFBundleGetInfoString': 'Automated wildlife video analysis using YOLOv8',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025 sanhak994. MIT License.',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15.0',
        'NSRequiresAquaSystemAppearance': False,
    },
)
