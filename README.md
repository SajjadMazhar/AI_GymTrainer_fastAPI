# AI Gym Trainer

A Python 3 backend that watches your exercise form through your phone's
camera and, in real time:

- **Counts reps** for squats, push-ups, bicep curls, and lunges
- **Detects incorrect posture** (e.g. knees caving in, hips sagging, leaning
  too far forward) and tells you what to fix
- **Estimates calories burned** during the session
- **Gives personalized feedback** as you train, prioritized by injury risk

Everything runs live in a browser tab on your phone — no app install. There's
no persistence: each session is live-only, and reps/history reset when you
refresh or reconnect.

There's also a **video upload option for testing**: upload a pre-recorded
clip instead of using a live camera, and the backend runs the same pipeline
over every frame and returns a rep count + posture summary. No phone or
WebSocket needed — useful for validating the pipeline without a live camera.

## Architecture

```
Phone browser (camera + <canvas> overlay)
   │  getUserMedia -> downscaled JPEG frames over WebSocket
   ▼
FastAPI backend (Python)
   │
   ├─ Pose estimation (MediaPipe Pose Landmarker, 33 body landmarks)
   ├─ Per-exercise analyzer (rep counting + posture rules from joint angles)
   ├─ Calorie estimator (MET formula: MET × bodyweight × elapsed time)
   └─ Feedback generator (posture errors -> prioritized tips)
   │
   ▼  JSON: landmarks, rep_count, posture_errors, feedback, calories
Phone browser draws the skeleton + HUD on <canvas>
```

