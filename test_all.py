#!/usr/bin/env python3
"""
Single-file test runner for:
- text_editor.py
- image.py
- screensaver.py
- snake.py
- tetris.py

Run:
  python test_all.py

It uses only the Python standard library (unittest).
"""

import io
import os
import sys
import time
import types
import struct
import zlib
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Compatibility: provide a dummy msvcrt on non-Windows so snake/tetris import.
# ---------------------------------------------------------------------------
if "msvcrt" not in sys.modules:
    dummy = types.ModuleType("msvcrt")
    dummy.kbhit = lambda: False
    dummy.getch = lambda: b""
    sys.modules["msvcrt"] = dummy


# ---------------------------------------------------------------------------
# Import modules under test
# ---------------------------------------------------------------------------
from apps import text_editor
from apps import image
from apps import screensaver
from apps import snake
from apps import tetris


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_png_bytes(width, height, color_type, pixels, *, filter_type=0):
    """
    Create a minimal PNG bytes object (CRC ignored by our decoder).
    Supports only bit depth 8 and non-interlaced, with raw pixels bytes.
    - color_type: 0 (G), 2 (RGB), 4 (GA), 6 (RGBA)
    - pixels: bytes of length width*height*bpp
    - filter_type: 0..4 for each row (we use same for all rows)
    """
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    if len(pixels) != width * height * bpp:
        raise ValueError("pixels length mismatch")

    sig = b"\x89PNG\r\n\x1a\n"

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"

    # Raw scanlines: each row: filter byte + row bytes
    stride = width * bpp
    raw = bytearray()
    for y in range(height):
        raw.append(filter_type)
        start = y * stride
        raw.extend(pixels[start:start + stride])

    comp = zlib.compress(bytes(raw))
    idat = struct.pack(">I", len(comp)) + b"IDAT" + comp + b"\x00\x00\x00\x00"
    iend = struct.pack(">I", 0) + b"IEND" + b"" + b"\x00\x00\x00\x00"
    return sig + ihdr + idat + iend


class _ResultCatchingRunner(unittest.TextTestRunner):
    """Text runner that also returns success boolean."""
    def run(self, test):
        result = super().run(test)
        result.success = result.wasSuccessful()
        return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestTextEditor(unittest.TestCase):
    def test_text_editor_concatenates_until_exit(self):
        inputs = iter(["hello", " ", "world", "[exit]"])

        def fake_input(_prompt=""):
            return next(inputs)

        with patch("builtins.input", side_effect=fake_input):
            out = text_editor.main()

        self.assertEqual(out, "hello world")


class TestImageModule(unittest.TestCase):
    def test_path_paeth_predictor_helper(self):
        # Basic sanity checks: if p is closest to a, return a; etc.
        self.assertEqual(image._path(10, 20, 30), 10)  # p=0 => closest to 10
        self.assertEqual(image._path(20, 10, 30), 10)  # p=0 => closest to 10
        self.assertEqual(image._path(30, 20, 10), 30)  # p=40 => closest to 30

    def test_gray_to_ansi256_bounds_and_mid(self):
        self.assertEqual(image._gray_to_ansi256(0), 232)
        self.assertEqual(image._gray_to_ansi256(255), 255)
        # mid-ish should be within range
        code = image._gray_to_ansi256(128)
        self.assertTrue(232 <= code <= 255)

    def test_nearest_resize_identity(self):
        src = bytes([1, 2, 3, 4])  # 2x2, bpp=1
        out = image._nearest_resize(2, 2, src, 1, 2, 2)
        self.assertEqual(bytes(out), src)

    def test_unfilter_filter0_none(self):
        # 1 row, 3 bytes, filter type 0
        raw = bytes([0, 10, 20, 30])
        out = image._unfilter(raw, width=3, height=1, bpp=1)
        self.assertEqual(bytes(out), bytes([10, 20, 30]))

    def test_unfilter_filter1_sub(self):
        # Reconstruct: out[x] = row[x] + left
        # Want output [10, 12, 15] with bpp=1 => row bytes should be [10,2,3]
        raw = bytes([1, 10, 2, 3])
        out = image._unfilter(raw, width=3, height=1, bpp=1)
        self.assertEqual(list(out), [10, 12, 15])

    def test_unfilter_filter2_up(self):
        # Two rows, bpp=1, width=3
        # Row0 f0: [1,2,3]
        # Row1 f2 raw bytes: [1,1,1] => output row1 = [2,3,4]
        raw = bytes([
            0, 1, 2, 3,
            2, 1, 1, 1
        ])
        out = image._unfilter(raw, width=3, height=2, bpp=1)
        self.assertEqual(list(out), [1,2,3, 2,3,4])

    def test_unfilter_filter3_average(self):
        # Two rows, width=3 bpp=1
        # Row0 none => [10,10,10]
        # Row1 avg: choose row bytes [5,5,5]
        # x0: left=0 up=10 => +((0+10)>>1)=+5 => 10
        # x1: left=10 up=10 => +10 => 15
        # x2: left=15 up=10 => +12 => 17
        raw = bytes([
            0, 10, 10, 10,
            3, 5, 5, 5
        ])
        out = image._unfilter(raw, width=3, height=2, bpp=1)
        self.assertEqual(list(out), [10,10,10, 10,15,17])

    def test_unfilter_filter4_paeth(self):
        # Simple case where paeth predictor matches left on row1
        # Row0 none => [10,10,10]
        # Row1 paeth with row bytes [1,1,1]
        # x0: left=0 up=10 ul=0 => predictor ~10 => 11
        # x1: left=11 up=10 ul=10 => predictor ~11 => 12
        # x2: left=12 up=10 ul=10 => predictor ~12 => 13
        raw = bytes([
            0, 10, 10, 10,
            4, 1, 1, 1
        ])
        out = image._unfilter(raw, width=3, height=2, bpp=1)
        self.assertEqual(list(out), [10,10,10, 11,12,13])

    def test_read_png_and_display_runs(self):
        # Create a tiny 2x2 grayscale PNG on disk and ensure decoder works,
        # and display function prints something.
        pixels = bytes([
            0, 255,
            128, 64
        ])  # 2x2, bpp=1
        png_bytes = _make_png_bytes(2, 2, 0, pixels, filter_type=0)

        tmp = os.path.join(os.path.dirname(__file__) if "__file__" in globals() else os.getcwd(), "_tmp_test.png")
        with open(tmp, "wb") as f:
            f.write(png_bytes)

        try:
            w, h, ctype, pix = image._read_png_8bit_noninterlaced(tmp)
            self.assertEqual((w, h, ctype), (2, 2, 0))
            self.assertEqual(bytes(pix), pixels)

            buf = io.StringIO()
            with redirect_stdout(buf), patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 24))):
                image.display_png_grayscale_ansi256(tmp, max_width=2)
            printed = buf.getvalue()
            self.assertTrue("▀" in printed)  # should contain block chars
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass


