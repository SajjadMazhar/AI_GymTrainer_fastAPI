from app.exercises.squat import SquatAnalyzer
from app.pose.landmark_index import LandmarkIndex as LM
from tests.helpers import default_landmarks, far_point, near_point, set_point


def build_squat_frame(theta_deg, knee_gap=0.2, ankle_gap=0.2, shoulder_offset=0.0):
    lms = default_landmarks()
    cx = 0.5
    knee_y = 0.7
    left_knee = (cx - knee_gap / 2, knee_y)
    right_knee = (cx + knee_gap / 2, knee_y)
    left_hip = near_point(left_knee)
    right_hip = near_point(right_knee)
    left_ankle = far_point(left_knee, theta_deg)
    right_ankle = (left_ankle[0] + ankle_gap, left_ankle[1])
    hip_mid_x = (left_hip[0] + right_hip[0]) / 2
    shoulder_y = left_hip[1] - 0.3
    left_shoulder = (hip_mid_x + shoulder_offset - 0.1, shoulder_y)
    right_shoulder = (hip_mid_x + shoulder_offset + 0.1, shoulder_y)

    set_point(lms, LM.LEFT_KNEE, left_knee)
    set_point(lms, LM.RIGHT_KNEE, right_knee)
    set_point(lms, LM.LEFT_HIP, left_hip)
    set_point(lms, LM.RIGHT_HIP, right_hip)
    set_point(lms, LM.LEFT_ANKLE, left_ankle)
    set_point(lms, LM.RIGHT_ANKLE, right_ankle)
    set_point(lms, LM.LEFT_SHOULDER, left_shoulder)
    set_point(lms, LM.RIGHT_SHOULDER, right_shoulder)
    return lms


def feed(analyzer, frames):
    results = []
    for frame in frames:
        results.append(analyzer.analyze(frame))
    return results


def test_full_depth_rep_counts_once_no_errors():
    analyzer = SquatAnalyzer()
    frames = [build_squat_frame(180)] * 6 + [build_squat_frame(80)] * 8 + [build_squat_frame(180)] * 8
    results = feed(analyzer, frames)
    assert analyzer.rep_count == 1
    assert all("SQUAT_NOT_DEEP_ENOUGH" not in r.posture_errors for r in results)


def test_shallow_squat_flags_not_deep_enough():
    analyzer = SquatAnalyzer()
    frames = [build_squat_frame(180)] * 6 + [build_squat_frame(105)] * 8 + [build_squat_frame(180)] * 8
    results = feed(analyzer, frames)
    assert analyzer.rep_count == 1
    assert any("SQUAT_NOT_DEEP_ENOUGH" in r.posture_errors for r in results)


def test_knee_valgus_detected_at_bottom():
    analyzer = SquatAnalyzer()
    warmup = [build_squat_frame(180)] * 6
    valgus_frames = [build_squat_frame(80, knee_gap=0.05, ankle_gap=0.3)] * 8
    results = feed(analyzer, warmup + valgus_frames)
    assert "KNEE_VALGUS" in results[-1].posture_errors


def test_torso_leaning_forward_detected_at_bottom():
    analyzer = SquatAnalyzer()
    warmup = [build_squat_frame(180)] * 6
    leaning_frames = [build_squat_frame(80, shoulder_offset=0.7)] * 8
    results = feed(analyzer, warmup + leaning_frames)
    assert "TORSO_LEANING_FORWARD" in results[-1].posture_errors


def test_low_confidence_when_landmarks_not_visible():
    analyzer = SquatAnalyzer()
    frame = default_landmarks(visibility=0.0)
    result = analyzer.analyze(frame)
    assert result.posture_errors == ["LOW_CONFIDENCE"]
    assert result.primary_angle is None
