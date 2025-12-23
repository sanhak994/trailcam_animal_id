#!/usr/bin/env python3
"""
Entry point for the packaged backend executable.
This ensures the __main__ block in video_backend.py executes properly.
"""

if __name__ == "__main__":
    import sys
    import os
    from datetime import datetime
    import traceback

    # Always write to log file for debugging
    log_file_path = "/tmp/trailcam_backend.log"
    crash_log_path = "/tmp/trailcam_backend_CRASH.log"
    
    try:
        log_file_obj = open(log_file_path, "w", buffering=1)
        sys.stdout = log_file_obj
        sys.stderr = log_file_obj
        print("=== Log file opened successfully ===", flush=True)
    except Exception as e:
        # If we can't open log, we can't do much, but let's try to report it.
        # This is a last-ditch effort.
        with open(crash_log_path, "w") as f:
            f.write(f"FATAL: Failed to open main log file {log_file_path}: {e}\n")
        sys.exit(1)

    try:
        # Import and run the backend
        print("Importing socket...", flush=True)
        import socket
        print("Importing video_backend...", flush=True)
        import video_backend
        print("Importing uvicorn...", flush=True)
        import uvicorn
        print("Imports successful.", flush=True)

        # Print diagnostics
        print(f"=== TrailCam Video Backend ===", flush=True)
        print(f"Started: {datetime.now()}", flush=True)
        print(f"Python: {sys.executable}", flush=True)
        print(f"Working dir: {os.getcwd()}", flush=True)
        print(f"Frozen: {getattr(sys, 'frozen', False)}", flush=True)

        # Find an available ephemeral port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        sock.close()

        print(f"Bound to port: {port}", flush=True)

        # Write port to file for GUI to read
        port_file = "/tmp/trailcam_backend_port"
        with open(port_file, "w") as f:
            f.write(str(port))
        print(f"Wrote port to: {port_file}", flush=True)

        # Write ready signal
        ready_file = os.environ.get("TRAILCAM_BACKEND_READY", "/tmp/trailcam_backend_ready")
        with open(ready_file, "w") as f:
            f.write(f"ready:{port}\n")
        print(f"Wrote ready signal to: {ready_file}", flush=True)

        print(f"Starting uvicorn server on http://127.0.0.1:{port}", flush=True)

        # Start server with the app from video_backend
        uvicorn.run(video_backend.app, host="127.0.0.1", port=port, log_level="info")

    except Exception as e:
        print(f"FATAL ERROR during backend startup: {e}", flush=True)
        traceback.print_exc()
        # Also write to a separate crash file for easy access
        with open(crash_log_path, "w") as f:
            f.write(f"Backend crashed during startup: {e}\n\n")
            traceback.print_exc(file=f)
        sys.exit(1)
