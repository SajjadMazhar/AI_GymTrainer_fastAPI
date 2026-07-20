import math

import pytest

from app.calories.estimator import CalorieEstimator


def test_estimate_matches_met_formula():
    est = CalorieEstimator("squat", bodyweight_kg=80.0)
    # 1 hour at MET 5.0, 80kg -> 5.0 * 80 * 1 = 400
    assert math.isclose(est.estimate(3600), 400.0, abs_tol=1e-6)


def test_estimate_zero_at_session_start():
    est = CalorieEstimator("pushup", bodyweight_kg=70.0)
    assert est.estimate(0) == 0.0


def test_estimate_scales_with_elapsed_time():
    est = CalorieEstimator("lunge", bodyweight_kg=60.0)
    half_hour = est.estimate(1800)
    full_hour = est.estimate(3600)
    assert math.isclose(full_hour, half_hour * 2, abs_tol=1e-6)


def test_unknown_exercise_raises():
    with pytest.raises(ValueError):
        CalorieEstimator("jumping_jacks", bodyweight_kg=70.0)
