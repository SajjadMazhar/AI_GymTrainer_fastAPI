from __future__ import annotations

from app.exercises.angles import (
    calculate_angle,
    lateral_velocity,
    midpoint,
    point_velocity,
    vertical_deviation_angle,
)
from app.exercises.base import (
    VISIBILITY_THRESHOLD,
    AnalysisResult,
    ExerciseAnalyzer,
    RepPhase,
    min_visibility,
    xy,
)
from app.pose.base import Landmark
from app.pose.landmark_index import LandmarkIndex as LM

DOWN_THRESH = 110.0  # front knee angle below this = descending into lunge
UP_THRESH = 160.0  # front knee angle above this = standing
SHALLOW_DEPTH_CUTOFF = 100.0  # front knee must reach at or below this to count as deep enough
KNEE_PAST_TOES_MARGIN = 0.03  # normalized-x tolerance
BACK_KNEE_HIGH_LIMIT = 130.0  # back knee angle above this while front knee is down = not low enough
TORSO_LEAN_LIMIT = 30.0  # degrees off vertical (stricter than squat, lunges stay more upright)

# Velocity-based risk thresholds
FRONT_KNEE_LATERAL_VELOCITY_WARN = 0.12  # lateral knee instability during lunge
FRONT_KNEE_LATERAL_VELOCITY_DANGER = 0.22

_LEFT_LEG = (LM.LEFT_HIP, LM.LEFT_KNEE, LM.LEFT_ANKLE)
_RIGHT_LEG = (LM.RIGHT_HIP, LM.RIGHT_KNEE, LM.RIGHT_ANKLE)


class LungeAnalyzer(ExerciseAnalyzer):
    name = "lunge"

    def analyze(self, landmarks: list[Landmark]) -> AnalysisResult:
        required = _LEFT_LEG + _RIGHT_LEG
        confidence = min_visibility(landmarks, required)
        if confidence < VISIBILITY_THRESHOLD:
            return AnalysisResult(self.rep_count, self.phase.value, ["LOW_CONFIDENCE"], None, confidence)

        left_hip, left_knee, left_ankle = (xy(landmarks, i) for i in _LEFT_LEG)
        right_hip, right_knee, right_ankle = (xy(landmarks, i) for i in _RIGHT_LEG)
        hip_mid = midpoint(left_hip, right_hip)

        # The stepped-forward leg has the ankle further (horizontally) from the
        # hip midpoint than the trailing leg's ankle.
        left_dist = abs(left_ankle[0] - hip_mid[0])
        right_dist = abs(right_ankle[0] - hip_mid[0])
        if left_dist >= right_dist:
            front_hip, front_knee, front_ankle = left_hip, left_knee, left_ankle
            back_hip, back_knee, back_ankle = right_hip, right_knee, right_ankle
            facing_positive_x = front_ankle[0] >= hip_mid[0]
        else:
            front_hip, front_knee, front_ankle = right_hip, right_knee, right_ankle
            back_hip, back_knee, back_ankle = left_hip, left_knee, left_ankle
            facing_positive_x = front_ankle[0] >= hip_mid[0]

        front_angle = calculate_angle(front_hip, front_knee, front_ankle)
        smoothed = self._smooth(front_angle)

        # Use personalized thresholds if available
        down_thresh = self._calibration.get("down_threshold", DOWN_THRESH)
        up_thresh = self._calibration.get("up_threshold", UP_THRESH)
        depth_cutoff = self._calibration.get("depth_cutoff", SHALLOW_DEPTH_CUTOFF)

        prev_phase = self.phase
        rep_completed = self._update_phase(smoothed, down_thresh, up_thresh)

        errors: list[str] = []
        frame_risk = 0
        if rep_completed and self._min_angle_this_phase is not None:
            if self._min_angle_this_phase > depth_cutoff:
                errors.append("INSUFFICIENT_DEPTH")

        if self.phase == RepPhase.DOWN:
            if facing_positive_x:
                knee_past_toes = front_knee[0] > front_ankle[0] + KNEE_PAST_TOES_MARGIN
            else:
                knee_past_toes = front_knee[0] < front_ankle[0] - KNEE_PAST_TOES_MARGIN
            if knee_past_toes:
                errors.append("FRONT_KNEE_PAST_TOES")

            back_angle = calculate_angle(back_hip, back_knee, back_ankle)
            if back_angle > BACK_KNEE_HIGH_LIMIT:
                errors.append("BACK_KNEE_TOO_HIGH")

            shoulders = (LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER)
            if min_visibility(landmarks, shoulders) >= VISIBILITY_THRESHOLD:
                shoulder_mid = midpoint(xy(landmarks, LM.LEFT_SHOULDER), xy(landmarks, LM.RIGHT_SHOULDER))
                if vertical_deviation_angle(shoulder_mid, hip_mid) > TORSO_LEAN_LIMIT:
                    errors.append("TORSO_LEANING")

        # Velocity-based risk: lateral front knee velocity during ascent (similar to squat)
        if self._prev_landmarks is not None and prev_phase == RepPhase.DOWN and self.phase == RepPhase.UP:
            # Determine which knee is the front knee from previous frame
            prev_left_ankle = xy(self._prev_landmarks, LM.LEFT_ANKLE)
            prev_right_ankle = xy(self._prev_landmarks, LM.RIGHT_ANKLE)
            prev_hip_mid = midpoint(xy(self._prev_landmarks, LM.LEFT_HIP), xy(self._prev_landmarks, LM.RIGHT_HIP))
            prev_left_dist = abs(prev_left_ankle[0] - prev_hip_mid[0])
            prev_right_dist = abs(prev_right_ankle[0] - prev_hip_mid[0])

            if prev_left_dist >= prev_right_dist:
                front_knee_idx = LM.LEFT_KNEE
            else:
                front_knee_idx = LM.RIGHT_KNEE

            front_knee_vel = point_velocity(xy(landmarks, front_knee_idx), xy(self._prev_landmarks, front_knee_idx))
            front_knee_lateral_speed = abs(lateral_velocity(front_knee_vel))

            if front_knee_lateral_speed > FRONT_KNEE_LATERAL_VELOCITY_DANGER:
                frame_risk = 75  # High risk during lunge ascent
                errors.append("DYNAMIC_KNEE_INSTABILITY")
            elif front_knee_lateral_speed > FRONT_KNEE_LATERAL_VELOCITY_WARN:
                frame_risk = 38

        self._add_risk_event(frame_risk)
        self._prev_landmarks = landmarks

        return AnalysisResult(
            self.rep_count, self.phase.value, errors, smoothed, confidence, self._compute_risk_score()
        )
