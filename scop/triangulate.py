"""Split polygons into triangles (bonus: concave and non-coplanar faces).

A simple "fan" (0,1,2), (0,2,3), ... only works for convex polygons: on a
concave one some triangles end up outside the shape. Ear clipping works for
any simple polygon:

  1. Find the plane that best fits the polygon (Newell's method) and project
     the points onto it, which gives a 2D polygon (this also handles faces whose
     points are not exactly on one plane).
  2. An "ear" is a corner whose triangle (prev, corner, next) is convex and
     contains no other point of the polygon. Cut it off, repeat until only
     one triangle is left.
"""

EPSILON = 1e-12


def newell_normal(points):
    """Normal of the best-fit plane of a 3D polygon (not normalised)."""
    nx = ny = nz = 0.0
    for i, (x0, y0, z0) in enumerate(points):
        x1, y1, z1 = points[(i + 1) % len(points)]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return (nx, ny, nz)


def _project_2d(points, normal):
    """Drop the axis the normal points along the most, keep the other two.

    The two kept axes are chosen so the polygon keeps the same turning
    direction (counter-clockwise when seen from the normal's side).
    """
    ax, ay, az = (abs(c) for c in normal)
    if ax >= ay and ax >= az:
        u, v, sign = 1, 2, normal[0]
    elif ay >= az:
        u, v, sign = 2, 0, normal[1]
    else:
        u, v, sign = 0, 1, normal[2]
    if sign < 0:
        u, v = v, u
    return [(p[u], p[v]) for p in points]


def _cross(o, a, b):
    """z of (a - o) x (b - o): > 0 when o -> a -> b turns left."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _inside_triangle(p, a, b, c):
    return (_cross(a, b, p) >= -EPSILON and _cross(b, c, p) >= -EPSILON
            and _cross(c, a, p) >= -EPSILON)


def triangulate(points):
    """Return a list of (i, j, k) index triples covering the polygon."""
    n = len(points)
    if n < 3:
        return []
    if n == 3:
        return [(0, 1, 2)]

    normal = newell_normal(points)
    if sum(c * c for c in normal) < EPSILON:
        return fan(n)                       # degenerate (zero area) polygon

    pts = _project_2d(points, normal)
    remaining = list(range(n))
    triangles = []

    while len(remaining) > 3:
        for k in range(len(remaining)):
            i_prev = remaining[k - 1]
            i_cur = remaining[k]
            i_next = remaining[(k + 1) % len(remaining)]
            a, b, c = pts[i_prev], pts[i_cur], pts[i_next]
            if _cross(a, b, c) <= EPSILON:
                continue                    # reflex (or flat) corner: not an ear
            if any(_inside_triangle(pts[j], a, b, c)
                   for j in remaining if j not in (i_prev, i_cur, i_next)):
                continue                    # another point inside: not an ear
            triangles.append((i_prev, i_cur, i_next))
            remaining.pop(k)
            break
        else:
            # No ear found: the polygon crosses itself. Finish with a fan so
            # we still draw something instead of failing.
            triangles.extend((remaining[0], remaining[i], remaining[i + 1])
                             for i in range(1, len(remaining) - 1))
            return triangles

    triangles.append(tuple(remaining))
    return triangles


def fan(n):
    return [(0, i, i + 1) for i in range(1, n - 1)]
