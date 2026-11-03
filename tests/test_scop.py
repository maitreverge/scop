"""Unit tests for the parts that do not need a GPU.

Run with:  make test   (or: python3 -m unittest discover -s tests -v)
"""

import math
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scop import math3d  # noqa: E402
from scop.bmp import BmpError, read_bmp, write_bmp  # noqa: E402
from scop.mesh import FLOATS_PER_VERTEX, Mesh  # noqa: E402
from scop.obj_loader import ObjError, load_obj, parse_obj  # noqa: E402
from scop.triangulate import triangulate  # noqa: E402


def close(a, b, eps=1e-6):
    return all(abs(x - y) < eps for x, y in zip(a, b))


class MathTest(unittest.TestCase):
    def test_identity_multiply(self):
        m = math3d.translate(1, 2, 3)
        self.assertEqual(math3d.multiply(math3d.identity(), m), m)

    def test_translate_point(self):
        p = math3d.transform_point(math3d.translate(1, 2, 3), (1, 1, 1))
        self.assertTrue(close(p, (2, 3, 4)))

    def test_rotate_y_quarter_turn(self):
        p = math3d.transform_point(math3d.rotate_y(math.pi / 2), (1, 0, 0))
        self.assertTrue(close(p, (0, 0, -1)))

    def test_order_matters(self):
        # chain(T, R): rotate first, then translate.
        m = math3d.chain(math3d.translate(5, 0, 0), math3d.rotate_z(math.pi / 2))
        self.assertTrue(close(math3d.transform_point(m, (1, 0, 0)), (5, 1, 0)))

    def test_perspective_far_is_smaller(self):
        proj = math3d.perspective(math.radians(45), 1.0, 0.1, 100.0)
        near = math3d.transform_point(proj, (1, 0, -2))
        far = math3d.transform_point(proj, (1, 0, -10))
        self.assertGreater(near[0], far[0])


class ObjTest(unittest.TestCase):
    def test_all_index_formats(self):
        text = """
        v 0 0 0
        v 1 0 0
        v 1 1 0
        v 0 1 0
        vt 0 0
        vt 1 0
        vt 1 1
        vn 0 0 1
        f 1/1/1 2/2/1 3/3/1   # comment
        f 1//1 3//1 4//1
        f -4 -2 -1
        """
        model = parse_obj(text)
        self.assertEqual(len(model.positions), 4)
        self.assertEqual(model.faces[0], [(0, 0), (1, 1), (2, 2)])
        self.assertEqual(model.faces[1], [(0, None), (2, None), (3, None)])
        self.assertEqual(model.faces[2], [(0, None), (2, None), (3, None)])

    def test_errors(self):
        with self.assertRaises(ObjError):
            parse_obj("v 0 0 0\nf 1 2 3")           # index out of range
        with self.assertRaises(ObjError):
            parse_obj("v 0 0\n")                    # not enough numbers
        with self.assertRaises(ObjError):
            parse_obj("v 0 0 0\n")                  # no faces
        with self.assertRaises(ObjError):
            load_obj("/does/not/exist.obj")

    def test_resources_load(self):
        for name, faces in (("42.obj", 47), ("teapot.obj", 6320), ("teapot2.obj", 6320)):
            path = os.path.join(ROOT, "resources", name)
            if os.path.exists(path):
                self.assertEqual(len(load_obj(path).faces), faces)


class TriangulateTest(unittest.TestCase):
    def area(self, pts, tris):
        total = 0.0
        for i, j, k in tris:
            (ax, ay, _), (bx, by, _), (cx, cy, _) = pts[i], pts[j], pts[k]
            total += abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) / 2
        return total

    def test_concave_polygon(self):
        # An arrow head: a fan from point 0 would use the diagonal
        # (4,0)-(0,0), which runs outside the shape, below the notch.
        pts = [(4, 0, 0), (2, 3, 0), (0, 0, 0), (2, 1, 0)]
        tris = triangulate(pts)
        self.assertEqual(len(tris), 2)
        self.assertAlmostEqual(self.area(pts, tris), 4.0)

    def test_l_shape_both_windings(self):
        pts = [(0, 0, 0), (2, 0, 0), (2, 1, 0), (1, 1, 0), (1, 2, 0), (0, 2, 0)]
        for poly in (pts, pts[::-1]):
            tris = triangulate(poly)
            self.assertEqual(len(tris), 4)
            self.assertAlmostEqual(self.area(poly, tris), 3.0)

    def test_tilted_plane(self):
        # Same L shape lying in the x/z plane.
        pts = [(0, 0, 0), (2, 0, 0), (2, 0, 1), (1, 0, 1), (1, 0, 2), (0, 0, 2)]
        self.assertEqual(len(triangulate(pts)), 4)


class MeshTest(unittest.TestCase):
    def test_quad_becomes_two_triangles(self):
        model = parse_obj("v 0 0 0\nv 2 0 0\nv 2 1 0\nv 0 1 0\nf 1 2 3 4")
        mesh = Mesh(model)
        self.assertEqual(mesh.vertex_count, 6)
        self.assertEqual(len(mesh.vertices), 6 * FLOATS_PER_VERTEX)
        self.assertTrue(close(mesh.center, (1, 0.5, 0)))
        self.assertAlmostEqual(mesh.fit_scale, 1.0)

    def test_box_uv_not_stretched(self):
        # A 2x1 rectangle: box mapping keeps the 2:1 ratio in uv space.
        model = parse_obj("v 0 0 0\nv 2 0 0\nv 2 1 0\nv 0 1 0\nf 1 2 3 4")
        v = Mesh(model).vertices
        uvs = [(v[i + 5], v[i + 6]) for i in range(0, len(v), FLOATS_PER_VERTEX)]
        us = [u for u, _ in uvs]
        vs = [w for _, w in uvs]
        self.assertAlmostEqual((max(us) - min(us)) / (max(vs) - min(vs)), 2.0)


class BmpTest(unittest.TestCase):
    def test_round_trip_with_padding(self):
        w, h = 3, 2                                # 9 bytes per row -> padded
        pixels = bytes(range(w * h * 3))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.bmp")
            write_bmp(path, w, h, pixels)
            self.assertEqual(read_bmp(path), (w, h, pixels))

    def test_not_a_bmp(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.bmp")
            with open(path, "wb") as f:
                f.write(b"hello")
            with self.assertRaises(BmpError):
                read_bmp(path)


if __name__ == "__main__":
    unittest.main()
