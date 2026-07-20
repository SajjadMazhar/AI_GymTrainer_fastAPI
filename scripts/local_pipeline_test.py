#!/usr/bin/env python3
"""Run the full pose -> analyzer -> calories -> feedback pipeline over a
webcam or a local video file, with no WebSocket and no phone involved.

This exercises the exact same modules the WebSocket handler uses
(app.pose, app.exercises, app.calories, app.feedback), so it's the fastest
way to tune angle thresholds or debug an exercise's rules.

Usage:
  python scripts/local_pipeline_test.py --exercise squat --source 0
  python scripts/local_pipeline_test.py --exercise pushup --video path/to/clip.mp4
  python scripts/local_pipeline_test.py --exercise squat --source 0 --no-preview
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.calories.estimator import CalorieEstimator
from app.exercises.registry import EXERCISES
from app.feedback.generator import FeedbackGenerator
from app.pose.factory import get_pose_estimator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exercise", required=True, choices=sorted(EXERCISES))
    parser.add_argument("--source", type=int, default=None, help="Webcam device index (e.g. 0)")
    parser.add_argument("--video", type=str, default=None, help="Path to a local video file instead of a webcam")
    parser.add_argument("--backend", default="mediapipe", choices=["mediapipe", "yolo"])
    parser.add_argument("--bodyweight", type=float, default=70.0)
    parser.add_argument("--no-preview", action="store_true", help="Don't open a cv2.imshow preview window")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.video is None and args.source is None:
        args.source = 0

    capture = cv2.VideoCapture(args.video if args.video else args.source)
    if not capture.isOpened():
        print(f"Could not open video source: {args.video or args.source}", file=sys.stderr)
        sys.exit(1)

    pose_estimator = get_pose_estimator(args.backend)
    analyzer = EXERCISES[args.exercise]()
    calorie_estimator = CalorieEstimator(args.exercise, args.bodyweight)
    feedback_generator = FeedbackGenerator()
    session_start = time.monotonic()

    show_preview = not args.no_preview
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            pose_result = pose_estimator.process(frame)
            if pose_result.landmarks is None:
                posture_errors = ["NO_PERSON_DETECTED"]
                rep_count, phase = analyzer.rep_count, analyzer.phase.value
            else:
                result = analyzer.analyze(pose_result.landmarks)
                posture_errors = result.posture_errors
                rep_count, phase = result.rep_count, result.phase

            elapsed = time.monotonic() - session_start
            calories = calorie_estimator.estimate(elapsed)
            feedback = feedback_generator.generate(posture_errors)

            print(
                f"\rreps={rep_count:<3} phase={phase:<5} "
                f"errors={','.join(posture_errors) or '-':<30} "
                f"calories={calories:<6.1f} feedback={feedback[0]:<45}",
                end="",
                flush=True,
            )

            if show_preview:
                if pose_result.landmarks is not None:
                    h, w = frame.shape[:2]
                    for lm in pose_result.landmarks:
                        if lm.visibility < 0.4:
                            continue
                        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 4, (0, 229, 255), -1)
                cv2.putText(frame, f"reps: {rep_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("local_pipeline_test", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        print()
        capture.release()
        pose_estimator.close()
        if show_preview:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
