#!/usr/bin/env python3
"""TrailCam Animal ID GUI Application

Entry point for the TrailCam pipeline GUI.
Run this to launch the graphical interface.
"""

import sys
import subprocess
import time
import atexit
import requests
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from gui.main_window import TrailCamApp


# Global backend process
backend_process = None


def find_backend_script():
    """Find the video_backend.py script.

    Returns:
        Path to video_backend.py
    """
    # When running from source
    source_path = Path(__file__).parent / "video_backend.py"
    if source_path.exists():
        return source_path

    # When packaged, backend is in Resources
    if getattr(sys, 'frozen', False):
        # Running as packaged app
        bundle_dir = Path(sys.executable).parent.parent
        backend_path = bundle_dir / "Resources" / "video_backend.py"
        if backend_path.exists():
            return backend_path

    raise FileNotFoundError("Could not find video_backend.py")


def start_backend():
    """Start the video backend server."""
    global backend_process

    try:
        backend_script = find_backend_script()

        # Use system Python for backend (not bundled Python)
        # Backend needs access to cv2 which is not packaged
        python_cmd = "python3"  # System Python

        # Start backend process
        backend_process = subprocess.Popen(
            [python_cmd, str(backend_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait for backend to be ready (max 10 seconds)
        backend_url = "http://127.0.0.1:8001/health"
        for _ in range(50):  # 50 * 0.2s = 10s max
            try:
                response = requests.get(backend_url, timeout=1)
                if response.status_code == 200:
                    print("Video backend started successfully")
                    return
            except requests.RequestException:
                pass
            time.sleep(0.2)

        raise RuntimeError("Video backend failed to start within 10 seconds")

    except Exception as e:
        print(f"Failed to start video backend: {e}")
        if backend_process:
            backend_process.terminate()
        raise


def stop_backend():
    """Stop the video backend server."""
    global backend_process
    if backend_process:
        backend_process.terminate()
        backend_process.wait(timeout=2)
        backend_process = None


def main():
    """Launch the GUI application."""
    # Start backend server
    try:
        start_backend()
    except Exception as e:
        print(f"ERROR: Could not start video backend: {e}")
        sys.exit(1)

    # Register cleanup on exit
    atexit.register(stop_backend)

    # Launch GUI
    try:
        app = TrailCamApp()
        app.mainloop()
    finally:
        stop_backend()


if __name__ == "__main__":
    main()
