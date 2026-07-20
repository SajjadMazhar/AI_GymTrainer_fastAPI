"""Optional pose backend: YOLOv11-pose via the `ultralytics` package.

Not the default backend. Select it with POSE_BACKEND=yolo. Requires the
`ultralytics` package (see requirements.txt) and will download the small
pose model weights on first run.
"""
from __future__ import annotations

import numpy as np

from app.pose.base import NUM_LANDMARKS, Landmark, PoseEstimator, PoseResult

# Maps COCO-17 keypoint index -> BlazePose-33 landmark index, for the
# keypoints both formats share (nose, eyes, ears, shoulders, elbows, wrists,
# hips, knees, ankles). Every exercise analyzer only reads these shared
# landmarks, so results are usable interchangeably regardless of backend.
_COCO17_TO_BLAZEPOSE33 = {
    0: 0,    # nose
    1: 2,    # left_eye
    2: 5,    # right_eye
    3: 7,    # left_ear
    4: 8,    # right_ear
    5: 11,   # left_shoulder
    6: 12,   # right_shoulder
    7: 13,   # left_elbow
    8: 14,   # right_elbow
    9: 15,   # left_wrist
    10: 16,  # right_wrist
    11: 23,  # left_hip
    12: 24,  # right_hip
    13: 25,  # left_knee
    14: 26,  # right_knee
    15: 27,  # left_ankle
    16: 28,  # right_ankle
}


def _coco17_to_blazepose33(keypoints_xyn: list[list[float]], confidences: list[float]) -> list[Landmark]:
    landmarks = [Landmark(x=0.0, y=0.0, z=0.0, visibility=0.0) for _ in range(NUM_LANDMARKS)]
    for coco_idx, blaze_idx in _COCO17_TO_BLAZEPOSE33.items():
        x, y = keypoints_xyn[coco_idx]
        conf = confidences[coco_idx] if coco_idx < len(confidences) else 1.0
        landmarks[blaze_idx] = Landmark(x=float(x), y=float(y), z=0.0, visibility=float(conf))
    return landmarks


class YoloPoseEstimator(PoseEstimator):
    def __init__(self, model_path: str = "yolo11n-pose.pt") -> None:
        from ultralytics import YOLO  # deferred import: optional dependency

        self._model = YOLO(model_path)

    def process(self, frame_bgr: np.ndarray) -> PoseResult:
        results = self._model(frame_bgr, verbose=False)[0]
        if results.keypoints is None or len(results.keypoints.xyn) == 0:
            return PoseResult(landmarks=None, backend="yolo")

        # Single-person MVP: take the first detected person.
        keypoints_xyn = results.keypoints.xyn[0].tolist()
        if results.keypoints.conf is not None:
            confidences = results.keypoints.conf[0].tolist()
        else:
            confidences = [1.0] * len(keypoints_xyn)

        landmarks = _coco17_to_blazepose33(keypoints_xyn, confidences)
        return PoseResult(landmarks=landmarks, backend="yolo")

    def close(self) -> None:
        pass  # no persistent native resource to release
