"""Generate synthetic pose sequences for each exercise to train the LSTM classifier."""
from __future__ import annotations

import numpy as np

# MediaPipe pose landmark indices for key joints
KEY_LANDMARKS = [
    11,
    12,  # shoulders
    13,
    14,  # elbows
    15,
    16,  # wrists
    23,
    24,  # hips
    25,
    26,  # knees
    27,
    28,  # ankles
]

SEQUENCE_LENGTH = 30  # number of frames in each training sequence
NUM_SAMPLES_PER_EXERCISE = 200  # synthetic samples per exercise


def generate_squat_sequence(rng: np.random.Generator) -> np.ndarray:
    """Generate a synthetic squat motion sequence.

    Squat: knees/hips flex and extend vertically, torso stays relatively upright.
    """
    sequence = []
    for frame_idx in range(SEQUENCE_LENGTH):
        # Simulate a squat: downward motion then upward
        phase = (frame_idx / SEQUENCE_LENGTH) * 2 * np.pi
        knee_flex = 0.3 * (1 - np.cos(phase))  # 0 -> 0.6 -> 0 (down and up)
        hip_flex = 0.25 * (1 - np.cos(phase))

        # Landmark positions (x, y, z) - simplified skeleton
        landmarks = np.zeros((len(KEY_LANDMARKS), 3))
        # Shoulders (11, 12)
        landmarks[0:2, 0] = [0.4, 0.6]  # x
        landmarks[0:2, 1] = 0.3 - hip_flex * 0.3  # y moves slightly with squat
        # Elbows (13, 14)
        landmarks[2:4, 0] = [0.35, 0.65]
        landmarks[2:4, 1] = 0.45 - hip_flex * 0.2
        # Wrists (15, 16)
        landmarks[4:6, 0] = [0.3, 0.7]
        landmarks[4:6, 1] = 0.5 - hip_flex * 0.1
        # Hips (23, 24)
        landmarks[6:8, 0] = [0.42, 0.58]
        landmarks[6:8, 1] = 0.5 + hip_flex
        # Knees (25, 26)
        landmarks[8:10, 0] = [0.42, 0.58]
        landmarks[8:10, 1] = 0.7 + knee_flex
        # Ankles (27, 28)
        landmarks[10:12, 0] = [0.4, 0.6]
        landmarks[10:12, 1] = 0.9

        # Add small random noise
        landmarks += rng.normal(0, 0.01, landmarks.shape)
        sequence.append(landmarks.flatten())

    return np.array(sequence)


def generate_pushup_sequence(rng: np.random.Generator) -> np.ndarray:
    """Generate a synthetic pushup motion sequence.

    Pushup: elbows flex/extend horizontally, body in plank position.
    """
    sequence = []
    for frame_idx in range(SEQUENCE_LENGTH):
        phase = (frame_idx / SEQUENCE_LENGTH) * 2 * np.pi
        elbow_flex = 0.2 * (1 - np.cos(phase))  # elbows bend and straighten

        landmarks = np.zeros((len(KEY_LANDMARKS), 3))
        # Shoulders (plank height)
        landmarks[0:2, 0] = [0.4, 0.6]
        landmarks[0:2, 1] = 0.4
        # Elbows move with flexion
        landmarks[2:4, 0] = [0.35 - elbow_flex, 0.65 + elbow_flex]
        landmarks[2:4, 1] = 0.5 + elbow_flex * 0.5
        # Wrists (on ground)
        landmarks[4:6, 0] = [0.3, 0.7]
        landmarks[4:6, 1] = 0.6
        # Hips (straight line with shoulders)
        landmarks[6:8, 0] = [0.42, 0.58]
        landmarks[6:8, 1] = 0.5
        # Knees
        landmarks[8:10, 0] = [0.42, 0.58]
        landmarks[8:10, 1] = 0.65
        # Ankles
        landmarks[10:12, 0] = [0.4, 0.6]
        landmarks[10:12, 1] = 0.8

        landmarks += rng.normal(0, 0.01, landmarks.shape)
        sequence.append(landmarks.flatten())

    return np.array(sequence)


