from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ConfigMessage(BaseModel):
    type: Literal["config"] = "config"
    exercise: Literal["squat", "pushup", "bicep_curl", "lunge"]
    bodyweight_kg: float = Field(gt=0, le=400)
    target_fps: int = Field(default=8, ge=1, le=30)


class LandmarkOut(BaseModel):
    x: float
    y: float
    z: float
    visibility: float


class AnalysisMessage(BaseModel):
    type: Literal["analysis"] = "analysis"
    landmarks: list[LandmarkOut] | None
    rep_count: int
    phase: str
    posture_errors: list[str]
    feedback: list[str]
    calories_estimate: float
    elapsed_seconds: float
    processing_ms: float


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str
