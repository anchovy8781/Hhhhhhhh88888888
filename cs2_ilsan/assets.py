"""일산지 거리 상가 — 시티즈: 스카이라인 2 건물 에셋 생성기.

    blender -b --python assets.py -- [옵션]
    (또는 bpy 모듈이 있는 파이썬:  python assets.py -- [옵션])

옵션
  --only NAME[,NAME]  일부만 (예: IlsanHoetjip01)
  --tex 2048          텍스처 해상도 (1024/2048/4096)
  --font PATH         간판 한글 폰트 (생략 시 맑은 고딕·애플 SD 고딕·나눔고딕 자동 탐색)
  --out DIR           출력 폴더 (기본 ./CS2Assets) — CS2 Asset Importer 의 Project Root 로 지정
  --preview DIR       미리보기 렌더 저장 폴더 (생략 시 렌더 안 함)
  --no-bake           베이크 생략 (모델만 .blend 로 확인할 때)

에셋마다 <out>/<이름>/ 에
  <이름>.fbx, <이름>_LOD1.fbx, <이름>_LOD2.fbx,
  <이름>_BaseColor/_Normal/_MaskMap/_ControlMask/_Emissive.png
를 만든다. 원점 = 부지 중심 지면, 정면 = 도로 쪽(-Y), 1 단위 = 1 m, 부지는 8 m 셀 단위.
"""

import argparse
import glob
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bake  # noqa: E402
import catalog  # noqa: E402
import kit  # noqa: E402
from kit import BOTTOM, Facade, Mesh, fit_text, text_mesh  # noqa: E402

CELL = 8.0
FONT_CANDIDATES = [
    os.path.join(HERE, "fonts", "*.ttf"), os.path.join(HERE, "fonts", "*.otf"),
    "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/NanumGothicBold.ttf", os.path.expanduser("~/Library/Fonts/NanumGothicBold.ttf"),
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]


# ---------------------------------------------------------------------------
# 공통 건물 골격
# ---------------------------------------------------------------------------

