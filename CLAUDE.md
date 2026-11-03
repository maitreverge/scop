# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

42 school project **scop** (`subject.pdf`): an OpenGL viewer for Wavefront `.obj` files, written in Python and run in Docker. The README.md must keep the 42-mandated sections (italic first line with logins, Description, Instructions, Resources including an AI-usage note).

## Hard constraints from the subject

- External libraries are allowed **only for window/event management**. Here that means `glfw` (window, context, input) and `PyOpenGL` used purely as the raw GL binding.
- **Never** use a library for OBJ loading, matrices or shader loading. No numpy, and no `OpenGL.GL.shaders` helpers. Math is pure Python in `scop/math3d.py`, and shaders are compiled with raw `glCreateShader`/`glCompileShader` calls in `scop/shader.py`.
- Texture loading is also hand-written (`scop/bmp.py`, uncompressed 24/32-bit BMP only).
- Bonus work is only graded if the mandatory part is perfect: perspective, rotation and translation on 3 axes around the object's center, distinct gray faces, and a T-key texture toggle with a smooth fade.

## Commands

```bash
make                  # check Docker, build the `scop` image (all deps live in the image)
make run              # run resources/42.obj on the host display (X11/XWayland + /dev/dri)
make run OBJ=path/model.obj TEXTURE=path/img.bmp ARGS="--textured --box --light"
make test             # unit tests inside the container
make fclean           # remove the image
python3 -m unittest discover -s tests -v                          # tests also run on the host (stdlib only)
python3 -m unittest tests.test_scop.TriangulateTest.test_concave_polygon   # single test
python3 tools/make_texture.py textures/rainbow.bmp                # regenerate default texture
```

- Code is COPYed into the image, so `make run` rebuilds the image first (layers are cached, so this is fast). The model and texture folders are mounted at `/models` and `/textures-in`, so any host path works.
- The Makefile variable is `TEXTURE`, not `TEX`, because GNU make has a built-in `TEX = tex` that `?=` would not override.
- Visual check without a visible window: `--snapshot out.bmp` renders one frame in a hidden window and writes a BMP. Run it through the `make -n run` docker command with an extra `-v` for the output dir.
- The host has no PyOpenGL/glfw, so anything that imports `scop.app` or `scop.shader` must run in the container.

## Architecture

Data flow: `obj_loader.parse_obj` → `ObjModel` (positions, uvs, faces as 0-based `(pos_idx, uv_idx|None)` lists) → `mesh.Mesh` → flat float list → one VBO, drawn with `glDrawArrays`.

- **Unindexed vertices by design**: each triangle owns its 3 vertices, so per-face data (gray shade, box UVs) can differ between neighbors. Vertex layout is 11 floats: `pos(3) | planar uv(2) | box uv(2) | shade(1) | smooth normal(3)`. This layout must stay in sync across three places: `mesh.FLOATS_PER_VERTEX` and write order, the `attributes` table in `App._upload_mesh`, and the `layout(location=N)` inputs in `shaders/scop.vert`.
- **Triangulation** (`triangulate.py`): ear clipping on the Newell best-fit plane, falling back to a fan for degenerate or self-intersecting polygons.
- **Smooth normals** are grouped by *position*, not index, because the teapots repeat points under different indices. Normals are only averaged with faces within 60°, which keeps the 42 logo's hard edges.
- **Model matrix** (`App._model_matrix`): `T(user) · Rx · Ry(user+spin) · Rz · S(fit_scale) · T(-bbox_center)`. Matrices are column-major flat lists of 16 floats, and `math3d.chain(A, B, C) = A·B·C`.
- **Transitions**: each toggle (texture, box mapping, lighting) is a `Fade` object (0→1 over `FADE_SECONDS`, eased with smoothstep), sent as a uniform. `scop.frag` blends with `mix()`. Wireframe is an instant `glPolygonMode` switch.
- `__main__.py` reads the OBJ and BMP before importing `scop.app`, so input errors are reported before any window or GLFW initialisation. Errors raise `ObjError`, `BmpError`, `ShaderError` or `RuntimeError` and are printed as `scop: error: ...` with exit code 1.
- `scop/__init__.py` silences PyOpenGL's "numpy missing" log warning.
