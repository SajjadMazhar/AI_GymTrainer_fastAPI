from app.exercises.lunge import LungeAnalyzer
from app.pose.landmark_index import LandmarkIndex as LM
from tests.helpers import default_landmarks, point_at_angle, set_point


def build_frame(front_theta_deg, back_theta_deg=175.0, lean=False):
    """Right leg is the "front" leg (its knee sits well forward in +x, so its
    ankle stays clearly further from the hip midpoint than the back leg's,
    regardless of bend angle). front_theta_deg drives the rep-counting angle
    (front knee hip-knee-ankle); back_theta_deg controls the back knee bend."""
    lms = default_landmarks()
    back_hip = (0.48, 0.5)
    front_hip = (0.52, 0.5)
    hip_mid_x = (back_hip[0] + front_hip[0]) / 2

    back_knee = (0.45, 0.7)
    back_ankle = point_at_angle(back_knee, back_hip, back_theta_deg, scale=0.2)

    front_knee = (0.8, 0.7)
    front_ankle = point_at_angle(front_knee, front_hip, front_theta_deg, scale=0.2)

    shoulder_y = 0.2
    shoulder_offset = 0.7 if lean else 0.0
    left_shoulder = (hip_mid_x + shoulder_offset - 0.1, shoulder_y)
    right_shoulder = (hip_mid_x + shoulder_offset + 0.1, shoulder_y)

    set_point(lms, LM.LEFT_HIP, back_hip)
    set_point(lms, LM.LEFT_KNEE, back_knee)
    set_point(lms, LM.LEFT_ANKLE, back_ankle)
    set_point(lms, LM.RIGHT_HIP, front_hip)
    set_point(lms, LM.RIGHT_KNEE, front_knee)
    set_point(lms, LM.RIGHT_ANKLE, front_ankle)
    set_point(lms, LM.LEFT_SHOULDER, left_shoulder)
    set_point(lms, LM.RIGHT_SHOULDER, right_shoulder)
    return lms


def feed(analyzer, frames):
    return [analyzer.analyze(f) for f in frames]


def test_full_depth_rep_counts_once_no_errors():
    analyzer = LungeAnalyzer()
    frames = [build_frame(180)] * 6 + [build_frame(80)] * 8 + [build_frame(180)] * 8
    results = feed(analyzer, frames)
    assert analyzer.rep_count == 1
    assert all("INSUFFICIENT_DEPTH" not in r.posture_errors for r in results)


def test_shallow_lunge_flags_insufficient_depth():
    analyzer = LungeAnalyzer()
    frames = [build_frame(180)] * 6 + [build_frame(105)] * 8 + [build_frame(180)] * 8
    results = feed(analyzer, frames)
    assert analyzer.rep_count == 1
    assert any("INSUFFICIENT_DEPTH" in r.posture_errors for r in results)


def test_back_knee_too_high_detected():
    analyzer = LungeAnalyzer()
    warmup = [build_frame(180, back_theta_deg=175)] * 6
    # front leg drops low, back knee stays nearly straight (too high off the floor)
    frames = [build_frame(80, back_theta_deg=175)] * 8
    results = feed(analyzer, warmup + frames)
    assert "BACK_KNEE_TOO_HIGH" in results[-1].posture_errors


def test_back_knee_low_enough_not_flagged():
    analyzer = LungeAnalyzer()
    warmup = [build_frame(180, back_theta_deg=90)] * 6
    frames = [build_frame(80, back_theta_deg=90)] * 8
    results = feed(analyzer, warmup + frames)
    assert "BACK_KNEE_TOO_HIGH" not in results[-1].posture_errors


def test_torso_leaning_detected():
    analyzer = LungeAnalyzer()
    warmup = [build_frame(180, lean=False)] * 6
    frames = [build_frame(80, lean=True)] * 8
    results = feed(analyzer, warmup + frames)
    assert "TORSO_LEANING" in results[-1].posture_errors


def test_low_confidence_when_landmarks_not_visible():
    analyzer = LungeAnalyzer()
    frame = default_landmarks(visibility=0.0)
    result = analyzer.analyze(frame)
    assert result.posture_errors == ["LOW_CONFIDENCE"]
    assert result.primary_angle is None
