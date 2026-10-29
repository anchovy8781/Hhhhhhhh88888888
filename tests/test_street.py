import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ulsan_ilsan"))
import street as S  # noqa: E402
import terrain as T  # noqa: E402


class PolylineTest(unittest.TestCase):
    def test_resample_spacing(self):
        poly = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]])
        r = S.resample(poly, 2.0)
        self.assertEqual(len(r), 11)
        np.testing.assert_allclose(np.linalg.norm(np.diff(r, axis=0), axis=1), 2.0)

    def test_normals_point_right(self):
        poly = np.array([[0.0, 0.0], [0.0, -1.0], [0.0, -2.0]])  # 남쪽으로 진행
        np.testing.assert_allclose(S.normals(poly), [[-1, 0]] * 3, atol=1e-12)  # 오른쪽 = 서쪽


class IlsanStreetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dem = T.prepare(T.Dem.load(), 3)
        cls.st = S.Street(cls.dem)

    def test_beach_length(self):
        # 일산해수욕장 백사장은 약 850 m. 추적 구간은 그 대부분
        self.assertTrue(500 < self.st.length < 900, self.st.length)

    def test_normals_point_inland(self):
        for i in range(0, len(self.st.poly), 40):
            land = self.st.poly[i] + self.st.n[i] * 80
            sea = self.st.poly[i] - self.st.n[i] * 80
            self.assertGreater(self.dem.sample(*S.Street.latlon(self.dem, *land)),
                               self.dem.sample(*S.Street.latlon(self.dem, *sea)))

    def test_road_above_sea(self):
        self.assertTrue(np.all(self.st.road_z >= 3.0))

    def test_strip_faces_up(self):
        v, f = self.st.strip(S.PROMENADE_END, S.ROAD_END, 0.0, 0.0)
        a, b, c = v[f[0, 0]], v[f[0, 1]], v[f[0, 2]]
        self.assertGreater(np.cross(b - a, c - b)[2], 0)

    def test_project_roundtrip(self):
        (x, y), n, _ = self.st.frame(self.st.length / 2, 30.0)
        s, d, interior = self.st.project(np.array([[x, y]]))
        self.assertAlmostEqual(s[0], self.st.length / 2, delta=1.0)
        self.assertAlmostEqual(d[0], 30.0, delta=0.5)
        self.assertTrue(interior[0])


class LotTest(unittest.TestCase):
    def test_lots_do_not_overlap(self):
        lots, alleys = S.lay_lots(600.0, seed=3)
        self.assertGreater(len(lots), 20)
        self.assertGreater(len(alleys), 3)
        for a, b in zip(lots, lots[1:]):
            self.assertLessEqual(a["s1"], b["s0"])
        for s in alleys:
            self.assertFalse(any(l["s0"] < s < l["s1"] for l in lots))
        self.assertTrue(all(l["s1"] <= 600 - 12 for l in lots))


if __name__ == "__main__":
    unittest.main()
