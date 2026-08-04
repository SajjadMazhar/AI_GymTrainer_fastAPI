"""Offline video analysis: run the same pose -> analyzer pipeline used for
live phone sessions over every frame of an already-recorded video file.

For testing/debugging only -- lets you validate rep counting and posture
rules against a pre-recorded clip without a phone or WebSocket involved.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import cv2

from app.calories.estimator import CalorieEstimator
from app.exercises.registry import EXERCISES
from app.feedback.generator import FeedbackGenerator
from app.pose.factory import get_pose_estimator

MAX_FRAMES = 9000  # safety cap (~5 min at 30fps) so one upload can't block indefinitely
DEFAULT_FPS = 30.0


@dataclass
class VideoAnalysisResult:
    exercise: str
    rep_count: int
    duration_seconds: float
    frames_processed: int
    frames_with_person_detected: int
    posture_error_counts: dict[str, int]
    calories_estimate: float
    feedback_summary: list[str]
    truncated: bool
    average_risk_score: int = 0  # average risk score across all frames


def analyze_video_file(
    video_path: str,
    exercise: str,
    bodyweight_kg: float,
    pose_backend: str = "mediapipe",
) -> VideoAnalysisResult:
    if exercise not in EXERCISES:
        raise ValueError(f"Unknown exercise: {exercise!r}")

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError("Could not open uploaded video file")

    fps = capture.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = DEFAULT_FPS

    pose_estimator = get_pose_estimator(pose_backend)
    analyzer = EXERCISES[exercise]()
    error_counts: Counter[str] = Counter()
    frames_processed = 0
    frames_with_person_detected = 0
    truncated = False
    risk_scores: list[int] = []  # collect risk scores for averaging

    try:
        while True:
            if frames_processed >= MAX_FRAMES:
                truncated = True
                break
            ok, frame = capture.read()
            if not ok:
                break

            pose_result = pose_estimator.process(frame)
            frames_processed += 1
            if pose_result.landmarks is None:
                error_counts["NO_PERSON_DETECTED"] += 1
                continue

            frames_with_person_detected += 1
            result = analyzer.analyze(pose_result.landmarks)
            for code in result.posture_errors:
                error_counts[code] += 1
            risk_scores.append(result.risk_score)
    finally:
        capture.release()
        pose_estimator.close()

    duration_seconds = frames_processed / fps
    calories = CalorieEstimator(exercise, bodyweight_kg).estimate(duration_seconds)

    observed_errors = [code for code in error_counts if code != "NO_PERSON_DETECTED"]
    feedback_summary = FeedbackGenerator().generate(observed_errors, max_messages=3)
    avg_risk = int(sum(risk_scores) / len(risk_scores)) if risk_scores else 0

    return VideoAnalysisResult(
        exercise=exercise,
        rep_count=analyzer.rep_count,
        duration_seconds=round(duration_seconds, 1),
        frames_processed=frames_processed,
        frames_with_person_detected=frames_with_person_detected,
        posture_error_counts=dict(error_counts),
        calories_estimate=calories,
        feedback_summary=feedback_summary,
        truncated=truncated,
        average_risk_score=avg_risk,
    )
