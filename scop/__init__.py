import logging

# PyOpenGL warns at import time that numpy is missing. We do not use numpy
# on purpose (no external math library), so hide that message.
logging.getLogger("OpenGL").setLevel(logging.ERROR)
