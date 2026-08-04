#!/usr/bin/env python3
"""Train the LSTM exercise classifier on synthetic data."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from app.ml.exercise_classifier import train_model
from app.ml.synthetic_data import generate_training_data

if __name__ == "__main__":
    print("Generating synthetic training data...")
    X, y = generate_training_data(seed=42)
    print(f"Generated {len(X)} samples with shape {X.shape}")
    print(f"Class distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

    print("\nTraining LSTM model...")
    model = train_model(X, y, epochs=50, validation_split=0.2)

    print("\nTraining complete!")
    print("Model saved and ready for inference.")
