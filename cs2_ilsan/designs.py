"""일산지 거리 상가 건물 디자인 (블렌더 없이 동작 — 글자 메시만 text_fn 으로 주입).

좌표: 미터, 원점 = 부지 중심 지면, 정면 = -Y. 부지는 8 m 셀 단위.
모든 파사드 요소는 geom.Facade 예약 규칙을 따르므로 문 · 창 · 간판 · 설비가 서로 겹치지 않는다.
validate() 가 겹침 · 부지 이탈 · 재질 누락을 검사한다.
"""

import math
import random

import materials
from geom import (BOTTOM, FIXTURE, FOREGROUND, OPENING, SIGN, Box3, Facade, Mesh, box_conflicts, conflicts,
                  rects_minus)

CELL = 8.0
SIDES = ("front", "back", "left", "right")


# 간판 문구 -> 실제 로고 키 (logos/<키>.svg 가 있으면 sign_band · lightbox · wall_text 가 문구 대신 로고를 붙인다)
BRAND_LOGOS = {
    "STARBUCKS": "starbucks_wordmark", "Homeplus": "homeplus", "GS25": "gs25", "CU": "cu", "7-ELEVEN": "7eleven",
    "emart24": "emart24", "PARIS BAGUETTE": "parisbaguette", "baskin robbins": "baskinrobbins",
    "COMPOSE COFFEE": "composecoffee", "MEGA COFFEE": "megacoffee", "EDIYA COFFEE": "ediya",
    "ANGEL-IN-US": "angelinus", "PASCUCCI": "pascucci", "Gong cha": "gongcha", "봉구비어": "bonggubeer",
    "DROPTOP": "droptop", "오가다": "ogada", "OLIVE YOUNG": "oliveyoung", "Daiso": "daiso", "BBQ": "bbq",
    "교촌치킨": "kyochon", "김밥천국": "kimbapcheonguk", "MG새마을금고": "mg", "GS칼텍스": "gscaltex",
}


