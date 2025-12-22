#!/usr/bin/env python3
"""TrailCam Animal ID GUI Application

Entry point for the TrailCam pipeline GUI.
Run this to launch the graphical interface.
"""

import sys
import os
import subprocess
import time
import atexit
import requests
from pathlib import Path
import tkinter.messagebox as mb

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from gui.main_window import TrailCamApp


# Global backend process and port
backend_process = None
backend_port = None


def find_backend_script():
    """Find video_backend.py script for development mode.

    Returns:
        Path to video_backend.py
    """
    script_path = Path(__file__).parent / "video_backend.py"
    if script_path.exists():
        return script_path
    raise FileNotFoundError("Could not find video_backend.py")


def find_python():
    """Find Python executable for development mode.

    Returns:
        Path to Python executable (current interpreter with all deps)
    """
    # When running from source, use current Python (has all deps in venv)
    return sys.executable


def find_backend_executable():
    """Find the backend executable for production mode.

    Returns:
        Path to trailcam_backend executable
    """
    # When running from source (after building with PyInstaller)
    source_exe = Path(__file__).parent / "dist" / "trailcam_backend"
    if source_exe.exists():
        return source_exe

    # When packaged, backend is in Resources folder (copied by build script)
    if getattr(sys, 'frozen', False):
        # Running as packaged app - backend is in the Resources folder
        bundle_dir = Path(sys.executable).parent.parent  # Go up to Contents
        backend_exe = bundle_dir / "Resources" / "trailcam_backend"
        if backend_exe.exists():
            return backend_exe

    raise FileNotFoundError(
        "Could not find backend executable.\n\n"
        "Please run: ./build.sh"
    )


def start_backend():
    """Start the video backend server and return the port it's running on.

    Returns:
        int: Port number the backend is listening on

    Raises:
        RuntimeError: If backend fails to start
    """
    global backend_process, backend_port

    # Clean up any stale files from previous runs
    for f in ["/tmp/trailcam_backend_port", "/tmp/trailcam_backend_ready"]:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

    try:
        # Open log file for backend output
        log_file = open("/tmp/trailcam_backend.log", "w")

        # Choose backend launch method based on mode
        if getattr(sys, 'frozen', False):
            # Production: use bundled executable
            backend_exe = find_backend_executable()
            cmd = [str(backend_exe)]
            print(f"Starting backend executable: {backend_exe}")
        else:
            # Development: use Python script
            backend_script = find_backend_script()
            python_cmd = find_python()
            cmd = [python_cmd, str(backend_script)]
            print(f"Starting backend via Python: {python_cmd} {backend_script}")

        print(f"Logs: /tmp/trailcam_backend.log")

        # Start backend process
        backend_process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            env={
                **os.environ,
                "TRAILCAM_BACKEND_READY": "/tmp/trailcam_backend_ready"
            },
            start_new_session=True  # Daemonize properly
        )

        # Wait for backend to signal ready and write port (max 10 seconds)
        ready_file = "/tmp/trailcam_backend_ready"
        port_file = "/tmp/trailcam_backend_port"

        for i in range(50):  # 50 * 0.2s = 10s max
            if os.path.exists(ready_file) and os.path.exists(port_file):
                # Read port number
                try:
                    with open(port_file) as f:
                        backend_port = int(f.read().strip())
                    print(f"Backend ready on port {backend_port}")

                    # Verify backend is responding
                    try:
                        response = requests.get(
                            f"http://127.0.0.1:{backend_port}/health",
                            timeout=1
                        )
                        if response.status_code == 200:
                            return backend_port
                    except requests.RequestException:
                        pass  # Will retry

                except (ValueError, FileNotFoundError) as e:
                    print(f"Error reading port file: {e}")

            time.sleep(0.2)

        # Backend failed to start - read log for details
        try:
            with open("/tmp/trailcam_backend.log") as f:
                log_content = f.read()
        except:
            log_content = "Could not read log file"

        raise RuntimeError(
            f"Backend failed to start within 10 seconds.\n\n"
            f"Check /tmp/trailcam_backend.log for details.\n\n"
            f"Last log output:\n{log_content[-500:]}"  # Last 500 chars
        )

    except Exception as e:
        print(f"Failed to start video backend: {e}")
        if backend_process:
            backend_process.terminate()
        raise


def stop_backend():
    """Stop the video backend server and clean up temp files."""
    global backend_process, backend_port

    if backend_process:
        backend_process.terminate()
        try:
            backend_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        backend_process = None

    # Clean up temp files
    for f in ["/tmp/trailcam_backend_port", "/tmp/trailcam_backend_ready"]:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

    backend_port = None


def main():
    """Launch the GUI application."""
    # Start backend server
    try:
        port = start_backend()

        # Set port as environment variable for video_client to read
        os.environ["TRAILCAM_BACKEND_PORT"] = str(port)

    except Exception as e:
        error_msg = (
            f"Failed to start video backend.\n\n"
            f"Error: {str(e)}\n\n"
            f"Logs: /tmp/trailcam_backend.log"
        )
        print(f"ERROR: {error_msg}")

        # Show error dialog if possible
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            mb.showerror("Backend Startup Failed", error_msg)
            root.destroy()
        except:
            pass  # Can't show dialog, already printed to console

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
