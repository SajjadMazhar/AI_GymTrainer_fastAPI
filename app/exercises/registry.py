from __future__ import annotations

from app.exercises.base import ExerciseAnalyzer
from app.exercises.bicep_curl import BicepCurlAnalyzer
from app.exercises.lunge import LungeAnalyzer
from app.exercises.pushup import PushupAnalyzer
from app.exercises.squat import SquatAnalyzer

EXERCISES: dict[str, type[ExerciseAnalyzer]] = {
    "squat": SquatAnalyzer,
    "pushup": PushupAnalyzer,
    "bicep_curl": BicepCurlAnalyzer,
    "lunge": LungeAnalyzer,
}