class Building:
    def __init__(self, lot, width, depth, setback=3.0, seed=0, text_fn=None):
        self.lot = tuple(lot)
        self.lw, self.ld = lot[0] * CELL, lot[1] * CELL
        self.m = Mesh()
        self.rng = random.Random(seed)
        self.text_fn = text_fn
        self.x0, self.x1 = -width / 2, width / 2
        self.y0 = -self.ld / 2 + setback
        self.y1 = self.y0 + depth
        self.w, self.d = width, depth
        self.slots = []
        self.roof = []
        self.mats = {}
        self.zones = {}
        self.vols = {}          # 추가 몸체: 이름 -> (x0, x1, y0, y1, 바닥, 높이)
        self.height = 0.0
        self.top = 0.0          # 지붕 구조물 포함 최고 높이 (참고용)
        if self.y1 > self.ld / 2 + 1e-6 or width > self.lw + 1e-6:
            raise ValueError("건물이 부지보다 큽니다")

    # -- 기본 ---------------------------------------------------------------

    def face(self, side):
        """'front' 처럼 면 이름만 주면 기본 몸체, 'tower:front' 처럼 주면 volume() 으로 만든 몸체의 면"""
        if ":" in side:
            key, s = side.split(":")
            x0, x1, y0, y1 = self.vols[key][:4]
            return Facade(self.m, s, x0, x1, y0, y1, self.slots, key=side)
        return Facade(self.m, side, self.x0, self.x1, self.y0, self.y1, self.slots)

    def volume(self, key, x0, x1, y0, y1, base, height, zones=None, roof="roof", roof_holes=()):
        """추가 몸체 (저층부 위의 탑, 엘리베이터 코어 등). 벽은 finalize() 에서 개구부를 뚫어 만든다.
        zones = {면: [(z0, z1, 재질[, u0, u1])]}, roof_holes = 지붕에서 비울 사각형 (위에 다른 몸체가 서는 곳)."""
        self.vols[key] = (x0, x1, y0, y1, base, height)
        for s in SIDES:
            self.zones[f"{key}:{s}"] = [(base, height, "wall" if s == "front" else "wall_side")]
        for s, z in (zones or {}).items():
            self.zones[f"{key}:{s}"] = z
        self.top = max(self.top, height)
        if roof:
            for a, b, c, d in rects_minus(x0, x1, y0, y1, roof_holes):
                self.m.quad((a, c, height), (b, c, height), (b, d, height), (a, d, height), roof)

    def in_lot(self, f, u0, u1, d_out, margin=0.05):
        """파사드 위 구간 (u0..u1) 을 d_out 만큼 내민 것이 부지 안에 들어가는지 (옆 부지와 닿지 않게)"""
        for u in (u0, u1):
            x, y = f.xy(u, d_out)
            if abs(x) > self.lw / 2 - margin or abs(y) > self.ld / 2 - margin:
                return False
        return True

    def letters(self, text, max_w, max_h, extrude=0.05):
        if not text or self.text_fn is None:
            return None
        return self.text_fn(text, max_w, max_h, extrude)

    def logo(self, key, max_w, max_h, depth=0.03):
        """logos/<key>.svg 실제 로고의 색별 조각 (파일 · 글자 함수가 없으면 None → 호출한 쪽이 글자로 대신한다)"""
        fn = getattr(self.text_fn, "logo", None)
        return fn(key, max_w, max_h, depth) if fn else None

    def brand_text(self, f, text, u, z, d, max_w, max_h, depth, mat, emit=2.0, key=None):
        """손으로 만든 간판 위 브랜드 이름: 실제 로고가 있으면 로고, 없으면 글자 (예약은 하지 않는다)"""
        key = key or BRAND_LOGOS.get(text)
        parts = self.logo(key, max_w, max_h, depth) if key else None
        if parts:
            self.put_logo(f, parts, key, u, z, d, emit=emit, kind=None)
            return True
        t = self.letters(text, max_w, max_h, depth)
        if t:
            f.text(t, u, z, d, mat, kind=None)
        return bool(t)

    def put_logo(self, f, parts, key, u, z, d, emit=0.0, kind=SIGN, name="logo"):
        """로고 조각을 파사드 f 의 (u, z) 중심, 뒷면 d 에 붙인다. 조각 색마다 재질(letters_logo_*)을 만들어
        LOD · UV 에서 글자와 같이 다룬다. emit > 0 이면 밤에 로고 색으로 빛난다. 반환: (폭, 높이, 두께)"""
        for i, (verts, faces, w, h, depth, rgb) in enumerate(parts):
            mat = f"letters_logo_{key}_{i}"
            self.mats[mat] = {"color": rgb, "rough": 0.35}
            if emit > 0:
                self.mats[mat].update(emit=tuple(min(1.0, c * 1.25 + 0.02) for c in rgb), emit_strength=emit)
            f.text((verts, faces, w, h, depth), u, z, d, mat, kind=None)
        w, h, depth = parts[0][2:5]
        if kind:
            f.reserve(kind, u - w / 2, u + w / 2, z - h / 2, z + h / 2, d, d + depth, name)
        return w, h, depth

    def chance(self, p):
        return self.rng.random() < p

    def blind(self):
        return self.rng.choice([0, 0, 0, 0.3, 0.5, 0.85])

    def lot_slab(self, mat="paving"):
        """부지 바닥 (얇은 판). 게임이 부지를 평탄화한다."""
        hw, hd = self.lw / 2 - 0.05, self.ld / 2 - 0.05
        self.m.box(-hw, hw, -hd, hd, -0.30, 0.03, mat, skip=(BOTTOM,))

    def shell(self, height, base=0.03, zones=None, roof="roof", roof_holes=()):
        """건물 몸체: 지붕면은 바로 만들고, 벽은 finalize() 에서 개구부를 뚫어 만든다.
        zones = {면: [(z0, z1, 재질)]} — 기본은 정면 'wall', 나머지 'wall_side'."""
        self.height, self.base = height, base
        self.top = max(self.top, height)
        for s in SIDES:
            self.zones[s] = [(base, height, "wall" if s == "front" else "wall_side")]
        if zones:
            self.zones.update(zones)
        if roof:
            for a, b, c, d in rects_minus(self.x0, self.x1, self.y0, self.y1, roof_holes):
                self.m.quad((a, c, height), (b, c, height), (b, d, height), (a, d, height), roof)

    def finalize(self):
        for side, zones in self.zones.items():
            self.face(side).walls(zones)

    # -- 옥상 예약 ------------------------------------------------------------

    def roof_reserve(self, name, x0, x1, y0, y1, z0, z1):
        self.roof.append(Box3(x0, x1, y0, y1, z0, z1, name))
        self.top = max(self.top, z1)

    def roof_fits(self, x0, x1, y0, y1, z0, z1):
        probe = Box3(x0, x1, y0, y1, z0, z1)
        return not any(probe.overlaps(b) for b in self.roof)

    def parapet(self, h=1.0, t=0.22, mat="wall_side", cap="trim", vol=None):
        if vol:
            x0, x1, y0, y1, _, z = self.vols[vol]
        else:
            x0, x1, y0, y1, z = self.x0, self.x1, self.y0, self.y1, self.height
        o = 0.05
        segs = (("front", x0, x1, y0, y0 + t), ("back", x0, x1, y1 - t, y1),
                ("left", x0, x0 + t, y0 + t, y1 - t), ("right", x1 - t, x1, y0 + t, y1 - t))
        for name, a, b, c, d in segs:
            self.m.box(a, b, c, d, z, z + h, mat, skip=(BOTTOM,))
            tag = f"parapet_{vol}_{name}" if vol else "parapet_" + name
            if name in ("front", "back"):
                self.m.box(a - o, b + o, c - o, d + o, z + h, z + h + 0.08, cap)
                self.roof_reserve(tag, a - o, b + o, c - o, d + o, z, z + h + 0.08)
            else:
                self.m.box(a - o, b + o, c + o, d - o, z + h, z + h + 0.08, cap)
                self.roof_reserve(tag, a - o, b + o, c + o, d - o, z, z + h + 0.08)
        self.parapet_t = t + o

    # -- 옥상 설비 ------------------------------------------------------------

    def ac_roof(self, x, y, z, facing="-y"):
        w, d, h = 0.86, 0.34, 0.62
        along_x = facing in ("-y", "+y")
        hx, hy = (w / 2, d / 2) if along_x else (d / 2, w / 2)
        if not self.roof_fits(x - hx - 0.05, x + hx + 0.05, y - hy - 0.05, y + hy + 0.05, z, z + h + 0.1):
            return False
        self.m.box(x - hx, x + hx, y - hy, y + hy, z + 0.1, z + h + 0.1, "ac")
        for sx in (-1, 1):  # 받침대
            if along_x:
                self.m.box(x + sx * (hx - 0.08) - 0.03, x + sx * (hx - 0.08) + 0.03, y - hy, y + hy, z, z + 0.1,
                           "metal_dark")
            else:
                self.m.box(x - hx, x + hx, y + sx * (hy - 0.08) - 0.03, y + sx * (hy - 0.08) + 0.03, z, z + 0.1,
                           "metal_dark")
        side = {"-y": "front", "+y": "back", "-x": "left", "+x": "right"}[facing]
        f = Facade(self.m, side, x - hx, x + hx, y - hy, y + hy)
        f.disc(f.width / 2 - 0.12, z + 0.1 + h / 2, 0.0, 0.22, 0.02, "metal_dark")
        self.roof_reserve("ac", x - hx - 0.05, x + hx + 0.05, y - hy - 0.05, y + hy + 0.05, z, z + h + 0.1)
        return True

    def water_tank(self, x, y, z, r=0.85, h=1.6):
        self.m.box(x - r, x + r, y - r, y + r, z, z + 0.25, "metal_dark")
        self.m.cylinder(x, y, r, z + 0.25, z + 0.25 + h, "tank", n=20)
        self.m.cylinder(x, y, r * 0.35, z + 0.25 + h, z + 0.4 + h, "tank", n=12)
        for k in range(3):  # 보강 띠
            zz = z + 0.25 + h * (k + 1) / 4
            self.m.cylinder(x, y, r + 0.02, zz - 0.03, zz + 0.03, "tank", n=20)
        self.roof_reserve("tank", x - r - 0.02, x + r + 0.02, y - r - 0.02, y + r + 0.02, z, z + 0.4 + h)

    def stair_house(self, x0, x1, y0, y1, h=2.7, door="front"):
        """옥상 계단실: 몸체 + 지붕 판 + 철문 + 환기창"""
        z = self.height
        self.m.box(x0, x1, y0, y1, z, z + h, "wall_side", skip=(BOTTOM,))
        self.m.box(x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, z + h, z + h + 0.15, "trim")
        f = Facade(self.m, door, x0, x1, y0, y1)
        u = f.width / 2
        f.box(u - 0.5, u + 0.5, z + 0.02, z + 2.12, 0, 0.04, "frame")
        f.box(u - 0.45, u + 0.45, z + 0.02, z + 2.07, 0.04, 0.06, "door_metal")
        f.box(u + 0.3, u + 0.34, z + 0.95, z + 1.1, 0.06, 0.1, "metal", attached=False)
        f.box(u - 0.3, u + 0.3, z + h - 0.55, z + h - 0.25, 0, 0.03, "grille")
        self.roof_reserve("stair", x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, z, z + h + 0.15)
        return z + h + 0.15

    def roof_rail(self, x0, x1, y0, y1, z, h=1.1, style="bars"):
        self.rail_geom(x0, x1, y0, y1, z, h, style)
        self.roof_reserve("rail", x0, x1, y0, y1, z, z + h)

    def rail_geom(self, x0, x1, y0, y1, z, h=1.1, style="bars", mat="metal"):
        """직선 난간 (x 또는 y 방향으로 긴 얇은 영역)"""
        if style == "wood":
            mat = "wood"
        self.m.box(x0, x1, y0, y1, z + h - 0.05, z + h, mat)
        if style in ("bars", "wood"):
            for zz in (z + h * 0.35, z + h * 0.68):
                self.m.box(x0, x1, y0, y1, zz - 0.02, zz + 0.02, mat)
        length = max(x1 - x0, y1 - y0)
        n = max(int(length / (1.5 if style != "posts" else 0.15)), 1)
        for k in range(n + 1):
            t = k / n
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            r = 0.03 if style != "posts" else 0.012
            px = min(max(px, x0 + r), x1 - r) if x1 - x0 > 2 * r else (x0 + x1) / 2
            py = min(max(py, y0 + r), y1 - r) if y1 - y0 > 2 * r else (y0 + y1) / 2
            self.m.box(px - r, px + r, py - r, py + r, z, z + h - 0.05, mat)

    # -- 파사드 설비 ----------------------------------------------------------

    def ac_wall(self, side, u, z, d=0.35, bracket=True, cage=False, tries=(0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9)):
        """벽걸이 실외기 (브래킷 · 배관 · 선택적 보호망). 창 · 간판과 겹치면 옆으로 옮기고, 자리가 없으면 생략."""
        f = self.face(side)
        top = 0.74 if cage else 0.66
        bottom = z - 0.42 if bracket else z      # 브래킷 지지대가 아래로 내려온다
        for dx in tries:
            uu = u + dx
            if f.fits(FIXTURE, uu - 0.5, uu + 0.5, bottom, z + top, 0, d + 0.22) and \
                    self.in_lot(f, uu - 0.5, uu + 0.5, d + 0.22):
                break
        else:
            return False
        f.box(uu - 0.43, uu + 0.43, z, z + 0.62, d - 0.17, d + 0.17, "ac", attached=False)
        f.disc(uu - 0.1, z + 0.31, d + 0.17, 0.22, 0.02, "metal_dark")
        f.box(uu + 0.28, uu + 0.32, z + 0.35, z + 0.39, 0, d - 0.17, "metal")           # 냉매 배관
        if bracket:
            for bu in (uu - 0.38, uu + 0.34):
                f.box(bu, bu + 0.04, z - 0.08, z, 0, d + 0.2, "metal_dark")
                f.box(bu, bu + 0.04, z - 0.4, z - 0.08, 0, 0.04, "metal_dark")
        if cage:
            f.box(uu - 0.48, uu + 0.48, z + 0.68, z + 0.72, 0, d + 0.21, "grille")
            for k in range(9):
                gu = uu - 0.46 + 0.92 * k / 8
                f.box(gu - 0.01, gu + 0.01, z - 0.04, z + 0.68, d + 0.19, d + 0.21, "grille", attached=False)
        f.reserve(FIXTURE, uu - 0.5, uu + 0.5, bottom, z + top, 0, d + 0.22, "ac")
        return True

    def downpipe(self, side, u, top=None):
        """우수관 + 상부 깔때기 + 고정 밴드 + 하부 꺾임"""
        f = self.face(side)
        top = top if top is not None else self.height + 0.9
        if not f.fits(FIXTURE, u - 0.1, u + 0.1, 0.03, top, 0, 0.3) or not self.in_lot(f, u - 0.1, u + 0.1, 0.3):
            return False
        f.box(u - 0.05, u + 0.05, 0.15, top - 0.25, 0.05, 0.15, "metal_dark")
        f.box(u - 0.09, u + 0.09, top - 0.25, top, 0.03, 0.2, "metal_dark")
        z = 0.8
        while z < top - 0.5:
            f.box(u - 0.07, u + 0.07, z, z + 0.04, 0, 0.17, "metal_dark")
            z += 1.6
        f.box(u - 0.05, u + 0.05, 0.03, 0.15, 0.05, 0.3, "metal_dark")
        f.reserve(FIXTURE, u - 0.1, u + 0.1, 0.03, top, 0, 0.3, "downpipe")
        return True

    def gas_pipe(self, side, z, riser_u):
        """노란 가스관: 수평관(창 · 간판을 자동으로 피해 끊김) + 지면에서 올라오는 수직관 + 계량기"""
        f = self.face(side)
        if f.fits(FIXTURE, riser_u - 0.06, riser_u + 0.06, 0.03, z + 0.05, 0, 0.1) and \
                f.fits(FIXTURE, riser_u - 0.3, riser_u + 0.3, 1.0, 1.55, 0, 0.2):
            f.box(riser_u - 0.03, riser_u + 0.03, 0.03, z + 0.05, 0.04, 0.1, "gas_pipe")
            f.reserve(FIXTURE, riser_u - 0.06, riser_u + 0.06, 0.03, 1.0, 0, 0.1, "gas_riser_low")
            f.reserve(FIXTURE, riser_u - 0.06, riser_u + 0.06, 1.55, z + 0.05, 0, 0.1, "gas_riser")
            f.box(riser_u - 0.25, riser_u + 0.25, 1.0, 1.5, 0, 0.18, "ac")
            f.box(riser_u - 0.12, riser_u + 0.12, 1.2, 1.4, 0.18, 0.19, "glass", attached=False)
            f.reserve(FIXTURE, riser_u - 0.3, riser_u + 0.3, 1.0, 1.55, 0, 0.2, "meter")
        f.band(z, z + 0.05, 0.1, "gas_pipe", name="gas_pipe")

    def windows(self, side, levels, n, w, h, sill=0.9, margin=1.0, lit=0.35, style="sliding", grille=False,
                blinds=True):
        f = self.face(side)
        span = f.width - 2 * margin
        placed = 0
        for z in levels:
            for i in range(n):
                u = margin + span * (i + 0.5) / n
                if f.window(u, z + sill, w, h, style=style, lit=self.chance(lit), grille=grille,
                            blind=self.blind() if blinds else 0.0):
                    placed += 1
        return placed

    # -- 간판 ---------------------------------------------------------------

    def sign_band(self, side, u0, u1, z0, z1, text, sub=None, out=0.32, mat="sign", letters="letters", logo=None,
                  logo_emit=2.0):
        """가로 간판: 패널 + 테두리 + 입체 채널 글자 (+ 보조 문구). logo 키의 실제 로고(logos/<키>.svg)가 있으면
        본 문구 대신 로고를 붙인다"""
        f = self.face(side)
        if not f.fits(SIGN, u0 - 0.05, u1 + 0.05, z0 - 0.07, z1 + 0.07, 0, out + 0.12):
            raise ValueError(f"{side}: 간판 '{text}' 자리가 다른 요소와 겹칩니다")
        f.box(u0, u1, z0, z1, 0, out, mat)
        f.box(u0 - 0.04, u1 + 0.04, z1, z1 + 0.06, 0, out + 0.04, "frame_dark")
        f.box(u0 - 0.04, u1 + 0.04, z0 - 0.06, z0, 0, out + 0.04, "frame_dark")
        f.box(u0 - 0.04, u0, z0, z1, 0, out + 0.04, "frame_dark")
        f.box(u1, u1 + 0.04, z0, z1, 0, out + 0.04, "frame_dark")
        h = z1 - z0
        logo = logo or BRAND_LOGOS.get(text)
        mw, mh, zc = (u1 - u0) * 0.86, h * (0.56 if sub else 0.66), z0 + h * (0.62 if sub else 0.5)
        parts = self.logo(logo, mw, mh, 0.04) if logo else None
        if parts:
            self.put_logo(f, parts, logo, (u0 + u1) / 2, zc, out, emit=logo_emit, kind=None)
        else:
            t = self.letters(text, mw, mh, 0.05)
            if t is not None:
                f.text(t, (u0 + u1) / 2, zc, out, letters, kind=None)
        if sub:
            t2 = self.letters(sub, (u1 - u0) * 0.7, h * 0.2, 0.03)
            if t2 is not None:
                f.text(t2, (u0 + u1) / 2, z0 + h * 0.2, out, letters, kind=None)
        f.reserve(SIGN, u0 - 0.05, u1 + 0.05, z0 - 0.07, z1 + 0.07, 0, out + 0.12, "sign:" + text)

    def wall_text(self, side, text, u, z, max_w, max_h, mat="letters", extrude=0.06, logo=None, logo_emit=2.0):
        """벽에 직접 붙인 채널 글자 (logo 키의 실제 로고가 있으면 로고)"""
        f = self.face(side)
        logo = logo or BRAND_LOGOS.get(text)
        parts = self.logo(logo, max_w, max_h, extrude) if logo else None
        if parts:
            w, h, depth = parts[0][2:5]
            if not f.fits(SIGN, u - w / 2, u + w / 2, z - h / 2, z + h / 2, 0, depth + 0.02):
                raise ValueError(f"{side}: 로고 '{logo}' 자리가 다른 요소와 겹칩니다")
            self.put_logo(f, parts, logo, u, z, 0.02, emit=logo_emit, name="logo:" + logo)
            return True
        t = self.letters(text, max_w, max_h, extrude)
        if t is None:
            return False
        _, _, w, h, depth = t
        if not f.fits(SIGN, u - w / 2, u + w / 2, z - h / 2, z + h / 2, 0, depth + 0.02):
            raise ValueError(f"{side}: 글자 '{text}' 자리가 다른 요소와 겹칩니다")
        f.text(t, u, z, 0.02, mat)
        return True

    def vertical_sign(self, side, u, z0, z1, text, out=1.3, t=0.5, mat="sign2", letters="letters"):
        """건물 모서리에서 튀어나온 세로 간판 (양면에 한 자씩 세로로)"""
        f = self.face(side)
        if not f.fits(FIXTURE, u - t / 2 - 0.1, u + t / 2 + 0.1, z0, z1, 0, 0.15 + out):
            raise ValueError(f"{side}: 세로 간판 '{text}' 자리가 다른 요소와 겹칩니다")
        f.box(u - t / 2, u + t / 2, z0, z1, 0.15, 0.15 + out, mat, attached=False)
        f.box(u - t / 2 - 0.03, u + t / 2 + 0.03, z1, z1 + 0.06, 0.12, 0.18 + out, "frame_dark", attached=False)
        f.box(u - t / 2 - 0.03, u + t / 2 + 0.03, z0 - 0.06, z0, 0.12, 0.18 + out, "frame_dark", attached=False)
        for zz in (z0 + 0.4, z1 - 0.55):
            f.box(u - 0.08, u + 0.08, zz, zz + 0.15, 0, 0.15, "metal_dark")
        f.reserve(FIXTURE, u - t / 2 - 0.1, u + t / 2 + 0.1, z0, z1, 0, 0.15 + out, "vsign:" + text)
        chars = [c for c in text if c.strip()]
        if self.text_fn is None or not chars:
            return
        slot = (z1 - z0) / len(chars)
        for i, ch in enumerate(chars):
            tm = self.letters(ch, out * 0.78, slot * 0.78, 0.04)
            if tm is None:
                continue
            verts, faces, _, _, depth = tm
            zc = z1 - slot * (i + 0.5)
            for sgn in (-1, 1):
                # 판의 +u 면을 보는 사람에게는 +d(벽에서 멀어지는 쪽)가 왼쪽이므로 -lx
                pts = [f.p(u + sgn * (t / 2 + depth / 2 + lz), zc + ly,
                           0.15 + out / 2 + (-lx if sgn > 0 else lx)) for lx, ly, lz in verts]
                self.m.add(pts, faces, letters)

    def lightbox(self, side, u, z, w, h, text, mat="sign", letters="letters", out=0.18, logo=None, logo_emit=2.0):
        """작은 사각 간판 (돌출 아님). logo 키의 실제 로고가 있으면 문구 대신 로고"""
        f = self.face(side)
        if not f.fits(SIGN, u - w / 2 - 0.03, u + w / 2 + 0.03, z, z + h, 0, out + 0.08):
            return False
        f.box(u - w / 2, u + w / 2, z, z + h, 0, out, mat)
        f.box(u - w / 2 - 0.03, u + w / 2 + 0.03, z, z + h, 0, 0.02, "frame_dark")
        logo = logo or BRAND_LOGOS.get(text)
        parts = self.logo(logo, w * 0.84, h * 0.6, 0.03) if logo else None
        if parts:
            self.put_logo(f, parts, logo, u, z + h / 2, out, emit=logo_emit, kind=None)
        else:
            t = self.letters(text, w * 0.84, h * 0.6, 0.03)
            if t is not None:
                f.text(t, u, z + h / 2, out, letters, kind=None)
        f.reserve(SIGN, u - w / 2 - 0.03, u + w / 2 + 0.03, z, z + h, 0, out + 0.08, "lightbox:" + text)
        return True

    # -- 앞 공간 ---------------------------------------------------------------

    def awning(self, side, u0, u1, z, depth=2.4, drop=0.4, valance=0.3, mat="awning"):
        """경사 차양 (판) + 앞 처마 + 팔 + 고정 바"""
        f = self.face(side)
        if not f.fits(FOREGROUND, u0, u1, z - drop - valance, z + 0.1, 0, depth):
            raise ValueError(f"{side}: 차양 자리가 다른 요소와 겹칩니다")
        self.m.slab([f.p(u0, z, 0), f.p(u1, z, 0), f.p(u1, z - drop, depth), f.p(u0, z - drop, depth)], 0.04, mat)
        f.box(u0, u1, z - drop - valance, z - drop, depth - 0.03, depth, mat, attached=False)
        f.box(u0, u1, z, z + 0.1, 0, 0.12, "metal")
        for uu in (u0 + 0.12, u1 - 0.12):
            self.m.beam(f.p(uu, z - 0.7, 0.02), f.p(uu, z - drop - 0.02, depth - 0.05), 0.04, 0.04, "metal")
        f.reserve(FOREGROUND, u0, u1, z - drop - valance, z + 0.1, 0, depth, "awning")

    def canopy(self, side, u0, u1, z, depth=1.5, mat="trim"):
        """평 캐노피 (콘크리트 · 금속)"""
        f = self.face(side)
        if not f.fits(FOREGROUND, u0, u1, z, z + 0.18, 0, depth):
            raise ValueError(f"{side}: 캐노피 자리가 다른 요소와 겹칩니다")
        f.box(u0, u1, z, z + 0.18, 0, depth, mat)
        f.box(u0, u1, z - 0.06, z, depth - 0.06, depth, "frame_dark", attached=False)
        f.reserve(FOREGROUND, u0, u1, z - 0.06, z + 0.18, 0, depth, "canopy")

    def aquarium(self, side, u, w=1.6, d0=0.4, depth=0.9):
        """횟집 수족관: 스테인리스 받침 + 물 + 유리 + 모서리 기둥 + 뚜껑 + 산소 펌프 · 호스"""
        f = self.face(side)
        if not f.fits(FOREGROUND, u - w / 2, u + w / 2, 0.03, 2.05, d0, d0 + depth):
            raise ValueError(f"{side}: 수족관 자리가 다른 요소와 겹칩니다")
        a, b = u - w / 2, u + w / 2
        f.box(a, b, 0.03, 0.75, d0, d0 + depth, "stainless", attached=False)
        f.box(a + 0.04, b - 0.04, 0.75, 1.55, d0 + 0.04, d0 + depth - 0.04, "water", attached=False)
        f.box(a + 0.04, b - 0.04, 0.75, 1.76, d0 + depth - 0.03, d0 + depth - 0.01, "glass_tank", attached=False)
        for uu in (a, b - 0.04):
            for dd in (d0, d0 + depth - 0.04):
                f.box(uu, uu + 0.04, 0.75, 1.78, dd, dd + 0.04, "stainless", attached=False)
        f.box(a, b, 1.76, 1.82, d0, d0 + depth, "stainless", attached=False)
        f.box(u - 0.15, u + 0.15, 1.82, 2.0, d0 + 0.3, d0 + 0.6, "ac", attached=False)
        self.m.beam(f.p(u, 1.95, d0 + 0.3), f.p(u, 1.95, max(d0 - 0.25, 0.02)), 0.025, 0.025, "plastic_white")
        f.reserve(FOREGROUND, u - w / 2, u + w / 2, 0.03, 2.05, d0, d0 + depth, "aquarium")

    def fish_props(self, side, u, d=0.6):
        """스티로폼 상자 더미 + 빨간 고무 대야"""
        f = self.face(side)
        if not f.fits(FOREGROUND, u - 0.75, u + 0.75, 0.03, 1.0, d - 0.35, d + 0.35):
            return False
        for k in range(3):
            o = 0.03 if k % 2 else -0.02
            f.box(u - 0.7 + o, u - 0.1 + o, 0.03 + k * 0.28, 0.31 + k * 0.28, d - 0.2, d + 0.2, "styrofoam",
                  attached=False)
        x, y = f.xy(u + 0.4, d)
        self.m.cylinder(x, y, 0.33, 0.03, 0.3, "basin_red", n=16)
        f.reserve(FOREGROUND, u - 0.75, u + 0.75, 0.03, 1.0, d - 0.35, d + 0.35, "fish_props")
        return True

    def balcony(self, side, u0, u1, z, depth=1.2, rail="bars"):
        """발코니: 바닥 판(FIXTURE) + 앞 · 옆 난간(FOREGROUND)"""
        f = self.face(side)
        if not f.fits(FIXTURE, u0, u1, z - 0.15, z + 0.05, 0, depth):
            raise ValueError(f"{side}: 발코니 자리가 다른 요소와 겹칩니다")
        f.box(u0, u1, z - 0.15, z + 0.05, 0, depth, "concrete")
        f.reserve(FIXTURE, u0, u1, z - 0.15, z + 0.05, 0, depth, "balcony")
        hz = z + 0.05
        pts = [(f.xy(u0 + 0.03, depth - 0.04), f.xy(u1 - 0.03, depth - 0.04)),
               (f.xy(u0 + 0.03, 0.02), f.xy(u0 + 0.03, depth - 0.04)),
               (f.xy(u1 - 0.03, 0.02), f.xy(u1 - 0.03, depth - 0.04))]
        for (xa, ya), (xb, yb) in pts:
            x0, x1 = sorted((xa, xb))
            y0, y1 = sorted((ya, yb))
            self.rail_geom(x0 - 0.02, x1 + 0.02, y0 - 0.02, y1 + 0.02, hz, 1.05, rail)
        f.reserve(FOREGROUND, u0, u1, hz, hz + 1.05, depth - 0.07, depth, "rail_front")
        f.reserve(FOREGROUND, u0, u0 + 0.06, hz, hz + 1.05, 0, depth - 0.07, "rail_l")
        f.reserve(FOREGROUND, u1 - 0.06, u1, hz, hz + 1.05, 0, depth - 0.07, "rail_r")

    def plinth(self, h=0.45, out=0.05, mat="stone_base"):
        for s in SIDES:
            if self.zones.get(s) and self.zones[s][0][0] <= 0.1:
                self.face(s).band(0.03, h, out, mat, name="plinth")

    def bands(self, levels, sides=("front",), mat="trim", h=0.16, out=0.08):
        for s in sides:
            for z in levels:
                self.face(s).band(z - h / 2, z + h / 2, out, mat)

    def gable_roof(self, axis, rise, overhang=0.5, thickness=0.14, mat="roof_tile", gable_mat="wall_side",
                   fascia="trim"):
        """박공 지붕. axis='x' 면 용마루가 X(정면과 평행), 'y' 면 Y(정면에 박공 삼각형)."""
        x0, x1, y0, y1, h = self.x0, self.x1, self.y0, self.y1, self.height
        o, t = overhang, thickness
        if axis == "x":
            ym = (y0 + y1) / 2
            k = rise / (ym - y0)
            ze = h - k * o
            self.m.slab([(x0 - o, y0 - o, ze + t), (x1 + o, y0 - o, ze + t), (x1 + o, ym, h + rise + t),
                         (x0 - o, ym, h + rise + t)], t, mat)
            self.m.slab([(x0 - o, ym, h + rise + t), (x1 + o, ym, h + rise + t), (x1 + o, y1 + o, ze + t),
                         (x0 - o, y1 + o, ze + t)], t, mat)
            self.m.box(x0 - o, x1 + o, ym - 0.12, ym + 0.12, h + rise + t - 0.03, h + rise + t + 0.09, "metal_dark")
            for xx, off in ((x0, (0.0, 0, 0)), (x1, (0.0, 0, 0))):
                self.m.tri_prism((xx, y0, h), (xx, y1, h), (xx, ym, h + rise),
                                 (-0.02 if xx == x0 else 0.02, 0, 0), gable_mat)
            for yy, sgn in ((y0 - o, -1), (y1 + o, 1)):
                self.m.box(x0 - o, x1 + o, yy - 0.03 if sgn < 0 else yy, yy if sgn < 0 else yy + 0.03,
                           ze - 0.2 + t, ze + t, fascia)
        else:
            xm = (x0 + x1) / 2
            k = rise / (xm - x0)
            ze = h - k * o
            self.m.slab([(x0 - o, y0 - o, ze + t), (xm, y0 - o, h + rise + t), (xm, y1 + o, h + rise + t),
                         (x0 - o, y1 + o, ze + t)], t, mat)
            self.m.slab([(xm, y0 - o, h + rise + t), (x1 + o, y0 - o, ze + t), (x1 + o, y1 + o, ze + t),
                         (xm, y1 + o, h + rise + t)], t, mat)
            self.m.box(xm - 0.12, xm + 0.12, y0 - o, y1 + o, h + rise + t - 0.03, h + rise + t + 0.09, "metal_dark")
            for yy in (y0, y1):
                self.m.tri_prism((x0, yy, h), (x1, yy, h), (xm, yy, h + rise),
                                 (0, -0.02 if yy == y0 else 0.02, 0), gable_mat)
        self.top = max(self.top, h + rise + t + 0.09)
        self.roof_reserve("gable_roof", x0 - o, x1 + o, y0 - o, y1 + o, h, h + rise + t + 0.1)


