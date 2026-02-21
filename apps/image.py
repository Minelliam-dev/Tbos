import os, shutil, struct, zlib

def _enable_windows_vt_mode():
    """Enable ANSI escape processing on Windows terminals that need it."""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
            kernel32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass

def _path(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c

def _unfilter(raw: bytes, width: int, height: int, bpp: int) -> bytearray:
    stride = width * bpp
    out = bytearray(height * stride)

    i = 0
    for y in range(height):
        ftype = raw[i]
        i += 1
        row = raw[i:i + stride]
        i += stride
        row_out = memoryview(out)[y * stride:(y + 1) * stride]

        if ftype == 0:  # None
            row_out[:] = row

        elif ftype == 1:  # Sub
            for x in range(stride):
                left = row_out[x - bpp] if x >= bpp else 0
                row_out[x] = (row[x] + left) & 0xFF

        elif ftype == 2:  # Up
            prev = memoryview(out)[(y - 1) * stride:y * stride] if y > 0 else None
            for x in range(stride):
                up = prev[x] if prev is not None else 0
                row_out[x] = (row[x] + up) & 0xFF

        elif ftype == 3:  # Average
            prev = memoryview(out)[(y - 1) * stride:y * stride] if y > 0 else None
            for x in range(stride):
                left = row_out[x - bpp] if x >= bpp else 0
                up = prev[x] if prev is not None else 0
                row_out[x] = (row[x] + ((left + up) >> 1)) & 0xFF

        elif ftype == 4:  # Paeth
            prev = memoryview(out)[(y - 1) * stride:y * stride] if y > 0 else None
            for x in range(stride):
                left = row_out[x - bpp] if x >= bpp else 0
                up = prev[x] if prev is not None else 0
                up_left = prev[x - bpp] if (prev is not None and x >= bpp) else 0
                row_out[x] = (row[x] + _path(left, up, up_left)) & 0xFF
        else:
            raise ValueError(f"Unsupported PNG filter type: {ftype}")

    return out

def _read_png_8bit_noninterlaced(path: str):
    with open(path, "rb") as f:
        if f.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Not a PNG file")

        width = height = None
        bit_depth = color_type = interlace = None
        idat = []

        while True:
            length_b = f.read(4)
            if not length_b:
                break
            (length,) = struct.unpack(">I", length_b)
            ctype = f.read(4)
            data = f.read(length)
            f.read(4)  # CRC ignored

            if ctype == b"IHDR":
                width, height, bit_depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", data)
                if comp != 0 or filt != 0:
                    raise ValueError("Unsupported PNG compression/filter method")
                if interlace != 0:
                    raise ValueError("Unsupported PNG: interlaced PNGs are not handled")
                if bit_depth != 8:
                    raise ValueError("Unsupported PNG: only 8-bit depth is handled")
                if color_type not in (0, 2, 4, 6):
                    raise ValueError("Unsupported PNG: indexed-color (palette) PNGs (type 3) not handled")

            elif ctype == b"IDAT":
                idat.append(data)

            elif ctype == b"IEND":
                break

        if width is None or not idat:
            raise ValueError("Corrupt PNG (missing IHDR or IDAT)")

        bpp = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
        raw = zlib.decompress(b"".join(idat))

        expected = height * (1 + width * bpp)
        if len(raw) != expected:
            raise ValueError(
                f"Unexpected decompressed size (got {len(raw)}, expected {expected}). "
                "This decoder only supports common non-interlaced 8-bit PNGs."
            )

        pixels = _unfilter(raw, width, height, bpp)
        return width, height, color_type, pixels

def _nearest_resize(width, height, src, bpp, new_w, new_h):
    out = bytearray(new_w * new_h * bpp)
    for y2 in range(new_h):
        y = (y2 * height) // new_h
        for x2 in range(new_w):
            x = (x2 * width) // new_w
            si = (y * width + x) * bpp
            di = (y2 * new_w + x2) * bpp
            out[di:di + bpp] = src[si:si + bpp]
    return out

def _gray_to_ansi256(g: int) -> int:
    """
    Map 0..255 to ANSI 256 grayscale ramp (codes 232..255).
    That ramp has 24 levels.
    """
    if g <= 0:
        return 232
    if g >= 255:
        return 255
    level = (g * 23) // 255  # 0..23
    return 232 + level

def display_png_grayscale_ansi256(path: str, max_width: int | None = None, bg=(0, 0, 0)):
    """
    Render PNG to terminal using ANSI 256-color grayscale.

    Supports:
      - PNG bit depth 8
      - non-interlaced
      - color types 0,2,4,6

    Uses '▀' where FG is top pixel and BG is bottom pixel.
    """
    _enable_windows_vt_mode()

    w, h, ctype, pix = _read_png_8bit_noninterlaced(path)

    term_cols = shutil.get_terminal_size((80, 24)).columns
    if max_width is None:
        max_width = max(10, term_cols - 1)

    target_w = min(w, max_width)
    scale = target_w / w
    target_h = max(1, int(h * scale))
    if target_h % 2 == 1:
        target_h += 1

    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    if target_w != w or target_h != h:
        pix = _nearest_resize(w, h, pix, bpp, target_w, target_h)
        w, h = target_w, target_h

    bg_r, bg_g, bg_b = bg
    bg_l = (bg_r * 299 + bg_g * 587 + bg_b * 114) // 1000

    def gray_at(x, y):
        i = (y * w + x) * bpp
        if ctype == 0:  # G
            return pix[i]
        if ctype == 2:  # RGB
            r, g, b = pix[i], pix[i + 1], pix[i + 2]
            return (r * 299 + g * 587 + b * 114) // 1000
        if ctype == 4:  # GA
            g, a = pix[i], pix[i + 1]
            if a == 255:
                return g
            if a == 0:
                return bg_l
            return (g * a + bg_l * (255 - a)) // 255
        if ctype == 6:  # RGBA
            r, g, b, a = pix[i], pix[i + 1], pix[i + 2], pix[i + 3]
            lum = (r * 299 + g * 587 + b * 114) // 1000
            if a == 255:
                return lum
            if a == 0:
                return bg_l
            return (lum * a + bg_l * (255 - a)) // 255
        raise AssertionError("unreachable")

    reset = "\x1b[0m"
    lines = []
    for y in range(0, h, 2):
        line = []
        for x in range(w):
            top = _gray_to_ansi256(gray_at(x, y))
            bot = _gray_to_ansi256(gray_at(x, y + 1))
            line.append(f"\x1b[38;5;{top}m\x1b[48;5;{bot}m▀")
        line.append(reset)
        lines.append("".join(line))

    print("\n".join(lines))
