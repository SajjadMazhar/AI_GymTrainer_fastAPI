"""Per-WebSocket-connection state.

One SessionState is created per connection and lives only for that
connection's lifetime -- no state is shared across sessions and nothing is
persisted once the connection closes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.calories.estimator import CalorieEstimator
from app.exercises.base import ExerciseAnalyzer
from app.feedback.generator import FeedbackGenerator
from app.pose.base import PoseEstimator
from app.recording.video_recorder import VideoRecorder


@dataclass
class SessionState:
    pose_estimator: PoseEstimator
    analyzer: ExerciseAnalyzer
    calorie_estimator: CalorieEstimator
    feedback_generator: FeedbackGenerator = field(default_factory=FeedbackGenerator)
    video_recorder: VideoRecorder | None = None
    started_at: float = field(default_factory=time.monotonic)

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def close(self) -> None:
        self.pose_estimator.close()
        if self.video_recorder and self.video_recorder.is_recording():
            metadata = self.video_recorder.stop()
            if metadata:
                print(f"Recording saved: {metadata['path']} ({metadata['duration_seconds']}s, {metadata['frame_count']} frames)")
