"""Video player with threaded playback for GUI integration."""

import time
import threading
from pathlib import Path
from typing import Callable, Optional
import cv2
import customtkinter as ctk
from PIL import Image


class VideoPlayer:
    """Thread-safe video player that renders frames to customtkinter GUI."""

    def __init__(self, frame_callback: Callable, completion_callback: Callable, progress_callback: Optional[Callable] = None):
        """Initialize video player.

        Args:
            frame_callback: Called with CTkImage when new frame is ready
            completion_callback: Called when video playback completes
            progress_callback: Optional callback with progress (0.0 to 1.0)
        """
        self.frame_callback = frame_callback
        self.completion_callback = completion_callback
        self.progress_callback = progress_callback

        self.cap: Optional[cv2.VideoCapture] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.paused = False
        self.speed_multiplier = 1.0
        self.display_size = (640, 480)
        self.video_size = None  # Original video dimensions
        self.total_frames = 0
        self.target_container_size = None  # Will be set by UI for responsive sizing

    def set_target_container_size(self, width: int, height: int):
        """Set the target container size for responsive display.

        Args:
            width: Available width in pixels
            height: Available height in pixels
        """
        self.target_container_size = (width, height)
        if self.video_size:
            self._calculate_display_size()

    def _calculate_display_size(self):
        """Calculate optimal display size based on container and video aspect ratio."""
        if not self.video_size:
            return

        orig_width, orig_height = self.video_size
        aspect_ratio = orig_width / orig_height

        if self.target_container_size:
            container_width, container_height = self.target_container_size

            # Fit to width first
            target_width = container_width
            target_height = int(target_width / aspect_ratio)

            # If too tall, fit to height instead
            if target_height > container_height:
                target_height = container_height
                target_width = int(target_height * aspect_ratio)

            self.display_size = (target_width, target_height)
        else:
            # Fallback to 640px width (original behavior)
            target_width = 640
            target_height = int(target_width / aspect_ratio)
            self.display_size = (target_width, target_height)

    def load_video(self, path: Path):
        """Load a video file for playback.

        Args:
            path: Path to video file
        """
        # Stop any existing playback
        if self.running:
            self.stop()

        # Open video file
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {path}")

        # Get original video dimensions
        orig_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_size = (orig_width, orig_height)

        # Get total frame count
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate display size maintaining aspect ratio
        self._calculate_display_size()

        # Reset state
        self.paused = False

    def start(self):
        """Start video playback in background thread."""
        if not self.cap or not self.cap.isOpened():
            raise ValueError("No video loaded")

        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop playback and cleanup resources."""
        self.running = False

        # Wait for thread to finish (50ms is enough for graceful exit)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.05)

        # Release video capture
        if self.cap:
            self.cap.release()
            self.cap = None

    def toggle_pause(self):
        """Toggle pause/resume state."""
        self.paused = not self.paused

    def set_speed(self, multiplier: float):
        """Set playback speed multiplier.

        Args:
            multiplier: Speed multiplier (0.5 = half speed, 2.0 = double speed, etc.)
        """
        self.speed_multiplier = max(0.1, multiplier)

    def _playback_loop(self):
        """Main playback loop (runs in background thread)."""
        if not self.cap:
            return

        # Get video properties
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 24.0
        frame_delay = 1.0 / fps  # seconds per frame
        current_frame = 0

        while self.running:
            # Handle pause
            if self.paused:
                time.sleep(0.1)
                continue

            # Calculate how many frames to skip based on speed
            # At 4x speed, show every 4th frame
            frame_step = max(1, int(round(self.speed_multiplier)))

            # Calculate frame timing
            start_time = time.time()

            # Read frame
            ret, frame = self.cap.read()
            if not ret:
                # Video ended
                self.running = False
                if self.progress_callback:
                    self.progress_callback(1.0)  # Set to 100%
                self.completion_callback()
                break

            current_frame += 1

            # Skip additional frames to speed up playback
            for _ in range(frame_step - 1):
                if not self.cap.grab():
                    # Video ended while skipping
                    self.running = False
                    if self.progress_callback:
                        self.progress_callback(1.0)
                    self.completion_callback()
                    return
                current_frame += 1

            # Report progress
            if self.progress_callback and self.total_frames > 0:
                progress = min(1.0, current_frame / self.total_frames)
                self.progress_callback(progress)

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to PIL Image
            pil_image = Image.fromarray(frame_rgb)

            # Resize to display size maintaining aspect ratio
            pil_image = pil_image.resize(self.display_size, Image.Resampling.LANCZOS)

            # Convert to CTkImage
            ctk_image = ctk.CTkImage(
                light_image=pil_image,
                dark_image=pil_image,
                size=self.display_size
            )

            # Update GUI (thread-safe)
            self.frame_callback(ctk_image)

            # Sleep to maintain frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_delay - elapsed)
            time.sleep(sleep_time)
