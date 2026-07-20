from __future__ import annotations

from app.pose.base import PoseEstimator


def get_pose_estimator(name: str, model_complexity: int = 1) -> PoseEstimator:
    if name == "mediapipe":
        from app.pose.mediapipe_backend import MediaPipePoseEstimator

        return MediaPipePoseEstimator(model_complexity=model_complexity)
    if name == "yolo":
        from app.pose.yolo_backend import YoloPoseEstimator

        return YoloPoseEstimator()
    raise ValueError(f"Unknown pose backend: {name!r} (expected 'mediapipe' or 'yolo')")
