"""Pure geometry helpers for joint-angle based rep counting and posture checks.

All coordinates are (x, y) tuples in MediaPipe's normalized image space:
x/y in [0, 1], y increasing downward. Angle math uses the dot product, which
is scale-invariant, so results don't depend on how far the phone is from the
subject.
"""
from __future__ import annotations

import numpy as np

Point = tuple[float, float]


def calculate_angle(a: Point, b: Point, c: Point) -> float:
    """Angle ABC in degrees, measured at vertex b."""
    a_arr, b_arr, c_arr = np.array(a, dtype=float), np.array(b, dtype=float), np.array(c, dtype=float)
    ba = a_arr - b_arr
    bc = c_arr - b_arr
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom == 0:
        return 0.0
    cosine = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def vertical_deviation_angle(top: Point, bottom: Point) -> float:
    """Degrees the top->bottom vector deviates from true vertical (0 = upright)."""
    dx = top[0] - bottom[0]
    dy = top[1] - bottom[1]
    return float(np.degrees(np.arctan2(abs(dx), abs(dy) + 1e-8)))


def horizontal_distance(p1: Point, p2: Point) -> float:
    return abs(p1[0] - p2[0])


def euclidean_distance(p1: Point, p2: Point) -> float:
    return float(np.hypot(p1[0] - p2[0], p1[1] - p2[1]))


def midpoint(p1: Point, p2: Point) -> Point:
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
