"""
Setup script for packaging TrailCam Animal ID as macOS application.
"""

import sys
sys.setrecursionlimit(5000)  # Increase recursion limit for py2app

from setuptools import setup

APP = ['gui_app.py']
DATA_FILES = [
    ('assets', ['assets/logo.png']),
]

OPTIONS = {
    'argv_emulation': False,  # Don't emulate sys.argv
    'iconfile': 'assets/icon.icns',  # App icon
    'plist': {
        'CFBundleName': 'TrailCam Animal ID',
        'CFBundleDisplayName': 'TrailCam Animal ID',
        'CFBundleGetInfoString': 'Automated wildlife video analysis using YOLOv8',
        'CFBundleIdentifier': 'com.sanhak994.trailcam-animal-id',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025 sanhak994. MIT License.',
        'NSHighResolutionCapable': True,  # Retina support
        'LSMinimumSystemVersion': '10.15.0',  # macOS Catalina+
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
    },
    'packages': ['gui'],  # Only include our custom package, let py2app discover the rest
    'includes': [
        'tkinter',
        'tkinter.messagebox',
        'tkinter.filedialog',
    ],
    'excludes': [
        'matplotlib',  # Not used, saves space
        'scipy',       # Not used
        'pytest',      # Not needed in production
    ],
    'resources': [
        'assets/logo.png',
    ],
    'frameworks': [],  # Include any .dylib files if needed
}

setup(
    name='TrailCam Animal ID',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    python_requires='>=3.9',
)
