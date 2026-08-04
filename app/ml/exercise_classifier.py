"""LSTM-based exercise classifier for auto-detection."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

try:
    from tensorflow import keras
    from tensorflow.keras import layers

    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    keras = None
    layers = None

from app.ml.synthetic_data import EXERCISE_LABELS, KEY_LANDMARKS, SEQUENCE_LENGTH

LABEL_TO_EXERCISE = {v: k for k, v in EXERCISE_LABELS.items()}
MODEL_PATH = Path(__file__).parent / "exercise_model.keras"
SCALER_PATH = Path(__file__).parent / "exercise_scaler.pkl"


def build_model(input_shape: tuple[int, int]) -> keras.Model:
    """Build LSTM classifier model.

    Args:
        input_shape: (sequence_length, num_features)

    Returns:
        Compiled Keras model
    """
    if not TF_AVAILABLE:
        raise ImportError("TensorFlow/Keras required for LSTM classifier")

    model = keras.Sequential(
        [
            layers.LSTM(64, return_sequences=True, input_shape=input_shape),
            layers.Dropout(0.3),
            layers.LSTM(32),
            layers.Dropout(0.3),
            layers.Dense(16, activation="relu"),
            layers.Dense(len(EXERCISE_LABELS), activation="softmax"),
        ]
    )

    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

    return model


def train_model(X: np.ndarray, y: np.ndarray, epochs: int = 50, validation_split: float = 0.2) -> keras.Model:
    """Train the LSTM classifier on synthetic data.

    Args:
        X: (N, sequence_length, num_features) pose sequences
        y: (N,) exercise labels
        epochs: training epochs
        validation_split: fraction of data for validation

    Returns:
        Trained Keras model
    """
    if not TF_AVAILABLE:
        raise ImportError("TensorFlow/Keras required for training")

    # Normalize features (fit on training set only)
    from sklearn.preprocessing import StandardScaler

    # Flatten for scaler
    N, seq_len, num_features = X.shape
    X_flat = X.reshape(-1, num_features)
    scaler = StandardScaler()
    X_flat_scaled = scaler.fit_transform(X_flat)
    X_scaled = X_flat_scaled.reshape(N, seq_len, num_features)

    # Build and train model
    model = build_model((seq_len, num_features))

    early_stopping = keras.callbacks.EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)

    model.fit(X_scaled, y, epochs=epochs, validation_split=validation_split, callbacks=[early_stopping], verbose=1)

    # Save model and scaler
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_PATH)
    with SCALER_PATH.open("wb") as f:
        pickle.dump(scaler, f)

    print(f"Model saved to {MODEL_PATH}")
    print(f"Scaler saved to {SCALER_PATH}")

    return model


class ExerciseClassifier:
    """Real-time exercise classifier using trained LSTM model."""

    def __init__(self) -> None:
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow/Keras required for exercise classification")

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. Run training script first: "
                "python scripts/train_exercise_classifier.py"
            )

        self.model = keras.models.load_model(MODEL_PATH)

        with SCALER_PATH.open("rb") as f:
            self.scaler = pickle.load(f)

        self._sequence_buffer: list[np.ndarray] = []

    def add_frame(self, landmarks: list) -> None:
        """Add a frame's landmarks to the rolling buffer.

        Args:
            landmarks: List of 33 MediaPipe landmarks (only KEY_LANDMARKS used)
        """
        # Extract key landmarks
        key_coords = []
        for idx in KEY_LANDMARKS:
            lm = landmarks[idx]
            key_coords.extend([lm.x, lm.y, lm.z])

        self._sequence_buffer.append(np.array(key_coords))

        # Keep only the most recent SEQUENCE_LENGTH frames
        if len(self._sequence_buffer) > SEQUENCE_LENGTH:
            self._sequence_buffer.pop(0)

    def predict(self) -> tuple[str, float] | None:
        """Predict exercise type from buffered sequence.

        Returns:
            (exercise_name, confidence) or None if buffer not full yet
        """
        if len(self._sequence_buffer) < SEQUENCE_LENGTH:
            return None  # Not enough frames yet

        # Prepare sequence
        sequence = np.array(self._sequence_buffer[-SEQUENCE_LENGTH:])
        sequence_scaled = self.scaler.transform(sequence)
        sequence_batch = sequence_scaled[np.newaxis, :, :]  # (1, seq_len, features)

        # Predict
        probs = self.model.predict(sequence_batch, verbose=0)[0]
        predicted_label = int(np.argmax(probs))
        confidence = float(probs[predicted_label])

        exercise_name = LABEL_TO_EXERCISE[predicted_label]

        return exercise_name, confidence

    def reset(self) -> None:
        """Clear the sequence buffer."""
        self._sequence_buffer.clear()
