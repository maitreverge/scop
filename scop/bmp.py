"""Minimal BMP reader/writer for the texture (24 and 32 bit, uncompressed).

The pixels are returned bottom row first, which is exactly what OpenGL wants
for glTexImage2D (texture coordinate v = 0 is the bottom of the image).
"""

import struct


class BmpError(Exception):
    pass


def read_bmp(path):
    """Return (width, height, rgb_bytes) with rows ordered bottom to top."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise BmpError(f"cannot read '{path}': {e.strerror}")

    if len(data) < 54 or data[:2] != b"BM":
        raise BmpError(f"'{path}' is not a BMP file")

    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]

    if bpp not in (24, 32) or compression not in (0, 3):
        raise BmpError(f"'{path}': only uncompressed 24/32-bit BMP are supported")
    if width <= 0 or height == 0:
        raise BmpError(f"'{path}': invalid size")

    top_down = height < 0
    height = abs(height)
    bytes_pp = bpp // 8
    row_size = (width * bytes_pp + 3) & ~3          # rows are padded to 4 bytes
    if pixel_offset + row_size * height > len(data):
        raise BmpError(f"'{path}' is truncated")

    rows = []
    for y in range(height):
        start = pixel_offset + y * row_size
        row = data[start:start + width * bytes_pp]
        rgb = bytearray(width * 3)
        rgb[0::3] = row[2::bytes_pp]                # BMP stores B, G, R
        rgb[1::3] = row[1::bytes_pp]
        rgb[2::3] = row[0::bytes_pp]
        rows.append(bytes(rgb))
    if top_down:
        rows.reverse()
    return width, height, b"".join(rows)


def write_bmp(path, width, height, rgb_bottom_up):
    """Write 24-bit BMP from RGB bytes ordered bottom row first."""
    row_size = (width * 3 + 3) & ~3
    padding = b"\0" * (row_size - width * 3)
    body = bytearray()
    for y in range(height):
        row = rgb_bottom_up[y * width * 3:(y + 1) * width * 3]
        bgr = bytearray(len(row))
        bgr[0::3], bgr[1::3], bgr[2::3] = row[2::3], row[1::3], row[0::3]
        body += bgr + padding
    header = struct.pack("<2sIHHI", b"BM", 54 + len(body), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0,
                       len(body), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + body)
