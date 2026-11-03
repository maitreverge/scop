FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Mesa (OpenGL drivers for Intel/AMD GPUs + llvmpipe software fallback)
# and the X11 libraries GLFW loads at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglx-mesa0 libgl1-mesa-dri libegl1 \
        libx11-6 libx11-xcb1 libxext6 libxrandr2 libxinerama1 \
        libxcursor1 libxi6 libxxf86vm1 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /scop
COPY scop/ scop/
COPY shaders/ shaders/
COPY textures/ textures/
COPY tests/ tests/
COPY resources/ resources/

ENTRYPOINT ["python", "-m", "scop"]
CMD ["resources/42.obj"]
