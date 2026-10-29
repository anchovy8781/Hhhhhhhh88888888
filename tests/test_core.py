import os
import struct
import sys
import tempfile
import unittest
import zlib

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cs2_asset_tools"))
import core  # noqa: E402


def write_png(path, w, h, bit_depth=8):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    ihdr = struct.pack(">IIBBBBB", w, h, bit_depth, 2, 0, 0, 0)
    row = b"\x00" + b"\x00" * (w * 3 * bit_depth // 8)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b""))


class NamingTest(unittest.TestCase):
    def test_lod_name(self):
        self.assertEqual(core.lod_name("House", 0), "House")
        self.assertEqual(core.lod_name("House", 2), "House_LOD2")

    def test_texture_name(self):
        self.assertEqual(core.texture_name("House", "_MaskMap"), "House_MaskMap.png")
        with self.assertRaises(ValueError):
            core.texture_name("House", "_maskmap")

    def test_lod_ratios(self):
        self.assertEqual(core.lod_ratios(3, 0.5), [0.5, 0.25, 0.125])
        with self.assertRaises(ValueError):
            core.lod_ratios(2, 1.0)


class PackTest(unittest.TestCase):
    def test_maskmap_defaults_and_roughness(self):
        rough = np.full((4, 4, 4), 0.25, dtype=np.float32)
        out = core.pack_maskmap((4, 4), roughness=rough)
        self.assertEqual(out.shape, (4, 4, 4))
        np.testing.assert_allclose(out[0, 0], [0.0, 0.0, 0.0, 0.75])

    def test_maskmap_channels(self):
        metal = np.full((2, 2), 1.0)
        coat = np.full((2, 2), 0.3)
        out = core.pack_maskmap((2, 2), metallic=metal, coat=coat, glossiness=np.full((2, 2), 0.9))
        np.testing.assert_allclose(out[1, 1], [1.0, 0.3, 0.0, 0.9], rtol=1e-6)

    def test_size_mismatch(self):
        with self.assertRaises(ValueError):
            core.pack_maskmap((4, 4), metallic=np.zeros((2, 2)))

    def test_controlmask_overlap(self):
        m1 = np.zeros((2, 2)); m1[0, :] = 1
        m2 = np.zeros((2, 2)); m2[0, 0] = 1; m2[1, 1] = 1
        out = core.pack_controlmask((2, 2), m1, m2)
        self.assertEqual(out.shape, (2, 2, 3))
        self.assertAlmostEqual(core.controlmask_overlap(out), 0.25)


class TextureCheckTest(unittest.TestCase):
    def test_check_textures(self):
        self.assertEqual(core.check_textures({"a": (1024, 1024), "b": (1024, 1024)}), [])
        warnings = core.check_textures({"a": (1024, 512), "b": (1000, 1000)})
        self.assertEqual(len(warnings), 3)  # 비정사각형, 비 2의 거듭제곱, 해상도 불일치

    def test_png_size(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.png")
            write_png(p, 16, 8, 16)
            self.assertEqual(core.png_size(p), (16, 8, 16))
            bad = os.path.join(d, "bad.png")
            with open(bad, "wb") as f:
                f.write(b"nope" * 10)
            with self.assertRaises(ValueError):
                core.png_size(bad)


if __name__ == "__main__":
    unittest.main()
