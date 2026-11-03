"""Load, compile and link GLSL shaders with the raw OpenGL API.

PyOpenGL ships a helper (OpenGL.GL.shaders) that does this for you; it is
deliberately NOT used, since the subject asks us to write the loader ourselves.
"""

from OpenGL import GL


class ShaderError(Exception):
    pass


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise ShaderError(f"cannot read shader '{path}': {e.strerror}")


def _compile(kind, path):
    shader = GL.glCreateShader(kind)
    GL.glShaderSource(shader, _read(path))
    GL.glCompileShader(shader)
    if not GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS):
        log = GL.glGetShaderInfoLog(shader).decode(errors="replace")
        GL.glDeleteShader(shader)
        raise ShaderError(f"failed to compile '{path}':\n{log}")
    return shader


def load_program(vertex_path, fragment_path):
    """Compile both shaders, link them into a program and return its id."""
    vertex = _compile(GL.GL_VERTEX_SHADER, vertex_path)
    fragment = _compile(GL.GL_FRAGMENT_SHADER, fragment_path)

    program = GL.glCreateProgram()
    GL.glAttachShader(program, vertex)
    GL.glAttachShader(program, fragment)
    GL.glLinkProgram(program)
    # Once linked, the program keeps its own copy: the shader objects can go.
    GL.glDeleteShader(vertex)
    GL.glDeleteShader(fragment)

    if not GL.glGetProgramiv(program, GL.GL_LINK_STATUS):
        log = GL.glGetProgramInfoLog(program).decode(errors="replace")
        GL.glDeleteProgram(program)
        raise ShaderError(f"failed to link shader program:\n{log}")
    return program
