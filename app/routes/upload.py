"""Test-only endpoint: upload a pre-recorded video and get back rep counts
and posture-error tallies for the whole clip, without needing a phone.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.exercises.registry import EXERCISES
from app.video_analysis import VideoAnalysisResult, analyze_video_file

router = APIRouter()

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200MB safety cap
CHUNK_SIZE = 1024 * 1024


@router.post("/api/analyze-video")
async def analyze_video(
    file: UploadFile = File(...),
    exercise: str = Form(...),
    bodyweight_kg: float = Form(...),
) -> dict:
    if exercise not in EXERCISES:
        raise HTTPException(status_code=400, detail=f"Unknown exercise: {exercise!r}")
    if not (0 < bodyweight_kg <= 400):
        raise HTTPException(status_code=400, detail="bodyweight_kg must be between 0 and 400")

    suffix = Path(file.filename or "").suffix or ".mp4"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            total = 0
            while chunk := await file.read(CHUNK_SIZE):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Video file too large (max 200MB)")
                tmp.write(chunk)

        result: VideoAnalysisResult = await run_in_threadpool(
            analyze_video_file, str(tmp_path), exercise, bodyweight_kg
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    return {
        "exercise": result.exercise,
        "rep_count": result.rep_count,
        "duration_seconds": result.duration_seconds,
        "frames_processed": result.frames_processed,
        "frames_with_person_detected": result.frames_with_person_detected,
        "posture_error_counts": result.posture_error_counts,
        "calories_estimate": result.calories_estimate,
        "feedback_summary": result.feedback_summary,
        "truncated": result.truncated,
    }
