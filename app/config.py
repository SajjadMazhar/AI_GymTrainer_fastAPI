from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    pose_backend: str = "mediapipe"
    model_complexity: int = 1
    default_target_fps: int = 8
    max_feedback_messages: int = 2


settings = Settings()
