from __future__ import annotations

from app.exercises.angles import (
    calculate_angle,
    horizontal_distance,
    midpoint,
    point_velocity,
    velocity_magnitude,
)
from app.exercises.base import (
    VISIBILITY_THRESHOLD,
    AnalysisResult,
    ExerciseAnalyzer,
    RepPhase,
    min_visibility,
    pick_side,
    xy,
)
from app.pose.base import Landmark
from app.pose.landmark_index import LandmarkIndex as LM

DOWN_THRESH = 50.0  # elbow angle below this = fully contracted (curled up)
UP_THRESH = 140.0  # elbow angle above this = arm extending back down
FULL_EXTENSION_CUTOFF = 155.0  # must reach at or above this angle to count as fully extended
TORSO_SWING_LIMIT = 0.05  # normalized-unit drift of shoulder mid from its resting offset to hip mid
ELBOW_DRIFT_LIMIT = 0.08  # normalized-unit growth in elbow-to-shoulder horizontal distance during a rep

# Velocity-based risk thresholds
WRIST_VELOCITY_WARN = 0.20  # sudden wrist acceleration (jerking the weight)
WRIST_VELOCITY_DANGER = 0.35

_LEFT_ARM = (LM.LEFT_SHOULDER, LM.LEFT_ELBOW, LM.LEFT_WRIST)
_RIGHT_ARM = (LM.RIGHT_SHOULDER, LM.RIGHT_ELBOW, LM.RIGHT_WRIST)


class BicepCurlAnalyzer(ExerciseAnalyzer):
    name = "bicep_curl"

    def __init__(self, calibration: dict[str, float] | None = None) -> None:
        super().__init__(calibration)
        self._torso_baseline: tuple[float, float] | None = None
        self._elbow_shoulder_dist_at_rep_start: float | None = None

    def analyze(self, landmarks: list[Landmark]) -> AnalysisResult:
        shoulder_i, elbow_i, wrist_i = pick_side(landmarks, _LEFT_ARM, _RIGHT_ARM)
        confidence = min_visibility(landmarks, (shoulder_i, elbow_i, wrist_i))
        if confidence < VISIBILITY_THRESHOLD:
            return AnalysisResult(self.rep_count, self.phase.value, ["LOW_CONFIDENCE"], None, confidence)

        shoulder, elbow, wrist = xy(landmarks, shoulder_i), xy(landmarks, elbow_i), xy(landmarks, wrist_i)
        elbow_angle = calculate_angle(shoulder, elbow, wrist)
        smoothed = self._smooth(elbow_angle)

        # Use personalized thresholds if available
        down_thresh = self._calibration.get("down_threshold", DOWN_THRESH)
        up_thresh = self._calibration.get("up_threshold", UP_THRESH)
        extension_cutoff = self._calibration.get("depth_cutoff", FULL_EXTENSION_CUTOFF)

        was_up = self.phase == RepPhase.UP
        rep_completed = self._update_phase(smoothed, down_thresh, up_thresh)
        if was_up and self.phase == RepPhase.DOWN:
            self._elbow_shoulder_dist_at_rep_start = horizontal_distance(elbow, shoulder)

        errors: list[str] = []
        frame_risk = 0
        if self.phase == RepPhase.UP and self._max_angle_this_phase is not None:
            if self._max_angle_this_phase < extension_cutoff:
                errors.append("INCOMPLETE_EXTENSION")

        shoulder_mid = midpoint(xy(landmarks, LM.LEFT_SHOULDER), xy(landmarks, LM.RIGHT_SHOULDER))
        hip_mid = midpoint(xy(landmarks, LM.LEFT_HIP), xy(landmarks, LM.RIGHT_HIP))
        offset = (shoulder_mid[0] - hip_mid[0], shoulder_mid[1] - hip_mid[1])
        if self._torso_baseline is None:
            self._torso_baseline = offset
        elif self.phase == RepPhase.DOWN:
            drift = ((offset[0] - self._torso_baseline[0]) ** 2 + (offset[1] - self._torso_baseline[1]) ** 2) ** 0.5
            if drift > TORSO_SWING_LIMIT:
                errors.append("TORSO_SWING")

        if self.phase == RepPhase.DOWN and self._elbow_shoulder_dist_at_rep_start is not None:
            current_dist = horizontal_distance(elbow, shoulder)
            if current_dist - self._elbow_shoulder_dist_at_rep_start > ELBOW_DRIFT_LIMIT:
                errors.append("ELBOW_DRIFT")

        # Velocity-based risk: rapid wrist acceleration (jerking/cheating the curl)
        if self._prev_landmarks is not None and self.phase == RepPhase.DOWN:
            wrist_vel = point_velocity(wrist, xy(self._prev_landmarks, wrist_i))
            wrist_speed = velocity_magnitude(wrist_vel)

            if wrist_speed > WRIST_VELOCITY_DANGER:
                frame_risk = 60  # High risk: jerking the weight
                errors.append("JERKING_MOVEMENT")
            elif wrist_speed > WRIST_VELOCITY_WARN:
                frame_risk = 30

        self._add_risk_event(frame_risk)
        self._prev_landmarks = landmarks

        return AnalysisResult(
            self.rep_count, self.phase.value, errors, smoothed, confidence, self._compute_risk_score()
        )
