from __future__ import annotations

from app.exercises.angles import calculate_angle, point_velocity, velocity_magnitude, vertical_velocity
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

DOWN_THRESH = 110.0  # elbow angle below this = descending into push-up
UP_THRESH = 150.0  # elbow angle above this = arms extended
SHALLOW_DEPTH_CUTOFF = 100.0  # must reach at or below this angle to count as deep enough
STRAIGHT_BODY_LIMIT = 160.0  # shoulder-hip-ankle angle below this = hips out of line
HIP_LINE_MARGIN = 0.02  # normalized-y tolerance around the shoulder->ankle line

# Velocity-based risk thresholds
HIP_VERTICAL_VELOCITY_WARN = 0.10  # rapid vertical hip movement (sag/pike collapse)
HIP_VERTICAL_VELOCITY_DANGER = 0.18

_LEFT_ARM = (LM.LEFT_SHOULDER, LM.LEFT_ELBOW, LM.LEFT_WRIST)
_RIGHT_ARM = (LM.RIGHT_SHOULDER, LM.RIGHT_ELBOW, LM.RIGHT_WRIST)
_LEFT_BODY_LINE = (LM.LEFT_SHOULDER, LM.LEFT_HIP, LM.LEFT_ANKLE)
_RIGHT_BODY_LINE = (LM.RIGHT_SHOULDER, LM.RIGHT_HIP, LM.RIGHT_ANKLE)


class PushupAnalyzer(ExerciseAnalyzer):
    name = "pushup"

    def analyze(self, landmarks: list[Landmark]) -> AnalysisResult:
        shoulder_i, elbow_i, wrist_i = pick_side(landmarks, _LEFT_ARM, _RIGHT_ARM)
        confidence = min_visibility(landmarks, (shoulder_i, elbow_i, wrist_i))
        if confidence < VISIBILITY_THRESHOLD:
            return AnalysisResult(self.rep_count, self.phase.value, ["LOW_CONFIDENCE"], None, confidence)

        elbow_angle = calculate_angle(xy(landmarks, shoulder_i), xy(landmarks, elbow_i), xy(landmarks, wrist_i))
        smoothed = self._smooth(elbow_angle)

        # Use personalized thresholds if available
        down_thresh = self._calibration.get("down_threshold", DOWN_THRESH)
        up_thresh = self._calibration.get("up_threshold", UP_THRESH)
        depth_cutoff = self._calibration.get("depth_cutoff", SHALLOW_DEPTH_CUTOFF)

        rep_completed = self._update_phase(smoothed, down_thresh, up_thresh)

        errors: list[str] = []
        frame_risk = 0
        if rep_completed and self._min_angle_this_phase is not None:
            if self._min_angle_this_phase > depth_cutoff:
                errors.append("INSUFFICIENT_DEPTH")

        body_line_i = pick_side(landmarks, _LEFT_BODY_LINE, _RIGHT_BODY_LINE)
        if min_visibility(landmarks, body_line_i) >= VISIBILITY_THRESHOLD:
            shoulder, hip, ankle = (xy(landmarks, i) for i in body_line_i)
            body_angle = calculate_angle(shoulder, hip, ankle)
            if body_angle < STRAIGHT_BODY_LIMIT:
                # Straight-line shoulder->ankle at hip's x tells sag (hip below the
                # line, larger y) apart from pike (hip above the line, smaller y).
                t = (hip[0] - shoulder[0]) / (ankle[0] - shoulder[0]) if ankle[0] != shoulder[0] else 0.5
                expected_hip_y = shoulder[1] + t * (ankle[1] - shoulder[1])
                if hip[1] > expected_hip_y + HIP_LINE_MARGIN:
                    errors.append("HIP_SAG")
                elif hip[1] < expected_hip_y - HIP_LINE_MARGIN:
                    errors.append("HIP_PIKE")

        # Velocity-based risk: rapid vertical hip velocity (core instability / collapse)
        if self._prev_landmarks is not None and self.phase == RepPhase.DOWN:
            # During the descending phase, check for sudden hip drops/pikes
            hip_pos = xy(landmarks, body_line_i[1])  # middle element is hip
            prev_hip_pos = xy(self._prev_landmarks, body_line_i[1])
            hip_vel = point_velocity(hip_pos, prev_hip_pos)
            hip_vert_speed = abs(vertical_velocity(hip_vel))

            if hip_vert_speed > HIP_VERTICAL_VELOCITY_DANGER:
                frame_risk = 70  # High risk: core collapse
                errors.append("RAPID_CORE_INSTABILITY")
            elif hip_vert_speed > HIP_VERTICAL_VELOCITY_WARN:
                frame_risk = 35

        self._add_risk_event(frame_risk)
        self._prev_landmarks = landmarks

        return AnalysisResult(
            self.rep_count, self.phase.value, errors, smoothed, confidence, self._compute_risk_score()
        )
