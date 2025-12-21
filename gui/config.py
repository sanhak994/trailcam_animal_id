"""Configuration defaults for the TrailCam Animal ID GUI."""

import os
from pathlib import Path

# Professional fonts (SF Pro Display on macOS, fallback to system default)
FONT_FAMILY = "SF Pro Display"
FONT_FAMILY_MONO = "SF Mono"

TITLE_FONT = {"family": FONT_FAMILY, "size": 18, "weight": "bold"}
HEADING_FONT = {"family": FONT_FAMILY, "size": 15, "weight": "normal"}
SUBHEADING_FONT = {"family": FONT_FAMILY, "size": 13, "weight": "bold"}
BODY_FONT = {"family": FONT_FAMILY, "size": 13, "weight": "normal"}
SMALL_FONT = {"family": FONT_FAMILY, "size": 11, "weight": "normal"}
MONO_FONT = {"family": FONT_FAMILY_MONO, "size": 11, "weight": "normal"}

# Professional Video Editor Color Palette
# True black backgrounds like Premiere Pro, Final Cut Pro, DaVinci Resolve
COLORS = {
    # Backgrounds (true black like professional video editors)
    'bg_primary': '#000000',        # True black - main background
    'bg_secondary': '#0a0a0a',      # Near black - panels
    'bg_tertiary': '#1a1a1a',       # Dark gray - elevated elements

    # UI Elements
    'ui_button': '#2a2a2a',         # Button background
    'ui_button_hover': '#3a3a3a',   # Button hover
    'ui_input': '#1a1a1a',          # Input fields
    'ui_frame': '#0a0a0a',          # Frame backgrounds

    # Text Colors
    'text_primary': '#e0e0e0',      # Primary text (light gray)
    'text_secondary': '#9a9a9a',    # Secondary text (medium gray)
    'text_disabled': '#5a5a5a',     # Disabled text (dark gray)

    # Accents (semantic colors for UX)
    'accent_active': '#2d5a2d',     # Active/selected (dark green)
    'accent_active_hover': '#3a7a3a',
    'accent_danger': '#8b0000',     # Danger/delete (dark red)
    'accent_danger_hover': '#a52a2a',

    # Video Display
    'video_bg': '#000000',          # Pure black for video area
    'video_border': '#1a1a1a',      # Subtle border
}

DEFAULT_CONFIG = {
    'clips_dir': str(Path.home() / "Desktop"),
    'frames_per_clip': 4,
    'frame_workers': min(4, os.cpu_count() or 1),
    'classify_workers': min(4, os.cpu_count() or 1),
    'extensions': '.mp4,.MP4,.mov,.MOV',
    'force': False,
    'play_rate': 4.0,
    'clip_pause_seconds': 2.0,
}

def get_worker_options() -> list:
    """Generate worker count options based on CPU count."""
    cpu_count = os.cpu_count() or 4
    # Generate: 1, 2, 4, then powers of 2 up to cpu_count, then cpu_count if not power of 2
    options = [1, 2, 4]

    # Add power-of-2 values up to cpu_count
    next_power = 8
    while next_power <= cpu_count:
        options.append(next_power)
        next_power *= 2

    # Add actual cpu_count if not already in list
    if cpu_count not in options:
        options.append(cpu_count)

    # Add one option above cpu_count for hyperthreading scenarios
    if cpu_count < 32:
        options.append(min(32, cpu_count * 2))

    return sorted(set(options))

FRAMES_PER_CLIP_RANGE = (1, 30)
PLAY_RATE_RANGE = (0.5, 8.0)
PAUSE_DURATION_RANGE = (0, 10)
