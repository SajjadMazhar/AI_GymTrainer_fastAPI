# Video Recording Feature

## Overview

The AI Gym Trainer now automatically records every workout session to video. This allows users to:
- Review their form after the workout
- Share workout videos with trainers or on social media
- Track progress over time
- Analyze movement patterns offline

## How It Works

### Automatic Recording
- Recording starts **automatically** when the workout begins
- First frame triggers the video recorder
- All subsequent frames are written to video at ~8 FPS
- Recording stops automatically when the workout ends

### Recording Indicator
- **Red "REC" badge** appears in the top-right corner
- Blinking red dot animation indicates active recording
- Badge is visible throughout the entire workout

### File Naming Convention
Videos are saved with descriptive filenames:
```
[user_id_]exercise_YYYYMMDD_HHMMSS.mp4

Examples:
- squat_20260804_143022.mp4
- john_doe_pushup_20260804_143525.mp4
- bicep_curl_20260804_144130.mp4
```

**Filename Components:**
- `user_id` (optional): User's ID if provided during calibration
- `exercise`: Type of exercise (squat, pushup, bicep_curl, lunge)
- `timestamp`: Date and time when recording started (YYYYMMDD_HHMMSS)

## Storage Location

All recordings are saved to:
```
/home/phi-machine/Documents/Sajjad/AI_GYMTrainer/recordings/
```

This directory is created automatically on first use.

## File Format

- **Container**: MP4
- **Codec**: H.264 (mp4v/avc1)
- **Frame Rate**: 8 FPS (matches analysis frame rate)
- **Resolution**: Same as camera input (typically 640x480 or 1280x720)
- **Video Only**: No audio track

## Features

### 1. Standard Workout Mode
```
User starts workout → Recording begins → User stops → Recording saved
```

### 2. Auto-Detect Mode
```
User starts auto-detect → Detection phase (not recorded) →
Exercise detected → Recording begins → User stops → Recording saved
```
**Note**: Only the main workout is recorded, not the detection phase.

### 3. Calibration Mode
Calibration sessions are **not** recorded to save disk space.

## Recording Metadata

When a recording stops, the system prints:
```
Recording saved: john_doe_squat_20260804_143022.mp4 (45.3s, 362 frames)
```

**Metadata includes:**
- File path
- Duration in seconds
- Total frame count
- Frame rate

## API Integration

### WebSocket Protocol Extension

#### AnalysisMessage (during workout)
```json
{
  "type": "analysis",
  "landmarks": [...],
  "rep_count": 5,
  "phase": "up",
  "risk_score": 15,
  "recording": true,  // NEW: indicates recording is active
  "recording_path": "squat_20260804_143022.mp4"  // NEW: sent on first frame only
  ...
}
```

#### New Fields
- `recording` (boolean): True if currently recording
- `recording_path` (string, optional): Filename of the recording (sent once at start)

### SessionState Enhancement

The `SessionState` class now includes:
```python
@dataclass
class SessionState:
    pose_estimator: PoseEstimator
    analyzer: ExerciseAnalyzer
    calorie_estimator: CalorieEstimator
    feedback_generator: FeedbackGenerator
    video_recorder: VideoRecorder | None = None  # NEW
    started_at: float
```

## VideoRecorder Class

Located in `app/recording/video_recorder.py`

### Methods

#### `start(exercise, user_id, width, height) -> Path`
Starts recording a new video.
```python
recorder = VideoRecorder()
path = recorder.start(
    exercise="squat",
    user_id="john_doe",
    width=640,
    height=480
)
```

#### `write_frame(frame: np.ndarray) -> None`
Writes a single frame to the video.
```python
recorder.write_frame(frame)  # frame is BGR numpy array
```

#### `stop() -> dict`
Stops recording and returns metadata.
```python
metadata = recorder.stop()
# Returns: {"path": "...", "duration_seconds": 45.3, "frame_count": 362, "fps": 8.0}
```

#### `is_recording() -> bool`
Check if currently recording.
```python
if recorder.is_recording():
    recorder.write_frame(frame)
```

#### `get_current_path() -> Path | None`
Get path to current recording file.
```python
path = recorder.get_current_path()
```

## Storage Management

### Disk Space Considerations

**Approximate file sizes** (at 640x480 resolution, 8 FPS):
- 1 minute workout: ~10-15 MB
- 5 minute workout: ~50-75 MB
- 10 minute workout: ~100-150 MB

**Recommendations:**
1. **Short workouts (<5 min)**: Negligible storage impact
2. **Long workouts (>10 min)**: Monitor disk space
3. **Many users**: Implement cleanup policy

