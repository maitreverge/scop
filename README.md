*This project has been created as part of the 42 curriculum by &lt;login&gt;.*

# scop

## Description

`scop` is a small 3D viewer: it reads a Wavefront `.obj` file and displays it
with OpenGL, in perspective, spinning around its own center.

- Each face gets its own shade of gray so faces are easy to tell apart.
- Pressing **T** fades smoothly to a texture (rainbow, hearts and stars) and back.
- The object can be moved and rotated along its three axes, with the keyboard or the mouse.

It is written in **Python**, runs in a **Docker container**, and follows the
subject's constraints: the only external libraries are

| library    | used for                                                         |
|------------|------------------------------------------------------------------|
| `glfw`     | window, OpenGL context, keyboard and mouse events                |
| `PyOpenGL` | plain bindings to the OpenGL API (its shader helpers are not used) |

The OBJ parser, the matrices, the shader loader, the BMP reader and the
triangulation are all written by hand (no numpy either).

## Instructions

Requirements: Linux with a graphical session (X11, or Wayland with XWayland)
and Docker. Everything else is installed inside the image.

```bash
make                 # checks Docker, then builds the image with all dependencies
make run             # shows the 42 logo
make run OBJ=resources/teapot.obj
make run OBJ=/any/path/model.obj TEXTURE=/any/path/ponies.bmp
make test            # unit tests (parser, matrices, triangulation, BMP)
make fclean          # removes the image
```

Shortcuts: `make 42`, `make teapot`, `make teapot2`.
Extra program options go through `ARGS`, e.g. `make run ARGS="--textured --light"`.
The texture must be an uncompressed 24 or 32-bit BMP.

### Controls

| key            | action                                            |
|----------------|---------------------------------------------------|
| `T`            | gray faces ⇄ texture (smooth fade)                |
| `W` / `S`      | move up / down (Y)                                |
| `A` / `D`      | move left / right (X)                             |
| `Q` / `E`      | move away / closer (Z)                            |
| `I` / `K`      | rotate around X                                   |
| `J` / `L`      | rotate around Y                                   |
| `U` / `O`      | rotate around Z                                   |
| mouse drag     | rotate                                            |
| mouse wheel    | move closer / away                                |
| `SPACE`        | pause / resume the automatic spin                 |
| `R`            | reset                                             |
| `M` *(bonus)*  | planar ⇄ box texture mapping (smooth fade)        |
| `N` *(bonus)*  | lighting on / off (smooth fade)                   |
| `F` *(bonus)*  | wireframe on / off                                |
| `ESC`          | quit                                              |

## How it works

```
.obj file ──► obj_loader.py ──► mesh.py ──────────► GPU vertex buffer
              (v, vt, f)        triangulate,        x y z | uv planar | uv box | gray | normal
                                gray per face,
                                uv + normals
                                                     shaders/scop.vert  (position = MVP × vertex)
math3d.py ──► model / view / projection ──► uMVP ──► shaders/scop.frag  (gray ⇄ texture mix)
```

| file                   | role |
|------------------------|------|
| `scop/obj_loader.py`   | parses `v`, `vt`, `f` (`v`, `v/vt`, `v/vt/vn`, `v//vn`, negative indices), clear errors |
| `scop/triangulate.py`  | ear clipping, works for concave and non-flat polygons |
| `scop/mesh.py`         | builds the vertex buffer: gray shade per face, texture coordinates, smooth normals |
| `scop/math3d.py`       | 4×4 column-major matrices: translate, scale, rotate, perspective |
| `scop/shader.py`       | reads, compiles and links GLSL with raw OpenGL calls |
| `scop/bmp.py`          | BMP reader / writer |
| `scop/app.py`          | window, input, render loop, transitions |
| `tools/make_texture.py`| generates `textures/rainbow.bmp` |

Key points:

- **Perspective**: `math3d.perspective` puts the distance from the camera into
  `w`. The GPU then divides x and y by `w`, so far objects look smaller.
- **Rotation around the center**: the model matrix is
  `T(user) · Rx · Ry · Rz · S(fit) · T(-center)`. Read from right to left, it
  first moves the bounding-box center to the origin, so every rotation
  happens around the middle of the object, not around one of its corners.
  `S(fit)` resizes any model to the same on-screen size.
- **Distinct faces**: the triangles do not share vertices, so each one can
  carry its face's gray level. The level is `0.12 + 0.5 · frac(i · φ)` (golden ratio),
  which keeps neighboring faces clearly different.
- **Smooth transition**: a value goes from 0 to 1 over 0.8 s, is eased with
  `smoothstep`, and the fragment shader does `mix(gray, texture, value)`.

## Bonus

1. **Complex `.obj` files**: polygons are split with ear clipping on their
   best-fit plane (Newell's method), so concave and non-coplanar faces render
   correctly, where a plain triangle fan would draw outside the shape.
   The original `teapot.obj` has the same triangles as `teapot2.obj`, but has
   160 open edges (you can see inside through gaps) and repeats 403 points
   under different indices. scop draws both sides of every face, lights the
   inside correctly, and builds smooth normals by grouping on *position* rather
   than index, so the lit surface has no seams.
2. **Texture without stretching** (`M`): box mapping projects each triangle
   along the axis it faces most, with the same scale on both axes, so side
   faces no longer show stretched lines.
3. **More**: lighting (`N`), wireframe (`F`), mouse control, any BMP as
   texture, `--snapshot file.bmp` to render one frame to an image.

## Resources

- [LearnOpenGL](https://learnopengl.com/): shaders, textures, coordinate systems, transformations
- [docs.gl](https://docs.gl/): OpenGL function reference
- [Wavefront OBJ specification](https://paulbourke.net/dataformats/obj/)
- [Song Ho Ahn: OpenGL projection matrix](https://www.songho.ca/opengl/gl_projectionmatrix.html)
- [Ear clipping triangulation (Eberly)](https://www.geometrictools.com/Documentation/TriangulationByEarClipping.pdf)
- [Newell's method for polygon normals](https://www.khronos.org/opengl/wiki/Calculating_a_Surface_Normal)
- [BMP file format](https://en.wikipedia.org/wiki/BMP_file_format)
- [GLFW documentation](https://www.glfw.org/docs/latest/)

### Use of AI

An AI assistant (Claude) was used for:

- the first version of the code, Docker setup and Makefile, written from the subject;
- analysing the two teapot files to find out why the original one shows artifacts;
- writing the unit tests and this README.

Every part was then reviewed, run and tested by me, and I can explain each
design choice (matrix order, triangulation, transitions, container setup).
