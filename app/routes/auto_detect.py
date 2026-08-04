"""WebSocket endpoint with exercise auto-detection."""
from __future__ import annotations

import asyncio
import time

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.calories.estimator import CalorieEstimator
from app.config import settings
from app.exercises.registry import EXERCISES
from app.feedback.generator import FeedbackGenerator
from app.pose.factory import get_pose_estimator
from app.session.session import SessionState
from app.user.profile import ProfileStore

router = APIRouter()

# Lazy import ML classifier (only if TF is installed)
try:
    from app.ml.exercise_classifier import ExerciseClassifier

    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    ExerciseClassifier = None


class AutoDetectConfigMessage(BaseModel):
    """Config message for auto-detection mode."""

    type: str = "config"
    bodyweight_kg: float
    target_fps: int = 8
    user_id: str | None = None


@router.websocket("/ws/auto-detect")
async def auto_detect_endpoint(ws: WebSocket) -> None:
    """WebSocket endpoint with automatic exercise detection.

    Protocol:
    1. Client sends config WITHOUT exercise field
    2. Server auto-detects exercise from first 30 frames
    3. Once detected, switches to normal analysis mode
    """
    await ws.accept()

    if not CLASSIFIER_AVAILABLE:
        await ws.send_json(
            {
                "type": "error",
                "message": "Exercise auto-detection requires TensorFlow. Install with: pip install tensorflow scikit-learn",
            }
        )
        await ws.close()
        return

    try:
        # Receive config
        config_data = await ws.receive_json()
        config = AutoDetectConfigMessage(**config_data)

        # Initialize pose estimator and classifier
        pose_estimator = get_pose_estimator(settings.pose_backend, settings.model_complexity)
        classifier = ExerciseClassifier()
        loop = asyncio.get_event_loop()

        # Phase 1: Auto-detect exercise
        await ws.send_json({"type": "status", "message": "Detecting exercise... start moving!"})

        detected_exercise = None
        detection_confidence = 0.0

        while detected_exercise is None:
            frame_bytes = await ws.receive_bytes()
            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            pose_result = await loop.run_in_executor(None, pose_estimator.process, frame)

            if pose_result.landmarks is None:
                await ws.send_json({"type": "status", "message": "Step into frame to detect exercise"})
                continue

            # Feed landmarks to classifier
            classifier.add_frame(pose_result.landmarks)
            prediction = classifier.predict()

            if prediction:
                exercise_name, confidence = prediction
                # Require high confidence (>0.7) to lock in detection
                if confidence > 0.7:
                    detected_exercise = exercise_name
                    detection_confidence = confidence
                else:
                    await ws.send_json(
                        {
                            "type": "status",
                            "message": f"Detecting... ({exercise_name.replace('_', ' ').title()} {int(confidence*100)}%)",
                        }
                    )

        # Phase 2: Confirmed detection, switch to normal analysis
        await ws.send_json(
            {
                "type": "detected",
                "exercise": detected_exercise,
                "confidence": round(detection_confidence, 2),
                "message": f"Detected: {detected_exercise.replace('_', ' ').title()}",
            }
        )

        # Load user calibration if available
        calibration_data = None
        if config.user_id:
            profile_store = ProfileStore()
            profile = profile_store.load(config.user_id)
            if profile:
                cal = profile.get_calibration(detected_exercise)
                if cal:
                    calibration_data = {
                        "down_threshold": cal.down_threshold,
                        "up_threshold": cal.up_threshold,
                        "depth_cutoff": cal.depth_cutoff,
                    }

        # Initialize video recorder and session with detected exercise
        from app.recording.video_recorder import VideoRecorder

        video_recorder = VideoRecorder()

        session = SessionState(
            pose_estimator=pose_estimator,
            analyzer=EXERCISES[detected_exercise](calibration_data),
            calorie_estimator=CalorieEstimator(detected_exercise, config.bodyweight_kg),
            video_recorder=video_recorder,
        )

        recording_started_main = False

        # Phase 3: Normal workout analysis loop
        while True:
            frame_bytes = await ws.receive_bytes()
            start_time = time.perf_counter()

            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            # Start recording on first valid frame in main workout loop
            if not recording_started_main and frame is not None:
                height, width = frame.shape[:2]
                recording_path = video_recorder.start(
                    exercise=detected_exercise,
                    user_id=config.user_id,
                    width=width,
                    height=height,
                )
                recording_started_main = True
                print(f"Started recording: {recording_path}")

            # Write frame to video
            if video_recorder.is_recording():
                video_recorder.write_frame(frame)

            pose_result = await loop.run_in_executor(None, pose_estimator.process, frame)
            processing_ms = (time.perf_counter() - start_time) * 1000

            if pose_result.landmarks is None:
                landmarks_out = None
                result = session.analyzer.analyze([])  # dummy to maintain state
                errors = ["NO_PERSON_DETECTED"]
            else:
                landmarks_out = [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility} for lm in pose_result.landmarks]
                result = session.analyzer.analyze(pose_result.landmarks)
                errors = result.posture_errors

            elapsed = session.elapsed_seconds()
            calories = session.calorie_estimator.estimate(elapsed)
            feedback = FeedbackGenerator().generate(errors, max_messages=settings.max_feedback_messages)

            response = {
                "type": "analysis",
                "landmarks": landmarks_out,
                "rep_count": result.rep_count,
                "phase": result.phase,
                "posture_errors": errors,
                "feedback": feedback,
                "calories_estimate": calories,
                "elapsed_seconds": round(elapsed, 1),
                "processing_ms": round(processing_ms, 1),
                "risk_score": result.risk_score,
                "recording": video_recorder.is_recording(),
            }

            # Send recording notification on first frame
            if recording_started_main and video_recorder.get_current_path():
                response["recording_path"] = str(video_recorder.get_current_path().name)
                recording_started_main = False  # Only send once

            await ws.send_json(response)

    except WebSocketDisconnect:
        pass
    finally:
        if "session" in locals():
            session.close()
        elif "pose_estimator" in locals():
            pose_estimator.close()
