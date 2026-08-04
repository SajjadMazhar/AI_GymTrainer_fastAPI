"""Shared contract and state-machine helpers for per-exercise analyzers.

Each concrete analyzer (SquatAnalyzer, PushupAnalyzer, ...) is instantiated
fresh per WebSocket session and holds rep_count/phase as instance state --
there is no shared global mutable state, so concurrent sessions never cross-talk.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from app.pose.base import Landmark
from app.pose.landmark_index import LandmarkIndex as LM

Point = tuple[float, float]

VISIBILITY_THRESHOLD = 0.5


class RepPhase(str, Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class AnalysisResult:
    rep_count: int
    phase: str
    posture_errors: list[str]
    primary_angle: float | None
    confidence: float
    risk_score: int = 0  # 0-100, higher = more injury risk from velocity patterns


def xy(landmarks: list[Landmark], idx: LM) -> Point:
    lm = landmarks[idx]
    return (lm.x, lm.y)


def visibility(landmarks: list[Landmark], idx: LM) -> float:
    return landmarks[idx].visibility


def min_visibility(landmarks: list[Landmark], indices: tuple[LM, ...]) -> float:
    return min(visibility(landmarks, idx) for idx in indices)


def pick_side(
    landmarks: list[Landmark],
    left_indices: tuple[LM, ...],
    right_indices: tuple[LM, ...],
) -> tuple[LM, ...]:
    """Pick whichever side (left/right) has higher average landmark visibility.

    Home camera setups often only see one side of the body cleanly, so
    exercises that use a single-side joint (e.g. one leg's knee angle) should
    pick the more visible side rather than always defaulting to left.
    """
    left_vis = sum(visibility(landmarks, i) for i in left_indices) / len(left_indices)
    right_vis = sum(visibility(landmarks, i) for i in right_indices) / len(right_indices)
    return left_indices if left_vis >= right_vis else right_indices


class ExerciseAnalyzer(ABC):
    name: str

    def __init__(self, calibration: dict[str, float] | None = None) -> None:
        self.rep_count = 0
        self.phase = RepPhase.UP
        self._angle_history: list[float] = []
        self._min_angle_this_phase: float | None = None
        self._max_angle_this_phase: float | None = None
        self._prev_landmarks: list[Landmark] | None = None  # previous frame for velocity computation
        self._risk_events: list[int] = []  # sliding window of per-frame risk contributions
        self._calibration = calibration or {}  # personalized thresholds from user calibration

    @abstractmethod
    def analyze(self, landmarks: list[Landmark]) -> AnalysisResult:
        """Read/update self state from one frame's landmarks, return this frame's analysis.

        Must not raise on missing/low-confidence landmarks -- callers should
        return posture_errors=["LOW_CONFIDENCE"] or similar instead.
        """

    def _smooth(self, angle: float, window: int = 5) -> float:
        self._angle_history.append(angle)
        if len(self._angle_history) > window:
            self._angle_history.pop(0)
        return sum(self._angle_history) / len(self._angle_history)

    def _update_phase(self, smoothed_angle: float, down_thresh: float, up_thresh: float) -> bool:
        """Debounced UP<->DOWN hysteresis state machine; counts a rep on DOWN->UP.

        Two distinct thresholds (down_thresh well below up_thresh) instead of a
        single crossing point absorb landmark jitter so noisy angles don't
        double-count a single rep. Also tracks the running min/max angle seen
        during the current phase, exposed for per-exercise depth/completion
        checks (e.g. "never got low enough this rep").

        Returns True the frame a rep is completed (DOWN -> UP transition).
        """
        rep_completed = False
        if self.phase == RepPhase.UP:
            self._max_angle_this_phase = (
                smoothed_angle
                if self._max_angle_this_phase is None
                else max(self._max_angle_this_phase, smoothed_angle)
            )
            if smoothed_angle < down_thresh:
                self.phase = RepPhase.DOWN
                self._min_angle_this_phase = smoothed_angle
        else:  # DOWN
            self._min_angle_this_phase = (
                smoothed_angle
                if self._min_angle_this_phase is None
                else min(self._min_angle_this_phase, smoothed_angle)
            )
            if smoothed_angle > up_thresh:
                self.phase = RepPhase.UP
                self.rep_count += 1
                rep_completed = True
                self._max_angle_this_phase = smoothed_angle
        return rep_completed

    def _compute_risk_score(self) -> int:
        """Aggregate recent risk events into a 0-100 score (windowed average)."""
        if not self._risk_events:
            return 0
        # Keep last 10 frames in the window
        if len(self._risk_events) > 10:
            self._risk_events = self._risk_events[-10:]
        avg_risk = sum(self._risk_events) / len(self._risk_events)
        return int(min(100, max(0, avg_risk)))

    def _add_risk_event(self, risk_value: int) -> None:
        """Record a per-frame risk contribution (0-100)."""
        self._risk_events.append(risk_value)
