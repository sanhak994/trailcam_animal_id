# -*- mode: python ; coding: utf-8 -*-
"""
Unified spec that builds both GUI and backend in one COLLECT.
This deduplicates shared libraries and prevents conflicts.
This is the industry standard for multi-process PyInstaller apps.
"""

# Analyze GUI (exclude cv2/torch)
a_gui = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/logo.png', 'assets'),
        # Bundle pipeline scripts for packaged app
        ('run_pipeline.py', '.'),
        ('extract_frames.py', '.'),
        ('classify_frames.py', '.'),
        ('summarize_videos.py', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'PIL._tkinter_finder',
        'customtkinter',
        'darkdetect',
        'requests',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['cv2', 'ultralytics', 'torch', 'matplotlib', 'scipy'],
    noarchive=False,
    optimize=0,
)

# Analyze backend (include cv2/torch)
a_backend = Analysis(
    ['backend_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle ML model for offline operation
        ('assets/TrapperAI-v02.2024-YOLOv8-m.pt', '.'),
    ],
    hiddenimports=[
        'video_backend',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Build GUI executable
pyz_gui = PYZ(a_gui.pure)
exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name='TrailCam Animal ID',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

# Build backend executable
pyz_backend = PYZ(a_backend.pure)
exe_backend = EXE(
    pyz_backend,
    a_backend.scripts,
    [],
    exclude_binaries=True,
    name='trailcam_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

# CRITICAL: Single COLLECT that includes both executables
# This deduplicates shared libraries (numpy, etc.) to prevent conflicts
coll = COLLECT(
    exe_gui,
    a_gui.binaries,
    a_gui.datas,
    exe_backend,
    a_backend.binaries,
    a_backend.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TrailCam Animal ID',
)

# Bundle as macOS app
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
