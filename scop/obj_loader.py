"""Wavefront .obj parser, written by hand (no external library allowed).

Only the parts needed for rendering are read:
    v  x y z [w]         vertex position
    vt u [v [w]]         texture coordinate
    f  a b c ...         polygon; each corner is v, v/vt, v/vt/vn or v//vn
Everything else (vn, o, g, s, usemtl, mtllib, l, ...) is ignored.
Indices start at 1; negative indices count back from the end of the list.
"""


class ObjError(Exception):
    pass


class ObjModel:
    def __init__(self):
        self.positions = []   # [(x, y, z), ...]
        self.uvs = []         # [(u, v), ...]
        self.faces = []       # [[(pos_index, uv_index_or_None), ...], ...] 0-based


def _resolve_index(token, count, kind, line_no):
    """Turn an OBJ index (1-based or negative) into a 0-based Python index."""
    try:
        idx = int(token)
    except ValueError:
        raise ObjError(f"line {line_no}: invalid {kind} index '{token}'")
    if idx > 0:
        idx -= 1
    elif idx < 0:
        idx += count
    else:
        raise ObjError(f"line {line_no}: {kind} index 0 is not valid")
    if not 0 <= idx < count:
        raise ObjError(f"line {line_no}: {kind} index {token} out of range")
    return idx


def _parse_floats(parts, minimum, line_no, keyword):
    if len(parts) < minimum:
        raise ObjError(f"line {line_no}: '{keyword}' needs {minimum} numbers")
    try:
        return [float(p) for p in parts]
    except ValueError:
        raise ObjError(f"line {line_no}: invalid number in '{keyword}'")


def parse_obj(text):
    model = ObjModel()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        keyword, *parts = line.split()

        if keyword == "v":
            x, y, z = _parse_floats(parts, 3, line_no, "v")[:3]
            model.positions.append((x, y, z))

        elif keyword == "vt":
            values = _parse_floats(parts, 1, line_no, "vt")
            model.uvs.append((values[0], values[1] if len(values) > 1 else 0.0))

        elif keyword == "f":
            if len(parts) < 3:
                raise ObjError(f"line {line_no}: a face needs at least 3 vertices")
            face = []
            for corner in parts:
                fields = corner.split("/")
                pos = _resolve_index(fields[0], len(model.positions), "vertex", line_no)
                uv = None
                if len(fields) > 1 and fields[1] != "":
                    uv = _resolve_index(fields[1], len(model.uvs), "texture", line_no)
                face.append((pos, uv))
            model.faces.append(face)

    if not model.faces:
        raise ObjError("the file contains no faces")
    return model


def load_obj(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return parse_obj(f.read())
    except OSError as e:
        raise ObjError(f"cannot read '{path}': {e.strerror}")
