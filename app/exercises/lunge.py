from __future__ import annotations

from app.exercises.angles import calculate_angle, midpoint, vertical_deviation_angle
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
        rep_completed = self._update_phase(smoothed, DOWN_THRESH, UP_THRESH)

        errors: list[str] = []
        if rep_completed and self._min_angle_this_phase is not None:
            if self._min_angle_this_phase > SHALLOW_DEPTH_CUTOFF:
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

        return AnalysisResult(self.rep_count, self.phase.value, errors, smoothed, confidence)
