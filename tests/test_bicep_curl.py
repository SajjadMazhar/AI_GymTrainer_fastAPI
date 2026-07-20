from app.exercises.bicep_curl import BicepCurlAnalyzer
from app.pose.landmark_index import LandmarkIndex as LM
from tests.helpers import default_landmarks, point_at_angle, set_point


def build_frame(theta_deg, shoulder=(0.5, 0.4), hip=(0.5, 0.8), elbow_offset=(0.0, 0.3)):
    """theta_deg drives the elbow angle (shoulder-elbow-wrist). elbow is
    placed at shoulder + elbow_offset (world-space, so shoulder/hip can move
    for torso-swing tests without perturbing the elbow-to-shoulder distance
    used by the elbow-drift check, unless elbow_offset itself is changed)."""
    lms = default_landmarks()
    elbow = (shoulder[0] + elbow_offset[0], shoulder[1] + elbow_offset[1])
    wrist = point_at_angle(elbow, shoulder, theta_deg)

    set_point(lms, LM.LEFT_SHOULDER, shoulder)
    set_point(lms, LM.RIGHT_SHOULDER, shoulder)
    set_point(lms, LM.LEFT_ELBOW, elbow)
    set_point(lms, LM.RIGHT_ELBOW, elbow)
    set_point(lms, LM.LEFT_WRIST, wrist)
    set_point(lms, LM.RIGHT_WRIST, wrist)
    set_point(lms, LM.LEFT_HIP, hip)
    set_point(lms, LM.RIGHT_HIP, hip)
    return lms


def feed(analyzer, frames):
    return [analyzer.analyze(f) for f in frames]


def test_full_curl_rep_counts_once_no_errors():
    analyzer = BicepCurlAnalyzer()
    # extended (180) -> fully contracted (30) -> extended (180)
    frames = [build_frame(180)] * 6 + [build_frame(30)] * 8 + [build_frame(180)] * 8
    results = feed(analyzer, frames)
    assert analyzer.rep_count == 1
    assert all("INCOMPLETE_EXTENSION" not in r.posture_errors for r in results[-3:])
    assert all("TORSO_SWING" not in r.posture_errors for r in results)
    assert all("ELBOW_DRIFT" not in r.posture_errors for r in results)


def test_incomplete_extension_flagged():
    analyzer = BicepCurlAnalyzer()
    # extended baseline, then contract, then only partially extend back (145 < 155 cutoff)
    frames = [build_frame(180)] * 6 + [build_frame(30)] * 8 + [build_frame(145)] * 8
    results = feed(analyzer, frames)
    assert analyzer.rep_count == 1
    assert "INCOMPLETE_EXTENSION" in results[-1].posture_errors


def test_torso_swing_detected():
    analyzer = BicepCurlAnalyzer()
    warmup = [build_frame(180, shoulder=(0.5, 0.4))] * 6
    # shoulder drifts away from its resting offset relative to the hip while contracted
    swinging = [build_frame(30, shoulder=(0.65, 0.4))] * 8
    results = feed(analyzer, warmup + swinging)
    assert "TORSO_SWING" in results[-1].posture_errors


def test_elbow_drift_detected():
    analyzer = BicepCurlAnalyzer()
    warmup = [build_frame(180, elbow_offset=(0.0, 0.3))] * 6
    # enter the contracted phase with the elbow still pinned (zero drift)...
    contract_start = [build_frame(30, elbow_offset=(0.0, 0.3))] * 8
    # ...then let the elbow drift forward mid-rep
    drifting = [build_frame(30, elbow_offset=(0.2, 0.3))] * 8
    results = feed(analyzer, warmup + contract_start + drifting)
    assert "ELBOW_DRIFT" in results[-1].posture_errors


def test_low_confidence_when_landmarks_not_visible():
    analyzer = BicepCurlAnalyzer()
    frame = default_landmarks(visibility=0.0)
    result = analyzer.analyze(frame)
    assert result.posture_errors == ["LOW_CONFIDENCE"]
    assert result.primary_angle is None
