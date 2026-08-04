"""Compute personalized thresholds from calibration data."""
from __future__ import annotations

from app.user.profile import ExerciseCalibration

# Default thresholds (fallback when no calibration exists)
DEFAULT_THRESHOLDS = {
    "squat": {
        "down_thresh": 110.0,
        "up_thresh": 160.0,
        "depth_cutoff": 100.0,
    },
    "pushup": {
        "down_thresh": 110.0,
        "up_thresh": 150.0,
        "depth_cutoff": 100.0,
    },
    "bicep_curl": {
        "down_thresh": 50.0,
        "up_thresh": 140.0,
        "depth_cutoff": None,
    },
    "lunge": {
        "down_thresh": 100.0,
        "up_thresh": 160.0,
        "depth_cutoff": 90.0,
    },
}


def compute_personalized_thresholds(
    exercise: str,
    min_angle: float,
    max_angle: float,
) -> dict[str, float | None]:
    """Compute personalized thresholds from observed min/max angles during calibration.

    Args:
        exercise: Exercise name (squat, pushup, bicep_curl, lunge)
        min_angle: Minimum angle observed across calibration reps
        max_angle: Maximum angle observed across calibration reps

    Returns:
        dict with keys: down_threshold, up_threshold, depth_cutoff

    Strategy:
        - down_threshold: set slightly above the user's observed min (with ~10° buffer)
        - up_threshold: set slightly below the user's observed max (with ~10° buffer)
        - depth_cutoff: set at user's min + small margin (ensures they can reach it)
    """
    defaults = DEFAULT_THRESHOLDS.get(exercise, DEFAULT_THRESHOLDS["squat"])

    # Add buffers to avoid false positives from noise
    down_buffer = 10.0
    up_buffer = 10.0
    depth_margin = 5.0

    down_threshold = min(min_angle + down_buffer, defaults["down_thresh"])
    up_threshold = max(max_angle - up_buffer, defaults["up_thresh"])

    # Depth cutoff: user's min + small margin (must be achievable)
    depth_cutoff = None
    if defaults["depth_cutoff"] is not None:
        depth_cutoff = min_angle + depth_margin

    return {
        "down_threshold": down_threshold,
        "up_threshold": up_threshold,
        "depth_cutoff": depth_cutoff,
    }


def calibrate_from_reps(
    exercise: str,
    angle_observations: list[float],
) -> ExerciseCalibration:
    """Build a calibration from a list of angle observations (from multiple reps).

    Args:
        exercise: Exercise name
        angle_observations: List of primary angles observed across calibration reps

    Returns:
        ExerciseCalibration with computed personalized thresholds
    """
    if not angle_observations:
        raise ValueError("Need at least one angle observation to calibrate")

    min_angle = min(angle_observations)
    max_angle = max(angle_observations)

    thresholds = compute_personalized_thresholds(exercise, min_angle, max_angle)

    return ExerciseCalibration(
        exercise=exercise,
        min_angle_observed=min_angle,
        max_angle_observed=max_angle,
        sample_count=len(angle_observations),
        down_threshold=thresholds["down_threshold"],
        up_threshold=thresholds["up_threshold"],
        depth_cutoff=thresholds["depth_cutoff"],
    )
