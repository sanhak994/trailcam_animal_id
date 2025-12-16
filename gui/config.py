"""Configuration defaults for the TrailCam Animal ID GUI."""

import os
from pathlib import Path

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

WORKER_OPTIONS = [1, 2, 4, 8, 16]
FRAMES_PER_CLIP_RANGE = (1, 30)
PLAY_RATE_RANGE = (0.5, 8.0)
PAUSE_DURATION_RANGE = (0, 10)