class Building:
    def __init__(self, lot, width, depth, setback=1.2, seed=0):
        self.lot = lot
        self.lw, self.ld = lot[0] * CELL, lot[1] * CELL
        self.m = Mesh()
        self.rng = np.random.default_rng(seed)
        self.x0, self.x1 = -width / 2, width / 2
        self.y0 = -self.ld / 2 + setback
        self.y1 = self.y0 + depth
        self.w, self.d = width, depth
        self.mats = {}

    def face(self, side):
        return Facade(self.m, side, self.x0, self.x1, self.y0, self.y1)

    def lot_slab(self, mat="paving"):
        """부지 바닥 (얇은 판). 건물 아래는 생략하지 않는다 — 게임이 부지를 평탄화한다."""
        hw, hd = self.lw / 2 - 0.05, self.ld / 2 - 0.05
        self.m.box(-hw, hw, -hd, hd, -0.30, 0.03, mat, skip=(BOTTOM,))

    def shell(self, height, front="wall", side="wall_side", roof="roof", base=0.03):
        x0, x1, y0, y1 = self.x0, self.x1, self.y0, self.y1
        z0 = base
        self.m.add([(x0, y0, z0), (x1, y0, z0), (x1, y0, height), (x0, y0, height)], [(0, 1, 2, 3)], front)
        self.m.add([(x1, y0, z0), (x1, y1, z0), (x1, y1, height), (x1, y0, height)], [(0, 1, 2, 3)], side)
        self.m.add([(x1, y1, z0), (x0, y1, z0), (x0, y1, height), (x1, y1, height)], [(0, 1, 2, 3)], side)
        self.m.add([(x0, y1, z0), (x0, y0, z0), (x0, y0, height), (x0, y1, height)], [(0, 1, 2, 3)], side)
        self.m.add([(x0, y0, height), (x1, y0, height), (x1, y1, height), (x0, y1, height)], [(0, 1, 2, 3)], roof)
        self.height = height

    def plinth(self, h=0.45, out=0.06, mat="concrete"):
        for s in ("front", "back", "left", "right"):
            f = self.face(s)
            f.box(-out, f.width + out, 0.03, h, 0, out, mat)

    def bands(self, levels, sides=("front",), mat="trim", h=0.18, out=0.10):
        for s in sides:
            f = self.face(s)
            for z in levels:
                f.box(-out, f.width + out, z - h / 2, z + h / 2, 0, out, mat)

    def parapet(self, h=1.0, t=0.22, mat="wall_side", cap="trim"):
        x0, x1, y0, y1, z = self.x0, self.x1, self.y0, self.y1, self.height
        for (a, b, c, d) in ((x0, x1, y0, y0 + t), (x0, x1, y1 - t, y1), (x0, x0 + t, y0 + t, y1 - t),
                             (x1 - t, x1, y0 + t, y1 - t)):
            self.m.box(a, b, c, d, z, z + h, mat, skip=(BOTTOM,))
        o = 0.05
        for (a, b, c, d) in ((x0 - o, x1 + o, y0 - o, y0 + t + o), (x0 - o, x1 + o, y1 - t - o, y1 + o),
                             (x0 - o, x0 + t + o, y0 + t, y1 - t), (x1 - t - o, x1 + o, y0 + t, y1 - t)):
            self.m.box(a, b, c, d, z + h, z + h + 0.08, cap)

    def rail(self, x0, x1, y0, y1, z, h=1.1, glass=False):
        """옥상·발코니 난간 (사각 둘레 중 지정 구간)"""
        if glass:
            self.m.box(x0, x1, y0, y1, z, z + h, "glass_rail", skip=(BOTTOM,))
            self.m.box(x0 - 0.02, x1 + 0.02, y0 - 0.02, y1 + 0.02, z + h, z + h + 0.05, "metal")
            return
        self.m.box(x0, x1, y0, y1, z + h - 0.05, z + h, "metal")
        length = max(x1 - x0, y1 - y0)
        n = max(int(length / 1.2), 1)
        for k in range(n + 1):
            t = k / n
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            self.m.box(px - 0.025, px + 0.025, py - 0.025, py + 0.025, z, z + h, "metal")

    def ac_unit(self, x, y, z, facing="-y", bracket=False):
        """실외기: 몸체 + 팬 그릴 원판"""
        w, d, h = 0.86, 0.34, 0.62
        if facing in ("-y", "+y"):
            self.m.box(x - w / 2, x + w / 2, y - d / 2, y + d / 2, z, z + h, "ac")
            gy = y - d / 2 - 0.01 if facing == "-y" else y + d / 2 + 0.01
            self._disc(x - 0.12, gy, z + h / 2, 0.22, "y")
        else:
            self.m.box(x - d / 2, x + d / 2, y - w / 2, y + w / 2, z, z + h, "ac")
            gx = x - d / 2 - 0.01 if facing == "-x" else x + d / 2 + 0.01
            self._disc(gx, y - 0.12, z + h / 2, 0.22, "x")
        if bracket:
            self.m.box(x - 0.45, x + 0.45, y - 0.2, y + 0.2, z - 0.06, z, "metal_dark")

    def _disc(self, x, y, z, r, axis, n=14):
        ring = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        t = 0.02
        if axis == "y":
            v = [(x + a, y - t, z + b) for a, b in ring] + [(x + a, y + t, z + b) for a, b in ring]
        else:
            v = [(x - t, y + a, z + b) for a, b in ring] + [(x + t, y + a, z + b) for a, b in ring]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        f += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        self.m.add(v, f, "metal_dark")

    def water_tank(self, x, y, z, r=0.85, h=1.6):
        self.m.box(x - r, x + r, y - r, y + r, z, z + 0.25, "metal_dark")
        self.m.cylinder(x, y, r, z + 0.25, z + 0.25 + h, "tank", n=20)
        self.m.cylinder(x, y, r * 0.35, z + 0.25 + h, z + 0.4 + h, "tank", n=12)

    def stair_house(self, x0, x1, y0, y1, h=2.7):
        z = self.height
        self.m.box(x0, x1, y0, y1, z, z + h, "wall_side", skip=(BOTTOM,))
        self.m.box(x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, z + h, z + h + 0.15, "trim")
        f = Facade(self.m, "front", x0, x1, y0, y1)
        f.box(f.width / 2 - 0.45, f.width / 2 + 0.45, z + 0.02, z + 2.1, 0, 0.05, "metal_dark")

    def downpipe(self, side, u, top):
        f = self.face(side)
        f.box(u - 0.06, u + 0.06, 0.03, top, 0.04, 0.16, "metal_dark")

    def blind(self):
        """창마다 블라인드 내림 정도 (0 = 없음)"""
        return float(self.rng.choice([0, 0, 0.3, 0.5, 0.85]))

    def windows(self, side, levels, n, w, h, sill=0.9, margin=1.0, lit=0.35, mullions=1):
        f = self.face(side)
        span = f.width - 2 * margin
        for z in levels:
            for i in range(n):
                u = margin + span * (i + 0.5) / n
                f.window(u, z + sill, w, h, mullions=mullions, lit=self.rng.random() < lit,
                         blind=self.blind())

    def sign_band(self, side, u0, u1, z0, z1, text, sub=None, font=None, out=0.32, mat="sign"):
        """간판: 패널 + 입체 채널 글자 (+ 보조 문구)"""
        f = self.face(side)
        f.box(u0, u1, z0, z1, 0, out, mat)
        f.box(u0 - 0.04, u1 + 0.04, z1, z1 + 0.06, 0, out + 0.04, "frame_dark")
        f.box(u0 - 0.04, u1 + 0.04, z0 - 0.06, z0, 0, out + 0.04, "frame_dark")
        h = z1 - z0
        main_h = h * (0.58 if sub else 0.68)
        t = fit_text(text, font, (u1 - u0) * 0.86, main_h, 0.05)
        if t is not None:
            zc = z0 + h * (0.60 if sub else 0.5)
            f.text(t, (u0 + u1) / 2, zc, out, "letters")
        if sub:
            t2 = fit_text(sub, font, (u1 - u0) * 0.7, h * 0.2, 0.03)
            if t2 is not None:
                f.text(t2, (u0 + u1) / 2, z0 + h * 0.18, out, "letters")

    def vertical_sign(self, side, u, z0, z1, text, font, out=1.4, w=1.1, t=0.5, mat="sign2"):
        """건물 모서리에서 튀어나온 세로 간판 (글자를 한 자씩 세로로)"""
        f = self.face(side)
        # 벽에서 수직으로 뻗은 판: 파사드 좌표에서 u 방향 두께 t, d 방향 길이 out
        f.box(u - t / 2, u + t / 2, z0, z1, 0.15, 0.15 + out, mat)
        f.box(u - 0.08, u + 0.08, z0 + 0.4, z0 + 0.55, 0, 0.2, "metal_dark")
        f.box(u - 0.08, u + 0.08, z1 - 0.55, z1 - 0.4, 0, 0.2, "metal_dark")
        chars = [c for c in text if c.strip()]
        if font is None or not chars:
            return
        slot = (z1 - z0) / len(chars)
        size = min(slot * 0.78, out * 0.8)
        for i, ch in enumerate(chars):
            tm = text_mesh(ch, font, size, 0.04)
            if tm is None:
                continue
            zc = z1 - slot * (i + 0.5)
            # 양면: 세로 간판의 좌우 면에 글자를 붙인다
            for sgn in (-1, 1):
                verts, faces, _, _, depth = tm
                out_v = []
                for lx, ly, lz in verts:
                    d = 0.15 + out / 2 + (lx if sgn > 0 else -lx)
                    uu = u + sgn * (t / 2 + depth / 2 + lz)
                    x, y = f.xy(uu, d)
                    out_v.append((x, y, zc + ly))
                self.m.add(out_v, faces, "letters")

    def awning(self, side, u0, u1, z, depth=2.2, drop=0.35, mat="awning"):
        """경사 차양 + 앞 처마(밸런스)"""
        f = self.face(side)
        steps = 6
        for k in range(steps):
            d0 = depth * k / steps
            d1 = depth * (k + 1) / steps
            za = z - drop * k / steps
            f.box(u0, u1, za - 0.06, za + 0.02, d0, d1, mat, attached=(k == 0))
        f.box(u0, u1, z - drop - 0.32, z - drop, depth - 0.04, depth, mat, attached=False)
        for uu in (u0 + 0.1, u1 - 0.1):
            f.box(uu - 0.03, uu + 0.03, z - drop - 0.05, z, 0.0, depth, "metal", attached=False)

    def aquarium(self, side, u, w=1.6, d0=0.5, depth=0.9):
        """횟집 수족관: 스테인리스 받침 + 유리 수조 + 물 + 산소 펌프"""
        f = self.face(side)
        f.box(u - w / 2, u + w / 2, 0.03, 0.75, d0, d0 + depth, "stainless", attached=False)
        f.box(u - w / 2 + 0.04, u + w / 2 - 0.04, 0.75, 1.55, d0 + 0.04, d0 + depth - 0.04, "water",
              attached=False)
        f.box(u - w / 2, u + w / 2, 0.75, 1.78, d0, d0 + 0.02, "glass_tank", attached=False)
        f.box(u - w / 2, u + w / 2, 1.76, 1.82, d0, d0 + depth, "stainless", attached=False)
        for uu in (u - w / 2, u + w / 2 - 0.04):
            f.box(uu, uu + 0.04, 0.75, 1.78, d0, d0 + depth, "stainless", attached=False)
        f.box(u - 0.15, u + 0.15, 1.82, 2.0, d0 + 0.3, d0 + 0.6, "ac", attached=False)

    def build(self, name, coll=None):
        mats = {}
        for key in self.m.mat_names:
            spec = dict(kit.BASE_MATERIALS.get(key, {}))
            spec.update(self.mats.get(key, {}))
            if not spec:
                raise KeyError(f"재질 정의 없음: {key}")
            mats[key] = kit.make_material(f"{name}_{key}", spec)
        return self.m.to_object(name, mats, coll)


