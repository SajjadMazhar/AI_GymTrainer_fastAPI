from __future__ import annotations

import asyncio
import time
from dataclasses import asdict

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.calories.estimator import CalorieEstimator
from app.config import settings
from app.exercises.base import AnalysisResult
from app.exercises.registry import EXERCISES
from app.pose.base import PoseResult
from app.pose.factory import get_pose_estimator
from app.protocol.schemas import ConfigMessage
from app.session.session import SessionState

router = APIRouter()

NO_PERSON_RESULT_TEMPLATE = ["NO_PERSON_DETECTED"]


async def _receive_config(ws: WebSocket) -> ConfigMessage | None:
    raw = await ws.receive_json()
    try:
        return ConfigMessage(**raw)
    except ValidationError as exc:
        await ws.send_json({"type": "error", "message": str(exc)})
        return None


def _decode_frame(frame_bytes: bytes) -> np.ndarray | None:
    array = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    return frame


@router.websocket("/ws/session")
async def session_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    config = await _receive_config(ws)
    if config is None:
        await ws.close()
        return

    session = SessionState(
        pose_estimator=get_pose_estimator(settings.pose_backend, settings.model_complexity),
        analyzer=EXERCISES[config.exercise](),
        calorie_estimator=CalorieEstimator(config.exercise, config.bodyweight_kg),
    )
    loop = asyncio.get_running_loop()

    try:
        while True:
            frame_bytes = await ws.receive_bytes()
            frame = _decode_frame(frame_bytes)
            if frame is None:
                continue

            t0 = time.monotonic()
            pose_result: PoseResult = await loop.run_in_executor(None, session.pose_estimator.process, frame)
            processing_ms = (time.monotonic() - t0) * 1000

            if pose_result.landmarks is None:
                result = AnalysisResult(
                    rep_count=session.analyzer.rep_count,
                    phase=session.analyzer.phase.value,
                    posture_errors=NO_PERSON_RESULT_TEMPLATE,
                    primary_angle=None,
                    confidence=0.0,
                )
                landmarks_out = None
            else:
                result = session.analyzer.analyze(pose_result.landmarks)
                landmarks_out = [asdict(lm) for lm in pose_result.landmarks]

            elapsed = session.elapsed_seconds()
            calories = session.calorie_estimator.estimate(elapsed)
            feedback = session.feedback_generator.generate(
                result.posture_errors, max_messages=settings.max_feedback_messages
            )

            await ws.send_json(
                {
                    "type": "analysis",
                    "landmarks": landmarks_out,
                    "rep_count": result.rep_count,
                    "phase": result.phase,
                    "posture_errors": result.posture_errors,
                    "feedback": feedback,
                    "calories_estimate": calories,
                    "elapsed_seconds": round(elapsed, 1),
                    "processing_ms": round(processing_ms, 1),
                }
            )
    except WebSocketDisconnect:
        pass
    finally:
        session.close()
