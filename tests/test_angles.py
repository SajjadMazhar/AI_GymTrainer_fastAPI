import math

from app.exercises.angles import (
    calculate_angle,
    euclidean_distance,
    horizontal_distance,
    midpoint,
    vertical_deviation_angle,
)


def test_calculate_angle_right_angle():
    # b at origin, a straight up, c straight right -> 90 degrees
    assert math.isclose(calculate_angle((0, -1), (0, 0), (1, 0)), 90.0, abs_tol=1e-6)


def test_calculate_angle_straight_line():
    # a, b, c colinear with b between a and c -> 180 degrees
    assert math.isclose(calculate_angle((-1, 0), (0, 0), (1, 0)), 180.0, abs_tol=1e-6)


def test_calculate_angle_zero_degrees():
    # a and c on the same side of b -> 0 degrees
    assert math.isclose(calculate_angle((1, 0), (0, 0), (2, 0)), 0.0, abs_tol=1e-6)


def test_calculate_angle_degenerate_zero_length_vector():
    # a == b makes the ba vector zero-length; must not raise or divide by zero
    assert calculate_angle((0, 0), (0, 0), (1, 0)) == 0.0


def test_vertical_deviation_angle_upright():
    # top directly above bottom -> 0 degrees deviation
    assert math.isclose(vertical_deviation_angle((0, 0), (0, 1)), 0.0, abs_tol=1e-6)


def test_vertical_deviation_angle_horizontal_lean():
    # top directly to the side of bottom (same y) -> ~90 degrees deviation
    assert vertical_deviation_angle((1, 0), (0, 0)) > 89.0


def test_horizontal_distance():
    assert math.isclose(horizontal_distance((0.2, 0.5), (0.7, 0.9)), 0.5, abs_tol=1e-9)


def test_euclidean_distance():
    assert math.isclose(euclidean_distance((0, 0), (3, 4)), 5.0, abs_tol=1e-9)


def test_midpoint():
    assert midpoint((0, 0), (2, 4)) == (1.0, 2.0)