# ---------------------------------------------------------------------------
# 검사
# ---------------------------------------------------------------------------

def validate(b, extra_mats=None):
    """겹침 · 부지 이탈 · 재질 누락 보고서 (모두 비어 있어야 정상)"""
    defined = set(materials.BASE) | set(b.mats) | set(extra_mats or {})
    hw, hd = b.lw / 2 + 1e-4, b.ld / 2 + 1e-4
    outside = [v for v in b.m.verts if abs(v[0]) > hw or abs(v[1]) > hd or v[2] < -0.31]
    return {
        "facade": conflicts(b.slots),
        "roof": box_conflicts(b.roof),
        "outside_lot": len(outside),
        "missing_materials": sorted(set(b.m.mat_names) - defined),
    }


def stub_text(text, max_w, max_h, extrude=0.05):
    """테스트용 글자 대용 박스 (글자 비율 0.9)"""
    n = max(len(text.replace(" ", "")), 1)
    w = min(max_w, max_h * 0.9 * n)
    h = min(max_h, w / (0.9 * n))
    m = Mesh()
    m.box(-w / 2, w / 2, -h / 2, h / 2, -extrude, extrude, "x")
    return m.verts, m.faces, w, h, 2 * extrude


def stub_logo(key, max_w, max_h, depth=0.03):
    """테스트용 로고 대용: 두 색 조각 (바탕 사각 + 앞 작은 사각), 최대 크기를 꽉 채운다"""
    a, b = Mesh(), Mesh()
    a.box(-max_w / 2, max_w / 2, -max_h / 2, max_h / 2, -depth / 2, depth / 2 - 0.002, "x")
    b.box(-max_w / 4, max_w / 4, -max_h / 4, max_h / 4, -depth / 2, depth / 2, "x")
    return [(a.verts, a.faces, max_w, max_h, depth, (0.0, 0.3, 0.1)),
            (b.verts, b.faces, max_w, max_h, depth, (1.0, 1.0, 1.0))]


stub_text.logo = stub_logo


# ---------------------------------------------------------------------------
# 공통 재질 조각
# ---------------------------------------------------------------------------

def render(color, control=True, grime=0.25):
    """도장 벽 (색상 변형 대상)"""
    return {"color": color, "pattern": "noise", "scale": 1.2, "rough": 0.85, "grime": grime,
            "control": (1, 0, 0) if control else (0, 0, 0)}