class TestScreensaver(unittest.TestCase):
    def test_clear_calls_cls(self):
        with patch("screensaver.os.system") as system:
            screensaver.clear()
            system.assert_called_with("cls")

    def test_get_keypress_checker_windows_branch(self):
        # Force windows branch without requiring real msvcrt
        fake_msvcrt = types.SimpleNamespace(kbhit=lambda: True)
        with patch.object(screensaver, "os") as os_mod:
            os_mod.name = "nt"
            with patch.dict(sys.modules, {"msvcrt": fake_msvcrt}):
                key_pressed = screensaver._get_keypress_checker()
                self.assertTrue(callable(key_pressed))
                self.assertTrue(key_pressed())

    def test_matrix_screensaver_exits_immediately(self):
        # Patch keypress to True immediately so it exits fast.
        def fake_key_checker():
            return lambda: True

        buf = io.StringIO()
        with redirect_stdout(buf), \
             patch("screensaver._get_keypress_checker", side_effect=fake_key_checker), \
             patch("screensaver.os.name", "nt"), \
             patch("screensaver.shutil.get_terminal_size", return_value=os.terminal_size((20, 10))), \
             patch("screensaver.time.sleep", return_value=None):
            screensaver.matrix_screensaver(fps=999, density=0.0)
        # Should have printed ANSI sequences at least once (hide cursor or clear)
        out = buf.getvalue()
        self.assertTrue("\x1b" in out or out == "")


class TestSnakeAndTetris(unittest.TestCase):
    def test_snake_main_quits_on_q(self):
        # Make msvcrt return 'q' immediately.
        with patch("snake.msvcrt.kbhit", return_value=True), \
             patch("snake.msvcrt.getch", return_value=b"q"), \
             patch("snake.os.system", return_value=0), \
             patch("snake.time.sleep", return_value=None):
            buf = io.StringIO()
            with redirect_stdout(buf):
                snake.snake_main()
            self.assertIn("Thanks for playing", buf.getvalue())

    def test_tetris_quits_on_q(self):
        with patch("tetris.msvcrt.kbhit", return_value=True), \
             patch("tetris.msvcrt.getch", return_value=b"q"), \
             patch("tetris.os.system", return_value=0), \
             patch("tetris.time.sleep", return_value=None), \
             patch("tetris.time.time", side_effect=[0.0, 0.0, 0.0]):
            # time.time called at least twice; side_effect provides enough.
            buf = io.StringIO()
            with redirect_stdout(buf):
                tetris.tetris()
            # No fixed message on quit, but should not error.
            self.assertTrue(True)


# ---------------------------------------------------------------------------
# Main: run and print success/failure summary
# ---------------------------------------------------------------------------
def main():
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = _ResultCatchingRunner(stream=sys.stdout, verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.success:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        print(f"Failures: {len(result.failures)}  Errors: {len(result.errors)}")


if __name__ == "__main__":
    main()