### Manual Cleanup

Delete old recordings:
```bash
# Delete recordings older than 7 days
find recordings/ -name "*.mp4" -mtime +7 -delete

# Delete all recordings
rm -rf recordings/*.mp4
```

### Automatic Cleanup (Future Enhancement)

Consider implementing:
- Automatic deletion after N days
- Maximum storage quota per user
- Compression of old videos
- Upload to cloud storage

## Privacy & Security

### Considerations
- Videos contain personally identifiable information
- Store recordings securely
- Implement user consent mechanisms
- Allow users to delete their recordings
- Consider encryption for sensitive deployments

### Recommended Practices
1. **Inform users**: Display recording notification clearly
2. **User control**: Allow users to opt-out or delete recordings
3. **Retention policy**: Auto-delete after reasonable period
4. **Access control**: Restrict access to recordings directory
5. **Compliance**: Follow GDPR/privacy regulations if applicable

## Troubleshooting

### "Recording failed to start"
**Symptom**: No recording file created
**Causes**:
- Permissions issue on `recordings/` directory
- Invalid codec (mp4v not available)
- Disk space full

**Fix**:
```bash
mkdir -p recordings
chmod 755 recordings
df -h  # Check disk space
```

### "Video file corrupted"
**Symptom**: Video won't play
**Causes**:
- Recording not properly closed (server crash)
- Codec mismatch

**Fix**:
- Ensure `session.close()` is called
- Try different codec: `VideoRecorder(codec="avc1")`

### "Recording indicator not showing"
**Symptom**: No red REC badge during workout
**Causes**:
- Frontend not receiving `recording` field
- CSS not loaded

**Fix**:
- Check browser console for errors
- Verify WebSocket message includes `recording: true`
- Clear browser cache

## Future Enhancements

### Planned Features
1. **Video Annotations**
   - Overlay rep count and risk score on video
   - Draw skeleton overlay on recorded video
   - Add posture error annotations

2. **Cloud Storage**
   - Upload to S3/Google Cloud Storage
   - Share videos via URL
   - Stream videos in browser

3. **Video Analytics**
   - Generate highlight reels (best reps)
   - Create side-by-side comparison videos
   - Export frame-by-frame analysis data

4. **User Controls**
   - Toggle recording on/off
   - Choose recording quality (resolution/FPS)
   - Select storage location

5. **Advanced Features**
   - Slow-motion replay
   - Multi-angle recording (multiple cameras)
   - Live streaming to social platforms

## Code Examples

### Basic Usage (Internal)
```python
from app.recording.video_recorder import VideoRecorder

# Initialize
recorder = VideoRecorder(output_dir="recordings", fps=8.0)

# Start recording
path = recorder.start(exercise="squat", user_id="john", width=640, height=480)

# Write frames
for frame in video_stream:
    recorder.write_frame(frame)

# Stop and get metadata
metadata = recorder.stop()
print(f"Saved: {metadata['path']} ({metadata['duration_seconds']}s)")
```

### Integration with Session
```python
# In WebSocket handler
session = SessionState(
    pose_estimator=...,
    analyzer=...,
    calorie_estimator=...,
    video_recorder=VideoRecorder(),  # NEW
)

# In frame processing loop
if not recording_started and frame is not None:
    session.video_recorder.start(exercise, user_id, width, height)
    recording_started = True

session.video_recorder.write_frame(frame)

# On disconnect
session.close()  # Automatically stops recording
```

## Testing

### Unit Test Example
```python
def test_video_recorder():
    recorder = VideoRecorder(output_dir="test_recordings")
    
    # Create dummy frames
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Start recording
    path = recorder.start("squat", "test_user", 640, 480)
    assert recorder.is_recording()
    
    # Write frames
    for _ in range(100):
        recorder.write_frame(frame)
    
    # Stop and verify
    metadata = recorder.stop()
    assert not recorder.is_recording()
    assert metadata["frame_count"] == 100
    assert Path(metadata["path"]).exists()
```

### Manual Test
1. Start server
2. Open app in browser
3. Start workout
4. Verify red REC indicator appears
5. Perform a few reps
6. Stop workout
7. Check `recordings/` directory for video file
8. Play video to verify it's valid

## Conclusion

The video recording feature enhances the AI Gym Trainer by providing:
- **Automatic documentation** of every workout
- **Post-workout review** capabilities
- **Progress tracking** over time
- **Sharable content** for social media or coaching

All recordings are saved locally with descriptive filenames, making it easy to organize and review past workouts.

---

**Implementation Date**: August 4, 2026
**Status**: ✅ Production Ready