def tile(color, color2, size=(0.6, 0.3), mortar=(0.75, 0.72, 0.66), rough=0.35):
    return {"color": color, "color2": color2, "pattern": "tile", "scale": size, "mortar": 0.01,
            "mortar_color": mortar, "rough": rough, "bump": 0.25, "grime": 0.2}


def sign(color, glow=0.6):
    return {"color": color, "rough": 0.4, "emit": tuple(min(1.0, c * 1.4 + 0.05) for c in color),
            "emit_strength": glow}


def stripes(c1, c2, width=0.5):
    return {"color": c1, "color2": c2, "pattern": "stripes", "scale": width, "rough": 0.7, "control": (0, 1, 0)}


BRICK = {"color": (0.42, 0.16, 0.10), "color2": (0.36, 0.13, 0.08), "pattern": "tile", "scale": (0.42, 0.14),
         "mortar": 0.012, "mortar_color": (0.62, 0.58, 0.52), "rough": 0.8, "bump": 0.4, "grime": 0.2}


def side_details(b, back_door_u=None, gas_side="right", gas_z=None, levels=(), side_n=2, back_n=2):
    """옆 · 뒷면 공통: 창, 뒷문, 우수관, 가스관 (자리가 없으면 자동으로 생략)"""
    if levels:
        b.windows("left", levels, side_n, 1.3, 1.25, margin=2.4)
        b.windows("right", levels, side_n, 1.3, 1.25, margin=2.4)
    if back_door_u is not None:
        b.face("back").door(back_door_u, 0.9, 2.1, leaf="door_metal", canopy=True)
    b.windows("back", [0.03] + list(levels), back_n, 1.1, 1.0, sill=1.2, margin=2.8, grille=True, lit=0.2)
    b.downpipe("left", 0.35)
    b.downpipe("right", b.d - 0.35)
    if gas_side:
        b.gas_pipe(gas_side, gas_z if gas_z is not None else 3.0, b.face(gas_side).width - 1.2)


# ---------------------------------------------------------------------------
# 1. 바다횟집 — 2x3, 3층, 베이지 타일, 수족관 3개, 청백 줄무늬 차양
# ---------------------------------------------------------------------------

def hoetjip01(text_fn=None):
    b = Building((2, 3), 15.2, 15.0, seed=11, text_fn=text_fn)
    b.mats.update({
        "wall": tile((0.66, 0.56, 0.44), (0.60, 0.50, 0.39)),
        "wall_side": render((0.78, 0.76, 0.72)),
        "sign": sign((0.02, 0.10, 0.42)),
        "sign_small": sign((0.80, 0.70, 0.10), 0.5),
        "awning": stripes((0.10, 0.25, 0.60), (0.90, 0.90, 0.88)),
    })
    g, u = 4.2, 3.2
    b.lot_slab()
    b.shell(g + 2 * u)
    f = b.face("front")
    f.storefront(0.5, b.w - 0.5, 0.03, 3.3, doors=[(b.w / 2, 1.8)])
    b.sign_band("front", 0.25, b.w - 0.25, 3.42, 4.58, "바다횟집", "자연산 활어 · 회 · 물회")
    b.awning("front", 0.6, b.w - 0.6, 3.25, depth=2.6, drop=0.45)
    for uu in (2.0, 4.3, b.w - 2.0):
        b.aquarium("front", uu, d0=0.45)
    b.fish_props("front", b.w - 4.3, d=0.75)
    b.windows("front", [g, g + u], 3, 2.8, 1.6, sill=0.85, margin=0.9)
    b.lightbox("front", 5.37, g + 1.0, 1.1, 0.7, "단체석", mat="sign_small", letters="letters")
    side_details(b, back_door_u=b.w - 2.2, levels=[g, g + u], gas_z=3.7)
    b.ac_wall("back", 7.6, 1.4)
    b.ac_wall("back", 7.6, 4.8)
    b.bands([g, g + u], ("front", "left", "right"))
    b.plinth()
    b.parapet()
    top = b.stair_house(b.x0 + 0.6, b.x0 + 3.8, b.y1 - 3.9, b.y1 - 0.6)
    b.water_tank(b.x0 + 2.2, b.y1 - 2.25, top, r=0.75, h=1.2)
    for i in range(3):
        b.ac_roof(b.x1 - 1.4 - i * 1.25, b.y1 - 1.2, b.height)
    b.finalize()
    return b, "바다횟집"


# ---------------------------------------------------------------------------
# 2. 일산회센터 (실제: 해수욕장10길 60, 2007년) — 3x3, 2층 넓은 횟집, 흰 도장벽, 수족관 6개, 2층 통창, 옥상 현수막
# ---------------------------------------------------------------------------

def hoetjip02(text_fn=None):
    b = Building((3, 3), 23.0, 14.5, seed=12, text_fn=text_fn)
    b.mats.update({
        "wall": render((0.86, 0.85, 0.82)),
        "wall_side": render((0.80, 0.79, 0.76)),
        "sign": sign((0.55, 0.04, 0.03)),
        "awning": stripes((0.70, 0.08, 0.06), (0.92, 0.90, 0.86), 0.6),
    })
    g, u = 4.4, 3.6
    b.lot_slab()
    b.shell(g + u)
    f = b.face("front")
    f.storefront(0.5, b.w - 0.5, 0.03, 3.4, bay=1.4, doors=[(b.w / 2, 2.0)])
    b.sign_band("front", 0.3, b.w - 0.3, 3.52, 4.8, "일산회센터", "활어 · 대게 · 물회 · 매운탕")
    b.awning("front", 0.5, b.w - 0.5, 3.33, depth=2.9, drop=0.5)
    for uu in (2.0, 4.6, 7.2, b.w - 7.2, b.w - 4.6, b.w - 2.0):
        b.aquarium("front", uu, w=2.2, d0=0.45)
    for i in range(4):
        uu = 1.2 + (b.w - 2.4) * (i + 0.5) / 4
        f.window(uu, g + 0.55, 4.4, 2.2, style="sliding", lit=b.chance(0.6), blind=b.blind())
    side_details(b, back_door_u=3.0, levels=[g], side_n=2, back_n=3, gas_z=3.9)
    b.ac_wall("back", 11.5, 1.4)
    b.ac_wall("back", 7.0, 1.4)
    b.bands([g], ("front", "left", "right"))
    b.plinth()
    b.parapet()
    z = b.height
    b.stair_house(b.x1 - 4.0, b.x1 - 0.8, b.y1 - 4.0, b.y1 - 0.8)
    for i in range(4):
        b.ac_roof(b.x0 + 1.5 + i * 1.3, b.y1 - 1.2, z)
    b.water_tank(b.x0 + 2.0, b.y0 + 2.6, z)
    # 옥상 현수막: 기둥 + 판 + 글자
    bx0, bx1, by = b.x0 + 4.0, b.x1 - 6.0, b.y0 + 0.65
    b.m.box(bx0, bx1, by, by + 0.08, z + 1.1, z + 2.6, "sign")
    for px in (bx0 + 0.2, (bx0 + bx1) / 2, bx1 - 0.2):
        b.m.box(px - 0.05, px + 0.05, by + 0.08, by + 0.18, z, z + 2.65, "metal_dark")
    t = b.letters("싱싱한 자연산 활어", bx1 - bx0 - 1.0, 1.0, 0.03)
    if t:
        Facade(b.m, "front", bx0, bx1, by, by + 0.08).text(t, (bx1 - bx0) / 2, z + 1.85, 0.0, "letters", kind=None)
    b.roof_reserve("banner", bx0, bx1, by - 0.1, by + 0.2, z, z + 2.65)
    b.finalize()
    return b, "일산회센터"


# ---------------------------------------------------------------------------
# 3. 카페 파도 — 2x3, 3층 + 루프탑, 짙은 금속 패널, 2층 커튼월, 발코니, 세로 간판
# ---------------------------------------------------------------------------

def cafe01(text_fn=None):
    b = Building((2, 3), 14.0, 14.0, seed=13, text_fn=text_fn)
    b.mats.update({
        "wall": {"color": (0.17, 0.18, 0.19), "color2": (0.15, 0.16, 0.17), "pattern": "panel",
                 "scale": (1.2, 0.6), "mortar": 0.006, "mortar_color": (0.05, 0.05, 0.05), "rough": 0.35,
                 "metal": 0.5, "bump": 0.15},
        "wall_side": render((0.82, 0.80, 0.76), grime=0.15),
        "sign2": sign((0.85, 0.80, 0.70), 0.4),
    })
    g, u = 4.4, 3.4
    b.lot_slab()
    b.shell(g + 2 * u)
    f = b.face("front")
    f.storefront(0.6, b.w - 0.6, 0.03, g - 0.35, bay=1.5, transom=2.6, doors=[(b.w - 2.4, 1.8)])
    b.balcony("front", 0.4, b.w - 0.4, g, depth=1.6, rail="bars")
    f.storefront(1.0, b.w - 0.6, g + 0.2, g + u - 0.2, bay=1.6, transom=1.0, kick=0.85, name="curtainwall")
    b.windows("front", [g + u], 4, 2.3, 1.7, sill=0.5, margin=0.8, style="casement", lit=0.5)
    b.wall_text("front", "CAFE PADO", b.w * 0.45, g + 2 * u - 0.6, 6.5, 0.62)
    b.vertical_sign("front", 0.45, g + 1.3, g + 2 * u - 0.4, "카페파도", out=1.2, t=0.45)
    side_details(b, back_door_u=2.5, levels=[g, g + u], side_n=3, gas_z=3.8)
    b.plinth()
    b.parapet(h=0.45, mat="wall")
    z = b.height
    # 루프탑: 데크, 난간, 파라솔 테이블, 계단실, 실외기
    pt = b.parapet_t
    b.m.box(b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y1 - 5.0, z, z + 0.15, "deck", skip=(BOTTOM,))
    b.roof_reserve("deck", b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y1 - 5.0, z, z + 0.15)
    zr = z + 0.15
    b.roof_rail(b.x0 + pt + 0.05, b.x1 - pt - 0.05, b.y0 + pt + 0.05, b.y0 + pt + 0.11, zr)
    b.roof_rail(b.x0 + pt + 0.05, b.x0 + pt + 0.11, b.y0 + pt + 0.11, b.y1 - 5.0, zr)
    b.roof_rail(b.x1 - pt - 0.11, b.x1 - pt - 0.05, b.y0 + pt + 0.11, b.y1 - 5.0, zr)
    for px in (b.x0 + 3.0, 0.0, b.x1 - 3.0):
        py = b.y0 + 3.6
        b.m.cylinder(px, py, 0.04, zr, zr + 2.4, "metal", n=8)
        b.m.cone(px, py, 1.45, zr + 2.0, zr + 2.6, "parasol", n=16)
        b.m.cylinder(px, py, 0.45, zr + 0.70, zr + 0.75, "deck", n=16)
        b.m.cylinder(px, py, 0.06, zr, zr + 0.7, "metal_dark", n=8)
        for a in range(3):
            ang = a * 2.09 + 0.5
            b.m.cylinder(px + 0.85 * math.cos(ang), py + 0.85 * math.sin(ang), 0.2, zr, zr + 0.45, "wall_side", n=10)
        b.roof_reserve("parasol", px - 1.46, px + 1.46, py - 1.46, py + 1.46, zr, zr + 2.6)
    b.stair_house(b.x0 + 0.6, b.x0 + 4.2, b.y1 - 4.4, b.y1 - 0.6)
    for i in range(3):
        b.ac_roof(b.x1 - 1.2 - i * 1.25, b.y1 - 1.0, z)
    b.finalize()
    return b, "카페 파도"


# ---------------------------------------------------------------------------
# 4. 호텔 일산 — 3x4, 7층, 분홍빛 타일, 객실 창 + 실외기, 세로 간판, 옥상 대형 간판, 드라이브인 주차
# ---------------------------------------------------------------------------

