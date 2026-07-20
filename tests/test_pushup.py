from app.exercises.pushup import PushupAnalyzer
from app.pose.landmark_index import LandmarkIndex as LM
from tests.helpers import default_landmarks, far_point, set_point


def build_frame(theta_deg, hip_offset_y=0.0):
    """theta_deg drives the elbow angle (shoulder-elbow-wrist). hip_offset_y
    shifts the hip off the straight shoulder->ankle line: positive = sag
    (hip lower, larger y), negative = pike (hip higher, smaller y)."""
    lms = default_landmarks()

    shoulder = (0.2, 0.4)
    ankle = (0.8, 0.4)
    # elbow placed so that (shoulder - elbow) is the analyzer's fixed (0, -1)
    # reference direction, and far_point(elbow, theta_deg) gives the wrist at
    # exactly theta_deg degrees from that reference -- see tests/helpers.py.
    elbow = (shoulder[0], shoulder[1] + 1.0)
    wrist = far_point(elbow, theta_deg)

    hip_x = (shoulder[0] + ankle[0]) / 2
    hip_y = (shoulder[1] + ankle[1]) / 2 + hip_offset_y
    hip = (hip_x, hip_y)

    set_point(lms, LM.LEFT_SHOULDER, shoulder)
    set_point(lms, LM.RIGHT_SHOULDER, shoulder)
    set_point(lms, LM.LEFT_ELBOW, elbow)
    set_point(lms, LM.RIGHT_ELBOW, elbow)
    set_point(lms, LM.LEFT_WRIST, wrist)
    set_point(lms, LM.RIGHT_WRIST, wrist)
    set_point(lms, LM.LEFT_HIP, hip)
    set_point(lms, LM.RIGHT_HIP, hip)
    set_point(lms, LM.LEFT_ANKLE, ankle)
    set_point(lms, LM.RIGHT_ANKLE, ankle)
    return lms


def feed(analyzer, frames):
    return [analyzer.analyze(f) for f in frames]


def test_full_depth_rep_counts_once_no_errors():
    analyzer = PushupAnalyzer()
    frames = [build_frame(180)] * 6 + [build_frame(80)] * 8 + [build_frame(180)] * 8
    results = feed(analyzer, frames)
    assert analyzer.rep_count == 1
    assert all("INSUFFICIENT_DEPTH" not in r.posture_errors for r in results)


def test_shallow_pushup_flags_insufficient_depth():
    analyzer = PushupAnalyzer()
    frames = [build_frame(180)] * 6 + [build_frame(105)] * 8 + [build_frame(180)] * 8
    results = feed(analyzer, frames)
    assert analyzer.rep_count == 1
    assert any("INSUFFICIENT_DEPTH" in r.posture_errors for r in results)


def test_hip_sag_detected():
    analyzer = PushupAnalyzer()
    frames = [build_frame(180, hip_offset_y=0.15)] * 8
    results = feed(analyzer, frames)
    assert "HIP_SAG" in results[-1].posture_errors


def test_hip_pike_detected():
    analyzer = PushupAnalyzer()
    frames = [build_frame(180, hip_offset_y=-0.15)] * 8
    results = feed(analyzer, frames)
    assert "HIP_PIKE" in results[-1].posture_errors


def test_straight_body_no_sag_or_pike():
    analyzer = PushupAnalyzer()
    frames = [build_frame(180, hip_offset_y=0.0)] * 8
    results = feed(analyzer, frames)
    assert "HIP_SAG" not in results[-1].posture_errors
    assert "HIP_PIKE" not in results[-1].posture_errors