def generate_bicep_curl_sequence(rng: np.random.Generator) -> np.ndarray:
    """Generate a synthetic bicep curl motion sequence.

    Bicep curl: elbows stay fixed, wrists move up/down vertically.
    """
    sequence = []
    for frame_idx in range(SEQUENCE_LENGTH):
        phase = (frame_idx / SEQUENCE_LENGTH) * 2 * np.pi
        curl_lift = 0.25 * (1 - np.cos(phase))  # wrists lift and lower

        landmarks = np.zeros((len(KEY_LANDMARKS), 3))
        # Shoulders (standing upright)
        landmarks[0:2, 0] = [0.4, 0.6]
        landmarks[0:2, 1] = 0.3
        # Elbows (fixed at waist level)
        landmarks[2:4, 0] = [0.38, 0.62]
        landmarks[2:4, 1] = 0.45
        # Wrists (move up and down)
        landmarks[4:6, 0] = [0.37, 0.63]
        landmarks[4:6, 1] = 0.6 - curl_lift
        # Hips
        landmarks[6:8, 0] = [0.42, 0.58]
        landmarks[6:8, 1] = 0.5
        # Knees (standing, minimal movement)
        landmarks[8:10, 0] = [0.42, 0.58]
        landmarks[8:10, 1] = 0.7
        # Ankles
        landmarks[10:12, 0] = [0.4, 0.6]
        landmarks[10:12, 1] = 0.9

        landmarks += rng.normal(0, 0.01, landmarks.shape)
        sequence.append(landmarks.flatten())

    return np.array(sequence)


def generate_lunge_sequence(rng: np.random.Generator) -> np.ndarray:
    """Generate a synthetic lunge motion sequence.

    Lunge: asymmetric leg movement, one knee forward and down.
    """
    sequence = []
    for frame_idx in range(SEQUENCE_LENGTH):
        phase = (frame_idx / SEQUENCE_LENGTH) * 2 * np.pi
        front_knee_flex = 0.4 * (1 - np.cos(phase))
        back_knee_flex = 0.3 * (1 - np.cos(phase))

        landmarks = np.zeros((len(KEY_LANDMARKS), 3))
        # Shoulders
        landmarks[0:2, 0] = [0.4, 0.6]
        landmarks[0:2, 1] = 0.3 - front_knee_flex * 0.15
        # Elbows
        landmarks[2:4, 0] = [0.35, 0.65]
        landmarks[2:4, 1] = 0.4
        # Wrists
        landmarks[4:6, 0] = [0.3, 0.7]
        landmarks[4:6, 1] = 0.5
        # Hips (lower with lunge)
        landmarks[6:8, 0] = [0.42, 0.58]
        landmarks[6:8, 1] = 0.5 + front_knee_flex * 0.2
        # Knees (asymmetric: left front, right back)
        landmarks[8, 0] = 0.35  # left knee forward
        landmarks[8, 1] = 0.7 + front_knee_flex
        landmarks[9, 0] = 0.58  # right knee back
        landmarks[9, 1] = 0.75 + back_knee_flex
        # Ankles (asymmetric)
        landmarks[10, 0] = 0.3  # left ankle forward
        landmarks[10, 1] = 0.9
        landmarks[11, 0] = 0.6  # right ankle back
        landmarks[11, 1] = 0.85

        landmarks += rng.normal(0, 0.01, landmarks.shape)
        sequence.append(landmarks.flatten())

    return np.array(sequence)


EXERCISE_GENERATORS = {
    "squat": generate_squat_sequence,
    "pushup": generate_pushup_sequence,
    "bicep_curl": generate_bicep_curl_sequence,
    "lunge": generate_lunge_sequence,
}

EXERCISE_LABELS = {"squat": 0, "pushup": 1, "bicep_curl": 2, "lunge": 3}


def generate_training_data(seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic training data for all exercises.

    Returns:
        X: (N, SEQUENCE_LENGTH, num_features) array of pose sequences
        y: (N,) array of exercise labels
    """
    rng = np.random.default_rng(seed)
    X_list = []
    y_list = []

    for exercise_name, generator_fn in EXERCISE_GENERATORS.items():
        label = EXERCISE_LABELS[exercise_name]
        for _ in range(NUM_SAMPLES_PER_EXERCISE):
            sequence = generator_fn(rng)
            X_list.append(sequence)
            y_list.append(label)

    X = np.array(X_list)
    y = np.array(y_list)

    # Shuffle
    indices = rng.permutation(len(X))
    X = X[indices]
    y = y[indices]

    return X, y