def motel01(text_fn=None):
    b = Building((3, 4), 20.0, 18.0, seed=14, text_fn=text_fn)
    b.mats.update({
        "wall": tile((0.68, 0.54, 0.50), (0.63, 0.49, 0.45), mortar=(0.78, 0.74, 0.70)),
        "wall_side": render((0.80, 0.76, 0.72), grime=0.2),
        "sign": sign((0.30, 0.05, 0.35), 0.8),
        "sign2": sign((0.08, 0.05, 0.30), 0.8),
    })
    g, u, floors = 4.5, 3.0, 7
    levels = [g + i * u for i in range(floors - 1)]
    b.lot_slab()
    b.shell(g + (floors - 1) * u)
    f = b.face("front")
    f.storefront(0.6, 9.0, 0.03, 3.6, bay=1.4, doors=[(4.8, 2.0)])
    b.canopy("front", 0.9, 8.7, 3.8, depth=2.4)
    t = b.letters("HOTEL ILSAN", 6.6, 0.15, 0.03)
    if t:
        f.text(t, 4.8, 3.89, 2.4, "letters", kind=None)
    f.garage(11.0, b.w - 1.4, 0.03, 3.2)
    b.vertical_sign("front", b.w - 0.45, g + 0.5, b.height - 0.6, "호텔일산", out=1.6, t=0.55)
    for z in levels:
        for i in range(5):
            uu = 1.6 + (b.w - 3.6) * (i + 0.5) / 5
            if f.window(uu, z + 0.9, 1.7, 1.5, lit=b.chance(0.4), blind=b.blind()) and b.chance(0.6):
                b.ac_wall("front", uu + 1.35, z + 0.42)
    side_details(b, back_door_u=3.0, levels=levels, side_n=3, back_n=4, gas_z=4.2)
    b.bands(levels, ("front",), h=0.12, out=0.06)
    b.plinth()
    b.parapet()
    z = b.height
    sx0, sx1, sy = b.x0 + 3.0, b.x1 - 3.0, b.y0 + 2.0
    for px in [sx0 + 0.3 + (sx1 - sx0 - 0.6) * k / 4 for k in range(5)]:
        b.m.box(px - 0.08, px + 0.08, sy - 0.08, sy + 0.08, z, z + 5.4, "metal_dark")
        b.m.beam((px, sy, z + 4.0), (px, sy + 1.5, z + 0.05), 0.06, 0.06, "metal_dark")
    b.m.box(sx0, sx1, sy - 0.25, sy - 0.08, z + 2.4, z + 5.2, "sign")
    t = b.letters("HOTEL", (sx1 - sx0) * 0.85, 2.2, 0.08)
    if t:
        Facade(b.m, "front", sx0, sx1, sy - 0.25, sy).text(t, (sx1 - sx0) / 2, z + 3.8, 0.0, "letters", kind=None)
    b.roof_reserve("roof_sign", sx0 - 0.1, sx1 + 0.1, sy - 0.45, sy + 1.6, z, z + 5.4)
    b.stair_house(b.x1 - 4.5, b.x1 - 0.8, b.y1 - 5.5, b.y1 - 0.8, h=3.0)
    b.water_tank(b.x0 + 2.0, b.y1 - 2.2, z, r=1.0, h=1.8)
    b.water_tank(b.x0 + 4.4, b.y1 - 2.2, z, r=1.0, h=1.8)
    for i in range(4):
        b.ac_roof(b.x0 + 7.5 + i * 1.3, b.y1 - 1.2, z)
    b.finalize()
    return b, "호텔 일산"


# ---------------------------------------------------------------------------
# 5. 편의점 + 다가구 — 2x2, 3층 붉은 벽돌, 1층 편의점, 2~3층 발코니, 옆 계단 출입구
# ---------------------------------------------------------------------------

def shop01(text_fn=None):
    b = Building((2, 2), 14.0, 12.0, seed=15, text_fn=text_fn)
    b.mats.update({
        "wall": BRICK, "wall_side": BRICK,
        "sign": sign((0.90, 0.90, 0.88), 0.5),
        "accent": {"color": (0.92, 0.35, 0.02), "rough": 0.4, "emit": (1.0, 0.45, 0.05), "emit_strength": 0.6},
        "accent2": {"color": (0.0, 0.40, 0.25), "rough": 0.4, "emit": (0.05, 0.6, 0.35), "emit_strength": 0.6},
        "accent3": {"color": (0.80, 0.05, 0.05), "rough": 0.4, "emit": (1.0, 0.1, 0.05), "emit_strength": 0.6},
        "letters_dark": {"color": (0.0, 0.40, 0.25), "rough": 0.4, "emit": (0.05, 0.7, 0.4), "emit_strength": 1.2},
    })
    g, u = 4.0, 2.9
    b.lot_slab()
    b.shell(g + 2 * u)
    f = b.face("front")
    f.storefront(0.5, b.w - 0.5, 0.03, 3.05, bay=1.3, doors=[(2.2, 1.7)])
    b.sign_band("front", 0.2, b.w - 0.2, 3.15, 3.72, "7-ELEVEN", out=0.3, letters="letters_dark")
    for zz, mat in ((3.15, "accent"), (3.62, "accent2")):                     # 세븐일레븐 주황 · 초록 · 빨강 띠
        f.box(0.2, b.w - 0.2, zz, zz + 0.1, 0.3, 0.31, mat, attached=False)
    f.box(0.2, 1.4, 3.25, 3.62, 0.3, 0.31, "accent3", attached=False)
    for z in (g, g + u):
        b.balcony("front", 0.8, b.w - 0.8, z, depth=1.2)
        for uu in (3.4, b.w - 3.4):
            f.window(uu, z + 0.05, 2.6, 2.2, sill=None, lit=b.chance(0.4), blind=b.blind())
        b.ac_wall("front", b.w / 2, z + 0.06, d=0.6, bracket=False)
    b.face("left").door(3.0, 1.0, 2.2, leaf="door_metal")
    b.lightbox("left", 4.8, 1.6, 0.6, 0.35, "102호", mat="sign")
    side_details(b, back_door_u=None, levels=[g, g + u], side_n=2, gas_side="right", gas_z=3.6)
    b.plinth()
    b.parapet(mat="wall_side")
    z = b.height
    b.water_tank(b.x1 - 1.6, b.y1 - 1.6, z, r=0.7, h=1.3)
    b.stair_house(b.x0 + 0.6, b.x0 + 3.4, b.y1 - 3.6, b.y1 - 0.6)
    b.ac_roof(1.0, b.y1 - 1.0, z)
    b.finalize()
    return b, "세븐일레븐"


# ---------------------------------------------------------------------------
# 6. 조개구이 — 2x2, 단층 경량 철골 + 줄무늬 천막 박공 지붕, 말아 올린 비닐, 화로 테이블
# ---------------------------------------------------------------------------

def grill01(text_fn=None):
    b = Building((2, 2), 14.0, 11.0, setback=1.5, seed=16, text_fn=text_fn)
    b.mats.update({
        "wall_side": {"color": (0.78, 0.78, 0.76), "pattern": "panel", "scale": (1.0, 3.2), "mortar": 0.01,
                      "mortar_color": (0.6, 0.6, 0.6), "rough": 0.5, "metal": 0.3, "control": (1, 0, 0)},
        "sign": sign((0.95, 0.75, 0.05)),
        "floor": {"color": (0.40, 0.39, 0.37), "pattern": "noise", "scale": 2.0, "rough": 0.6},
        "tent": stripes((0.75, 0.10, 0.08), (0.92, 0.90, 0.86), 0.9),
        "letters_red": {"color": (0.70, 0.05, 0.03), "rough": 0.4, "emit": (1.0, 0.1, 0.05), "emit_strength": 1.0},
    })
    h = 3.4
    b.lot_slab()
    x0, x1, y0, y1 = b.x0, b.x1, b.y0, b.y1
    m = b.m
    m.box(x0, x1, y0, y1, 0.03, 0.12, "floor", skip=(BOTTOM,))
    m.box(x0, x0 + 0.12, y0, y1, 0.12, h, "wall_side", skip=(BOTTOM,))
    m.box(x1 - 0.12, x1, y0, y1, 0.12, h, "wall_side", skip=(BOTTOM,))
    m.box(x0 + 0.12, x1 - 0.12, y1 - 0.12, y1, 0.12, h, "wall_side", skip=(BOTTOM,))
    for px in [x0 + 0.1 + (b.w - 0.2) * k / 5 for k in range(6)]:
        m.box(px - 0.06, px + 0.06, y0, y0 + 0.12, 0.12, h - 0.2, "metal_dark", skip=(BOTTOM,))
    m.box(x0, x1, y0, y0 + 0.15, h - 0.2, h, "metal_dark")
    m.cylinder_x(x0 + 0.2, x1 - 0.2, y0 - 0.1, h - 0.38, 0.14, "vinyl")
    for px in [x0 + 1.0 + (b.w - 2.0) * k / 5 for k in range(6)]:
        m.box(px - 0.03, px + 0.03, y0 - 0.26, y0 - 0.0, h - 0.24, h - 0.2, "metal_dark")
    ridge, ov, t = h + 1.8, 0.5, 0.12
    ym = (y0 + y1) / 2
    ze = h - (ridge - h) / (ym - y0) * ov
    m.slab([(x0 - ov, y0 - ov, ze + t), (x1 + ov, y0 - ov, ze + t), (x1 + ov, ym, ridge + t),
            (x0 - ov, ym, ridge + t)], t, "tent")
    m.slab([(x0 - ov, ym, ridge + t), (x1 + ov, ym, ridge + t), (x1 + ov, y1 + ov, ze + t),
            (x0 - ov, y1 + ov, ze + t)], t, "tent")
    m.box(x0 - ov, x1 + ov, ym - 0.12, ym + 0.12, ridge + t - 0.02, ridge + t + 0.08, "metal_dark")
    for side_x, dx in ((x0, 0.12), (x1 - 0.12, 0.12)):
        m.tri_prism((side_x, y0, h), (side_x, y1, h), (side_x, ym, ridge), (dx, 0, 0), "wall_side")
    for i in range(3):
        for j in range(2):
            tx, ty = x0 + 2.4 + i * 4.6, y0 + 3.0 + j * 3.6
            m.cylinder(tx, ty, 0.08, 0.12, 0.72, "metal_dark", n=8)
            m.cylinder(tx, ty, 0.55, 0.72, 0.78, "stainless", n=20)
            m.cylinder(tx, ty, 0.22, 0.78, 0.84, "metal_dark", n=12)
            m.cylinder(tx, ty, 0.04, 0.84, 2.5, "metal", n=6)            # 배연 덕트
            m.cylinder(tx, ty, 0.25, 2.5, 2.7, "metal", n=12)
            for a in range(4):
                ang = a * math.pi / 2 + 0.4
                mat = "plastic_red" if (a + i) % 2 else "plastic_blue"
                m.cylinder(tx + 0.95 * math.cos(ang), ty + 0.95 * math.sin(ang), 0.18, 0.12, 0.55, mat, n=10)
    m.box(x0 + 1.0, x0 + 5.0, y1 - 1.0, y1 - 0.12, 0.12, 1.0, "stainless", skip=(BOTTOM,))
    m.box(x1 - 2.3, x1 - 1.0, y1 - 0.9, y1 - 0.12, 0.12, 2.1, "ac", skip=(BOTTOM,))
    Facade(m, "front", x1 - 2.3, x1 - 1.0, y1 - 0.9, y1 - 0.12).box(0.08, 1.22, 0.35, 1.95, 0, 0.02, "glass_shop")
    f = Facade(m, "front", x0 + 1.0, x1 - 1.0, y0 - ov - 0.1, y0 - ov)
    f.box(0, f.width, h + 0.1, h + 1.3, 0, 0.12, "sign", attached=False)
    for uu in (0.6, f.width - 0.6):
        f.box(uu - 0.05, uu + 0.05, ze + t, h + 0.4, -0.25, -0.05, "metal_dark", attached=False)
    t2 = b.letters("조개구이 · 장어구이", f.width * 0.85, 0.75, 0.04)
    if t2:
        f.text(t2, f.width / 2, h + 0.7, 0.12, "letters_red", kind=None)
    b.height = ridge
    b.top = ridge + t + 0.1
    return b, "조개구이"


# ---------------------------------------------------------------------------
# 7. 대게 · 킹크랩 — 2x3, 2층, 옥상 앞의 대형 게 조형물, 대형 수조, 붉은 간판
# ---------------------------------------------------------------------------

