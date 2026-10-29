"""건물 디자인 검사: 문 · 창 · 간판 · 설비 겹침 없음, 옥상 설비 충돌 없음, 부지 이탈 없음, 재질 정의 완비."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cs2_ilsan"))
import catalog  # noqa: E402
import designs as D  # noqa: E402
import geom as G  # noqa: E402


class DesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = {name: fn(D.stub_text) for name, fn in D.DESIGNS.items()}

    def test_catalog_matches_designs(self):
        self.assertEqual(set(D.DESIGNS), set(catalog.ASSETS))
        for name, (b, _) in self.built.items():
            self.assertEqual(b.lot, tuple(catalog.ASSETS[name][:2]), name)

    def test_no_overlaps_and_inside_lot(self):
        for name, (b, _) in self.built.items():
            report = D.validate(b)
            self.assertEqual(report["facade"], [], name)
            self.assertEqual(report["roof"], [], name)
            self.assertEqual(report["outside_lot"], 0, name)
            self.assertEqual(report["missing_materials"], [], name)

    def test_openings_are_cut_into_walls(self):
        for name, (b, _) in self.built.items():
            holes = [s for s in b.slots if s.kind == G.OPENING and s.recess > 0]
            if name != "IlsanGrill01":                       # 조개구이는 벽 없는 천막 구조
                self.assertGreater(len(holes), 4, name)
            self.assertIn("reveal", b.m.mat_names if holes else ["reveal"], name)

    def test_storefront_doors_have_no_mullion_through_them(self):
        for name, (b, _) in self.built.items():
            stores = [s for s in b.slots if s.kind == G.OPENING and s.name in ("storefront", "pharmacy", "snack")]
            for s in stores:
                self.assertGreater(s.recess, 0.1, name)

    def test_walls_face_outward_and_roofs_up(self):
        """CS2 는 뒷면을 그리지 않는다: 바깥벽은 건물 밖을, 지붕면은 위를 향해야 한다"""
        for name, (b, _) in self.built.items():
            wall_mats = {m for zones in b.zones.values() for (_, _, m) in zones}
            cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
            checked = 0
            for fi, f in enumerate(b.m.faces):
                mat = b.m.mat_names[b.m.mats[fi]]
                n = G.face_normal(b.m.verts, f)
                c = [sum(b.m.verts[i][k] for i in f) / len(f) for k in range(3)]
                on_shell = (abs(c[0] - b.x0) < 1e-6 or abs(c[0] - b.x1) < 1e-6 or
                            abs(c[1] - b.y0) < 1e-6 or abs(c[1] - b.y1) < 1e-6)
                if mat in wall_mats and on_shell and abs(n[2]) < 1e-9 and c[2] < b.height:
                    self.assertGreater(n[0] * (c[0] - cx) + n[1] * (c[1] - cy), 0, (name, mat, c))
                    checked += 1
                if mat == "roof":
                    self.assertGreater(n[2], 0, (name, c))
            if b.zones:
                self.assertGreater(checked, 4, name)

    def test_variety(self):
        kinds = {v[2] for v in catalog.ASSETS.values()}
        self.assertGreaterEqual(len(kinds), 12)
        heights = sorted(round(b.top) for b, _ in self.built.values())
        self.assertGreater(heights[-1] - heights[0], 15)     # 단층 천막부터 7층 호텔까지


if __name__ == "__main__":
    unittest.main()
