"""WebSocket endpoint for user calibration flow."""
from __future__ import annotations

import asyncio
import time

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.exercises.registry import EXERCISES
from app.pose.factory import get_pose_estimator
from app.user.calibration import calibrate_from_reps
from app.user.profile import ProfileStore, UserProfile

router = APIRouter()

CALIBRATION_REP_TARGET = 5  # number of reps needed for calibration


@router.websocket("/ws/calibrate")
async def calibrate_endpoint(ws: WebSocket) -> None:
    """Calibration WebSocket: guides user through 5 reps to compute personalized thresholds.

    Protocol:
    1. Client sends config: {"type": "config", "user_id": "...", "exercise": "...", "bodyweight_kg": 70}
    2. Server responds with instructions
    3. Client sends JPEG frames
    4. Server responds with {"type": "progress", "rep_count": N, "target": 5, "landmarks": [...]}
    5. After 5 reps, server computes calibration and responds with:
       {"type": "complete", "calibration": {...}}
    """
    await ws.accept()

    try:
        # Step 1: Receive config
        config_data = await ws.receive_json()
        user_id = config_data["user_id"]
        exercise = config_data["exercise"]
        bodyweight_kg = config_data["bodyweight_kg"]
        pose_backend = config_data.get("pose_backend", "mediapipe")

        if exercise not in EXERCISES:
            await ws.send_json({"type": "error", "message": f"Unknown exercise: {exercise}"})
            await ws.close()
            return

        # Initialize pose estimator and analyzer
        pose_estimator = get_pose_estimator(pose_backend)
        analyzer = EXERCISES[exercise]()  # fresh analyzer, no calibration yet
        loop = asyncio.get_event_loop()

        angle_observations: list[float] = []  # collect angles across all reps

        await ws.send_json(
            {
                "type": "instructions",
                "message": f"Perform {CALIBRATION_REP_TARGET} full-range {exercise} reps at your natural pace.",
            }
        )

        # Step 2: Process frames until we have enough reps
        while analyzer.rep_count < CALIBRATION_REP_TARGET:
            frame_bytes = await ws.receive_bytes()
            start_time = time.perf_counter()

            # Decode JPEG
            frame_np = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            # Run pose estimation
            pose_result = await loop.run_in_executor(None, pose_estimator.process, frame)

            if pose_result.landmarks is None:
                await ws.send_json(
                    {
                        "type": "progress",
                        "rep_count": analyzer.rep_count,
                        "target": CALIBRATION_REP_TARGET,
                        "landmarks": None,
                        "message": "Step into frame",
                    }
                )
                continue

            # Analyze
            result = analyzer.analyze(pose_result.landmarks)

            # Collect angle observations (all frames, not just rep completions)
            if result.primary_angle is not None:
                angle_observations.append(result.primary_angle)

            processing_ms = (time.perf_counter() - start_time) * 1000

            await ws.send_json(
                {
                    "type": "progress",
                    "rep_count": result.rep_count,
                    "target": CALIBRATION_REP_TARGET,
                    "landmarks": [
                        {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                        for lm in pose_result.landmarks
                    ],
                    "primary_angle": result.primary_angle,
                    "processing_ms": round(processing_ms, 1),
                }
            )

        # Step 3: Compute calibration
        calibration = calibrate_from_reps(exercise, angle_observations)

        # Step 4: Save to profile
        profile_store = ProfileStore()
        profile = profile_store.load(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id, bodyweight_kg=bodyweight_kg, calibrations={})
        profile.set_calibration(calibration)
        profile_store.save(profile)

        await ws.send_json(
            {
                "type": "complete",
                "message": f"Calibration complete! Personalized thresholds saved for {exercise}.",
                "calibration": {
                    "exercise": calibration.exercise,
                    "min_angle_observed": round(calibration.min_angle_observed, 1),
                    "max_angle_observed": round(calibration.max_angle_observed, 1),
                    "down_threshold": round(calibration.down_threshold, 1),
                    "up_threshold": round(calibration.up_threshold, 1),
                    "depth_cutoff": round(calibration.depth_cutoff, 1) if calibration.depth_cutoff else None,
                },
            }
        )

    except WebSocketDisconnect:
        pass
    finally:
        if "pose_estimator" in locals():
            pose_estimator.close()
