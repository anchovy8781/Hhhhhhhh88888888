import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cs2_ilsan"))
import geom as G  # noqa: E402


def normals(mesh, start=0):
    return [G.face_normal(mesh.verts, f) for f in mesh.faces[start:]]


def unit(v):
    n = sum(c * c for c in v) ** 0.5
    return tuple(c / n for c in v)


class PrimitiveOrientationTest(unittest.TestCase):
    """닫힌 조각은 모두 바깥을 향해야 한다 (CS2 는 뒷면을 그리지 않는다)"""

    def check(self, build):
        m = G.Mesh()
        build(m)
        self.assertGreater(G.signed_volume(m.verts, m.faces), 0)

    def test_primitives(self):
        self.check(lambda m: m.box(0, 2, 0, 1, 0, 3, "a"))
        self.check(lambda m: m.box(2, 0, 1, 0, 3, 0, "a"))           # 뒤집힌 인자
        self.check(lambda m: m.cylinder(0, 0, 1, 0, 2, "a"))
        self.check(lambda m: m.cone(0, 0, 1, 0, 2, "a"))
        self.check(lambda m: m.cylinder_x(0, 3, 0, 0, 0.5, "a"))
        self.check(lambda m: m.ellipsoid(0, 0, 0, 2, 1, 0.5, "a"))
        self.check(lambda m: m.beam((0, 0, 0), (3, 1, 2), 0.2, 0.3, "a"))
        self.check(lambda m: m.beam((0, 0, 0), (0, 0, 2), 0.2, 0.3, "a"))  # 수직
        self.check(lambda m: m.slab([(0, 0, 1), (4, 0, 1), (4, 3, 2), (0, 3, 2)], 0.1, "a"))
        self.check(lambda m: m.slab([(0, 0, 1), (0, 3, 2), (4, 3, 2), (4, 0, 1)], 0.1, "a"))  # 시계 방향 입력
        for off in ((0.2, 0, 0), (-0.2, 0, 0)):
            self.check(lambda m: m.tri_prism((0, 0, 0), (0, 4, 0), (0, 2, 2), off, "a"))
        f = G.Facade(G.Mesh(), "left", -5, 5, -3, 3)
        f.disc(1, 1, 0, 0.3, 0.05, "a")
        self.assertGreater(G.signed_volume(f.m.verts, f.m.faces), 0)

    def test_attached_box_faces_still_outward(self):
        m = G.Mesh()
        m.box(0, 1, 0, 1, 0, 1, "a", skip=(G.BACK,))
        self.assertEqual(len(m.faces), 5)
        for n in normals(m):
            c = [sum(m.verts[i][k] for i in f) / len(f) for f in [m.faces[0]] for k in range(3)]
        center = (0.5, 0.5, 0.5)
        for f in m.faces:
            fc = [sum(m.verts[i][k] for i in f) / len(f) for k in range(3)]
            n = G.face_normal(m.verts, f)
            self.assertGreater(sum((fc[k] - center[k]) * n[k] for k in range(3)), 0)