EXTRA_MATERIALS = {
    "tank": {"color": (0.12, 0.30, 0.60), "rough": 0.4},
    "glass_rail": {"color": (0.30, 0.40, 0.42), "rough": 0.05, "metal": 0.2},
    "glass_tank": {"color": (0.35, 0.50, 0.55), "rough": 0.03, "metal": 0.1},
    "curtain": {"color": (0.10, 0.30, 0.20), "color2": (0.07, 0.22, 0.15), "pattern": "stripes",
                "scale": 0.25, "rough": 0.6},
    "tent": {"color": (0.75, 0.10, 0.08), "color2": (0.92, 0.90, 0.86), "pattern": "stripes",
             "scale": 0.9, "rough": 0.7, "control": (0, 1, 0)},
    "vinyl": {"color": (0.55, 0.60, 0.60), "rough": 0.08, "metal": 0.1},
    "parasol": {"color": (0.92, 0.90, 0.84), "rough": 0.7, "control": (0, 1, 0)},
}


# ---------------------------------------------------------------------------
# 건물 디자인
# ---------------------------------------------------------------------------

def hoetjip01(font):
    """바다횟집 — 2x3 셀, 3층, 베이지 타일, 수족관 3개, 청백 줄무늬 차양"""
    b = Building((2, 3), 15.2, 15.0, seed=11)
    b.mats.update({
        "wall": {"color": (0.66, 0.56, 0.44), "color2": (0.60, 0.50, 0.39), "pattern": "tile",
                 "scale": (0.6, 0.3), "mortar": 0.01, "mortar_color": (0.75, 0.72, 0.66), "rough": 0.35,
                 "bump": 0.25, "grime": 0.25},
        "wall_side": {"color": (0.78, 0.76, 0.72), "pattern": "noise", "scale": 1.2, "rough": 0.85,
                      "grime": 0.3, "control": (1, 0, 0)},
        "sign": {"color": (0.02, 0.10, 0.42), "rough": 0.4, "emit": (0.05, 0.25, 0.9), "emit_strength": 0.6},
        "awning": {"color": (0.10, 0.25, 0.60), "color2": (0.90, 0.90, 0.88), "pattern": "stripes",
                   "scale": 0.5, "rough": 0.7, "control": (0, 1, 0)},
    })
    b.mats.update(EXTRA_MATERIALS)
    g, u = 4.2, 3.2
    b.lot_slab()
    b.shell(g + 2 * u)
    b.plinth()
    f = b.face("front")
    f.storefront(0.5, b.w - 0.5, 0.03, 3.3, door=(b.w / 2, 1.8))
    b.sign_band("front", 0.2, b.w - 0.2, 3.38, 4.55, "바다횟집", "자연산 활어 · 회 · 물회", font)
    b.awning("front", 0.6, b.w - 0.6, 3.25, depth=2.6)
    for uu in (2.0, 4.3, b.w - 2.0):  # 가운데 문 앞은 비워 둔다
        b.aquarium("front", uu, d0=0.4)
    b.bands([g, g + u], ("front", "left", "right"))
    b.windows("front", [g, g + u], 3, 3.0, 1.6, sill=0.85, margin=0.9, mullions=1)
    b.windows("left", [g, g + u], 2, 1.4, 1.3, margin=2.5)
    b.windows("right", [g, g + u], 2, 1.4, 1.3, margin=2.5)
    b.windows("back", [0, g, g + u], 2, 1.2, 1.1, margin=3.0)
    b.downpipe("left", 0.3, b.height + 0.9)
    b.downpipe("right", b.d - 0.3, b.height + 0.9)
    b.parapet()
    z = b.height
    b.stair_house(b.x0 + 0.8, b.x0 + 4.0, b.y1 - 4.2, b.y1 - 0.8)
    b.water_tank(b.x0 + 2.4, b.y1 - 2.5, z + 2.85, r=0.75, h=1.2)
    for i in range(3):
        b.ac_unit(b.x1 - 1.5 - i * 1.3, b.y1 - 1.2, z + 0.05, "-y")
    b.ac_unit(b.x1 + 0.2, b.y0 + 6.0, 1.2, "+x", bracket=True)
    return b, "바다횟집"


