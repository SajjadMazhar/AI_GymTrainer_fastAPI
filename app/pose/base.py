"""Backend-agnostic pose estimation interface.

All estimators normalize their output to the same 33-landmark layout used by
MediaPipe's BlazePose (`mediapipe.solutions.pose.PoseLandmark`), so exercise
analyzers never need to know which backend produced a given frame's landmarks.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

NUM_LANDMARKS = 33


@dataclass
class Landmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 0.0


@dataclass
class PoseResult:
    landmarks: list[Landmark] | None
    backend: str


class PoseEstimator(ABC):
    """Synchronous, blocking, CPU-bound pose estimator.

    Instances hold internal tracking state and are NOT thread-safe for
    concurrent calls, so exactly one instance is created per WebSocket
    session. `process()` should always be invoked from a thread pool
    executor to avoid blocking the asyncio event loop.
    """

    @abstractmethod
    def process(self, frame_bgr: np.ndarray) -> PoseResult: ...

    @abstractmethod
    def close(self) -> None: ...
