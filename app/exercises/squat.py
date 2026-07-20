from __future__ import annotations

from app.exercises.angles import calculate_angle, horizontal_distance, midpoint, vertical_deviation_angle
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
        rep_completed = self._update_phase(smoothed, DOWN_THRESH, UP_THRESH)

        errors: list[str] = []
        if rep_completed and self._min_angle_this_phase is not None:
            if self._min_angle_this_phase > SHALLOW_DEPTH_CUTOFF:
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

        return AnalysisResult(self.rep_count, self.phase.value, errors, smoothed, confidence)
