# 🎉 AI Gym Trainer Server is Running!

## Server Status: ✅ ONLINE

**Server URL**: `https://10.18.218.51:8000`

---

## How to Access

### On Your Phone (Same Wi-Fi Network)
1. Connect your phone to the **same Wi-Fi network** as this computer
2. Open your phone's browser (Chrome/Safari)
3. Navigate to: **`https://10.18.218.51:8000`**
4. Accept the SSL certificate warning (it's self-signed, safe to proceed)
5. Grant camera permissions when prompted

### On This Computer (for testing)
```bash
# Open in browser
firefox https://localhost:8000
# or
google-chrome https://localhost:8000
```

---

## Available Features

### 1. Main Workout Page (`/`)
- **Standard Mode**: Select exercise manually, enter user ID (optional)
- **Auto-Detect Mode**: Click "Auto-Detect Exercise" - system recognizes exercise automatically
- **Personalize Thresholds**: Click to calibrate personalized thresholds

**What you'll see:**
- Real-time skeleton overlay
- Rep count
- Calories burned
- Time elapsed
- **Risk Score** (0-100, color-coded: green/yellow/red)
- Live posture feedback

### 2. Calibration Page (`/static/calibrate.html`)
- Enter user ID and select exercise
- Perform 5 full-range reps
- System computes personalized thresholds
- Saved to your profile for future workouts

### 3. Health Check (`/health`)
- Simple endpoint to verify server is running
- Returns: `{"status": "healthy"}`

---

## Usage Examples

### Basic Workout (No Setup Required)
1. Open `https://10.18.218.51:8000`
2. Select exercise (e.g., "Squat")
3. Click "Start Workout"
4. Grant camera access
5. Position yourself so your whole body is visible
6. Start exercising!

### With Auto-Detection (If TensorFlow Installed)
1. Open `https://10.18.218.51:8000`
2. Click "Auto-Detect Exercise"
3. Grant camera access
4. Start doing any exercise
5. System will detect it automatically within 3-5 reps

### With Personalized Calibration
1. First time: Click "Personalize Thresholds"
2. Enter your user ID (e.g., "john_doe")
3. Select exercise
4. Perform 5 good reps at full range of motion
5. Return to main page
6. Enter same user ID
7. Start workout with personalized thresholds!

---

## Advanced Features in Action

### 🚨 Velocity-Based Risk Scoring
Watch the **Risk Score** in the HUD:
- **Green (0-30)**: Safe movement speed
- **Yellow (31-60)**: Moderate risk - slow down slightly
- **Red (61-100)**: High risk - dangerous movement patterns detected

**What it catches:**
- Rapid lateral knee movement (squats/lunges)
- Core collapse during push-ups
- Jerking movements in bicep curls

### 🎯 Personalized Calibration
Your calibrated thresholds adapt to YOUR flexibility:
- If you're very flexible: deeper squat thresholds
- If you're less flexible: adjusted to your safe range
- No more false "not deep enough" warnings!

### 🤖 Exercise Auto-Detection
No manual selection needed:
- Start moving
- LSTM model recognizes your exercise
- See "Detecting... Squat 85%" messages
- Seamless transition to workout mode

---

## Stopping the Server

To stop the server, in the terminal where it's running:
```bash
Press CTRL+C
```

Or find and kill the process:
```bash
pkill -f "uvicorn app.main:app"
```

---

## Troubleshooting

### "Can't connect from phone"
- ✅ Verify phone is on same Wi-Fi
- ✅ Check firewall isn't blocking port 8000
- ✅ Try accessing from computer first: `https://localhost:8000`

### "SSL Certificate Warning"
- This is normal for self-signed certificates
- Safe to click "Advanced" → "Proceed anyway"
- The connection is still encrypted

### "Camera not working"
- Grant camera permissions in browser
- HTTPS is required for camera access (we're using HTTPS ✅)
- Try flipping camera (⟳ button)

### "Auto-detect not working"
- Requires TensorFlow:
  ```bash
  pip install tensorflow>=2.13 scikit-learn>=1.3
  python scripts/train_exercise_classifier.py
  ```

### "Server crashed"
- Check terminal output for errors
- Restart with: `./run.sh`
- View logs: `cat /tmp/claude-1000/.../tasks/bh72eauj4.output`

---

## API Endpoints

For developers/testing:

### WebSocket Endpoints
- `/ws/session` - Standard workout with manual exercise selection
- `/ws/calibrate` - Calibration flow (5 reps)
- `/ws/auto-detect` - Auto-detection + workout

### HTTP Endpoints
- `GET /` - Main workout page
- `GET /static/calibrate.html` - Calibration page
- `GET /health` - Health check
- `POST /api/analyze-video` - Upload video for offline analysis

---

## Testing Without Phone

### Upload Video Test
1. Open `https://localhost:8000`
2. Scroll to "Test with a video upload"
3. Select a video file of someone exercising
4. Click "Analyze Video"
5. See results: reps, calories, posture errors

### Desktop Webcam Test
1. Open `https://localhost:8000`
2. Click "Start Workout"
3. Use your computer's webcam
4. Position yourself in frame

---

## Performance Notes

- **Frame Processing**: ~8 FPS (target)
- **MediaPipe Latency**: 50-150ms per frame
- **Risk Score Computation**: <1ms overhead
- **Auto-Detection Buffer**: 30 frames (~4 seconds at 8 FPS)

---

## Server Information

- **Host**: `0.0.0.0` (all network interfaces)
- **Port**: `8000`
- **Protocol**: HTTPS (self-signed certificate)
- **LAN IP**: `10.18.218.51`
- **Process ID**: Check with `ps aux | grep uvicorn`

---

## Next Steps

1. **Test on Phone**: Open `https://10.18.218.51:8000` on your phone
2. **Try Auto-Detection**: Click "Auto-Detect Exercise" and start moving
3. **Calibrate Your Profile**: Set up personalized thresholds
4. **Monitor Risk Scores**: Watch the color-coded risk indicator

---

**Need Help?**
- Check logs in terminal
- Read `README.md` for detailed documentation
- See `ADVANCED_FEATURES.md` for feature details

**Enjoy Your Workout! 💪**
