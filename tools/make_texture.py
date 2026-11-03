"""Generate the cheerful default texture: rainbow, hearts and stars.

Run with:  python3 tools/make_texture.py textures/rainbow.bmp
Only the standard library is used. Any 24/32-bit BMP can replace it
(ponies, kittens, unicorns...) through the --texture option.
"""

import colorsys
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from scop.bmp import write_bmp  # noqa: E402

SIZE = 512
CELL = 128          # one heart or one star per 128x128 cell


def star_polygon(cx, cy, outer, inner, points=5):
    pts = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = math.pi / 2 + i * math.pi / points
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def inside_polygon(x, y, poly):
    """Even-odd rule: count how many edges a horizontal ray crosses."""
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def inside_heart(x, y):
    """Classic heart curve (x^2 + y^2 - 1)^3 - x^2 y^3 <= 0."""
    return (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0


def main(path):
    pixels = bytearray(SIZE * SIZE * 3)
    star = star_polygon(0.0, 0.0, 1.0, 0.42)
    for y in range(SIZE):
        for x in range(SIZE):
            # Rainbow background with soft diagonal waves.
            hue = ((x + y) / (2 * SIZE) + 0.05 * math.sin(y / 23.0)) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.55, 1.0)

            # Position inside the cell, in [-1.6, 1.6], y going up.
            cx, cy = x // CELL, y // CELL
            lx = ((x % CELL) / CELL - 0.5) * 3.2
            ly = ((y % CELL) / CELL - 0.5) * 3.2
            if (cx + cy) % 2 == 0:
                if inside_heart(lx * 1.05, ly * 1.05 - 0.1):
                    r, g, b = 1.0, 0.30, 0.55
                elif inside_heart(lx * 0.95, ly * 0.95 - 0.1):
                    r, g, b = 1.0, 1.0, 1.0          # white outline
            else:
                if inside_polygon(lx, ly, [(px * 1.15, py * 1.15) for px, py in star]):
                    r, g, b = 1.0, 0.85, 0.15
                elif inside_polygon(lx, ly, [(px * 1.3, py * 1.3) for px, py in star]):
                    r, g, b = 1.0, 1.0, 1.0

            i = (y * SIZE + x) * 3
            pixels[i:i + 3] = bytes((int(r * 255), int(g * 255), int(b * 255)))
    write_bmp(path, SIZE, SIZE, bytes(pixels))
    print(f"texture written to {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "textures/rainbow.bmp")
