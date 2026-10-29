import json
import os
import struct
import sys
import tempfile
import unittest
import zlib

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "ulsan_ilsan"))
sys.path.insert(0, os.path.join(ROOT, "cs2_ilsan"))
import catalog  # noqa: E402
import heightmap as H  # noqa: E402
import placement as P  # noqa: E402
import pngio  # noqa: E402
import street as S  # noqa: E402
import terrain as T  # noqa: E402


def read_png(path):
    """테스트용 최소 PNG 디코더 (필터 0 만)"""
    data = open(path, "rb").read()
    pos, idat, ihdr = 8, b"", None
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    w, h, depth, ctype = ihdr[:4]
    ch = {0: 1, 2: 3, 6: 4}[ctype]
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(h, -1)
    assert np.all(raw[:, 0] == 0)
    px = raw[:, 1:]
    if depth == 16:
        return px.copy().view(">u2").reshape(h, w, ch) if ch > 1 else px.copy().view(">u2").reshape(h, w)
    return px.reshape(h, w, ch)


class PngTest(unittest.TestCase):
    def test_gray16_roundtrip(self):
        a = (np.arange(12, dtype=np.uint32).reshape(3, 4) * 5000).astype(np.uint16)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.png")
            pngio.write_gray16(p, a)
            np.testing.assert_array_equal(read_png(p), a)

    def test_rgb8_roundtrip(self):
        a = np.random.default_rng(0).integers(0, 255, (5, 6, 4), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.png")
            pngio.write_rgb8(p, a)
            np.testing.assert_array_equal(read_png(p), a)

    def test_srgb(self):
        np.testing.assert_allclose(pngio.linear_to_srgb(np.array([0.0, 0.2140, 1.0])), [0, 0.5, 1], atol=1e-3)


class HeightTest(unittest.TestCase):
    def test_height_encoding(self):
        h = np.array([[-H.SEA_LEVEL, 0.0, 100.0]])
        v = H.to_u16(h).astype(np.int64)
        self.assertEqual(v[0, 0], 0)
        self.assertAlmostEqual(v[0, 1] / 65535 * H.HEIGHT_SCALE, H.SEA_LEVEL, delta=0.1)
        self.assertAlmostEqual(v[0, 2] / 65535 * H.HEIGHT_SCALE, H.SEA_LEVEL + 100, delta=0.1)

    def test_world_contains_play(self):
        self.assertAlmostEqual(H.WORLD_SIZE / H.PLAY_SIZE, 4.0)

    def test_sample_grid_synthetic(self):
        # 동서로 경사진 가짜 타일: 샘플 결과도 동쪽으로 갈수록 높아야 한다
        tile = np.tile(np.linspace(1, 100, 3600, dtype=np.float32), (3600, 1))
        out = H.sample_grid(tile, 35.5, 129.5, 2000.0, 64)
        self.assertEqual(out.shape, (64, 64))
        self.assertTrue(np.all(np.diff(out[10]) > 0))
        self.assertTrue(np.allclose(out[:, 5], out[0, 5]))


class PlacementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dem = T.prepare(T.Dem.load(), 3)
        cls.dem = dem
        cls.st = S.Street(dem)
        _, alleys = S.lay_lots(cls.st.length)
        cls.items = P.plan(cls.st, alleys)

    def test_lots_are_cell_sized_rectangles(self):
        for it in self.items:
            cw, cd = catalog.ASSETS[it["asset"]][:2]
            c = it["corners"]
            self.assertAlmostEqual(np.linalg.norm(c[1] - c[0]), cw * catalog.CELL, places=3)
            self.assertAlmostEqual(np.linalg.norm(c[3] - c[0]), cd * catalog.CELL, places=3)

    def test_no_overlaps(self):
        c = [it["corners"] for it in self.items]
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                self.assertFalse(P.overlaps(c[i], c[j]), (i, j))

    def test_lots_face_the_road_and_stay_on_land(self):
        for it in self.items:
            front_mid = (it["corners"][0] + it["corners"][1]) / 2
            back_mid = (it["corners"][2] + it["corners"][3]) / 2
            s_f, d_f, _ = self.st.project(front_mid[None])
            s_b, d_b, _ = self.st.project(back_mid[None])
            self.assertLess(d_f[0], d_b[0])                 # 앞이 바다(도로) 쪽
            self.assertAlmostEqual(d_f[0], P.ROAD_CENTER + P.ROAD_HALF, delta=1.0)
            lat, lon = S.Street.latlon(self.dem, *back_mid)
            self.assertGreater(self.dem.sample(lat, lon), 0)

    def test_mix_of_assets(self):
        used = {it["asset"] for it in self.items}
        self.assertEqual(used, set(catalog.ASSETS))


if __name__ == "__main__":
    unittest.main()
