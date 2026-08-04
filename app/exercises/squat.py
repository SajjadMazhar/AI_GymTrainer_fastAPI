from __future__ import annotations

from app.exercises.angles import (
    calculate_angle,
    horizontal_distance,
    lateral_velocity,
    midpoint,
    point_velocity,
    velocity_magnitude,
    vertical_deviation_angle,
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

DOWN_THRESH = 110.0  # knee angle below this = descending into squat
UP_THRESH = 160.0  # knee angle above this = standing
SHALLOW_DEPTH_CUTOFF = 100.0  # must reach at or below this angle to count as deep enough
VALGUS_RATIO = 0.7  # knee-gap < this * ankle-gap -> knees caving in
TORSO_LEAN_LIMIT = 45.0  # degrees off vertical

# Velocity-based risk thresholds
LATERAL_KNEE_VELOCITY_WARN = 0.15  # normalized units/frame - sudden lateral knee movement during ascent
LATERAL_KNEE_VELOCITY_DANGER = 0.25  # above this = high injury risk

_LEFT_LEG = (LM.LEFT_HIP, LM.LEFT_KNEE, LM.LEFT_ANKLE)
_RIGHT_LEG = (LM.RIGHT_HIP, LM.RIGHT_KNEE, LM.RIGHT_ANKLE)


class SquatAnalyzer(ExerciseAnalyzer):
    name = "squat"

    def analyze(self, landmarks: list[Landmark]) -> AnalysisResult:
        hip_i, knee_i, ankle_i = pick_side(landmarks, _LEFT_LEG, _RIGHT_LEG)
        confidence = min_visibility(landmarks, (hip_i, knee_i, ankle_i))
        if confidence < VISIBILITY_THRESHOLD:
            return AnalysisResult(self.rep_count, self.phase.value, ["LOW_CONFIDENCE"], None, confidence)

        knee_angle = calculate_angle(xy(landmarks, hip_i), xy(landmarks, knee_i), xy(landmarks, ankle_i))
        smoothed = self._smooth(knee_angle)

        # Use personalized thresholds if available, otherwise use defaults
        down_thresh = self._calibration.get("down_threshold", DOWN_THRESH)
        up_thresh = self._calibration.get("up_threshold", UP_THRESH)
        depth_cutoff = self._calibration.get("depth_cutoff", SHALLOW_DEPTH_CUTOFF)

        # Track previous frame for velocity computation
        prev_phase = self.phase
        rep_completed = self._update_phase(smoothed, down_thresh, up_thresh)

        errors: list[str] = []
        frame_risk = 0  # 0-100 risk contribution this frame
        if rep_completed and self._min_angle_this_phase is not None:
            if self._min_angle_this_phase > depth_cutoff:
                errors.append("SQUAT_NOT_DEEP_ENOUGH")

        if self.phase == RepPhase.DOWN:
            knee_gap = horizontal_distance(xy(landmarks, LM.LEFT_KNEE), xy(landmarks, LM.RIGHT_KNEE))
            ankle_gap = horizontal_distance(xy(landmarks, LM.LEFT_ANKLE), xy(landmarks, LM.RIGHT_ANKLE))
            if ankle_gap > 0 and knee_gap < VALGUS_RATIO * ankle_gap:
                errors.append("KNEE_VALGUS")

            shoulder_mid = midpoint(xy(landmarks, LM.LEFT_SHOULDER), xy(landmarks, LM.RIGHT_SHOULDER))
            hip_mid = midpoint(xy(landmarks, LM.LEFT_HIP), xy(landmarks, LM.RIGHT_HIP))
            if vertical_deviation_angle(shoulder_mid, hip_mid) > TORSO_LEAN_LIMIT:
                errors.append("TORSO_LEANING_FORWARD")

        # Velocity-based risk: lateral knee velocity during ascent (DOWN->UP transition or early UP phase)
        # This catches dynamic knee valgus/varus that static checks miss
        if self._prev_landmarks is not None and prev_phase == RepPhase.DOWN and self.phase == RepPhase.UP:
            # Just transitioned from DOWN to UP (ascending phase where injury risk is highest)
            left_knee_vel = point_velocity(xy(landmarks, LM.LEFT_KNEE), xy(self._prev_landmarks, LM.LEFT_KNEE))
            right_knee_vel = point_velocity(xy(landmarks, LM.RIGHT_KNEE), xy(self._prev_landmarks, LM.RIGHT_KNEE))

            # Check magnitude of lateral (horizontal) knee velocity
            left_lateral_speed = abs(lateral_velocity(left_knee_vel))
            right_lateral_speed = abs(lateral_velocity(right_knee_vel))
            max_lateral_speed = max(left_lateral_speed, right_lateral_speed)

            if max_lateral_speed > LATERAL_KNEE_VELOCITY_DANGER:
                frame_risk = 80  # High risk: rapid lateral knee movement during ascent
                errors.append("DYNAMIC_KNEE_INSTABILITY")
            elif max_lateral_speed > LATERAL_KNEE_VELOCITY_WARN:
                frame_risk = 40  # Moderate risk

        self._add_risk_event(frame_risk)
        self._prev_landmarks = landmarks  # Store for next frame

        return AnalysisResult(
            self.rep_count, self.phase.value, errors, smoothed, confidence, self._compute_risk_score()
        )
