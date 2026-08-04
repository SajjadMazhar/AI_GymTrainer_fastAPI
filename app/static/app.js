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

const GOOD_POSTURE_COLOR = "#3fb950"; // green: this part of the body looks correct
const BAD_POSTURE_COLOR = "#f85149"; // red: this part is implicated in a flagged posture error

// Connection groups reused across exercises' error-to-body-part mapping below.
const LEG_CONNECTIONS = [[23, 25], [25, 27], [24, 26], [26, 28]];
const ARM_CONNECTIONS = [[11, 13], [13, 15], [12, 14], [14, 16]];
const TORSO_CONNECTIONS = [[11, 12], [11, 23], [12, 24], [23, 24]];

// Maps each exercise's posture-error codes (see app/feedback/generator.py) to
// the skeleton connections that should be drawn red instead of green, so the
// overlay points at *where* the flagged issue is, not just that one exists.
const ERROR_HIGHLIGHT_CONNECTIONS = {
  squat: {
    KNEE_VALGUS: LEG_CONNECTIONS,
    DYNAMIC_KNEE_INSTABILITY: LEG_CONNECTIONS,
    SQUAT_NOT_DEEP_ENOUGH: LEG_CONNECTIONS,
    TORSO_LEANING_FORWARD: TORSO_CONNECTIONS,
  },
  pushup: {
    INSUFFICIENT_DEPTH: ARM_CONNECTIONS,
    HIP_SAG: TORSO_CONNECTIONS,
    HIP_PIKE: TORSO_CONNECTIONS,
    RAPID_CORE_INSTABILITY: TORSO_CONNECTIONS,
  },
  bicep_curl: {
    INCOMPLETE_EXTENSION: ARM_CONNECTIONS,
    TORSO_SWING: TORSO_CONNECTIONS,
    ELBOW_DRIFT: ARM_CONNECTIONS,
    JERKING_MOVEMENT: ARM_CONNECTIONS,
  },
  lunge: {
    INSUFFICIENT_DEPTH: LEG_CONNECTIONS,
    FRONT_KNEE_PAST_TOES: LEG_CONNECTIONS,
    BACK_KNEE_TOO_HIGH: LEG_CONNECTIONS,
    DYNAMIC_KNEE_INSTABILITY: LEG_CONNECTIONS,
    TORSO_LEANING: TORSO_CONNECTIONS,
  },
};

let ws = null;
let stream = null;
let sessionActive = false;
let awaitingResponse = false;
let currentFacingMode = "user";
let latestLandmarks = null;
let latestPostureErrors = [];

const setupScreen = document.getElementById("setup-screen");
const workoutScreen = document.getElementById("workout-screen");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const flipCameraBtn = document.getElementById("flip-camera-btn");
const exerciseSelect = document.getElementById("exercise-select");
const bodyweightInput = document.getElementById("bodyweight-input");
const userIdInput = document.getElementById("user-id-input");
const errorBanner = document.getElementById("error-banner");

const video = document.getElementById("video");
const overlay = document.getElementById("overlay");
const overlayCtx = overlay.getContext("2d");
const captureCanvas = document.createElement("canvas");
const captureCtx = captureCanvas.getContext("2d");

const repCountEl = document.getElementById("rep-count");
const caloriesEl = document.getElementById("calories");
const timerEl = document.getElementById("timer");
const riskScoreEl = document.getElementById("risk-score");
const feedbackEl = document.getElementById("feedback");

const videoFileInput = document.getElementById("video-file-input");
const analyzeVideoBtn = document.getElementById("analyze-video-btn");
const autoDetectBtn = document.getElementById("auto-detect-btn");
const videoResultEl = document.getElementById("video-result");

startBtn.addEventListener("click", startSession);
autoDetectBtn.addEventListener("click", startAutoDetectSession);
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
  latestLandmarks = null;
  latestPostureErrors = [];
  sessionActive = true;
  requestAnimationFrame(renderLoop);
  connectWebSocket();
}

