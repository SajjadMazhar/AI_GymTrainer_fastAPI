"""User profile management for personalized threshold calibration."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExerciseCalibration:
    """Calibration data for a single exercise."""

    exercise: str
    min_angle_observed: float  # minimum angle reached across calibration reps
    max_angle_observed: float  # maximum angle reached across calibration reps
    sample_count: int  # number of reps used for calibration

    # Computed personalized thresholds (adjusted from defaults based on user's ROM)
    down_threshold: float
    up_threshold: float
    depth_cutoff: float | None = None  # for depth checks (squat/pushup/lunge)


@dataclass
class UserProfile:
    """Complete user profile with calibration data for all exercises."""

    user_id: str
    bodyweight_kg: float
    calibrations: dict[str, ExerciseCalibration]  # exercise name -> calibration

    def get_calibration(self, exercise: str) -> ExerciseCalibration | None:
        """Retrieve calibration data for a specific exercise."""
        return self.calibrations.get(exercise)

    def set_calibration(self, calibration: ExerciseCalibration) -> None:
        """Store or update calibration data for an exercise."""
        self.calibrations[calibration.exercise] = calibration


class ProfileStore:
    """Persistent storage for user profiles (JSON file per user)."""

    def __init__(self, storage_dir: str = "data/profiles") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, user_id: str) -> Path:
        """Get the file path for a user's profile."""
        return self.storage_dir / f"{user_id}.json"

    def load(self, user_id: str) -> UserProfile | None:
        """Load a user profile from disk, or None if not found."""
        path = self._profile_path(user_id)
        if not path.exists():
            return None

        with path.open("r") as f:
            data = json.load(f)

        # Reconstruct ExerciseCalibration objects
        calibrations = {}
        for ex_name, cal_data in data.get("calibrations", {}).items():
            calibrations[ex_name] = ExerciseCalibration(**cal_data)

        return UserProfile(
            user_id=data["user_id"],
            bodyweight_kg=data["bodyweight_kg"],
            calibrations=calibrations,
        )

    def save(self, profile: UserProfile) -> None:
        """Save a user profile to disk."""
        path = self._profile_path(profile.user_id)

        data = {
            "user_id": profile.user_id,
            "bodyweight_kg": profile.bodyweight_kg,
            "calibrations": {
                ex_name: asdict(cal) for ex_name, cal in profile.calibrations.items()
            },
        }

        with path.open("w") as f:
            json.dump(data, f, indent=2)

    def delete(self, user_id: str) -> bool:
        """Delete a user profile. Returns True if the profile existed."""
        path = self._profile_path(user_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_users(self) -> list[str]:
        """List all user IDs with stored profiles."""
        return [p.stem for p in self.storage_dir.glob("*.json")]