def crab_sculpture(b, cx, cy, cz, s=1.0, mat="crab"):
    """옥상 게 조형물 (몸통 · 눈 · 다리 8 · 집게 2 · 받침대). 정면(-Y)을 본다."""
    m = b.m
    m.ellipsoid(cx, cy, cz, 1.5 * s, 1.05 * s, 0.45 * s, mat, nu=20, nv=10)
    m.ellipsoid(cx, cy + 0.05 * s, cz + 0.12 * s, 1.15 * s, 0.75 * s, 0.4 * s, mat, nu=16, nv=8)
    for sx in (-1, 1):
        ex = cx + sx * 0.32 * s
        m.cylinder(ex, cy - 0.8 * s, 0.05 * s, cz + 0.2 * s, cz + 0.62 * s, mat, n=8)
        m.ellipsoid(ex, cy - 0.8 * s, cz + 0.68 * s, 0.1 * s, 0.1 * s, 0.1 * s, "crab_eye", nu=10, nv=6)
        for k in range(4):                                  # 다리: 몸통 -> 무릎 -> 끝
            y = cy + (-0.45 + k * 0.35) * s
            hip = (cx + sx * 1.25 * s, y, cz)
            knee = (cx + sx * 2.35 * s, y + 0.12 * s, cz + 0.55 * s)
            tip = (cx + sx * 3.0 * s, y + 0.3 * s, cz - 0.5 * s)
            m.beam(hip, knee, 0.16 * s, 0.13 * s, mat)
            m.beam(knee, tip, 0.12 * s, 0.1 * s, mat)
        sh = (cx + sx * 0.8 * s, cy - 0.75 * s, cz)          # 집게 팔 -> 집게
        el = (cx + sx * 1.3 * s, cy - 1.75 * s, cz + 0.35 * s)
        m.beam(sh, el, 0.2 * s, 0.16 * s, mat)
        m.ellipsoid(el[0] + sx * 0.08 * s, el[1] - 0.45 * s, el[2] + 0.05 * s, 0.34 * s, 0.55 * s, 0.26 * s, mat,
                    nu=14, nv=8)
        m.beam((el[0] - sx * 0.12 * s, el[1] - 0.7 * s, el[2] + 0.12 * s),
               (el[0] - sx * 0.22 * s, el[1] - 1.15 * s, el[2] + 0.2 * s), 0.11 * s, 0.09 * s, mat)
    for sx in (-0.6, 0.6):                                   # 받침대
        b.m.box(cx + sx * s - 0.07, cx + sx * s + 0.07, cy - 0.07, cy + 0.07, b.height, cz - 0.4 * s, "metal_dark")


def crab01(text_fn=None):
    b = Building((2, 3), 15.0, 15.0, seed=17, text_fn=text_fn)
    b.mats.update({
        "wall": tile((0.80, 0.78, 0.74), (0.76, 0.74, 0.70), size=(0.9, 0.45), mortar=(0.6, 0.58, 0.55)),
        "wall_side": render((0.84, 0.82, 0.78)),
        "sign": sign((0.62, 0.05, 0.03)),
        "crab": {"color": (0.82, 0.22, 0.06), "color2": (0.70, 0.15, 0.04), "pattern": "noise", "scale": 3.0,
                 "rough": 0.35, "bump": 0.2},
        "crab_eye": {"color": (0.02, 0.02, 0.02), "rough": 0.1},
    })
    g, u = 4.4, 3.4
    b.lot_slab()
    b.shell(g + u)
    f = b.face("front")
    f.storefront(0.5, b.w - 0.5, 0.03, 3.3, doors=[(b.w - 3.0, 1.8)])
    b.sign_band("front", 0.25, b.w - 0.25, 3.5, 4.75, "대게 · 킹크랩", "산지직송 · 찜 · 회")
    b.canopy("front", 0.5, b.w - 0.5, 3.18, depth=1.9)
    for uu in (2.0, 5.0):
        b.aquarium("front", uu, w=2.6, d0=0.45, depth=1.0)
    b.fish_props("front", 8.0, d=0.8)
    for i in range(3):
        uu = 0.9 + (b.w - 1.8) * (i + 0.5) / 3
        f.window(uu, g + 0.7, 3.4, 2.0, lit=b.chance(0.6), blind=b.blind())
    side_details(b, back_door_u=b.w - 2.5, levels=[g], gas_z=3.9)
    b.ac_wall("back", 7.5, 1.4)
    b.bands([g], ("front", "left", "right"))
    b.plinth()
    b.parapet()
    z = b.height
    s, cy = 1.3, b.y0 + 1.9                      # 크기 1.3배, 다리 끝이 난간 위로 오도록 띄운다
    cz = z + 1.95
    crab_sculpture(b, 0.0, cy, cz, s=s)
    b.roof_reserve("crab_body", -3.1 * s - 0.1, 3.1 * s + 0.1, b.y0 + 0.3, cy + 1.3 * s, z, cz + 0.8 * s)
    b.roof_reserve("crab_claws", -1.95 * s, 1.95 * s, cy - 3.0 * s, b.y0 + 0.3, z + 1.15, cz + 0.8 * s)
    b.stair_house(b.x1 - 3.8, b.x1 - 0.6, b.y1 - 3.8, b.y1 - 0.6)
    for i in range(3):
        b.ac_roof(b.x0 + 1.4 + i * 1.25, b.y1 - 1.1, z)
    b.finalize()
    return b, "대게 · 킹크랩"


# ---------------------------------------------------------------------------
# 8. 근린상가 — 3x3, 5층, 층마다 다른 업종 간판 띠, 1층 약국 · 분식 + 계단 출입구, 세로 간판
# ---------------------------------------------------------------------------

FLOOR_SIGNS = [("노래연습장", (0.75, 0.12, 0.45), "노래방"), ("PC방", (0.10, 0.25, 0.70), "PC"),
               ("당구장", (0.08, 0.45, 0.25), "당구"), ("휘트니스", (0.85, 0.45, 0.05), "GYM")]


def mixed01(text_fn=None):
    b = Building((3, 3), 22.0, 16.0, seed=18, text_fn=text_fn)
    b.mats.update({
        "wall": {"color": (0.70, 0.69, 0.66), "color2": (0.66, 0.65, 0.62), "pattern": "panel", "scale": (1.2, 0.6),
                 "mortar": 0.006, "mortar_color": (0.45, 0.45, 0.44), "rough": 0.5, "bump": 0.1, "grime": 0.15},
        "wall_ground": {"color": (0.20, 0.20, 0.21), "color2": (0.17, 0.17, 0.18), "pattern": "panel",
                        "scale": (0.9, 0.6), "mortar": 0.004, "rough": 0.3},
        "wall_side": render((0.78, 0.72, 0.62)),
        "sign_pharm": sign((0.05, 0.40, 0.20)),
        "sign_food": sign((0.85, 0.30, 0.05)),
        "sign_bldg": sign((0.12, 0.12, 0.14), 0.3),
        "sign2": sign((0.75, 0.12, 0.45), 0.8),
        "cross": {"color": (0.1, 0.9, 0.3), "rough": 0.3, "emit": (0.1, 1.0, 0.35), "emit_strength": 4.0},
    })
    for i, (_, col, _) in enumerate(FLOOR_SIGNS):
        b.mats[f"sign_f{i + 2}"] = sign(col, 0.7)
    g, u = 4.2, 3.4
    floors = [g + k * u for k in range(4)]
    b.lot_slab()
    b.shell(g + 4 * u, zones={"front": [(0.03, g, "wall_ground"), (g, g + 4 * u, "wall")]})
    f = b.face("front")
    f.storefront(0.4, 9.4, 0.03, 3.3, bay=1.3, doors=[(2.0, 1.6)], name="pharmacy")
    f.door(11.0, 1.6, 2.4, leaf="glass_door", name="stair_hall")
    f.storefront(12.6, 21.6, 0.03, 3.3, bay=1.3, doors=[(20.0, 1.6)], name="snack")
    b.sign_band("front", 0.3, 9.5, 3.42, 4.08, "약국", mat="sign_pharm")
    for (a, c, d0, d1) in ((0.62, 1.22, 3.63, 3.87), (0.80, 1.04, 3.45, 4.05)):   # 약국 십자
        f.box(a, c, d0, d1, 0.32, 0.38, "cross", attached=False)
    b.sign_band("front", 12.5, 21.7, 3.42, 4.08, "김밥천국", mat="sign_food")
    b.lightbox("front", 11.0, 3.42, 2.3, 0.62, "일산빌딩", mat="sign_bldg")
    for (name, _, short), zf, k in zip(FLOOR_SIGNS, floors, range(2, 6)):
        b.sign_band("front", 0.5, b.w - 1.4, zf + 0.1, zf + 0.92, name, out=0.25, mat=f"sign_f{k}")
        for i in range(3):
            uu = 1.2 + (b.w - 2.4) * (i + 0.5) / 3
            ok = f.window(uu, zf + 1.05, 3.6, 1.9, lit=b.chance(0.55), blind=0 if i == 1 else b.blind())
            if ok and i == 1:
                t = b.letters(short, 2.6, 0.9, 0.01)
                if t:
                    f.glass_text(t, uu, zf + 2.0)
    b.vertical_sign("front", b.w - 0.5, g + 0.45, g + 4 * u - 1.0, "노래방PC방", out=1.4, t=0.5)
    side_details(b, back_door_u=3.0, levels=floors, side_n=2, back_n=3, gas_z=3.8)
    b.plinth(mat="stone_base")
    b.parapet(h=1.2)
    z = b.height
    top = b.stair_house(b.x0 + 0.8, b.x0 + 5.0, b.y1 - 4.6, b.y1 - 0.6, h=3.2)
    b.water_tank(b.x0 + 2.0, b.y1 - 2.6, top, r=0.8, h=1.3)
    b.water_tank(b.x0 + 3.9, b.y1 - 2.6, top, r=0.8, h=1.3)
    for i in range(5):
        b.ac_roof(b.x1 - 1.4 - i * 1.25, b.y1 - 1.1, z)
    b.m.cylinder(b.x1 - 2.0, b.y0 + 2.0, 0.05, z, z + 5.0, "metal", n=8)              # 안테나
    for k in range(3):
        b.m.box(b.x1 - 2.6, b.x1 - 1.4, b.y0 + 1.98, b.y0 + 2.02, z + 3.6 + k * 0.4, z + 3.64 + k * 0.4, "metal")
    b.roof_reserve("antenna", b.x1 - 2.65, b.x1 - 1.35, b.y0 + 1.9, b.y0 + 2.1, z, z + 5.0)
    b.finalize()
    return b, "근린상가"


# ---------------------------------------------------------------------------
# 9. 필로티 빌라 — 2x3, 1층 필로티 주차 + 4층 주거, 박공 지붕, 실외기 보호망
# ---------------------------------------------------------------------------

def villa01(text_fn=None):
    b = Building((2, 3), 14.0, 13.0, seed=19, text_fn=text_fn)
    b.mats.update({
        "wall": render((0.88, 0.87, 0.84)),
        "wall_side": render((0.86, 0.85, 0.82)),
        "accent_stone": {"color": (0.45, 0.43, 0.40), "color2": (0.40, 0.38, 0.36), "pattern": "tile",
                         "scale": (0.6, 0.3), "mortar": 0.004, "rough": 0.6},
        "roof_tile": {"color": (0.16, 0.20, 0.26), "color2": (0.13, 0.16, 0.21), "pattern": "tile",
                      "scale": (0.32, 0.2), "mortar": 0.012, "mortar_color": (0.08, 0.09, 0.11), "rough": 0.6,
                      "bump": 0.4},
        "column": {"color": (0.40, 0.38, 0.36), "color2": (0.34, 0.33, 0.31), "pattern": "tile",
                   "scale": (0.45, 0.3), "mortar": 0.004, "rough": 0.5},
        "mailbox": {"color": (0.55, 0.57, 0.60), "rough": 0.4, "metal": 0.8},
    })
    pil, u = 3.1, 2.8
    floors = [pil + k * u for k in range(4)]
    H = pil + 4 * u
    b.lot_slab()
    b.shell(H, base=pil, roof=None)
    x0, x1, y0, y1 = b.x0, b.x1, b.y0, b.y1
    b.m.box(x0, x1, y0, y1, pil - 0.3, pil, "concrete", skip=(5 - 4,))          # 2층 바닥 슬래브 (윗면 생략)
    for k, (cx, cy) in enumerate([(x0 + 0.225, y0 + 0.225), (-1.0, y0 + 0.225), (4.0, y0 + 0.225),
                                  (x1 - 0.225, y0 + 0.225), (x1 - 0.225, (y0 + y1) / 2), (x1 - 0.225, y1 - 0.225),
                                  (1.5, y1 - 0.225), (x0 + 0.225, (y0 + y1) / 2)]):
        b.m.box(cx - 0.225, cx + 0.225, cy - 0.225, cy + 0.225, 0.03, pil - 0.3, "column", skip=(BOTTOM,))
    for lx in (-6.0, -3.5, -1.0, 1.5, 4.0):                                         # 주차선 · 차바퀴 멈춤턱
        b.m.box(lx - 0.05, lx + 0.05, y0 + 0.3, y0 + 5.3, 0.03, 0.036, "parking_line", skip=(BOTTOM,))
    for lx in (-4.75, -2.25, 0.25, 2.75):
        b.m.box(lx - 0.8, lx + 0.8, y0 + 4.7, y0 + 4.85, 0.03, 0.15, "concrete", skip=(BOTTOM,))
    for lx in (-4.0, 0.0, 4.0):                                                      # 천장 등
        b.m.box(lx - 0.2, lx + 0.2, y0 + 3.0 - 0.2, y0 + 3.0 + 0.2, pil - 0.33, pil - 0.3, "lamp")
    # 1층 계단실 코어 (뒤 왼쪽): 유리문 + 우편함
    cx0, cx1, cy0 = x0 + 0.45, x0 + 4.6, y1 - 4.6
    b.m.box(cx0, cx1, cy0, y1, 0.03, pil - 0.3, "wall_side", skip=(BOTTOM,))
    core = Facade(b.m, "front", cx0, cx1, cy0, y1)
    core.box(1.0, 2.6, 0.03, 2.4, 0, 0.04, "frame")
    core.box(1.07, 2.53, 0.05, 2.33, 0.04, 0.06, "glass_door")
    core.box(1.79, 1.81, 0.05, 2.33, 0.06, 0.08, "frame", attached=False)
    core.box(2.8, 3.8, 1.0, 1.6, 0, 0.12, "mailbox")
    for r in range(3):
        for c in range(4):
            core.box(2.83 + c * 0.24, 3.03 + c * 0.24, 1.05 + r * 0.18, 1.2 + r * 0.18, 0.12, 0.13, "frame_dark",
                     attached=False)
    f = b.face("front")
    b.wall_text("front", "해송빌라", 2.2, pil + 0.45, 3.0, 0.38, mat="letters")
    f.box(5.0, 6.0, pil, H, 0, 0.05, "accent_stone")                                # 계단 창 세로 띠
    f.reserve(FIXTURE, 5.0, 6.0, pil, H, 0, 0.05, "accent_strip")
    for zf in floors:
        f.window(2.6, zf + 0.9, 2.4, 1.5, lit=b.chance(0.4), blind=b.blind())
        f.window(9.4, zf + 0.9, 2.4, 1.5, lit=b.chance(0.4), blind=b.blind())
        f.window(12.4, zf + 1.4, 0.8, 0.9, style="fixed", glass="glass_frost")
        b.ac_wall("front", 7.3, zf + 0.5, cage=True)
    for zf in floors[:-1]:
        b.face("front").window(5.5, zf + 1.8, 0.6, 1.0, style="fixed")              # 계단참 창 (띠 위 X)
    b.windows("left", floors, 2, 1.3, 1.2, margin=2.5)
    b.windows("right", floors, 2, 1.3, 1.2, margin=2.5)
    b.windows("back", floors, 3, 1.1, 1.0, sill=1.2, margin=2.0)
    b.downpipe("left", b.d - 0.3, top=H)
    b.downpipe("right", 0.3, top=H)
    b.bands(floors[1:], ("front", "left", "right"), h=0.1, out=0.05)
    b.gable_roof("x", rise=2.4, overhang=0.6)
    b.finalize()
    return b, "해송빌라"