The phone streams camera frames to the backend over a WebSocket; MediaPipe
Pose runs server-side in Python (the default backend). A pluggable
YOLOv11-pose backend (via `ultralytics`) is also available for experimentation
— see [Switching pose backends](#switching-pose-backends).

One `PoseEstimator` and one exercise `Analyzer` instance is created per phone
connection, so multiple people/phones can use the server at once without
interfering with each other. Nothing is persisted: closing or refreshing the
page resets the session to zero.

## Project Structure

```
app/
├── main.py                     FastAPI app factory, static mount, routes
├── config.py                   Settings (pose backend, thresholds, fps, ...)
├── routes/
│   ├── pages.py                GET / -> index.html, GET /health
│   ├── ws.py                   WebSocket endpoint /ws/session (live camera)
│   └── upload.py               POST /api/analyze-video (test-only video upload)
├── video_analysis.py            Offline per-frame analysis used by /api/analyze-video
├── session/session.py          Per-connection session state
├── pose/
│   ├── base.py                 PoseEstimator interface, Landmark/PoseResult
│   ├── mediapipe_backend.py    Default backend (MediaPipe Pose Landmarker)
│   ├── yolo_backend.py         Optional backend (YOLOv11-pose)
│   ├── factory.py              get_pose_estimator(name)
│   └── landmark_index.py       33-point BlazePose landmark index constants
├── exercises/
│   ├── base.py                 ExerciseAnalyzer base class, rep state machine
│   ├── angles.py                Joint-angle geometry helpers
│   ├── squat.py / pushup.py / bicep_curl.py / lunge.py
│   └── registry.py             EXERCISES: name -> analyzer class
├── calories/estimator.py        MET-based CalorieEstimator
├── feedback/generator.py        Posture-error -> feedback message mapping
├── protocol/schemas.py          WebSocket message schemas (pydantic)
└── static/                      index.html, style.css, app.js (frontend)
scripts/
├── gen_cert.sh                  Self-signed HTTPS cert generator
└── local_pipeline_test.py       Test the pipeline over webcam/video, no phone
tests/                            pytest unit tests
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The MediaPipe pose model (~6MB) is downloaded automatically on first use and
cached in `~/.cache/ai_gym_trainer/`.

## Running it (phone on the same Wi-Fi)

Phone browsers only allow camera access (`getUserMedia`) over a *secure*
context, and a LAN IP address doesn't count as one automatically — so the
server needs to run over HTTPS with a certificate the phone will accept.

```bash
./scripts/gen_cert.sh   # generates a self-signed cert for your LAN IP (run once)
./run.sh                # starts the server over HTTPS, prints the URL to open
```

`run.sh` also generates the cert automatically on first run if missing. On
your phone (connected to the **same Wi-Fi** as the machine running the
server), open the printed URL, e.g.:

```
https://192.168.1.23:8000
```

The browser will warn that the certificate isn't trusted (it's self-signed).
Tap **Advanced -> Proceed** (Chrome) or the equivalent on Safari — this is
expected and safe on your own LAN. If you'd rather avoid that warning
entirely, install [mkcert](https://github.com/FiloSottile/mkcert), run
`mkcert -install` once, then `mkcert <lan-ip> localhost 127.0.0.1` in
`certs/` (as `cert.pem`/`key.pem`) and also install mkcert's root CA on your
phone.

## Using it

1. Open the URL on your phone, grant camera access.
2. Pick an exercise and enter your bodyweight.
3. Prop the phone up so your whole body is visible, tap **Start Workout**.
4. Do reps — the rep counter, calorie estimate, and feedback update live.
   Tap the circular button on the video to switch between front/rear camera.
5. Tap **Stop** to end the session (nothing is saved).

## Testing with a video upload (no camera)

For quick testing without a live camera, expand **"Test with a video upload
(no camera)"** on the setup screen, pick a video file, and tap **Analyze
Video**. This uses the same exercise/bodyweight selection above it. The
backend processes every frame of the clip through the same pose + rep +
posture pipeline used for live sessions and returns a one-shot summary: total
reps, posture-error tallies, an estimated calorie burn, and a feedback
summary.

This is also available directly as an HTTP endpoint if you want to script it:

```bash
curl -k -X POST https://<lan-ip>:8000/api/analyze-video \
  -F "file=@clip.mp4" \
  -F "exercise=squat" \
  -F "bodyweight_kg=75"
```

Response:

```json
{
  "exercise": "squat",
  "rep_count": 12,
  "duration_seconds": 34.5,
  "frames_processed": 690,
  "frames_with_person_detected": 650,
  "posture_error_counts": {"KNEE_VALGUS": 15, "SQUAT_NOT_DEEP_ENOUGH": 3},
  "calories_estimate": 8.2,
  "feedback_summary": ["Push your knees outward, don't let them cave in."],
  "truncated": false
}
```

Uploads are capped at 200MB and processing stops after ~5 minutes of video
(`truncated: true` in the response) so one large upload can't block the
server indefinitely — this endpoint is meant for short test clips, not
production batch processing.

## Switching pose backends

MediaPipe is the default. To try the optional YOLOv11-pose backend instead:

```bash
pip install ultralytics   # not installed by default
POSE_BACKEND=yolo ./run.sh
```

YOLO weights (`yolo11n-pose.pt`) download automatically on first use via
`ultralytics`. Both backends are normalized to the same 33-point landmark
layout, so all exercise/posture logic works unchanged either way.

## Adding a new exercise

1. Create `app/exercises/<name>.py` with a class extending
   `ExerciseAnalyzer` (see `squat.py` for the simplest example): pick a
   primary joint angle, smooth it with `self._smooth()`, drive rep counting
   with `self._update_phase(angle, down_thresh, up_thresh)`, and add whatever
   posture checks make sense using the helpers in `app/exercises/angles.py`.
2. Register it in `app/exercises/registry.py`'s `EXERCISES` dict.
3. Add its posture-error codes and messages to
   `app/feedback/generator.py` (`FEEDBACK_MESSAGES`, `PRIORITY_ORDER`).
4. Add a MET value for it in `app/calories/estimator.py`'s `MET_VALUES`.
5. Add it to the `<select>` in `app/static/index.html`.
6. Write `tests/test_<name>.py` following the pattern in `tests/test_squat.py`
   (synthetic landmark frames built with `tests/helpers.py`).

## Testing

**Unit tests** (pure logic, no camera needed):

```bash
pytest
```

**Pipeline test** (real pose estimation over a webcam or video file, no
phone/WebSocket involved — the fastest way to tune angle thresholds):

```bash
python scripts/local_pipeline_test.py --exercise squat --source 0
python scripts/local_pipeline_test.py --exercise pushup --video clip.mp4
```

**Manual phone test checklist**:

1. `./scripts/gen_cert.sh && ./run.sh`
2. Confirm the phone and server machine are on the same Wi-Fi.
3. Open the HTTPS URL on the phone, accept the certificate warning.
4. Grant camera permission, pick an exercise, enter bodyweight, confirm the
   video preview and skeleton overlay appear and track movement smoothly.
5. Do 5 reps with good form — rep count should reach 5 and show "Nice form —
   keep it up!".
6. Do reps with deliberately bad form (e.g. shallow squat, knees caving in)
   and confirm the matching posture error/feedback appears.
7. Check the calorie estimate climbs plausibly over a longer session.
8. Refresh mid-session and confirm everything resets to zero (no
   persistence, by design).
9. On the setup screen, expand "Test with a video upload", pick a short clip,
   and tap Analyze Video — confirm a rep count and posture summary come back
   without ever touching the camera.