class FacadeTest(unittest.TestCase):
    SIDES = {"front": (0, -1, 0), "back": (0, 1, 0), "left": (-1, 0, 0), "right": (1, 0, 0)}

    def facade(self, side):
        return G.Facade(G.Mesh(), side, -6, 6, -4, 4, [])

    def test_wall_quads_face_out_and_leave_holes(self):
        for side, out in self.SIDES.items():
            f = self.facade(side)
            self.assertTrue(f.window(3, 1.0, 1.6, 1.2))
            n0 = len(f.m.faces)
            f.walls([(0.0, 3.0, "wall")])
            wall = [i for i in range(n0, len(f.m.faces)) if f.m.mat_names[f.m.mats[i]] == "wall"]
            area = 0.0
            for i in wall:
                nx, ny, nz = G.face_normal(f.m.verts, f.m.faces[i])
                self.assertGreater(nx * out[0] + ny * out[1] + nz * out[2], 0, side)
                area += (nx * nx + ny * ny + nz * nz) ** 0.5 / 2  # 뉴웰 법선 크기 = 2 x 넓이
            self.assertAlmostEqual(area, f.width * 3.0 - 1.6 * 1.2, places=6)

    def test_reveals_face_into_hole(self):
        f = self.facade("front")
        f.window(3, 1.0, 1.6, 1.2, recess=0.15)
        n0 = len(f.m.faces)
        f.walls([(0.0, 3.0, "wall")])
        cu, cz, cd = 3.0, 1.6, -0.075               # 개구부 안쪽 중심
        cx, cy = f.xy(cu, cd)
        for i in range(n0, len(f.m.faces)):
            if f.m.mat_names[f.m.mats[i]] != "reveal":
                continue
            fc = [sum(f.m.verts[j][k] for j in f.m.faces[i]) / 4 for k in range(3)]
            n = G.face_normal(f.m.verts, f.m.faces[i])
            to_center = (cx - fc[0], cy - fc[1], cz - fc[2])
            self.assertGreater(sum(a * b for a, b in zip(n, to_center)), 0)

    def test_window_skips_when_occupied(self):
        f = self.facade("front")
        self.assertTrue(f.window(3, 1.0, 1.6, 1.2))
        self.assertFalse(f.window(3.5, 1.2, 1.6, 1.2))      # 겹침 -> 만들지 않음
        self.assertTrue(f.window(6, 1.0, 1.6, 1.2))
        self.assertFalse(f.window(11.5, 1.0, 1.6, 1.2))     # 모서리 밖
        self.assertEqual(G.conflicts(f.slots), [])

    def test_storefront_mullions_avoid_doors(self):
        f = self.facade("front")
        f.storefront(0.5, 11.5, 0.03, 3.3, bay=1.25, doors=[(6.0, 1.8)])
        frames = []
        for i, face in enumerate(f.m.faces):
            if f.m.mat_names[f.m.mats[i]] != "frame":
                continue
        # 문 폭 안(문틀 제외)에 세로 멀리언(높이가 문 높이에 걸친 0.08 폭 frame)이 없어야 한다
        door_u0, door_u1 = 6.0 - 0.9, 6.0 + 0.9
        verts = f.m.verts
        for i, face in enumerate(f.m.faces):
            if f.m.mat_names[f.m.mats[i]] != "frame":
                continue
            xs = [verts[j][0] for j in face]
            zs = [verts[j][2] for j in face]
            u0, u1 = min(xs) + 6, max(xs) + 6
            if abs((u1 - u0) - 0.08) < 1e-6 and max(zs) - min(zs) > 1.5 and min(zs) < 2.0:
                self.assertFalse(door_u0 < (u0 + u1) / 2 < door_u1, (u0, u1))

    def test_door_inside_storefront_must_fit(self):
        f = self.facade("front")
        with self.assertRaises(ValueError):
            f.storefront(0.5, 4.0, 0.03, 3.3, doors=[(3.9, 1.8)])

    def test_band_splits_around_sign_and_windows(self):
        f = self.facade("front")
        f.reserve(G.SIGN, 2, 8, 3.3, 4.5, 0, 0.35, "sign")
        f.window(10, 3.6, 1.0, 1.0)
        n = f.band(3.9, 4.1, 0.1, "trim")
        self.assertEqual(n, 3)
        self.assertEqual(G.conflicts(f.slots), [])

    def test_clash_rules(self):
        S = G.Slot
        win = S("front", G.OPENING, 0, 2, 1, 2, -0.15, 0.06)
        ac = S("front", G.FIXTURE, 1.5, 2.5, 0.5, 1.2, 0.2, 0.6)        # 창 앞을 가림
        rail = S("front", G.FOREGROUND, -1, 5, 0, 1.1, 1.0, 1.1)         # 발코니 난간
        sign = S("front", G.SIGN, 0, 4, 2.5, 3.0, 0, 0.3)
        slab = S("front", G.FIXTURE, 0, 4, 2.8, 3.0, 0, 1.2)             # 간판을 관통
        other_side = S("left", G.FIXTURE, 0, 4, 2.8, 3.0, 0, 1.2)
        self.assertTrue(G.clash(win, ac))
        self.assertFalse(G.clash(win, rail))
        self.assertTrue(G.clash(sign, slab))
        self.assertFalse(G.clash(sign, other_side))


if __name__ == "__main__":
    unittest.main()
