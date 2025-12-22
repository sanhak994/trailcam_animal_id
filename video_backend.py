"""Video backend server using FastAPI and OpenCV.

This server runs as a separate process and handles all cv2.VideoCapture operations.
The GUI communicates with this backend via HTTP to avoid cv2 packaging issues.
"""

import base64
import io
import uuid
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

app = FastAPI(title="TrailCam Video Backend")

# Store active video captures by session ID
video_sessions: Dict[str, cv2.VideoCapture] = {}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "backend": "video"}


@app.post("/video/open")
async def open_video(path: str):
    """Open a video file and return a session ID.

    Args:
        path: Absolute path to video file

    Returns:
        session_id: Unique identifier for this video session
        width: Video width in pixels
        height: Video height in pixels
        frame_count: Total number of frames
        fps: Frames per second
    """
    video_path = Path(path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {path}")

    # Create video capture
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail=f"Could not open video: {path}")

    # Generate session ID
    session_id = str(uuid.uuid4())
    video_sessions[session_id] = cap

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0

    return {
        "session_id": session_id,
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "fps": fps
    }


@app.get("/video/{session_id}/read")
async def read_frame(session_id: str):
    """Read the next frame from the video.

    Args:
        session_id: Video session identifier

    Returns:
        success: Whether frame was read successfully
        frame: Base64-encoded JPEG frame (if success=True)
    """
    if session_id not in video_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    cap = video_sessions[session_id]
    ret, frame = cap.read()

    if not ret:
        return {"success": False, "frame": None}

    # Convert BGR to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Convert to JPEG with compression
    pil_image = Image.fromarray(frame_rgb)
    buffer = io.BytesIO()
    pil_image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    # Base64 encode for JSON transport
    frame_b64 = base64.b64encode(buffer.read()).decode('utf-8')

    return {
        "success": True,
        "frame": frame_b64
    }


@app.post("/video/{session_id}/grab")
async def grab_frame(session_id: str):
    """Skip the next frame without reading it (faster).

    Args:
        session_id: Video session identifier

    Returns:
        success: Whether frame grab was successful
    """
    if session_id not in video_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    cap = video_sessions[session_id]
    success = cap.grab()

    return {"success": success}


@app.post("/video/{session_id}/close")
async def close_video(session_id: str):
    """Close a video session and release resources.

    Args:
        session_id: Video session identifier
    """
    if session_id in video_sessions:
        cap = video_sessions[session_id]
        cap.release()
        del video_sessions[session_id]
        return {"status": "closed"}

    raise HTTPException(status_code=404, detail="Session not found")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up all video sessions on shutdown."""
    for cap in video_sessions.values():
        cap.release()
    video_sessions.clear()


if __name__ == "__main__":
    import sys
    import os
    import socket
    from datetime import datetime
    import uvicorn

    # Set up logging - write directly to file to avoid stdout redirection issues
    # Check if we're frozen (packaged executable) - if so, must write to file ourselves
    if getattr(sys, 'frozen', False):
        # Running as packaged executable - write logs directly to file
        log_file_obj = open("/tmp/trailcam_backend.log", "w", buffering=1)
        sys.stdout = log_file_obj
        sys.stderr = log_file_obj

    # Print diagnostics (goes to stdout, which is file if frozen or parent's redirect if not)
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

    # Start server
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
