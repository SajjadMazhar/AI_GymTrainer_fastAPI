"""Shared synthetic-landmark builders for exercise-analyzer unit tests.

Angles are constructed analytically: for a joint with vertex `v`, a fixed
reference point at `v + (0, -1)` (playing the role of hip/shoulder), and a
second point at `v + (sin(theta), -cos(theta))` (playing the role of
ankle/wrist), `calculate_angle` between them is exactly `theta` degrees.
This lets tests drive an analyzer through an exact, known angle sequence
without needing biomechanically realistic coordinates.
"""
from __future__ import annotations

import math

from app.pose.base import Landmark
from app.pose.landmark_index import LandmarkIndex as LM

NUM_LANDMARKS = 33
Point = tuple[float, float]


def default_landmarks(visibility: float = 1.0) -> list[Landmark]:
    return [Landmark(x=0.5, y=0.5, z=0.0, visibility=visibility) for _ in range(NUM_LANDMARKS)]


def set_point(landmarks: list[Landmark], idx: LM, point: Point, visibility: float = 1.0) -> None:
    landmarks[idx] = Landmark(x=point[0], y=point[1], z=0.0, visibility=visibility)


def far_point(vertex: Point, theta_deg: float) -> Point:
    """Point at angle theta_deg from vertex, given a fixed reference direction of (0, -1)."""
    theta = math.radians(theta_deg)
    return (vertex[0] + math.sin(theta), vertex[1] - math.cos(theta))


def near_point(vertex: Point) -> Point:
    """Fixed reference point establishing the (0, -1) direction from vertex."""
    return (vertex[0], vertex[1] - 1.0)


def point_at_angle(vertex: Point, reference_point: Point, theta_deg: float, scale: float = 1.0) -> Point:
    """A point p such that the angle at `vertex` between `reference_point` and
    `p` is exactly theta_deg, regardless of where reference_point sits
    relative to vertex. Lets tests move the "near" landmark freely (e.g. to
    also test shoulder/hip drift) while still controlling the joint angle
    precisely."""
    ref_x, ref_y = reference_point[0] - vertex[0], reference_point[1] - vertex[1]
    norm = math.hypot(ref_x, ref_y)
    ux, uy = ref_x / norm, ref_y / norm
    theta = math.radians(theta_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    rx = ux * cos_t - uy * sin_t
    ry = ux * sin_t + uy * cos_t
    return (vertex[0] + rx * scale, vertex[1] + ry * scale)
