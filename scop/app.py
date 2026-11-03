"""Window, input handling and render loop.

glfw is only used for the window, the OpenGL context and input events.
Everything else (OBJ parsing, matrices, shaders, BMP) is our own code.
"""

import ctypes
import math
from array import array

import glfw
from OpenGL import GL

from . import math3d
from .bmp import write_bmp
from .mesh import FLOATS_PER_VERTEX
from .shader import load_program

FADE_SECONDS = 0.8          # duration of every smooth transition
SPIN_SPEED = 0.6            # automatic rotation, radians per second
ROTATE_SPEED = 1.5          # keyboard rotation, radians per second
MOVE_SPEED = 1.5            # keyboard translation, units per second
MOUSE_SENSITIVITY = 0.01    # radians per pixel dragged
CAMERA_DISTANCE = 3.6
BACKGROUND = (0.80, 0.84, 0.90)

HELP = """\
Controls
  T               toggle texture / gray faces (smooth fade)
  W / S           move up / down          (Y axis)
  A / D           move left / right       (X axis)
  Q / E           move away / closer      (Z axis)
  I / K           rotate around X axis
  J / L           rotate around Y axis
  U / O           rotate around Z axis
  mouse drag      rotate      mouse wheel  move closer / away
  SPACE           pause / resume automatic spin
  R               reset position and rotation
  ESC             quit
Bonus
  M               texture mapping: planar <-> box (no stretching)
  N               lighting on / off
  F               wireframe on / off"""


def smoothstep(t):
    """Ease in/out curve: starts slow, ends slow, so fades have no jolt."""
    return t * t * (3.0 - 2.0 * t)


class Fade:
    """A value that slides smoothly between 0 and 1 when toggled."""

    def __init__(self, on=False):
        self.on = on
        self.value = 1.0 if on else 0.0

    def toggle(self):
        self.on = not self.on

    def update(self, dt):
        step = dt / FADE_SECONDS
        if self.on:
            self.value = min(1.0, self.value + step)
        else:
            self.value = max(0.0, self.value - step)

    def eased(self):
        return smoothstep(self.value)


