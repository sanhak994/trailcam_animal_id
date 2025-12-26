"""Video client that communicates with video backend server.

This client mimics cv2.VideoCapture interface but makes HTTP requests to the backend.
"""

import base64
import io
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import requests
from PIL import Image


class VideoCapture:
    """HTTP client that mimics cv2.VideoCapture interface."""

    # Constants that match cv2.VideoCapture properties
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5
    CAP_PROP_FRAME_COUNT = 7

    def __init__(self, path: str, backend_url: Optional[str] = None):
        """Initialize video capture client.

        Args:
            path: Path to video file
            backend_url: URL of video backend server (reads from env if not provided)
        """
        # Read backend port from environment variable if not provided
        if backend_url is None:
            port = os.environ.get("TRAILCAM_BACKEND_PORT", "8001")
            backend_url = f"http://127.0.0.1:{port}"

        self.backend_url = backend_url.rstrip('/')
        self.session_id: Optional[str] = None
        self._opened = False
        self._properties = {}

        # Open video on backend
        if path:
            self._open(path)

    def _open(self, path: str):
        """Open video file on backend."""
        try:
            response = requests.post(
                f"{self.backend_url}/video/open",
                params={"path": str(path)},
                timeout=5
            )
            response.raise_for_status()

            data = response.json()
            self.session_id = data["session_id"]
            self._properties = {
                self.CAP_PROP_FRAME_WIDTH: data["width"],
                self.CAP_PROP_FRAME_HEIGHT: data["height"],
                self.CAP_PROP_FRAME_COUNT: data["frame_count"],
                self.CAP_PROP_FPS: data["fps"]
            }
            self._opened = True

        except requests.RequestException as e:
            print(f"Failed to open video: {e}")
            self._opened = False

    def isOpened(self) -> bool:
        """Check if video is successfully opened."""
        return self._opened

    def get(self, prop_id: int) -> float:
        """Get video property.

        Args:
            prop_id: Property identifier (e.g., CAP_PROP_FRAME_WIDTH)

        Returns:
            Property value
        """
        return self._properties.get(prop_id, 0.0)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read next frame from video.

        Returns:
            ret: Success flag
            frame: Frame as numpy array (BGR format, like cv2)
        """
        if not self._opened or not self.session_id:
            return False, None

        try:
            response = requests.get(
                f"{self.backend_url}/video/{self.session_id}/read",
                timeout=2
            )
            response.raise_for_status()

            data = response.json()
            if not data["success"]:
                return False, None

            # Decode base64 JPEG
            frame_bytes = base64.b64decode(data["frame"])
            pil_image = Image.open(io.BytesIO(frame_bytes))

            # Convert to numpy array (RGB format - different from cv2's BGR)
            # video_player.py will skip the BGR->RGB conversion
            frame_rgb = np.array(pil_image)

            return True, frame_rgb

        except requests.RequestException as e:
            print(f"Failed to read frame: {e}")
            return False, None

    def grab(self) -> bool:
        """Skip next frame without reading (faster).

        Returns:
            Success flag
        """
        if not self._opened or not self.session_id:
            return False

        try:
            response = requests.post(
                f"{self.backend_url}/video/{self.session_id}/grab",
                timeout=2
            )
            response.raise_for_status()

            data = response.json()
            return data["success"]

        except requests.RequestException:
            return False

    def release(self):
        """Release video resources."""
        if self.session_id:
            try:
                requests.post(
                    f"{self.backend_url}/video/{self.session_id}/close",
                    timeout=2
                )
            except requests.RequestException:
                pass  # Ignore errors during cleanup

            self.session_id = None
        self._opened = False