def hoetjip02(font):
    """동해회센터 — 3x3 셀, 2층 넓은 횟집, 흰 도장벽(색상 변형), 수족관 5개, 2층 통창"""
    b = Building((3, 3), 23.0, 14.5, seed=12)
    b.mats.update({
        "wall": {"color": (0.86, 0.85, 0.82), "pattern": "noise", "scale": 1.0, "rough": 0.8, "grime": 0.25,
                 "control": (1, 0, 0)},
        "wall_side": {"color": (0.80, 0.79, 0.76), "pattern": "noise", "scale": 1.0, "rough": 0.85,
                      "grime": 0.3, "control": (1, 0, 0)},
        "sign": {"color": (0.55, 0.04, 0.03), "rough": 0.4, "emit": (0.9, 0.1, 0.05), "emit_strength": 0.6},
        "awning": {"color": (0.70, 0.08, 0.06), "color2": (0.92, 0.90, 0.86), "pattern": "stripes",
                   "scale": 0.6, "rough": 0.7, "control": (0, 1, 0)},
    })
    b.mats.update(EXTRA_MATERIALS)
    g, u = 4.4, 3.6
    b.lot_slab()
    b.shell(g + u)
    b.plinth()
    f = b.face("front")
    f.storefront(0.5, b.w - 0.5, 0.03, 3.4, bay=1.4, door=(b.w * 0.5, 2.0))
    b.sign_band("front", 0.3, b.w - 0.3, 3.5, 4.75, "동해회센터", "활어 · 대게 · 물회 · 매운탕", font)
    b.awning("front", 0.5, b.w - 0.5, 3.35, depth=3.0)
    for k, uu in enumerate((2.0, 4.6, 7.2, b.w - 4.6, b.w - 2.0)):
        b.aquarium("front", uu, w=2.2, d0=0.5)
    b.bands([g], ("front", "left", "right"))
    # 2층 바다 전망 통창
    for i in range(4):
        uu = 1.2 + (b.w - 2.4) * (i + 0.5) / 4
        f.window(uu, g + 0.5, 4.6, 2.4, mullions=2, lit=b.rng.random() < 0.6, blind=b.blind())
    b.windows("left", [g], 2, 1.6, 1.4, margin=3.0)
    b.windows("right", [g], 2, 1.6, 1.4, margin=3.0)
    b.windows("back", [0, g], 3, 1.2, 1.1, margin=3.0)
    b.downpipe("left", 0.3, b.height + 0.9)
    b.downpipe("right", b.d - 0.3, b.height + 0.9)
    b.parapet()
    z = b.height
    b.stair_house(b.x1 - 4.0, b.x1 - 0.8, b.y1 - 4.0, b.y1 - 0.8)
    for i in range(4):
        b.ac_unit(b.x0 + 1.5 + i * 1.3, b.y1 - 1.2, z + 0.05, "-y")
    b.water_tank(b.x0 + 2.0, b.y0 + 2.5, z + 0.05)
    # 옥상 현수막 거치대
    b.m.box(b.x0 + 4, b.x1 - 6, b.y0 + 0.3, b.y0 + 0.4, z + 1.0, z + 2.6, "sign")
    t = fit_text("싱싱한 자연산 활어", font, b.w - 12, 1.1, 0.03)
    if t:
        Facade(b.m, "front", b.x0 + 4, b.x1 - 6, b.y0 + 0.3, b.y0 + 0.4).text(t, (b.w - 10) / 2, z + 1.8, 0,
                                                                                "letters")
    return b, "동해회센터"


