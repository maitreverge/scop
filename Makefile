IMAGE     := scop
OBJ       ?= resources/42.obj
TEXTURE   ?= textures/rainbow.bmp
ARGS      ?=

OBJ_PATH  := $(abspath $(OBJ))
TEX_PATH  := $(abspath $(TEXTURE))
XAUTH     := $(or $(XAUTHORITY),$(HOME)/.Xauthority)

# GPU access: pass /dev/dri and the groups that own it (video, render).
GPU_FLAGS := $(if $(wildcard /dev/dri),--device /dev/dri \
	$(foreach g,$(sort $(shell stat -c '%g' /dev/dri/card* /dev/dri/renderD* 2>/dev/null)),--group-add $(g)))

# Show the window on the host X server (works on Wayland through XWayland).
X11_FLAGS := -e DISPLAY=$(DISPLAY) -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
	$(if $(wildcard $(XAUTH)),-v $(XAUTH):/tmp/.Xauthority:ro -e XAUTHORITY=/tmp/.Xauthority)

# The model and texture folders are mounted, so any file on the host works.
DOCKER_RUN := docker run --rm --init \
	--user $(shell id -u):$(shell id -g) -e HOME=/tmp \
	$(GPU_FLAGS) $(X11_FLAGS) \
	-v $(dir $(OBJ_PATH)):/models:ro -v $(dir $(TEX_PATH)):/textures-in:ro

# `make` = check the dependencies, then build the image that holds the rest.
all: check build

check:
	@command -v docker >/dev/null 2>&1 || { echo "Docker is required: https://docs.docker.com/engine/install/"; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "Docker is installed but not usable (is the daemon running / are you in the docker group?)"; exit 1; }
	@echo "docker: ok"

build: check
	docker build -t $(IMAGE) .

run: build
	@test -n "$(DISPLAY)" || { echo "DISPLAY is not set: run this from a graphical session"; exit 1; }
	$(DOCKER_RUN) $(IMAGE) /models/$(notdir $(OBJ_PATH)) --texture /textures-in/$(notdir $(TEX_PATH)) $(ARGS)

42: ; @$(MAKE) --no-print-directory run OBJ=resources/42.obj
teapot: ; @$(MAKE) --no-print-directory run OBJ=resources/teapot.obj
teapot2: ; @$(MAKE) --no-print-directory run OBJ=resources/teapot2.obj

test: build
	docker run --rm --entrypoint python $(IMAGE) -m unittest discover -s tests -v

# Regenerate the default texture (rainbow, hearts and stars).
texture:
	python3 tools/make_texture.py textures/rainbow.bmp

clean:
	rm -rf snapshots
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

fclean: clean
	-docker rmi $(IMAGE)

re: fclean all

.PHONY: all check build run 42 teapot teapot2 test texture clean fclean re
