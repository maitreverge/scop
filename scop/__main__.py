"""Entry point: python -m scop [model.obj] [--texture image.bmp]"""

import argparse
import os
import sys

from .bmp import BmpError, read_bmp
from .mesh import Mesh
from .obj_loader import ObjError, load_obj
from .shader import ShaderError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(prog="scop", description="Display a 3D .obj model.")
    parser.add_argument("model", nargs="?", default=os.path.join(ROOT, "resources", "42.obj"),
                        help=".obj file to display (default: resources/42.obj)")
    parser.add_argument("--texture", default=os.path.join(ROOT, "textures", "rainbow.bmp"),
                        help="24/32-bit BMP image used as texture")
    parser.add_argument("--textured", action="store_true",
                        help="start with the texture instead of gray faces")
    parser.add_argument("--box", action="store_true", help="start with box texture mapping")
    parser.add_argument("--light", action="store_true", help="start with lighting on")
    parser.add_argument("--snapshot", metavar="FILE.bmp",
                        help="render one frame off-screen into a BMP file, then quit")
    args = parser.parse_args()

    try:
        # Read every input file first, so mistakes are reported before any
        # window opens.
        mesh = Mesh(load_obj(args.model))
        texture = read_bmp(args.texture)
        # Imported here so that --help and parse errors work without a display.
        from .app import App
        App(mesh, texture, os.path.join(ROOT, "shaders"),
            title=f"scop - {os.path.basename(args.model)}",
            textured=args.textured, box=args.box, light=args.light,
            snapshot=args.snapshot).run()
    except (ObjError, BmpError, ShaderError, RuntimeError) as e:
        print(f"scop: error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