def cafe01(font):
    """카페 파도 — 2x3 셀, 3층 + 루프탑, 짙은 금속 패널, 통유리 커튼월, 유리 난간 발코니"""
    b = Building((2, 3), 14.0, 14.0, seed=13)
    b.mats.update({
        "wall": {"color": (0.17, 0.18, 0.19), "color2": (0.15, 0.16, 0.17), "pattern": "panel",
                 "scale": (1.2, 0.6), "mortar": 0.006, "mortar_color": (0.05, 0.05, 0.05), "rough": 0.35,
                 "metal": 0.5, "bump": 0.15},
        "wall_side": {"color": (0.82, 0.80, 0.76), "pattern": "noise", "scale": 1.0, "rough": 0.85,
                      "grime": 0.15, "control": (1, 0, 0)},
        "sign": {"color": (0.10, 0.10, 0.10), "rough": 0.5},
        "sign2": {"color": (0.85, 0.80, 0.70), "rough": 0.5, "emit": (1.0, 0.9, 0.7), "emit_strength": 0.4},
        "deck": {"color": (0.45, 0.30, 0.18), "color2": (0.35, 0.22, 0.12), "pattern": "wood", "rough": 0.7,
                 "bump": 0.1},
    })
    b.mats.update(EXTRA_MATERIALS)
    g, u = 4.4, 3.4
    b.lot_slab()
    b.shell(g + 2 * u)
    b.plinth(mat="frame_dark")
    f = b.face("front")
    # 1~2층 통유리 커튼월 (가로 띠 + 세로 멀리언)
    f.storefront(0.6, b.w - 0.6, 0.03, g - 0.2, bay=1.5, door=(b.w - 2.4, 1.8))
    cw0, cw1 = 0.6, b.w - 0.6
    f.box(cw0, cw1, g + 0.2, g + u - 0.2, 0, 0.04, "glass_shop")
    for k in range(9):
        uu = cw0 + (cw1 - cw0) * k / 8
        f.box(uu - 0.04, uu + 0.04, g, g + u, 0, 0.14, "frame_dark")
    for zz in (g, g + 1.4, g + u - 0.15):
        f.box(cw0, cw1, zz - 0.05, zz + 0.05, 0, 0.14, "frame_dark")
    # 2층 발코니 (유리 난간)
    f.box(0.4, b.w - 0.4, g - 0.25, g, 0, 1.6, "concrete", attached=True)
    b.rail(b.x0 + 0.45, b.x1 - 0.45, b.y0 - 1.6, b.y0 - 1.52, g, h=1.05, glass=True)
    # 3층: 창 4개
    b.windows("front", [g + u], 4, 2.4, 1.9, sill=0.6, margin=0.8, mullions=1, lit=0.5)
    b.windows("left", [0, g, g + u], 2, 1.2, 1.4, margin=3.0)
    b.windows("right", [g, g + u], 3, 1.6, 1.6, margin=2.0)
    # 간판: 파사드 상단 채널 글자 + 세로 돌출 간판
    t = fit_text("CAFE PADO", font, b.w * 0.6, 0.75, 0.06)
    if t:
        f.text(t, b.w * 0.42, g + 2 * u - 0.55, 0.0, "letters")
    b.vertical_sign("front", 0.45, g + 0.6, g + 2 * u - 0.4, "카페파도", font, out=1.2, w=1.0, t=0.45)
    b.parapet(h=0.4, mat="wall")
    z = b.height
    # 루프탑: 데크, 유리 난간, 파라솔 테이블
    b.m.box(b.x0 + 0.25, b.x1 - 0.25, b.y0 + 0.25, b.y1 - 5.0, z, z + 0.15, "deck", skip=(BOTTOM,))
    zr = z + 0.15
    b.rail(b.x0 + 0.3, b.x1 - 0.3, b.y0 + 0.3, b.y0 + 0.36, zr, glass=True)
    b.rail(b.x0 + 0.3, b.x0 + 0.36, b.y0 + 0.36, b.y1 - 5.0, zr, glass=True)
    b.rail(b.x1 - 0.36, b.x1 - 0.3, b.y0 + 0.36, b.y1 - 5.0, zr, glass=True)
    for px in (b.x0 + 3.0, 0.0, b.x1 - 3.0):
        py = b.y0 + 3.5
        b.m.cylinder(px, py, 0.04, zr, zr + 2.4, "metal", n=8)
        b.m.cone(px, py, 1.5, zr + 2.0, zr + 2.65, "parasol", n=16)
        b.m.cylinder(px, py, 0.45, zr + 0.70, zr + 0.75, "deck", n=16)
        for a in range(3):
            ang = a * 2.09
            b.m.cylinder(px + 0.85 * math.cos(ang), py + 0.85 * math.sin(ang), 0.2, zr, zr + 0.45,
                         "wall_side", n=10)
    b.stair_house(b.x0 + 0.6, b.x0 + 4.2, b.y1 - 4.4, b.y1 - 0.6)
    for i in range(3):
        b.ac_unit(b.x1 - 1.2 - i * 1.25, b.y1 - 1.0, z + 0.05, "-y")
    return b, "카페 파도"


