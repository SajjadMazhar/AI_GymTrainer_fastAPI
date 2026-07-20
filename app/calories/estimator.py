"""MET-based calorie estimation.

calories = MET * bodyweight_kg * elapsed_hours

Session duration is precisely trackable server-side (timestamp at session
start vs. now), so it's used as the source of truth rather than a
reps-based approximation.
"""
from __future__ import annotations

# Moderate-intensity resistance/calisthenics MET approximations
# (Compendium of Physical Activities-style values).
MET_VALUES: dict[str, float] = {
    "squat": 5.0,
    "pushup": 8.0,
    "bicep_curl": 3.5,
    "lunge": 4.0,
}


class CalorieEstimator:
    def __init__(self, exercise: str, bodyweight_kg: float) -> None:
        if exercise not in MET_VALUES:
            raise ValueError(f"Unknown exercise: {exercise!r}")
        self.met = MET_VALUES[exercise]
        self.bodyweight_kg = bodyweight_kg

    def estimate(self, elapsed_seconds: float) -> float:
        hours = elapsed_seconds / 3600.0
        return round(self.met * self.bodyweight_kg * hours, 2)