# ---------------------------------------------------------------------------
# 10. 바다펜션 — 2x3, 3층, 하늘색 사이딩, 정면 박공, 목재 난간 발코니, 외부 철골 계단, 앞 데크
# ---------------------------------------------------------------------------

def stair_run(b, f, u0, u1, z0, z1, width=1.0, d0=0.15):
    """파사드를 따라 오르는 외부 철골 계단 (옆판 · 디딤판 · 난간 · 기둥)"""
    m = b.m
    rise = z1 - z0
    n = max(int(round(rise / 0.2)), 1)
    for side_d in (d0, d0 + width):
        m.beam(f.p(u0, z0 - 0.15, side_d), f.p(u1, z1 - 0.15, side_d), 0.04, 0.22, "metal_dark")
    for k in range(n):
        uu = u0 + (u1 - u0) * (k + 0.5) / n
        zz = z0 + rise * (k + 1) / n
        a, c = sorted((uu - abs(u1 - u0) / n / 2, uu + abs(u1 - u0) / n / 2))
        f.box(a, c, zz - 0.04, zz, d0 + 0.02, d0 + width - 0.02, "grille", attached=False)
    m.beam(f.p(u0, z0 + 0.95, d0 + width), f.p(u1, z1 + 0.95, d0 + width), 0.05, 0.05, "metal")
    for t in (0.0, 0.5, 1.0):
        uu, zz = u0 + (u1 - u0) * t, z0 + rise * t
        m.beam(f.p(uu, zz, d0 + width), f.p(uu, zz + 0.95, d0 + width), 0.04, 0.04, "metal")


def pension01(text_fn=None):
    b = Building((2, 3), 12.5, 12.0, seed=20, text_fn=text_fn)
    b.mats.update({
        "wall": {"color": (0.55, 0.68, 0.74), "color2": (0.50, 0.62, 0.68), "pattern": "siding", "scale": 0.18,
                 "rough": 0.7, "control": (1, 0, 0)},
        "wall_side": {"color": (0.86, 0.86, 0.84), "color2": (0.80, 0.80, 0.78), "pattern": "siding",
                      "scale": 0.18, "rough": 0.7, "control": (1, 0, 0)},
        "roof_tile": {"color": (0.55, 0.16, 0.10), "color2": (0.48, 0.13, 0.08), "pattern": "seam", "axis": "y",
                      "scale": 0.45, "rough": 0.4, "metal": 0.6, "control": (0, 1, 0)},
        "plant": {"color": (0.10, 0.28, 0.08), "color2": (0.06, 0.18, 0.05), "pattern": "noise", "scale": 6.0,
                  "rough": 0.8, "bump": 0.4},
    })
    g, u = 3.3, 3.0
    H = g + 2 * u
    b.lot_slab()
    b.shell(H, roof=None, zones={"front": [(0.03, 0.9, "stone_base"), (0.9, H, "wall")]})
    f = b.face("front")
    deck = 0.33
    f.door(b.w / 2, 1.6, 2.3, z0=deck, step=False, canopy=False)
    f.window(2.2, 1.0, 2.4, 1.7, style="casement", lit=b.chance(0.5))
    f.window(b.w - 2.2, 1.0, 2.4, 1.7, style="casement", lit=b.chance(0.5))
    f.box(0.3, b.w - 0.3, 0.03, deck, 0, 2.3, "deck", attached=False)                # 앞 데크 + 계단
    f.box(b.w / 2 - 1.2, b.w / 2 + 1.2, 0.03, deck / 2 + 0.03, 2.3, 2.6, "deck", attached=False)
    f.reserve(FOREGROUND, 0.3, b.w - 0.3, 0.03, deck, 0, 2.6, "deck")
    for uu in (0.9, b.w - 0.9):                                                       # 화분
        f.box(uu - 0.4, uu + 0.4, deck, deck + 0.45, 1.7, 2.2, "wood", attached=False)
        f.box(uu - 0.35, uu + 0.35, deck + 0.45, deck + 0.75, 1.75, 2.15, "plant", attached=False)
        f.reserve(FOREGROUND, uu - 0.4, uu + 0.4, deck, deck + 0.75, 1.7, 2.2, "planter")
    f.box(2.0, 4.0, deck + 0.4, deck + 0.45, 1.85, 2.2, "wood", attached=False)      # 벤치
    for lu in (2.15, 3.85):
        f.box(lu - 0.05, lu + 0.05, deck, deck + 0.4, 1.9, 2.15, "metal_dark", attached=False)
    f.reserve(FOREGROUND, 2.0, 4.0, deck, deck + 0.45, 1.85, 2.2, "bench")
    for zf in (g, g + u):
        b.balcony("front", 0.4, b.w - 0.4, zf, depth=1.5, rail="wood")
        f.window(3.4, zf + 0.05, 2.6, 2.25, sill=None, lit=b.chance(0.5), blind=b.blind())
        f.window(b.w - 2.4, zf + 0.9, 2.0, 1.4, lit=b.chance(0.4), blind=b.blind())
    # 오른쪽 외부 계단: 1층 -> 2층 문 -> 3층 문
    r = b.face("right")
    r.door(6.0, 0.9, 2.1, z0=g + 0.02, leaf="door_wood", step=False, canopy=True, lamp=False)
    r.door(11.15, 0.9, 2.1, z0=g + u + 0.02, leaf="door_wood", step=False, canopy=False, lamp=False)
    stair_run(b, r, 0.6, 5.4, 0.03, g)
    stair_run(b, r, 6.8, 10.5, g, g + u)
    for (a, c, zz) in ((5.4, 6.8, g), (10.5, 11.85, g + u)):
        r.box(a, c, zz - 0.12, zz, 0.15, 1.15, "grille", attached=False)
        b.m.beam(r.p(a, zz + 0.95, 1.15), r.p(c, zz + 0.95, 1.15), 0.05, 0.05, "metal")
        b.m.box(*sorted((r.xy(c - 0.05, 1.1)[0], r.xy(c, 1.15)[0])), *sorted((r.xy(c - 0.05, 1.1)[1],
                r.xy(c, 1.15)[1])), 0.03, zz - 0.12, "metal_dark")
    for (a, c, za, zb) in ((0.6, 5.4, 0.03, g + 1.0), (5.4, 6.8, g - 0.12, g + 1.0),
                           (6.8, 10.5, g, g + u + 1.0), (10.5, 11.85, g + u - 0.12, g + u + 1.0)):
        r.reserve(FOREGROUND, a, c, za, zb, 0.15, 1.2, "ext_stair")
    b.windows("left", [0.03, g, g + u], 2, 1.2, 1.2, margin=2.5)
    b.windows("back", [0.03, g, g + u], 2, 1.1, 1.0, sill=1.2, margin=2.5)
    b.face("back").door(b.w - 2.0, 0.9, 2.1, leaf="door_wood")
    b.downpipe("left", b.d - 0.3, top=H)
    b.gable_roof("y", rise=3.0, overhang=0.6, mat="roof_tile")
    t = b.letters("바다펜션", 4.2, 0.7, 0.06)
    if t:
        f.text(t, b.w / 2, H + 0.9, 0.0, "letters_wood", kind=None)
    b.mats["letters_wood"] = {"color": (0.95, 0.92, 0.85), "rough": 0.5, "emit": (1.0, 0.95, 0.8),
                              "emit_strength": 1.5}
    b.finalize()
    return b, "바다펜션"


# ---------------------------------------------------------------------------
# 11. 일산수산물판매센터 (실제, 일산해수욕장 남쪽) — 4x3, 2층, 1층 롤업 셔터 점포 6칸 + 수조, 2층 식당, 대형 간판, 옥상 공조기
# ---------------------------------------------------------------------------

STALLS = [("1호 활어", 1.0), ("2호 조개", 0.9), ("3호 대게", 1.0), ("4호 횟감", 0.75), ("5호 건어물", 1.0),
          ("6호 젓갈", 0.0)]


def market01(text_fn=None):
    b = Building((4, 3), 30.0, 16.0, seed=21, text_fn=text_fn)
    b.mats.update({
        "wall": {"color": (0.16, 0.32, 0.58), "color2": (0.14, 0.29, 0.53), "pattern": "panel", "scale": (1.0, 0.5),
                 "mortar": 0.005, "mortar_color": (0.08, 0.15, 0.30), "rough": 0.4, "metal": 0.5,
                 "control": (1, 0, 0)},
        "wall_side": render((0.72, 0.72, 0.70)),
        "sign": sign((0.95, 0.95, 0.92), 0.6),
        "sign_stall": sign((0.95, 0.80, 0.10), 0.5),
        "letters_blue": {"color": (0.05, 0.15, 0.55), "rough": 0.4, "emit": (0.1, 0.3, 1.0), "emit_strength": 1.0},
    })
    g, u = 4.8, 3.6
    b.lot_slab()
    b.shell(g + u)
    f = b.face("front")
    open_w = 4.0
    pier = (b.w - 6 * open_w) / 7
    for i, (label, frac) in enumerate(STALLS):
        u0 = pier * (i + 1) + open_w * i
        f.shutter(u0, u0 + open_w, 0.03, 4.2, open_frac=frac, name=f"stall{i + 1}")
        b.lightbox("front", u0 + open_w / 2, 4.3, 3.0, 0.42, label, mat="sign_stall", letters="letters_blue")
        if frac > 0.5:
            b.aquarium("front", u0 + open_w / 2, w=2.6, d0=0.3, depth=0.9)
            b.fish_props("front", u0 + 0.75, d=1.75)
    for i in range(6):
        uu = pier * (i + 1) + open_w * i + open_w / 2
        f.window(uu, g + 0.8, 3.4, 2.0, lit=b.chance(0.6), blind=b.blind())
    b.sign_band("front", 2.0, b.w - 2.0, g + u - 0.7, g + u + 0.95, "일산수산물판매센터", "활어 · 조개 · 대게 · 건어물",
                out=0.35, letters="letters_blue")
    b.face("back").shutter(3.0, 7.0, 0.03, 4.0, open_frac=0.0, name="loading")
    side_details(b, back_door_u=10.0, levels=[g], side_n=3, back_n=4, gas_z=4.4)
    b.ac_wall("back", 14.0, 1.4)
    b.ac_wall("back", 19.0, 1.4)
    b.plinth()
    b.parapet(h=1.1)
    z = b.height
    for i in range(3):                                                              # 옥상 공조기
        cx = b.x0 + 6.0 + i * 3.4
        cy = b.y1 - 4.0
        b.m.box(cx - 1.1, cx + 1.1, cy - 0.65, cy + 0.65, z, z + 0.15, "metal_dark")
        b.m.box(cx - 1.05, cx + 1.05, cy - 0.6, cy + 0.6, z + 0.15, z + 1.35, "ac")
        for fx in (-0.5, 0.5):
            b.m.cylinder(cx + fx, cy, 0.42, z + 1.35, z + 1.45, "metal_dark", n=16)
            b.m.cylinder(cx + fx, cy, 0.08, z + 1.45, z + 1.5, "metal", n=8)
        b.m.box(cx - 0.08, cx + 0.08, cy + 0.6, cy + 1.6, z + 0.3, z + 0.5, "metal")
        b.roof_reserve("hvac", cx - 1.15, cx + 1.15, cy - 0.7, cy + 1.65, z, z + 1.5)
    top = b.stair_house(b.x1 - 5.0, b.x1 - 1.0, b.y1 - 4.5, b.y1 - 0.6, h=3.0)
    b.water_tank(b.x1 - 3.0, b.y1 - 2.5, top, r=0.9, h=1.4)
    for i in range(4):
        b.ac_roof(b.x0 + 2.0 + i * 1.3, b.y0 + 2.2, z)
    b.finalize()
    return b, "일산수산물판매센터"