def motel01(font):
    """호텔 일산 — 3x4 셀, 7층, 분홍빛 타일, 세로 간판, 옥상 대형 간판, 드라이브인 주차 커튼"""
    b = Building((3, 4), 20.0, 18.0, setback=1.5, seed=14)
    b.mats.update({
        "wall": {"color": (0.68, 0.54, 0.50), "color2": (0.63, 0.49, 0.45), "pattern": "tile",
                 "scale": (0.6, 0.3), "mortar": 0.01, "mortar_color": (0.78, 0.74, 0.70), "rough": 0.35,
                 "bump": 0.2, "grime": 0.2},
        "wall_side": {"color": (0.80, 0.76, 0.72), "pattern": "noise", "scale": 1.0, "rough": 0.85,
                      "grime": 0.2, "control": (1, 0, 0)},
        "sign": {"color": (0.30, 0.05, 0.35), "rough": 0.4, "emit": (0.8, 0.1, 0.9), "emit_strength": 0.8},
        "sign2": {"color": (0.08, 0.05, 0.30), "rough": 0.4, "emit": (0.2, 0.2, 1.0), "emit_strength": 0.8},
        "awning": {"color": (0.25, 0.22, 0.20), "rough": 0.5},
    })
    b.mats.update(EXTRA_MATERIALS)
    g, u, floors = 4.5, 3.0, 7
    levels = [g + i * u for i in range(floors - 1)]
    b.lot_slab()
    b.shell(g + (floors - 1) * u)
    b.plinth()
    f = b.face("front")
    # 로비 + 주차 입구(커튼)
    f.storefront(0.6, 9.0, 0.03, 3.6, bay=1.4, door=(4.8, 2.0))
    f.box(11.0, b.w - 0.8, 0.03, 3.2, -0.05, 0.0, "curtain", attached=False)
    f.box(10.8, 11.0, 0.03, 3.4, 0, 0.3, "trim")
    f.box(b.w - 0.8, b.w - 0.6, 0.03, 3.4, 0, 0.3, "trim")
    f.box(10.8, b.w - 0.6, 3.2, 3.4, 0, 0.3, "trim")
    b.awning("front", 1.2, 8.4, 3.75, depth=2.4, drop=0.1)
    t = fit_text("HOTEL ILSAN", font, 6.8, 0.42, 0.04)
    if t:
        f.text(t, 4.8, 3.62 - 0.1 - 0.36, 2.4, "letters")
    b.bands(levels, ("front",), h=0.12, out=0.06)
    # 객실 창 + 창 아래 실외기
    for z in levels:
        for i in range(5):
            uu = 1.6 + (b.w - 3.2) * (i + 0.5) / 5
            f.window(uu, z + 0.9, 1.7, 1.5, mullions=1, lit=b.rng.random() < 0.4, blind=b.blind())
            if b.rng.random() < 0.55:
                x, y = f.xy(uu + 1.2, 0.35)
                b.ac_unit(x, y, z + 0.25, "-y", bracket=True)
    b.windows("left", levels, 3, 1.2, 1.2, margin=3.0)
    b.windows("right", levels, 3, 1.2, 1.2, margin=3.0)
    b.windows("back", levels, 4, 1.0, 1.0, margin=3.0, lit=0.2)
    b.vertical_sign("front", b.w - 0.5, g + 0.5, b.height - 0.6, "호텔일산", font, out=1.6, t=0.55)
    b.downpipe("left", 0.3, b.height + 0.9)
    b.downpipe("right", b.d - 0.3, b.height + 0.9)
    b.parapet()
    z = b.height
    # 옥상 대형 간판 (철골 프레임 + 패널 + 글자)
    sx0, sx1 = b.x0 + 3.0, b.x1 - 3.0
    sy = b.y0 + 2.0
    for px in np.linspace(sx0 + 0.3, sx1 - 0.3, 5):
        b.m.box(px - 0.08, px + 0.08, sy - 0.08, sy + 0.08, z, z + 5.4, "metal_dark")
        b.m.box(px - 0.06, px + 0.06, sy, sy + 1.6, z, z + 0.12, "metal_dark")
    b.m.box(sx0, sx1, sy - 0.25, sy - 0.08, z + 2.4, z + 5.2, "sign")
    t = fit_text("HOTEL", font, (sx1 - sx0) * 0.85, 2.2, 0.08)
    if t:
        Facade(b.m, "front", sx0, sx1, sy - 0.25, sy).text(t, (sx1 - sx0) / 2, z + 3.8, 0.0, "letters")
    b.stair_house(b.x1 - 4.5, b.x1 - 0.8, b.y1 - 5.5, b.y1 - 0.8, h=3.0)
    b.water_tank(b.x0 + 2.0, b.y1 - 2.2, z + 0.05, r=1.0, h=1.8)
    b.water_tank(b.x0 + 4.4, b.y1 - 2.2, z + 0.05, r=1.0, h=1.8)
    for i in range(4):
        b.ac_unit(b.x0 + 7.5 + i * 1.3, b.y1 - 1.2, z + 0.05, "-y")
    return b, "호텔 일산"


