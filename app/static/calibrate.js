// Calibration flow client

const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
];

const CAPTURE_WIDTH = 480;
const JPEG_QUALITY = 0.6;
const VISIBILITY_THRESHOLD = 0.4;

let ws = null;
let stream = null;
let calibrationActive = false;
let awaitingResponse = false;
let currentFacingMode = "user";
let latestLandmarks = null;

const setupScreen = document.getElementById("setup-screen");
const calibrationScreen = document.getElementById("calibration-screen");
const completeScreen = document.getElementById("complete-screen");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const flipCameraBtn = document.getElementById("flip-camera-btn");
const userIdInput = document.getElementById("user-id-input");
const exerciseSelect = document.getElementById("exercise-select");
const bodyweightInput = document.getElementById("bodyweight-input");
const errorBanner = document.getElementById("error-banner");

const video = document.getElementById("video");
const overlay = document.getElementById("overlay");
const overlayCtx = overlay.getContext("2d");
const captureCanvas = document.createElement("canvas");
const captureCtx = captureCanvas.getContext("2d");

const repCountEl = document.getElementById("rep-count");
const repTargetEl = document.getElementById("rep-target");
const statusMessageEl = document.getElementById("status-message");
const completeMessageEl = document.getElementById("complete-message");
const calibrationResultsEl = document.getElementById("calibration-results");

startBtn.addEventListener("click", startCalibration);
stopBtn.addEventListener("click", stopCalibration);
flipCameraBtn.addEventListener("click", flipCamera);

function showError(msg) {
  errorBanner.textContent = msg;
  errorBanner.hidden = false;
  setTimeout(() => (errorBanner.hidden = true), 5000);
}

async function startCalibration() {
  const userId = userIdInput.value.trim();
  if (!userId) {
    showError("Please enter a user ID");
    return;
  }

  try {
    await startCamera();
    connectWebSocket(userId);
    setupScreen.hidden = true;
    calibrationScreen.hidden = false;
    calibrationActive = true;
    renderLoop();
  } catch (err) {
    showError(`Camera error: ${err.message}`);
  }
}

function stopCalibration() {
  calibrationActive = false;
  if (ws) {
    ws.close();
    ws = null;
  }
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  calibrationScreen.hidden = true;
  setupScreen.hidden = false;
}

async function flipCamera() {
  currentFacingMode = currentFacingMode === "user" ? "environment" : "user";
  await startCamera();
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

function connectWebSocket(userId) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${protocol}://${window.location.host}/ws/calibrate`);

  ws.onopen = () => {
    ws.send(
      JSON.stringify({
        type: "config",
        user_id: userId,
        exercise: exerciseSelect.value,
        bodyweight_kg: parseFloat(bodyweightInput.value) || 70,
      })
    );
    awaitingResponse = false;
    requestNextFrame();
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "error") {
      showError(data.message);
      stopCalibration();
      return;
    }

    if (data.type === "instructions") {
      statusMessageEl.textContent = data.message;
      return;
    }

    if (data.type === "progress") {
      latestLandmarks = data.landmarks;
      repCountEl.textContent = data.rep_count;
      repTargetEl.textContent = data.target;
      statusMessageEl.textContent = data.message || `${data.rep_count} / ${data.target} reps`;
      awaitingResponse = false;
      if (calibrationActive) requestNextFrame();
      return;
    }

    if (data.type === "complete") {
      calibrationActive = false;
      calibrationScreen.hidden = true;
      completeScreen.hidden = false;
      completeMessageEl.textContent = data.message;

      const cal = data.calibration;
      calibrationResultsEl.innerHTML = `
        <table>
          <tr><th>Exercise</th><td>${cal.exercise}</td></tr>
          <tr><th>Range Observed</th><td>${cal.min_angle_observed}° - ${cal.max_angle_observed}°</td></tr>
          <tr><th>Down Threshold</th><td>${cal.down_threshold}°</td></tr>
          <tr><th>Up Threshold</th><td>${cal.up_threshold}°</td></tr>
          ${cal.depth_cutoff ? `<tr><th>Depth Cutoff</th><td>${cal.depth_cutoff}°</td></tr>` : ""}
        </table>
      `;

      if (ws) ws.close();
      if (stream) stream.getTracks().forEach((t) => t.stop());
      return;
    }
  };

  ws.onerror = () => showError("Connection error");
  ws.onclose = () => {
    calibrationActive = false;
  };
}

function requestNextFrame() {
  if (!calibrationActive || awaitingResponse) return;
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
    overlayCtx.translate(overlay.width, 0);
    overlayCtx.scale(-1, 1);
  }
  overlayCtx.drawImage(video, 0, 0, overlay.width, overlay.height);
  overlayCtx.restore();
}

function renderLoop() {
  if (!calibrationActive) return;
  if (video.videoWidth) {
    drawVideoFrame();
    if (latestLandmarks) {
      drawLandmarks(latestLandmarks);
    }
  }
  requestAnimationFrame(renderLoop);
}

function drawLandmarks(landmarks) {
  overlayCtx.save();
  if (currentFacingMode === "user") {
    overlayCtx.translate(overlay.width, 0);
    overlayCtx.scale(-1, 1);
  }

  overlayCtx.strokeStyle = "#3fb950";
  overlayCtx.lineWidth = 2;

  for (const [a, b] of POSE_CONNECTIONS) {
    const lmA = landmarks[a];
    const lmB = landmarks[b];
    if (
      lmA.visibility >= VISIBILITY_THRESHOLD &&
      lmB.visibility >= VISIBILITY_THRESHOLD
    ) {
      overlayCtx.beginPath();
      overlayCtx.moveTo(lmA.x * overlay.width, lmA.y * overlay.height);
      overlayCtx.lineTo(lmB.x * overlay.width, lmB.y * overlay.height);
      overlayCtx.stroke();
    }
  }

  overlayCtx.restore();
}
