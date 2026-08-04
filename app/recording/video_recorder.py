"""Video recording functionality for workout sessions."""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


class VideoRecorder:
    """Records workout sessions to video files."""

    def __init__(
        self,
        output_dir: str = "recordings",
        fps: float = 8.0,
        codec: str = "mp4v",
    ) -> None:
        """Initialize video recorder.

        Args:
            output_dir: Directory to save recordings
            fps: Frames per second for output video
            codec: FourCC codec code (mp4v, avc1, x264)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.codec = codec

        self.writer: cv2.VideoWriter | None = None
        self.recording_path: Path | None = None
        self.start_time: float | None = None
        self.frame_count: int = 0

    def start(
        self,
        exercise: str,
        user_id: str | None = None,
        width: int = 640,
        height: int = 480,
    ) -> Path:
        """Start recording a new video.

        Args:
            exercise: Exercise name
            user_id: Optional user identifier
            width: Video width in pixels
            height: Video height in pixels

        Returns:
            Path to the output video file
        """
        if self.writer is not None:
            self.stop()  # Stop any existing recording

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_prefix = f"{user_id}_" if user_id else ""
        filename = f"{user_prefix}{exercise}_{timestamp}.mp4"
        self.recording_path = self.output_dir / filename

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        self.writer = cv2.VideoWriter(
            str(self.recording_path),
            fourcc,
            self.fps,
            (width, height),
        )

        if not self.writer.isOpened():
            raise RuntimeError(f"Failed to open video writer: {self.recording_path}")

        self.start_time = time.time()
        self.frame_count = 0

        return self.recording_path

    def write_frame(self, frame: np.ndarray) -> None:
        """Write a frame to the video.

        Args:
            frame: BGR image array (OpenCV format)
        """
        if self.writer is None:
            return

        self.writer.write(frame)
        self.frame_count += 1

    def stop(self) -> dict[str, any]:
        """Stop recording and finalize the video file.

        Returns:
            Recording metadata dict with path, duration, frame_count
        """
        if self.writer is None:
            return {}

        self.writer.release()
        self.writer = None

        duration = time.time() - self.start_time if self.start_time else 0

        metadata = {
            "path": str(self.recording_path),
            "duration_seconds": round(duration, 1),
            "frame_count": self.frame_count,
            "fps": self.fps,
        }

        # Reset state
        self.recording_path = None
        self.start_time = None
        self.frame_count = 0

        return metadata

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.writer is not None

    def get_current_path(self) -> Path | None:
        """Get path to current recording file."""
        return self.recording_path
