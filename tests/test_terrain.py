import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ulsan_ilsan"))
import terrain as T  # noqa: E402


class GridTest(unittest.TestCase):
    def test_upsample_keeps_corners_and_shape(self):
        a = np.arange(12, dtype=np.float32).reshape(3, 4)
        u = T.upsample(a, 3)
        self.assertEqual(u.shape, (7, 10))
        self.assertEqual(u[0, 0], a[0, 0])
        self.assertEqual(u[-1, -1], a[-1, -1])
        self.assertAlmostEqual(float(u[3, 0]), float(a[1, 0]))

    def test_distance_to(self):
        mask = np.zeros((5, 7), dtype=bool)
        mask[2, 0] = True
        d = T.distance_to(mask, 10.0, 10.0)
        self.assertEqual(d[2, 0], 0)
        self.assertAlmostEqual(d[2, 6], 60.0)
        self.assertAlmostEqual(d[0, 0], 20.0)

    def test_seabed_deepens_offshore(self):
        h = np.zeros((1, 6), dtype=np.float32)
        h[0, 0] = 5.0
        z = T.seabed(h, 30.0, 30.0)
        self.assertEqual(z[0, 0], 5.0)
        self.assertTrue(np.all(z[0, 1:] < 0))
        self.assertTrue(np.all(np.diff(z[0, 1:]) < 0))


class IlsanDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = T.Dem.load()
        cls.dem = T.prepare(cls.raw, 3)
        cls.cls, cls.coast = T.classify(cls.dem)

    def test_projection_is_centered(self):
        x0, x1, y0, y1 = self.raw.extent()
        self.assertAlmostEqual(x0, -x1, places=6)
        self.assertTrue(3000 < x1 - x0 < 4000)  # 동서 약 3.6 km
        self.assertTrue(2500 < y1 - y0 < 3000)  # 남북 약 2.7 km

    def test_landmarks_match_terrain(self):
        self.assertGreater(self.raw.sample(*T.LANDMARKS["울기등대"]), 30)   # 등대는 언덕 위
        self.assertGreater(self.raw.sample(*T.LANDMARKS["일산해수욕장"]), 0)
        # 일산만 한가운데는 바다
        self.assertLessEqual(self.raw.sample(35.4975, 129.4370), 0)

    def test_classes_present(self):
        counts = np.bincount(self.cls.ravel(), minlength=len(T.CLASS_NAMES))
        for k in (T.SEA, T.BEACH, T.ROCK, T.PARK_FOREST, T.URBAN):
            self.assertGreater(counts[k], 100, T.CLASS_NAMES[k])

    def test_beach_is_next_to_sea(self):
        self.assertTrue(np.all(self.coast[self.cls == T.BEACH] < 70))

    def test_buildings_avoid_sea(self):
        lots = T.building_lots(self.cls, self.coast, self.dem)
        self.assertGreater(len(lots), 100)
        self.assertTrue(np.all(lots[:, 2] > 0))


if __name__ == "__main__":
    unittest.main()