def shop01(font):
    """편의점 + 다가구 — 2x2 셀, 3층 붉은 벽돌, 1층 편의점, 2~3층 주거 발코니"""
    b = Building((2, 2), 14.0, 12.0, seed=15)
    b.mats.update({
        "wall": {"color": (0.42, 0.16, 0.10), "color2": (0.36, 0.13, 0.08), "pattern": "tile",
                 "scale": (0.42, 0.14), "mortar": 0.012, "mortar_color": (0.62, 0.58, 0.52), "rough": 0.8,
                 "bump": 0.4, "grime": 0.2},
        "wall_side": {"color": (0.42, 0.16, 0.10), "color2": (0.36, 0.13, 0.08), "pattern": "tile",
                      "scale": (0.42, 0.14), "mortar": 0.012, "mortar_color": (0.62, 0.58, 0.52),
                      "rough": 0.8, "bump": 0.4},
        "sign": {"color": (0.90, 0.90, 0.88), "rough": 0.4, "emit": (1, 1, 1), "emit_strength": 0.5},
        "accent": {"color": (0.05, 0.45, 0.25), "rough": 0.4, "emit": (0.1, 0.8, 0.4), "emit_strength": 0.5,
                   "control": (0, 1, 0)},
        "awning": {"color": (0.05, 0.45, 0.25), "rough": 0.5, "control": (0, 1, 0)},
    })
    b.mats.update(EXTRA_MATERIALS)
    g, u = 4.0, 2.9
    b.lot_slab()
    b.shell(g + 2 * u)
    b.plinth()
    f = b.face("front")
    f.storefront(0.5, b.w - 0.5, 0.03, 3.25, bay=1.3, door=(2.2, 1.7))
    f.box(0.2, b.w - 0.2, 3.3, 4.0, 0, 0.3, "sign")
    f.box(0.2, b.w - 0.2, 3.3, 3.45, 0, 0.32, "accent")
    f.box(0.2, b.w - 0.2, 3.85, 4.0, 0, 0.32, "accent")
    t = fit_text("편의점 24", font, 5.0, 0.36, 0.04)
    if t:
        f.text(t, b.w / 2, 3.65, 0.3, "letters_dark")
    b.mats["letters_dark"] = {"color": (0.05, 0.35, 0.18), "rough": 0.4, "emit": (0.1, 0.8, 0.4),
                              "emit_strength": 1.0}
    # 2~3층 발코니 (난간 + 실외기)
    for z in (g, g + u):
        f.box(0.8, b.w - 0.8, z - 0.15, z + 0.05, 0, 1.2, "concrete")
        b.rail(b.x0 + 0.85, b.x1 - 0.85, b.y0 - 1.2, b.y0 - 1.15, z + 0.05, h=1.0)
        for i in range(2):
            uu = 3.5 + i * 7.0
            f.window(uu, z + 0.3, 2.6, 2.1, mullions=1, lit=b.rng.random() < 0.4, blind=b.blind())
        x, y = f.xy(b.w / 2, 0.6)
        b.ac_unit(x, y, z + 0.06, "-y")
    b.windows("left", [g, g + u], 2, 1.0, 1.0, margin=2.5)
    b.windows("right", [g, g + u], 2, 1.0, 1.0, margin=2.5)
    b.windows("back", [g, g + u], 3, 1.0, 1.0, margin=2.0)
    b.downpipe("left", 0.3, b.height + 0.9)
    b.parapet(mat="wall_side")
    z = b.height
    b.water_tank(b.x1 - 1.6, b.y1 - 1.6, z + 0.05, r=0.7, h=1.3)
    b.stair_house(b.x0 + 0.6, b.x0 + 3.4, b.y1 - 3.6, b.y1 - 0.6)
    b.awning("left", 1.0, 5.0, 2.8, depth=1.2, drop=0.2)
    return b, "편의점"


def grill01(font):
    """조개구이 — 2x2 셀, 단층 경량 철골 + 줄무늬 천막 박공 지붕, 투명 비닐 가림막, 원형 화로 테이블"""
    b = Building((2, 2), 14.0, 11.0, seed=16)
    b.mats.update({
        "wall": {"color": (0.80, 0.80, 0.78), "rough": 0.5, "metal": 0.3},
        "wall_side": {"color": (0.78, 0.78, 0.76), "pattern": "panel", "scale": (1.0, 3.2),
                      "mortar": 0.01, "mortar_color": (0.6, 0.6, 0.6), "rough": 0.5, "metal": 0.3,
                      "control": (1, 0, 0)},
        "sign": {"color": (0.95, 0.75, 0.05), "rough": 0.4, "emit": (1.0, 0.8, 0.1), "emit_strength": 0.6},
        "floor": {"color": (0.40, 0.39, 0.37), "pattern": "noise", "scale": 2.0, "rough": 0.6},
    })
    b.mats.update(EXTRA_MATERIALS)
    h = 3.4
    b.lot_slab()
    x0, x1, y0, y1 = b.x0, b.x1, b.y0, b.y1
    m = b.m
    m.box(x0, x1, y0, y1, 0.03, 0.12, "floor", skip=(BOTTOM,))
    # 측벽·뒷벽(샌드위치 패널), 앞은 개방 + 비닐
    m.box(x0, x0 + 0.12, y0, y1, 0.12, h, "wall_side", skip=(BOTTOM,))
    m.box(x1 - 0.12, x1, y0, y1, 0.12, h, "wall_side", skip=(BOTTOM,))
    m.box(x0, x1, y1 - 0.12, y1, 0.12, h, "wall_side", skip=(BOTTOM,))
    for px in np.linspace(x0 + 0.1, x1 - 0.1, 6):
        m.box(px - 0.06, px + 0.06, y0, y0 + 0.12, 0.12, h, "metal_dark", skip=(BOTTOM,))
    m.box(x0, x1, y0, y0 + 0.15, h - 0.2, h, "metal_dark")
    m.box(x0 + 0.2, x1 - 0.2, y0 + 0.05, y0 + 0.08, 0.12, h - 0.2, "vinyl")
    # 박공 천막 지붕
    ridge = h + 1.8
    ov = 0.5
    ym = (y0 + y1) / 2
    for (ya, yb, za, zb) in ((y0 - ov, ym, h - 0.3, ridge), (ym, y1 + ov, ridge, h - 0.3)):
        steps = 8
        for k in range(steps):
            t0, t1 = k / steps, (k + 1) / steps
            yy0, yy1 = ya + (yb - ya) * t0, ya + (yb - ya) * t1
            zz = za + (zb - za) * (t0 + t1) / 2
            m.box(x0 - ov, x1 + ov, min(yy0, yy1), max(yy0, yy1), zz - 0.05, zz + 0.05, "tent")
    for side_x in (x0, x1 - 0.12):
        m.add([(side_x, y0, h), (side_x + 0.12, y0, h), (side_x + 0.12, ym, ridge), (side_x, ym, ridge)],
              [(0, 1, 2, 3)], "wall_side")
        m.add([(side_x, ym, ridge), (side_x + 0.12, ym, ridge), (side_x + 0.12, y1, h), (side_x, y1, h)],
              [(0, 1, 2, 3)], "wall_side")
    # 화로 테이블 + 플라스틱 의자
    for i in range(3):
        for j in range(2):
            tx = x0 + 2.4 + i * 4.6
            ty = y0 + 3.0 + j * 4.2
            m.cylinder(tx, ty, 0.08, 0.12, 0.72, "metal_dark", n=8)
            m.cylinder(tx, ty, 0.55, 0.72, 0.78, "stainless", n=20)
            m.cylinder(tx, ty, 0.22, 0.78, 0.84, "metal_dark", n=12)
            for a in range(4):
                ang = a * math.pi / 2 + 0.4
                mat = "plastic_red" if (a + i) % 2 else "plastic_blue"
                m.cylinder(tx + 0.95 * math.cos(ang), ty + 0.95 * math.sin(ang), 0.18, 0.12, 0.55, mat, n=10)
    # 앞 지붕 위 간판
    f = Facade(m, "front", x0 + 1.0, x1 - 1.0, y0 - ov - 0.1, y0 - ov)
    f.box(0, f.width, h + 0.1, h + 1.3, 0, 0.12, "sign", attached=False)
    t = fit_text("조개구이 · 장어구이", font, f.width * 0.85, 0.75, 0.04)
    if t:
        f.text(t, f.width / 2, h + 0.7, 0.12, "letters_red")
    b.mats["letters_red"] = {"color": (0.70, 0.05, 0.03), "rough": 0.4, "emit": (1.0, 0.1, 0.05),
                             "emit_strength": 1.0}
    b.height = ridge
    return b, "조개구이"


