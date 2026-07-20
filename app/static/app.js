// Skeleton connections as pairs of BlazePose landmark indices (subset covering
// shoulders, arms, torso, and legs -- enough for a readable overlay).
const POSE_CONNECTIONS = [
  [11, 12], // shoulders
  [11, 13], [13, 15], // left arm
  [12, 14], [14, 16], // right arm
  [11, 23], [12, 24], // shoulder -> hip
  [23, 24], // hips
  [23, 25], [25, 27], // left leg
  [24, 26], [26, 28], // right leg
];

const CAPTURE_WIDTH = 480;
const JPEG_QUALITY = 0.6;
const VISIBILITY_THRESHOLD = 0.4;

let ws = null;
let stream = null;
let sessionActive = false;
let awaitingResponse = false;
let currentFacingMode = "user";

const setupScreen = document.getElementById("setup-screen");
const workoutScreen = document.getElementById("workout-screen");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const flipCameraBtn = document.getElementById("flip-camera-btn");
const exerciseSelect = document.getElementById("exercise-select");
const bodyweightInput = document.getElementById("bodyweight-input");
const errorBanner = document.getElementById("error-banner");

const video = document.getElementById("video");
const overlay = document.getElementById("overlay");
const overlayCtx = overlay.getContext("2d");
const captureCanvas = document.createElement("canvas");
const captureCtx = captureCanvas.getContext("2d");

const repCountEl = document.getElementById("rep-count");
const caloriesEl = document.getElementById("calories");
const timerEl = document.getElementById("timer");
const feedbackEl = document.getElementById("feedback");

const videoFileInput = document.getElementById("video-file-input");
const analyzeVideoBtn = document.getElementById("analyze-video-btn");
const videoResultEl = document.getElementById("video-result");

startBtn.addEventListener("click", startSession);
stopBtn.addEventListener("click", stopSession);
flipCameraBtn.addEventListener("click", flipCamera);
analyzeVideoBtn.addEventListener("click", analyzeVideoUpload);

// Test-only path: upload a pre-recorded video and get back rep counts and
// posture-error tallies for the whole clip, computed server-side with no
// camera/WebSocket involved. Useful for validating the pipeline offline.
async function analyzeVideoUpload() {
  const file = videoFileInput.files[0];
  if (!file) {
    showError("Choose a video file first.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("exercise", exerciseSelect.value);
  formData.append("bodyweight_kg", parseFloat(bodyweightInput.value) || 70);

  analyzeVideoBtn.disabled = true;
  analyzeVideoBtn.textContent = "Analyzing…";
  videoResultEl.hidden = true;

  try {
    const response = await fetch("/api/analyze-video", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) {
      showError(data.detail || "Video analysis failed.");
      return;
    }
    renderVideoResult(data);
  } catch (err) {
    showError("Video analysis failed: " + err.message);
  } finally {
    analyzeVideoBtn.disabled = false;
    analyzeVideoBtn.textContent = "Analyze Video";
  }
}

function renderVideoResult(data) {
  const errorEntries = Object.entries(data.posture_error_counts || {}).filter(
    ([code]) => code !== "NO_PERSON_DETECTED"
  );
  const errorLines = errorEntries.length
    ? errorEntries.map(([code, count]) => `${code}: ${count}`).join(", ")
    : "none";

  videoResultEl.innerHTML = `
    <p><strong>${data.rep_count}</strong> reps counted over ${data.duration_seconds}s
      (${data.frames_with_person_detected}/${data.frames_processed} frames had a person detected)</p>
    <p>Estimated calories: ${data.calories_estimate.toFixed(1)}</p>
    <p>Posture issues: ${errorLines}</p>
    <p>${(data.feedback_summary || []).join(" ")}</p>
    ${data.truncated ? "<p><em>Note: video was truncated to the first ~5 minutes.</em></p>" : ""}
  `;
  videoResultEl.hidden = false;
}

async function startSession() {
  try {
    await startCamera();
  } catch (err) {
    showError("Camera access failed: " + err.message);
    return;
  }
  setupScreen.hidden = true;
  workoutScreen.hidden = false;
  connectWebSocket();
}

async function startCamera() {
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
  }
  stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: currentFacingMode,
      width: { ideal: 1280 },
      height: { ideal: 720 },
    },
    audio: false,
  });
  video.srcObject = stream;
  await video.play();
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${protocol}://${window.location.host}/ws/session`);

  ws.onopen = () => {
    ws.send(
      JSON.stringify({
        type: "config",
        exercise: exerciseSelect.value,
        bodyweight_kg: parseFloat(bodyweightInput.value) || 70,
        target_fps: 8,
      })
    );
    sessionActive = true;
    awaitingResponse = false;
    requestNextFrame();
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "error") {
      showError(data.message);
      awaitingResponse = false;
      return;
    }
    renderAnalysis(data);
    awaitingResponse = false;
    if (sessionActive) requestNextFrame();
  };

  ws.onerror = () => showError("Connection error — check you're on the same Wi-Fi as the server.");
  ws.onclose = () => {
    sessionActive = false;
  };
}

