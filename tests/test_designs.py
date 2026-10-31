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
            if b.zones:                                      # 벽 있는 건물 (천막 · 광장 · 소품 제외)
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
            wall_mats = {z[2] for zones in b.zones.values() for z in zones}
            vols = [(b.x0, b.x1, b.y0, b.y1, 0.0, b.height)] + list(b.vols.values())
            checked = 0
            for fi, f in enumerate(b.m.faces):
                mat = b.m.mat_names[b.m.mats[fi]]
                n = G.face_normal(b.m.verts, f)
                c = [sum(b.m.verts[i][k] for i in f) / len(f) for k in range(3)]
                if mat not in wall_mats or abs(n[2]) > 1e-9:
                    continue
                for x0, x1, y0, y1, z0, z1 in vols:          # 그 면이 놓인 몸체의 중심에서 바깥을 향해야 한다
                    inside = x0 - 1e-6 <= c[0] <= x1 + 1e-6 and y0 - 1e-6 <= c[1] <= y1 + 1e-6 and z0 <= c[2] < z1
                    on_shell = (abs(c[0] - x0) < 1e-6 or abs(c[0] - x1) < 1e-6 or
                                abs(c[1] - y0) < 1e-6 or abs(c[1] - y1) < 1e-6)
                    if inside and on_shell:
                        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                        self.assertGreater(n[0] * (c[0] - cx) + n[1] * (c[1] - cy), 0, (name, mat, c))
                        checked += 1
                        break
                if mat == "roof":
                    self.assertGreater(n[2], 0, (name, c))
            if b.zones:
                self.assertGreater(checked, 4, name)

    def test_variety(self):
        kinds = {v[2] for v in catalog.ASSETS.values()}
        self.assertGreaterEqual(len(kinds), 20)
        heights = sorted(round(b.top) for name, (b, _) in self.built.items() if catalog.TYPE[name] == "building")
        self.assertGreater(heights[-1] - heights[0], 60)     # 단층 천막부터 19층 호텔까지

    def test_multi_volume_hotel(self):
        b, _ = self.built["IlsanTanibayHotel"]
        self.assertEqual(set(b.vols), {"tower", "core"})
        self.assertGreater(b.top, 70)
        keys = {s.side for s in b.slots}
        self.assertTrue({"front", "tower:front", "tower:left", "core:back"} <= keys)
        rooms = [s for s in b.slots if s.name == "rooms"]
        self.assertEqual(len(rooms), 1)
        self.assertGreater(rooms[0].d1, 0.5)                  # 세로 핀이 개구부 예약 깊이에 포함

    def test_real_brand_details(self):
        """실제 브랜드 매장: 드라이브스루 픽업 창은 운전석(왼쪽) 쪽 면, 주문판은 뒤, 테라스파크는 층마다 3 m 물러남,
        모퉁이 상가 1층은 실제 편의점 브랜드"""
        sb, _ = self.built["IlsanStarbucksDT"]
        pickup = [s for s in sb.slots if s.name == "pickup"]
        self.assertEqual([s.side for s in pickup], ["left"])
        self.assertTrue(any(s.name == "menu_board" and s.side == "back" for s in sb.slots))
        for name in ("IlsanTerracePark01", "IlsanTerracePark02"):
            b, _ = self.built[name]
            fronts = [b.y0] + [b.vols[k][2] for k in ("f2", "f3", "f4")]
            self.assertEqual([round(q - p, 3) for p, q in zip(fronts, fronts[1:])], [3.0, 3.0, 3.0], name)
        signs = {s.name for n in ("IlsanCornerTower01", "IlsanCornerTower02") for s in self.built[n][0].slots}
        self.assertTrue({"sign:CU", "sign:GS25", "sign:MEGA COFFEE", "sign:EDIYA COFFEE"} <= signs)
        gs, _ = self.built["IlsanGasStation"]
        self.assertIn("gs_orange", gs.m.mat_names)
        self.assertGreater(gs.top, 7.0)                       # 가격 기둥 간판
        for name in ("IlsanSikdang153", "IlsanMGBank", "IlsanParisBaguette"):
            self.assertTrue(any(s.kind == G.OPENING for s in self.built[name][0].slots), name)
        hp, _ = self.built["IlsanHomeplus"]
        self.assertTrue(any(s.name == "atrium" for s in hp.slots))
        self.assertGreater(hp.top, 20)

    def test_curtain_wall_has_no_conflicts_with_signs(self):
        """모퉁이 상가: 층마다 간판 띠와 유리가 번갈아 놓이고 서로 겹치지 않는다"""
        for name in ("IlsanCornerTower01", "IlsanCornerTower02"):
            b, _ = self.built[name]
            signs = [s for s in b.slots if s.kind == G.SIGN and s.name.startswith("sign:")]
            glass = [s for s in b.slots if s.kind == G.OPENING and s.name.startswith("cw_")]
            self.assertGreaterEqual(len(signs), 12, name)
            self.assertEqual(len(glass), 12, name)
            self.assertEqual(G.conflicts(signs + glass), [], name)

    def test_real_logos_on_brand_signs(self):
        """로고 파일이 있으면 브랜드 간판 문구 자리에 실제 로고(색별 letters_logo_* 재질)가 붙는다.
        테스트용 로고는 허용 크기를 꽉 채우므로 어떤 비율의 로고도 다른 요소와 겹치지 않는다 (setUpClass 의 검사)"""
        expect = {"IlsanGS25": "gs25", "IlsanCU": "cu", "IlsanHomeplus": "homeplus", "IlsanStarbucksDT": "starbucks",
                  "IlsanParisBaguette": "parisbaguette", "IlsanOliveDaiso": "daiso", "IlsanGasStation": "gscaltex",
                  "IlsanMGBank": "mg", "IlsanShop01": "7eleven", "IlsanCornerTower01": "megacoffee",
                  "IlsanTerracePark01": "angelinus", "IlsanTerracePark02": "droptop"}
        for name, key in expect.items():
            mats = self.built[name][0].m.mat_names
            self.assertTrue(any(m.startswith(f"letters_logo_{key}_") for m in mats), name)
        bare = self.built["IlsanCrab01"][0].m.mat_names            # 브랜드가 아닌 가게는 글자 그대로
        self.assertFalse(any(m.startswith("letters_logo_") for m in bare))


if __name__ == "__main__":
    unittest.main()