DESIGNS = {
    "IlsanHoetjip01": hoetjip01,
    "IlsanHoetjip02": hoetjip02,
    "IlsanCafe01": cafe01,
    "IlsanMotel01": motel01,
    "IlsanShop01": shop01,
    "IlsanGrill01": grill01,
}


# ---------------------------------------------------------------------------

def find_font(path=None):
    if path:
        return path if os.path.isfile(path) else None
    for pattern in FONT_CANDIDATES:
        for f in sorted(glob.glob(pattern)):
            return f
    return None


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="assets.py")
    p.add_argument("--only")
    p.add_argument("--tex", type=int, default=2048)
    p.add_argument("--font")
    p.add_argument("--out", default=os.path.join(HERE, "CS2Assets"))
    p.add_argument("--preview")
    p.add_argument("--no-bake", action="store_true")
    p.add_argument("--save-blend")
    return p.parse_args(argv)


def make_asset(name, font_path, out_root, tex, preview_dir=None, do_bake=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    font = bpy.data.fonts.load(font_path) if font_path else None
    b, title = DESIGNS[name](font)
    assert tuple(b.lot) == catalog.ASSETS[name][:2], f"{name}: 부지 크기가 catalog.py 와 다릅니다"
    obj = b.build(name)
    info = {"name": name, "title": title, "lot_cells": list(b.lot), "lot_m": [b.lw, b.ld],
            "footprint_m": [round(b.w, 2), round(b.d, 2)], "height_m": round(float(obj.dimensions.z), 2),
            "lod0_tris": bake.tri_count(obj)}
    if not do_bake:
        return obj, info
    out_dir = os.path.join(out_root, name)
    bake.unwrap(obj)
    paths = bake.bake_texture_set(obj, name, out_dir, size=tex)
    mat = bake.baked_material(name, paths)
    bake.replace_materials(obj, mat)
    bake.export_fbx(obj, os.path.join(out_dir, name + ".fbx"))
    lods = []
    for level, ratio in ((1, 0.30), (2, 0.07)):
        lod = bake.make_lod(obj, f"{name}_LOD{level}", ratio)
        bake.export_fbx(lod, os.path.join(out_dir, lod.name + ".fbx"))
        lods.append(bake.tri_count(lod))
        lod.hide_render = True
    info["lod_tris"] = lods
    info["texture"] = tex
    with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    if preview_dir:
        os.makedirs(preview_dir, exist_ok=True)
        bake.preview(obj, b.lw, b.ld, os.path.join(preview_dir, name + ".png"))
        bake.set_night(mat, 6.0)
        bake.preview(obj, b.lw, b.ld, os.path.join(preview_dir, name + "_night.png"), night=True)
    return obj, info


def main():
    args = parse_args()
    font_path = find_font(args.font)
    print("간판 폰트:", font_path or "없음 (글자 생략)")
    names = args.only.split(",") if args.only else list(DESIGNS)
    infos = []
    for name in names:
        obj, info = make_asset(name, font_path, args.out, args.tex, args.preview, not args.no_bake)
        print(json.dumps(info, ensure_ascii=False))
        infos.append(info)
        if args.save_blend:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(args.save_blend), name + ".blend"))
    if not args.no_bake:
        with open(os.path.join(args.out, "catalog.json"), "w", encoding="utf-8") as f:
            json.dump(infos, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
