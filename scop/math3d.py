"""Tiny 4x4 matrix library (no numpy, as required by the subject).

Matrices are flat lists of 16 floats in COLUMN-MAJOR order, which is the
layout OpenGL expects: element (row r, column c) lives at index c * 4 + r.
"""

import math


def identity():
    return [1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0]


def multiply(a, b):
    """Return a * b (apply b first, then a)."""
    out = [0.0] * 16
    for c in range(4):
        for r in range(4):
            out[c * 4 + r] = (a[0 * 4 + r] * b[c * 4 + 0]
                              + a[1 * 4 + r] * b[c * 4 + 1]
                              + a[2 * 4 + r] * b[c * 4 + 2]
                              + a[3 * 4 + r] * b[c * 4 + 3])
    return out


def chain(*matrices):
    """chain(A, B, C) == A * B * C."""
    result = identity()
    for m in matrices:
        result = multiply(result, m)
    return result


def translate(x, y, z):
    m = identity()
    m[12], m[13], m[14] = x, y, z
    return m


def scale(s):
    m = identity()
    m[0] = m[5] = m[10] = s
    return m


def rotate_x(angle):
    c, s = math.cos(angle), math.sin(angle)
    m = identity()
    m[5], m[6] = c, s
    m[9], m[10] = -s, c
    return m


def rotate_y(angle):
    c, s = math.cos(angle), math.sin(angle)
    m = identity()
    m[0], m[2] = c, -s
    m[8], m[10] = s, c
    return m


def rotate_z(angle):
    c, s = math.cos(angle), math.sin(angle)
    m = identity()
    m[0], m[1] = c, s
    m[4], m[5] = -s, c
    return m


def perspective(fov_y, aspect, near, far):
    """Standard OpenGL perspective projection (fov_y in radians).

    Points farther from the camera end up with a bigger w, and the GPU divides
    x and y by w: that division is what makes far objects look smaller.
    """
    f = 1.0 / math.tan(fov_y / 2.0)
    m = [0.0] * 16
    m[0] = f / aspect
    m[5] = f
    m[10] = (far + near) / (near - far)
    m[11] = -1.0
    m[14] = (2.0 * far * near) / (near - far)
    return m


def transform_point(m, p):
    """Apply m to the 3D point p and do the perspective divide (used by tests)."""
    x, y, z = p
    out = [m[r] * x + m[4 + r] * y + m[8 + r] * z + m[12 + r] for r in range(4)]
    w = out[3] if out[3] != 0 else 1.0
    return (out[0] / w, out[1] / w, out[2] / w)
