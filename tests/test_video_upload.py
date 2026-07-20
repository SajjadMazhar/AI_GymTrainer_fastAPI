import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _write_video(path, frame, num_frames=8, fps=10.0) -> None:
    h, w = frame.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for _ in range(num_frames):
        writer.write(frame)
    writer.release()


@pytest.fixture
def noise_video(tmp_path):
    path = tmp_path / "noise.avi"
    frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    _write_video(path, frame)
    return path


def test_analyze_video_rejects_unknown_exercise(noise_video):
    with open(noise_video, "rb") as f:
        response = client.post(
            "/api/analyze-video",
            files={"file": ("clip.avi", f, "video/x-msvideo")},
            data={"exercise": "not_a_real_exercise", "bodyweight_kg": "70"},
        )
    assert response.status_code == 400


def test_analyze_video_rejects_bad_bodyweight(noise_video):
    with open(noise_video, "rb") as f:
        response = client.post(
            "/api/analyze-video",
            files={"file": ("clip.avi", f, "video/x-msvideo")},
            data={"exercise": "squat", "bodyweight_kg": "-5"},
        )
    assert response.status_code == 400


def test_analyze_video_with_no_person_detected(noise_video):
    with open(noise_video, "rb") as f:
        response = client.post(
            "/api/analyze-video",
            files={"file": ("clip.avi", f, "video/x-msvideo")},
            data={"exercise": "squat", "bodyweight_kg": "70"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["exercise"] == "squat"
    assert body["rep_count"] == 0
    assert body["frames_processed"] == 8
    assert body["frames_with_person_detected"] == 0
    assert body["posture_error_counts"].get("NO_PERSON_DETECTED") == 8


def test_analyze_video_rejects_unopenable_file(tmp_path):
    bogus = tmp_path / "not_a_video.avi"
    bogus.write_bytes(b"this is not video data")
    with open(bogus, "rb") as f:
        response = client.post(
            "/api/analyze-video",
            files={"file": ("clip.avi", f, "video/x-msvideo")},
            data={"exercise": "squat", "bodyweight_kg": "70"},
        )
    assert response.status_code == 400
