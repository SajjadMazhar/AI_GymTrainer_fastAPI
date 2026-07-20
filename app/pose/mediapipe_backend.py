"""Default pose backend: MediaPipe Pose Landmarker (BlazePose, 33 landmarks).

Uses MediaPipe's current Tasks API (`mediapipe.tasks.python.vision`), which
replaced the older `mp.solutions.pose` API in recent mediapipe releases (the
legacy `solutions` module is no longer bundled in the pip package). The model
bundle (~6MB) is downloaded once and cached locally on first use, mirroring
how `ultralytics` auto-downloads YOLO weights.
"""
from __future__ import annotations

import time
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
from mediapipe.tasks.python.vision.pose_landmarker import (
    PoseLandmarker,
    PoseLandmarkerOptions,
)

from app.pose.base import Landmark, PoseEstimator, PoseResult

CACHE_DIR = Path.home() / ".cache" / "ai_gym_trainer"

# model_complexity: 0 -> lite (fastest), 1 -> full (default, balanced), 2 -> heavy (most accurate)
_MODEL_VARIANTS = {0: "lite", 1: "full", 2: "heavy"}
_MODEL_URL_TEMPLATE = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_{variant}/float16/latest/pose_landmarker_{variant}.task"
)


def _ensure_model(model_complexity: int) -> Path:
    variant = _MODEL_VARIANTS.get(model_complexity, "full")
    model_path = CACHE_DIR / f"pose_landmarker_{variant}.task"
    if not model_path.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        url = _MODEL_URL_TEMPLATE.format(variant=variant)
        urllib.request.urlretrieve(url, model_path)
    return model_path


class MediaPipePoseEstimator(PoseEstimator):
    def __init__(
        self,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        model_path = _ensure_model(model_complexity)
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            # VIDEO mode enables frame-to-frame temporal smoothing/tracking,
            # which needs a single persistent instance fed frames from one
            # session in increasing-timestamp order -- never share this
            # instance across concurrent sessions.
            running_mode=VisionTaskRunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = PoseLandmarker.create_from_options(options)
        self._session_start_ms = time.monotonic() * 1000
        self._last_timestamp_ms = -1

    def process(self, frame_bgr: np.ndarray) -> PoseResult:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        timestamp_ms = int(time.monotonic() * 1000 - self._session_start_ms)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.pose_landmarks:
            return PoseResult(landmarks=None, backend="mediapipe")

        landmarks = [
            Landmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility) for lm in result.pose_landmarks[0]
        ]
        return PoseResult(landmarks=landmarks, backend="mediapipe")

    def close(self) -> None:
        self._landmarker.close()