class App:
    def __init__(self, mesh, texture_image, shader_dir, title="scop",
                 textured=False, box=False, light=False, snapshot=None):
        self.mesh = mesh
        self.texture_image = texture_image     # (width, height, rgb bytes)
        self.shader_dir = shader_dir
        self.title = title
        self.snapshot = snapshot

        self.texture_fade = Fade(textured)
        self.box_fade = Fade(box)
        self.light_fade = Fade(light)
        self.wireframe = False
        self.spinning = True
        self.reset()

        self.dragging = False
        self.last_cursor = (0.0, 0.0)

    def reset(self):
        self.position = [0.0, 0.0, 0.0]
        self.rotation = [0.0, 0.0, 0.0]     # user rotation around X, Y, Z
        # Automatic rotation around Y. A model that is thin along X (like the
        # 42 logo) starts turned a quarter so we see its front, not its edge.
        ex, _, ez = self.mesh.extent
        self.spin = -math.pi / 2 if ex < ez else 0.0

    # ------------------------------------------------------------ setup

    def _create_window(self):
        if not glfw.init():
            raise RuntimeError("cannot initialise GLFW (is DISPLAY set?)")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
        glfw.window_hint(glfw.SAMPLES, 4)
        if self.snapshot:
            glfw.window_hint(glfw.VISIBLE, False)

        self.window = glfw.create_window(1280, 800, self.title, None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("cannot create an OpenGL 3.3 window")
        glfw.make_context_current(self.window)
        glfw.swap_interval(1)

        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_mouse_button_callback(self.window, self._on_mouse_button)
        glfw.set_cursor_pos_callback(self.window, self._on_cursor)
        glfw.set_scroll_callback(self.window, self._on_scroll)

    def _upload_mesh(self):
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)

        self.vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        data = array("f", self.mesh.vertices).tobytes()
        GL.glBufferData(GL.GL_ARRAY_BUFFER, len(data), data, GL.GL_STATIC_DRAW)

        # Describe one vertex to the GPU: (shader location, float count,
        # offset in floats). Must match the layout written in mesh.py.
        stride = FLOATS_PER_VERTEX * 4
        attributes = (
            (0, 3, 0),      # position
            (1, 2, 3),      # planar uv
            (2, 2, 5),      # box uv
            (3, 1, 7),      # gray shade
            (4, 3, 8),      # smooth normal
        )
        for location, size, offset in attributes:
            GL.glEnableVertexAttribArray(location)
            GL.glVertexAttribPointer(location, size, GL.GL_FLOAT, GL.GL_FALSE,
                                     stride, ctypes.c_void_p(offset * 4))
        GL.glBindVertexArray(0)

    def _upload_texture(self):
        width, height, pixels = self.texture_image
        self.texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, width, height, 0,
                        GL.GL_RGB, GL.GL_UNSIGNED_BYTE, pixels)
        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER,
                           GL.GL_LINEAR_MIPMAP_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)

    # ------------------------------------------------------------ input

    def _on_key(self, window, key, scancode, action, mods):
        if action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_T:
            self.texture_fade.toggle()
        elif key == glfw.KEY_M:
            self.box_fade.toggle()
        elif key == glfw.KEY_N:
            self.light_fade.toggle()
        elif key == glfw.KEY_F:
            self.wireframe = not self.wireframe
        elif key == glfw.KEY_SPACE:
            self.spinning = not self.spinning
        elif key == glfw.KEY_R:
            self.reset()

    def _on_mouse_button(self, window, button, action, mods):
        if button == glfw.MOUSE_BUTTON_LEFT:
            self.dragging = action == glfw.PRESS
            self.last_cursor = glfw.get_cursor_pos(window)

    def _on_cursor(self, window, x, y):
        if self.dragging:
            dx, dy = x - self.last_cursor[0], y - self.last_cursor[1]
            self.rotation[1] += dx * MOUSE_SENSITIVITY
            self.rotation[0] += dy * MOUSE_SENSITIVITY
        self.last_cursor = (x, y)

    def _on_scroll(self, window, dx, dy):
        self.position[2] += dy * 0.2

    def _held(self, key):
        return glfw.get_key(self.window, key) == glfw.PRESS

    def _apply_held_keys(self, dt):
        """Keys that act continuously while held down."""
        pairs = (
            (glfw.KEY_D, glfw.KEY_A, self.position, 0, MOVE_SPEED),
            (glfw.KEY_W, glfw.KEY_S, self.position, 1, MOVE_SPEED),
            (glfw.KEY_E, glfw.KEY_Q, self.position, 2, MOVE_SPEED),
            (glfw.KEY_K, glfw.KEY_I, self.rotation, 0, ROTATE_SPEED),
            (glfw.KEY_L, glfw.KEY_J, self.rotation, 1, ROTATE_SPEED),
            (glfw.KEY_O, glfw.KEY_U, self.rotation, 2, ROTATE_SPEED),
        )
        for plus, minus, target, axis, speed in pairs:
            if self._held(plus):
                target[axis] += speed * dt
            if self._held(minus):
                target[axis] -= speed * dt

    # ------------------------------------------------------------ frame

    def _update(self, dt):
        self._apply_held_keys(dt)
        if self.spinning:
            self.spin = (self.spin + SPIN_SPEED * dt) % (2.0 * math.pi)
        for fade in (self.texture_fade, self.box_fade, self.light_fade):
            fade.update(dt)

    def _model_matrix(self):
        m = self.mesh
        return math3d.chain(
            math3d.translate(*self.position),
            math3d.rotate_x(self.rotation[0]),
            math3d.rotate_y(self.rotation[1] + self.spin),
            math3d.rotate_z(self.rotation[2]),
            math3d.scale(m.fit_scale),
            # Read from the bottom: first move the object's center to the
            # origin, so every rotation above turns around its middle.
            math3d.translate(-m.center[0], -m.center[1], -m.center[2]),
        )

    def _draw(self):
        width, height = glfw.get_framebuffer_size(self.window)
        if width == 0 or height == 0:          # minimised window
            return
        GL.glViewport(0, 0, width, height)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK,
                         GL.GL_LINE if self.wireframe else GL.GL_FILL)

        model = self._model_matrix()
        view = math3d.translate(0.0, 0.0, -CAMERA_DISTANCE)
        projection = math3d.perspective(math.radians(45.0), width / height, 0.1, 100.0)
        mvp = math3d.chain(projection, view, model)

        GL.glUseProgram(self.program)
        GL.glUniformMatrix4fv(self.uniforms["uMVP"], 1, GL.GL_FALSE, (GL.GLfloat * 16)(*mvp))
        GL.glUniformMatrix4fv(self.uniforms["uModel"], 1, GL.GL_FALSE, (GL.GLfloat * 16)(*model))
        GL.glUniform1f(self.uniforms["uTextureMix"], self.texture_fade.eased())
        GL.glUniform1f(self.uniforms["uBoxMix"], self.box_fade.eased())
        GL.glUniform1f(self.uniforms["uLightMix"], self.light_fade.eased())
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
        GL.glUniform1i(self.uniforms["uTexture"], 0)

        GL.glBindVertexArray(self.vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self.mesh.vertex_count)

    def _save_snapshot(self):
        width, height = glfw.get_framebuffer_size(self.window)
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT, 1)
        pixels = GL.glReadPixels(0, 0, width, height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        write_bmp(self.snapshot, width, height, bytes(pixels))
        print(f"snapshot saved to {self.snapshot}")

    def run(self):
        self._create_window()
        try:
            self.program = load_program(f"{self.shader_dir}/scop.vert",
                                        f"{self.shader_dir}/scop.frag")
            self.uniforms = {name: GL.glGetUniformLocation(self.program, name)
                             for name in ("uMVP", "uModel", "uTexture",
                                          "uTextureMix", "uBoxMix", "uLightMix")}
            self._upload_mesh()
            self._upload_texture()

            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_MULTISAMPLE)
            GL.glClearColor(*BACKGROUND, 1.0)

            print(f"OpenGL {GL.glGetString(GL.GL_VERSION).decode()}"
                  f" - {GL.glGetString(GL.GL_RENDERER).decode()}")
            print(f"{self.mesh.vertex_count // 3} triangles\n\n{HELP}")

            last = glfw.get_time()
            while not glfw.window_should_close(self.window):
                now = glfw.get_time()
                dt, last = min(now - last, 0.1), now
                glfw.poll_events()
                self._update(dt)
                self._draw()
                if self.snapshot:
                    self._save_snapshot()
                    break
                glfw.swap_buffers(self.window)
        finally:
            glfw.terminate()