# ---------------------------------------------------------------------------
# 12. 치킨 · 호프 — 2x2, 2층 벽돌, 노란 간판, 접이식 차양 아래 야외 테이블
# ---------------------------------------------------------------------------

def chicken01(text_fn=None):
    b = Building((2, 2), 13.5, 10.5, seed=22, text_fn=text_fn)
    b.mats.update({
        "wall": dict(BRICK, color=(0.36, 0.17, 0.11), color2=(0.30, 0.14, 0.09)),
        "wall_side": render((0.80, 0.74, 0.62)),
        "sign": sign((0.98, 0.78, 0.05), 0.6),
        "sign_small": sign((0.60, 0.05, 0.03), 0.6),
        "letters_dark": {"color": (0.45, 0.05, 0.02), "rough": 0.4, "emit": (0.9, 0.15, 0.05), "emit_strength": 1.0},
        "awning": stripes((0.10, 0.35, 0.18), (0.88, 0.86, 0.80), 0.45),
    })
    g, u = 4.0, 3.1
    b.lot_slab()
    b.shell(g + u)
    f = b.face("front")
    f.storefront(0.5, b.w - 0.5, 0.03, 3.05, bay=1.2, doors=[(b.w / 2, 1.8)])
    b.sign_band("front", 0.25, b.w - 0.25, 3.18, 3.95, "교촌치킨", "허니콤보 · 레드콤보 · 생맥주",
                letters="letters_dark")
    b.awning("front", 0.5, b.w - 0.5, 2.98, depth=2.8, drop=0.3, valance=0.25)
    for uu in (2.2, 4.4, b.w - 4.4, b.w - 2.2):                                     # 야외 테이블
        x, y = f.xy(uu, 1.7)
        b.m.cylinder(x, y, 0.45, 0.72, 0.76, "plastic_white", n=16)
        b.m.cylinder(x, y, 0.05, 0.03, 0.72, "metal_dark", n=8)
        b.m.cylinder(x, y, 0.3, 0.03, 0.06, "metal_dark", n=12)
        for a in range(4):
            ang = a * math.pi / 2 + 0.6
            cx, cy = x + 0.75 * math.cos(ang), y + 0.75 * math.sin(ang)
            b.m.box(cx - 0.2, cx + 0.2, cy - 0.2, cy + 0.2, 0.42, 0.46, "plastic_red")
            for lx, ly in ((-0.16, -0.16), (0.16, -0.16), (0.16, 0.16), (-0.16, 0.16)):
                b.m.box(cx + lx - 0.02, cx + lx + 0.02, cy + ly - 0.02, cy + ly + 0.02, 0.03, 0.42, "plastic_red")
        f.reserve(FOREGROUND, uu - 0.97, uu + 0.97, 0.03, 0.9, 0.73, 2.67, "table")
    for i in range(3):
        uu = 1.2 + (b.w - 2.4) * (i + 0.5) / 3
        ok = f.window(uu, g + 0.8, 3.0, 1.6, lit=b.chance(0.6), blind=0 if i == 1 else b.blind())
        if ok and i == 1:
            t = b.letters("HOF", 1.6, 0.7, 0.01)
            if t:
                f.glass_text(t, uu, g + 1.6)
    b.lightbox("front", 0.9 + 0.05, g + 1.2, 0.8, 1.2, "2층", mat="sign_small")
    side_details(b, back_door_u=2.5, levels=[g], side_n=2, gas_z=3.6)
    b.ac_wall("back", 7.0, 1.4)
    b.bands([g], ("front", "left", "right"), mat="trim")
    b.plinth()
    b.parapet()
    z = b.height
    b.water_tank(b.x0 + 1.8, b.y1 - 1.8, z, r=0.75, h=1.2)
    b.stair_house(b.x1 - 3.6, b.x1 - 0.6, b.y1 - 3.6, b.y1 - 0.6)
    b.ac_roof(0.0, b.y1 - 1.0, z)
    b.ac_roof(1.3, b.y1 - 1.0, z)
    b.finalize()
    return b, "교촌치킨"


# ---------------------------------------------------------------------------
# 13. 해변 화장실 · 샤워장 — 2x2 (해변 쪽 배치), 석재 + 목재, 깊은 출입구 2, 가림벽, 픽토그램, 야외 샤워 · 발 씻는 곳
# ---------------------------------------------------------------------------

def pictogram(b, f, u, z, female, mat, d=0.0, s=1.0):
    """사람 픽토그램 (머리 원판 + 몸통 · 다리, 여자는 치마 모양). d = 붙일 면의 깊이, s = 크기"""
    f.disc(u, z + 0.62 * s, d, 0.11 * s, 0.04, mat)
    if female:
        for zz0, zz1, hw in ((0.15, 0.28, 0.2), (0.28, 0.38, 0.16), (0.38, 0.48, 0.12)):
            f.box(u - hw * s, u + hw * s, z + zz0 * s, z + zz1 * s, d, d + 0.04, mat)
    else:
        f.box(u - 0.13 * s, u + 0.13 * s, z + 0.2 * s, z + 0.48 * s, d, d + 0.04, mat)
    for lu in (u - 0.07 * s, u + 0.07 * s):
        f.box(lu - 0.04 * s, lu + 0.04 * s, z, z + 0.2 * s, d, d + 0.04, mat)
    kind = SIGN if d <= 0.0 else FOREGROUND      # 벽에 붙으면 간판, 앞에 선 가림벽에 붙으면 그 일부
    f.reserve(kind, u - 0.22 * s, u + 0.22 * s, z, z + 0.75 * s, d, d + 0.06, "pictogram")


def toilet01(text_fn=None):
    b = Building((2, 2), 12.0, 7.0, setback=2.0, seed=23, text_fn=text_fn)
    b.mats.update({
        "wall": {"color": (0.55, 0.40, 0.26), "color2": (0.48, 0.34, 0.21), "pattern": "siding", "scale": 0.15,
                 "rough": 0.7},
        "wall_side": {"color": (0.55, 0.40, 0.26), "color2": (0.48, 0.34, 0.21), "pattern": "siding",
                      "scale": 0.15, "rough": 0.7},
        "stone_wall": {"color": (0.58, 0.55, 0.50), "color2": (0.50, 0.47, 0.43), "pattern": "tile",
                       "scale": (0.5, 0.3), "mortar": 0.012, "mortar_color": (0.35, 0.33, 0.30), "rough": 0.8,
                       "bump": 0.5},
        "picto_m": {"color": (0.05, 0.25, 0.75), "rough": 0.4},
        "picto_f": {"color": (0.80, 0.08, 0.10), "rough": 0.4},
        "sign": sign((0.10, 0.30, 0.55), 0.5),
    })
    H = 3.4
    b.lot_slab()
    stone = [(0.03, 1.3, "stone_wall"), (1.3, H, "wall")]
    b.shell(H, zones={s: [(0.03, 1.3, "stone_wall"), (1.3, H, "wall" if s == "front" else "wall_side")]
                      for s in SIDES})
    f = b.face("front")
    for uu, fem in ((2.2, False), (b.w - 2.2, True)):
        f.doorway(uu, 1.2, 2.3, name="woman" if fem else "man")
        f.box(uu - 1.0, uu + 1.0, 0.03, 2.1, 1.05, 1.2, "stone_wall", attached=False)   # 가림벽
        f.reserve(FOREGROUND, uu - 1.0, uu + 1.0, 0.03, 2.1, 1.05, 1.2, "screen")
        pictogram(b, f, uu, 1.0, fem, "picto_f" if fem else "picto_m", d=1.2, s=1.3)   # 가림벽 앞면
    b.lightbox("front", b.w / 2, 2.55, 3.0, 0.5, "화장실 · 샤워장", mat="sign")
    # 발 씻는 곳 + 야외 샤워 2
    f.box(b.w / 2 - 1.3, b.w / 2 + 1.3, 0.03, 0.5, 0.25, 0.85, "concrete", attached=False)
    f.box(b.w / 2 - 1.2, b.w / 2 + 1.2, 0.4, 0.5, 0.33, 0.77, "water", attached=False)
    for tu in (b.w / 2 - 0.7, b.w / 2, b.w / 2 + 0.7):
        x, y = f.xy(tu, 0.3)
        b.m.cylinder(x, y, 0.025, 0.5, 0.8, "stainless", n=8)
    f.reserve(FOREGROUND, b.w / 2 - 1.3, b.w / 2 + 1.3, 0.03, 0.8, 0.25, 0.85, "footwash")
    for su in (b.w / 2 - 2.0, b.w / 2 + 2.0):
        x, y = f.xy(su, 1.5)
        b.m.cylinder(x, y, 0.045, 0.03, 2.35, "stainless", n=10)
        x2, y2 = f.xy(su, 1.25)
        b.m.beam((x, y, 2.3), (x2, y2, 2.3), 0.04, 0.04, "stainless")
        b.m.cylinder(x2, y2, 0.13, 2.22, 2.26, "stainless", n=14)
        b.m.box(x - 0.4, x + 0.4, y - 0.4, y + 0.4, 0.03, 0.06, "concrete")
        f.reserve(FOREGROUND, su - 0.45, su + 0.45, 0.03, 2.4, 1.1, 1.9, "shower")
    for s in ("left", "right", "back"):
        b.windows(s, [0.03], 2 if s == "back" else 1, 1.0, 0.45, sill=2.45, margin=1.6, style="fixed",
                  blinds=False, lit=0.0)
    b.plinth(h=0.2, mat="concrete")
    # 큰 처마 지붕 + 목재 처마 띠
    o = 0.8
    b.m.box(b.x0 - o, b.x1 + o, b.y0 - o, b.y1 + o, H, H + 0.25, "concrete")
    for (a, c, d0, d1) in ((b.x0 - o, b.x1 + o, b.y0 - o - 0.04, b.y0 - o),
                           (b.x0 - o, b.x1 + o, b.y1 + o, b.y1 + o + 0.04)):
        b.m.box(a, c, d0, d1, H - 0.05, H + 0.3, "wood")
    b.roof_reserve("eave", b.x0 - o, b.x1 + o, b.y0 - o - 0.04, b.y1 + o + 0.04, H, H + 0.3)
    b.finalize()
    return b, "해변 화장실"


DESIGNS = {
    "IlsanHoetjip01": hoetjip01,
    "IlsanHoetjip02": hoetjip02,
    "IlsanCafe01": cafe01,
    "IlsanMotel01": motel01,
    "IlsanShop01": shop01,
    "IlsanGrill01": grill01,
    "IlsanCrab01": crab01,
    "IlsanMixed01": mixed01,
    "IlsanVilla01": villa01,
    "IlsanPension01": pension01,
    "IlsanMarket01": market01,
    "IlsanChicken01": chicken01,
    "IlsanToilet01": toilet01,
}

# 사진 속 건물 · 광장 시설 (landmarks.py, plaza.py) — 이 모듈의 Building · 도우미를 쓰므로 맨 끝에서 등록
import landmarks  # noqa: E402
import plaza  # noqa: E402

import brands  # noqa: E402
import franchises  # noqa: E402

DESIGNS.update(landmarks.DESIGNS)
DESIGNS.update(plaza.DESIGNS)
DESIGNS.update(brands.DESIGNS)
DESIGNS.update(franchises.DESIGNS)