function requestNextFrame() {
  if (!sessionActive || awaitingResponse) return;
  captureAndSendFrame();
}

function captureAndSendFrame() {
  if (!video.videoWidth) {
    requestAnimationFrame(requestNextFrame);
    return;
  }

  drawVideoFrame();

  const scale = CAPTURE_WIDTH / video.videoWidth;
  captureCanvas.width = CAPTURE_WIDTH;
  captureCanvas.height = Math.round(video.videoHeight * scale);
  captureCtx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);

  captureCanvas.toBlob(
    (blob) => {
      if (!blob || !ws || ws.readyState !== WebSocket.OPEN) return;
      awaitingResponse = true;
      blob.arrayBuffer().then((buf) => ws.send(buf));
    },
    "image/jpeg",
    JPEG_QUALITY
  );
}

function drawVideoFrame() {
  overlay.width = video.videoWidth;
  overlay.height = video.videoHeight;
  overlayCtx.save();
  if (currentFacingMode === "user") {
    // Mirror the preview for a natural selfie-style view.
    overlayCtx.translate(overlay.width, 0);
    overlayCtx.scale(-1, 1);
  }
  overlayCtx.drawImage(video, 0, 0, overlay.width, overlay.height);
  overlayCtx.restore();
}

function renderAnalysis(data) {
  if (data.landmarks) {
    drawLandmarks(data.landmarks);
  }
  repCountEl.textContent = data.rep_count;
  caloriesEl.textContent = data.calories_estimate.toFixed(1);
  timerEl.textContent = formatTime(data.elapsed_seconds);
  feedbackEl.textContent = (data.feedback || []).join("  ");
  feedbackEl.classList.toggle("warning", (data.posture_errors || []).length > 0);
}

function drawLandmarks(landmarks) {
  overlayCtx.save();
  if (currentFacingMode === "user") {
    overlayCtx.translate(overlay.width, 0);
    overlayCtx.scale(-1, 1);
  }
  overlayCtx.strokeStyle = "#00e5ff";
  overlayCtx.fillStyle = "#00e5ff";
  overlayCtx.lineWidth = 3;

  for (const [a, b] of POSE_CONNECTIONS) {
    const p1 = landmarks[a];
    const p2 = landmarks[b];
    if (!p1 || !p2 || p1.visibility < VISIBILITY_THRESHOLD || p2.visibility < VISIBILITY_THRESHOLD) continue;
    overlayCtx.beginPath();
    overlayCtx.moveTo(p1.x * overlay.width, p1.y * overlay.height);
    overlayCtx.lineTo(p2.x * overlay.width, p2.y * overlay.height);
    overlayCtx.stroke();
  }

  for (const lm of landmarks) {
    if (lm.visibility < VISIBILITY_THRESHOLD) continue;
    overlayCtx.beginPath();
    overlayCtx.arc(lm.x * overlay.width, lm.y * overlay.height, 4, 0, Math.PI * 2);
    overlayCtx.fill();
  }
  overlayCtx.restore();
}

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const s = Math.floor(totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function stopSession() {
  sessionActive = false;
  if (ws) ws.close();
  if (stream) stream.getTracks().forEach((t) => t.stop());
  workoutScreen.hidden = true;
  setupScreen.hidden = false;
  repCountEl.textContent = "0";
  caloriesEl.textContent = "0.0";
  timerEl.textContent = "00:00";
  feedbackEl.textContent = "";
}

async function flipCamera() {
  currentFacingMode = currentFacingMode === "user" ? "environment" : "user";
  try {
    await startCamera();
  } catch (err) {
    showError("Camera switch failed: " + err.message);
  }
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.hidden = false;
  setTimeout(() => {
    errorBanner.hidden = true;
  }, 4000);
}
