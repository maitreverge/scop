"""Turn a parsed ObjModel into a flat list of floats ready for the GPU.

Every triangle gets its own 3 vertices (no sharing), so each face can have
its own flat gray color and its own texture projection. One vertex = 11 floats:

    x, y, z,   u, v (planar),   u, v (box),   shade,   nx, ny, nz (smooth)
"""

import math

from .triangulate import triangulate

FLOATS_PER_VERTEX = 11
SMOOTH_ANGLE = math.radians(60.0)   # sharper edges than this stay sharp


def face_shade(face_index):
    """A gray level in [0.12, 0.62] that changes a lot between neighbor faces.

    Multiplying by the golden ratio and keeping the fractional part spreads
    consecutive numbers evenly over [0, 1), so adjacent faces always differ.
    """
    return 0.12 + 0.5 * ((face_index * 0.6180339887) % 1.0)


def bounding_box(positions):
    xs, ys, zs = zip(*positions)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _normalize(v):
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / length, v[1] / length, v[2] / length) if length > 0 else (0.0, 0.0, 0.0)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class Mesh:
    def __init__(self, model):
        lo, hi = bounding_box(model.positions)
        self.extent = [hi[i] - lo[i] for i in range(3)]
        size = max(self.extent) or 1.0

        # Center of the bounding box: the model matrix moves it to the origin,
        # so rotations happen around the middle of the object.
        self.center = tuple((lo[i] + hi[i]) / 2.0 for i in range(3))
        # Factor that makes the biggest side 2 units long, whatever the file.
        self.fit_scale = 2.0 / size

        # Planar projection (mandatory part): the two biggest axes of the box,
        # each stretched to [0, 1].
        axes = sorted(range(3), key=lambda i: self.extent[i], reverse=True)
        pu, pv = axes[0], axes[1]

        def planar_uv(p):
            return ((p[pu] - lo[pu]) / (self.extent[pu] or 1.0),
                    (p[pv] - lo[pv]) / (self.extent[pv] or 1.0))

        # Box projection (bonus): each triangle is projected along the axis it
        # faces the most, with the same scale on both axes -> no stretching.
        def box_uv(p, normal):
            ax = max(range(3), key=lambda i: abs(normal[i]))
            u, v = {0: (2, 1), 1: (0, 2), 2: (0, 1)}[ax]
            uu = (p[u] - lo[u]) / size
            vv = (p[v] - lo[v]) / size
            # Mirror on the "back" sides so the image reads the right way.
            flip = normal[ax] < 0 if ax != 0 else normal[ax] > 0
            return (-uu if flip else uu, vv)

        # 1. Triangulate every face, remember its triangles and normal.
        triangles = []       # (face_index, [(pos_index, uv_index) x3], normal)
        for face_index, face in enumerate(model.faces):
            points = [model.positions[pos_i] for pos_i, _ in face]
            for i, j, k in triangulate(points):
                corners = [face[i], face[j], face[k]]
                a, b, c = (model.positions[pos_i] for pos_i, _ in corners)
                normal = _normalize(_cross(_sub(b, a), _sub(c, a)))
                triangles.append((face_index, corners, normal))

        # 2. Smooth normals. Files often repeat the same point under several
        # indices (the teapot does), so we group by POSITION, not by index:
        # grouping by index would leave visible seams on the lit surface.
        normals_at = {}
        for _, corners, normal in triangles:
            for pos_i, _ in corners:
                normals_at.setdefault(model.positions[pos_i], []).append(normal)
        cos_limit = math.cos(SMOOTH_ANGLE)

        def smooth_normal(position, face_normal):
            total = [0.0, 0.0, 0.0]
            for n in normals_at[position]:
                if _dot(n, face_normal) >= cos_limit:
                    total = [total[i] + n[i] for i in range(3)]
            result = _normalize(total)
            return result if result != (0.0, 0.0, 0.0) else face_normal

        # 3. Write the vertex buffer.
        data = []
        for face_index, corners, normal in triangles:
            shade = face_shade(face_index)
            for pos_i, uv_i in corners:
                p = model.positions[pos_i]
                uv = model.uvs[uv_i] if uv_i is not None else planar_uv(p)
                data.extend(p)
                data.extend(uv)
                data.extend(box_uv(p, normal))
                data.append(shade)
                data.extend(smooth_normal(p, normal))

        self.vertices = data
        self.vertex_count = len(data) // FLOATS_PER_VERTEX