async function startAutoDetectSession() {
  try {
    await startCamera();
  } catch (err) {
    showError("Camera access failed: " + err.message);
    return;
  }
  setupScreen.hidden = true;
  workoutScreen.hidden = false;
  latestLandmarks = null;
  latestPostureErrors = [];
  sessionActive = true;
  requestAnimationFrame(renderLoop);
  connectAutoDetectWebSocket();
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
    const userId = userIdInput.value.trim() || null;
    ws.send(
      JSON.stringify({
        type: "config",
        exercise: exerciseSelect.value,
        bodyweight_kg: parseFloat(bodyweightInput.value) || 70,
        target_fps: 8,
        user_id: userId,
      })
    );
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

function connectAutoDetectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${protocol}://${window.location.host}/ws/auto-detect`);

  ws.onopen = () => {
    const userId = userIdInput.value.trim() || null;
    ws.send(
      JSON.stringify({
        type: "config",
        bodyweight_kg: parseFloat(bodyweightInput.value) || 70,
        target_fps: 8,
        user_id: userId,
      })
    );
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

    if (data.type === "status") {
      // Detection phase - show status in feedback area
      feedbackEl.textContent = data.message;
      feedbackEl.classList.remove("warning");
      awaitingResponse = false;
      if (sessionActive) requestNextFrame();
      return;
    }

    if (data.type === "detected") {
      // Exercise detected - show confirmation
      feedbackEl.textContent = `✓ ${data.message} (${Math.round(data.confidence * 100)}% confident)`;
      feedbackEl.classList.remove("warning");
      awaitingResponse = false;
      if (sessionActive) requestNextFrame();
      return;
    }

    if (data.type === "analysis") {
      renderAnalysis(data);
      awaitingResponse = false;
      if (sessionActive) requestNextFrame();
      return;
    }
  };

  ws.onerror = () => showError("Connection error");
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

// Continuously repaints the video + latest skeleton overlay at display
// refresh rate, independent of how often analysis results arrive over the
// WebSocket (~8/s). Drawing the skeleton only inside the WebSocket message
// handler used to get wiped out immediately by the next captured video
// frame before the browser ever painted it -- this loop is the single place
// responsible for painting the canvas, so that can't happen anymore.
function renderLoop() {
  if (!sessionActive) return;
  if (video.videoWidth) {
    drawVideoFrame();
    if (latestLandmarks) {
      drawLandmarks(latestLandmarks, latestPostureErrors);
    }
  }
  requestAnimationFrame(renderLoop);
}

function renderAnalysis(data) {
  latestLandmarks = data.landmarks;
  latestPostureErrors = data.posture_errors || [];
  repCountEl.textContent = data.rep_count;
  caloriesEl.textContent = data.calories_estimate.toFixed(1);
  timerEl.textContent = formatTime(data.elapsed_seconds);
  riskScoreEl.textContent = data.risk_score || 0;

  // Color code risk score: green (0-30), yellow (31-60), red (61-100)
  const risk = data.risk_score || 0;
  riskScoreEl.style.color = risk <= 30 ? "#3fb950" : risk <= 60 ? "#e3b341" : "#f85149";

  feedbackEl.textContent = (data.feedback || []).join("  ");
  feedbackEl.classList.toggle("warning", (data.posture_errors || []).length > 0);
}

// Which skeleton connections (by "a-b" landmark-index key) should be drawn
// red for the currently selected exercise, given this frame's posture errors.
function getHighlightedConnectionKeys(postureErrors) {
  const errorMap = ERROR_HIGHLIGHT_CONNECTIONS[exerciseSelect.value] || {};
  const keys = new Set();
  for (const code of postureErrors || []) {
    for (const [a, b] of errorMap[code] || []) {
      keys.add(`${a}-${b}`);
    }
  }
  return keys;
}

function drawLandmarks(landmarks, postureErrors) {
  const badConnectionKeys = getHighlightedConnectionKeys(postureErrors);
  const badPointIndices = new Set();
  for (const key of badConnectionKeys) {
    const [a, b] = key.split("-").map(Number);
    badPointIndices.add(a);
    badPointIndices.add(b);
  }

  overlayCtx.save();
  if (currentFacingMode === "user") {
    overlayCtx.translate(overlay.width, 0);
    overlayCtx.scale(-1, 1);
  }

  for (const [a, b] of POSE_CONNECTIONS) {
    const p1 = landmarks[a];
    const p2 = landmarks[b];
    if (!p1 || !p2 || p1.visibility < VISIBILITY_THRESHOLD || p2.visibility < VISIBILITY_THRESHOLD) continue;
    const isBad = badConnectionKeys.has(`${a}-${b}`);
    overlayCtx.strokeStyle = isBad ? BAD_POSTURE_COLOR : GOOD_POSTURE_COLOR;
    overlayCtx.lineWidth = isBad ? 5 : 3;
    overlayCtx.beginPath();
    overlayCtx.moveTo(p1.x * overlay.width, p1.y * overlay.height);
    overlayCtx.lineTo(p2.x * overlay.width, p2.y * overlay.height);
    overlayCtx.stroke();
  }

  landmarks.forEach((lm, i) => {
    if (lm.visibility < VISIBILITY_THRESHOLD) return;
    overlayCtx.fillStyle = badPointIndices.has(i) ? BAD_POSTURE_COLOR : GOOD_POSTURE_COLOR;
    overlayCtx.beginPath();
    overlayCtx.arc(lm.x * overlay.width, lm.y * overlay.height, 4, 0, Math.PI * 2);
    overlayCtx.fill();
  });
  overlayCtx.restore();
}

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const s = Math.floor(totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function stopSession() {
  sessionActive = false;
  latestLandmarks = null;
  latestPostureErrors = [];
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
