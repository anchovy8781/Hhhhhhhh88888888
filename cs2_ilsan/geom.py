"""건물 기하 핵심 (블렌더 없이 동작): 메시 조각, 파사드 좌표계, 요소 배치 예약과 겹침 검사.

좌표: 미터, Z 위. 에셋 원점 = 부지 중심 지면. 건물 정면 = -Y (도로 쪽).

겹침 방지
  파사드에 붙는 모든 요소는 그 면 위의 사각 영역(u, z)과 벽에서의 깊이(d)를 '예약'한다.
  - OPENING   창 · 문 · 상점 유리 · 커튼월 · 셔터 · 차고 입구
  - SIGN      벽에 붙은 간판 · 글자 · 명판 · 픽토그램
  - FIXTURE   실외기 · 우수관 · 돌출 간판 · 발코니 바닥 · 외장 띠
  - FOREGROUND 앞에 서 있는 것 (차양 · 난간 · 수족관 · 테라스 가구 · 계단) — 창 앞을 가려도 된다
  - TRIM      층 띠 · 굽도리 — 다른 요소를 자동으로 피해 끊어진다
  규칙: OPENING 은 FOREGROUND 외의 어떤 요소와도 면 투영(u, z)이 겹치면 안 되고,
        나머지끼리는 3차원(u, z, d)으로 겹치면 안 된다. TRIM 끼리는 검사하지 않는다.
"""

import math

BOTTOM, TOP, BACK, RIGHT, FRONT, LEFT = range(6)
BOX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]

OPENING, SIGN, FIXTURE, FOREGROUND, TRIM = "opening", "sign", "fixture", "foreground", "trim"
EPS = 0.005


# ---------------------------------------------------------------------------
# 메시
# ---------------------------------------------------------------------------

class Mesh:
    """머티리얼 이름별로 조각을 모아 한 메시 데이터로 만든다 (bpy 변환은 kit.to_object)."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.mat_names = []

    def _mi(self, name):
        if name not in self.mat_names:
            self.mat_names.append(name)
        return self.mat_names.index(name)

    def add(self, verts, faces, mat):
        o = len(self.verts)
        self.verts += [tuple(float(c) for c in v) for v in verts]
        self.faces += [tuple(int(i) + o for i in f) for f in faces]
        self.mats += [self._mi(mat)] * len(faces)

    def box(self, x0, x1, y0, y1, z0, z1, mat, skip=()):
        """축 정렬 박스. skip 에 BOTTOM/TOP/BACK(-Y)/RIGHT(+X)/FRONT(+Y)/LEFT(-X) 면 생략"""
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        self.add(v, [face for i, face in enumerate(BOX_FACES) if i not in skip], mat)

    def cylinder(self, cx, cy, r, z0, z1, mat, n=16, cap=True):
        ring = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        v = [(x, y, z0) for x, y in ring] + [(x, y, z1) for x, y in ring]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        if cap:
            f += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        self.add(v, f, mat)

    def cone(self, cx, cy, r, z0, z1, mat, n=16):
        v = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
        v.append((cx, cy, z1))
        self.add(v, [(i, (i + 1) % n, n) for i in range(n)] + [tuple(reversed(range(n)))], mat)

    def slab(self, top, thickness, mat):
        """위에서 보아 반시계 순서인 네 점(top)을 윗면으로 하는 두께 있는 판 (경사 지붕 등)"""
        bottom = [(x, y, z - thickness) for x, y, z in top]
        self.add(bottom + list(top), BOX_FACES, mat)

    def tri_prism(self, a, b, c, offset, mat):
        """삼각형 a-b-c 를 offset 벡터만큼 밀어낸 닫힌 삼각기둥 (박공 벽)"""
        v = [a, b, c] + [tuple(p + o for p, o in zip(q, offset)) for q in (a, b, c)]
        self.add(v, [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)], mat)

    def cylinder_x(self, x0, x1, cy, cz, r, mat, n=12):
        """X 축 방향 원기둥 (말아 올린 비닐 등)"""
        ring = [(cy + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        v = [(x0, y, z) for y, z in ring] + [(x1, y, z) for y, z in ring]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add(v, f + [tuple(reversed(range(n))), tuple(range(n, 2 * n))], mat)

    def beam(self, p0, p1, w, h, mat):
        """p0 -> p1 방향의 직사각 단면(w 가로, h 세로) 막대 (계단 옆판, 게 다리 등)"""
        ax = [b - a for a, b in zip(p0, p1)]
        length = math.sqrt(sum(c * c for c in ax))
        if length < 1e-6:
            return
        ax = [c / length for c in ax]
        up = (0.0, 0.0, 1.0) if abs(ax[2]) < 0.95 else (1.0, 0.0, 0.0)
        side = _norm(_cross(ax, up))
        upn = _cross(side, ax)
        v = []
        for p in (p0, p1):
            for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                v.append(tuple(p[i] + side[i] * s * w / 2 + upn[i] * t * h / 2 for i in range(3)))
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(v, f, mat)

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, mat, nu=16, nv=8, zmin=-1.0):
        """타원체 (zmin 으로 아래를 잘라 평평하게 할 수 있음)"""
        rings = []
        for j in range(1, nv):
            t = -math.pi / 2 + math.pi * j / nv
            if math.sin(t) < zmin:
                continue
            rings.append(t)
        v = [(cx, cy, cz - rz if zmin <= -1 else cz + rz * math.sin(rings[0]))]
        for t in rings:
            for i in range(nu):
                a = 2 * math.pi * i / nu
                v.append((cx + rx * math.cos(t) * math.cos(a), cy + ry * math.cos(t) * math.sin(a), cz + rz * math.sin(t)))
        v.append((cx, cy, cz + rz))
        f = [(0, (i + 1) % nu + 1, i + 1) for i in range(nu)]
        for k in range(len(rings) - 1):
            a0, a1 = 1 + k * nu, 1 + (k + 1) * nu
            f += [(a0 + i, a0 + (i + 1) % nu, a1 + (i + 1) % nu, a1 + i) for i in range(nu)]
        top, last = len(v) - 1, 1 + (len(rings) - 1) * nu
        f += [(last + i, last + (i + 1) % nu, top) for i in range(nu)]
        self.add(v, f, mat)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(sum(c * c for c in a))
    return tuple(c / n for c in a)


# ---------------------------------------------------------------------------
# 예약 슬롯과 겹침 규칙
# ---------------------------------------------------------------------------

class Slot:
    __slots__ = ("side", "kind", "u0", "u1", "z0", "z1", "d0", "d1", "name")

    def __init__(self, side, kind, u0, u1, z0, z1, d0, d1, name=""):
        self.side, self.kind, self.name = side, kind, name
        self.u0, self.u1 = sorted((u0, u1))
        self.z0, self.z1 = sorted((z0, z1))
        self.d0, self.d1 = sorted((d0, d1))

    def overlaps2d(self, o):
        return (self.u0 < o.u1 - EPS and o.u0 < self.u1 - EPS and
                self.z0 < o.z1 - EPS and o.z0 < self.z1 - EPS)

    def overlaps3d(self, o):
        return self.overlaps2d(o) and self.d0 < o.d1 - EPS and o.d0 < self.d1 - EPS

    def __repr__(self):
        return (f"{self.side}:{self.kind}:{self.name}"
                f"[u {self.u0:.2f}-{self.u1:.2f}, z {self.z0:.2f}-{self.z1:.2f}, d {self.d0:.2f}-{self.d1:.2f}]")


def clash(a, b):
    if a.side != b.side:
        return False
    if a.kind == TRIM and b.kind == TRIM:
        return False
    if OPENING in (a.kind, b.kind):
        other = b.kind if a.kind == OPENING else a.kind
        if other == FOREGROUND:
            return False
        return a.overlaps2d(b)
    return a.overlaps3d(b)


def conflicts(slots):
    out = []
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            if clash(slots[i], slots[j]):
                out.append((slots[i], slots[j]))
    return out


class Box3:
    """옥상 등 3차원 예약 (축 정렬)"""
    __slots__ = ("x0", "x1", "y0", "y1", "z0", "z1", "name")

    def __init__(self, x0, x1, y0, y1, z0, z1, name=""):
        self.x0, self.x1 = sorted((x0, x1))
        self.y0, self.y1 = sorted((y0, y1))
        self.z0, self.z1 = sorted((z0, z1))
        self.name = name

    def overlaps(self, o):
        return (self.x0 < o.x1 - EPS and o.x0 < self.x1 - EPS and self.y0 < o.y1 - EPS and o.y0 < self.y1 - EPS
                and self.z0 < o.z1 - EPS and o.z0 < self.z1 - EPS)

    def __repr__(self):
        return (f"roof:{self.name}[x {self.x0:.2f}-{self.x1:.2f}, y {self.y0:.2f}-{self.y1:.2f}, "
                f"z {self.z0:.2f}-{self.z1:.2f}]")


def box_conflicts(boxes):
    return [(boxes[i], boxes[j]) for i in range(len(boxes)) for j in range(i + 1, len(boxes))
            if boxes[i].overlaps(boxes[j])]


def subtract(intervals, blocks):
    """구간 목록에서 막힌 구간들을 뺀다"""
    out = list(intervals)
    for b0, b1 in blocks:
        nxt = []
        for a0, a1 in out:
            if b1 <= a0 or b0 >= a1:
                nxt.append((a0, a1))
                continue
            if a0 < b0:
                nxt.append((a0, b0))
            if b1 < a1:
                nxt.append((b1, a1))
        out = nxt
    return out


# ---------------------------------------------------------------------------
# 파사드
# ---------------------------------------------------------------------------

class Facade:
    """벽면 좌표계: u = 벽을 바라볼 때 오른쪽, z = 위, d = 벽에서 바깥쪽.

    side: 'front'(-Y 면), 'back'(+Y), 'left'(-X), 'right'(+X).
    slots: 건물 전체가 공유하는 예약 목록.
    """

    def __init__(self, mesh, side, x0, x1, y0, y1, slots=None):
        self.m = mesh
        self.side = side
        self.slots = slots if slots is not None else []
        if side == "front":
            self.o, self.r, self.n, self.width = (x0, y0), (1, 0), (0, -1), x1 - x0
        elif side == "back":
            self.o, self.r, self.n, self.width = (x1, y1), (-1, 0), (0, 1), x1 - x0
        elif side == "left":
            self.o, self.r, self.n, self.width = (x0, y1), (0, -1), (-1, 0), y1 - y0
        elif side == "right":
            self.o, self.r, self.n, self.width = (x1, y0), (0, 1), (1, 0), y1 - y0
        else:
            raise ValueError(side)

    # -- 좌표 / 원시 조각 ---------------------------------------------------

    def xy(self, u, d):
        return (self.o[0] + self.r[0] * u + self.n[0] * d, self.o[1] + self.r[1] * u + self.n[1] * d)

    def box(self, u0, u1, z0, z1, d0, d1, mat, attached=True):
        """벽에 붙은 박스. attached 면 벽 쪽(d=0) 면은 생략 (보이지 않아 텍스처 낭비)"""
        xa, ya = self.xy(u0, d0)
        xb, yb = self.xy(u1, d1)
        skip = ()
        if attached and min(d0, d1) <= 0.0:
            skip = {"front": (FRONT,), "back": (BACK,), "left": (RIGHT,), "right": (LEFT,)}[self.side]
        self.m.box(xa, xb, ya, yb, z0, z1, mat, skip)

    def disc(self, u, z, d, r, depth, mat, n=14):
        """벽을 향한 원판 (실외기 팬 그릴, 픽토그램 머리 등)"""
        ring = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        v = []
        for dd in (d, d + depth):
            for a, b in ring:
                x, y = self.xy(u + a, dd)
                v.append((x, y, z + b))
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.m.add(v, f + [tuple(reversed(range(n))), tuple(range(n, 2 * n))], mat)

    def text(self, letters, u, z, d, mat, kind=SIGN, name="letters"):
        """letters = (verts, faces, 폭, 높이, 두께). (u, z) 가 글자 중심, d 는 벽에서 띄우는 거리.
        kind=None 이면 예약하지 않는다 (이미 예약된 간판 · 유리 위에 붙일 때)."""
        verts, faces, w, h, depth = letters
        out = []
        for lx, ly, lz in verts:
            x, y = self.xy(u + lx, d + depth / 2 + lz)
            out.append((x, y, z + ly))
        self.m.add(out, faces, mat)
        if kind:
            self.reserve(kind, u - w / 2, u + w / 2, z - h / 2, z + h / 2, d, d + depth, name)

    # -- 예약 --------------------------------------------------------------

    def reserve(self, kind, u0, u1, z0, z1, d0=0.0, d1=0.0, name=""):
        s = Slot(self.side, kind, u0, u1, z0, z1, d0, d1, name)
        self.slots.append(s)
        return s

    def fits(self, kind, u0, u1, z0, z1, d0=0.0, d1=0.0, margin=0.0):
        probe = Slot(self.side, kind, u0, u1, z0, z1, d0, d1)
        if probe.u0 < -margin - EPS or probe.u1 > self.width + margin + EPS:
            return False
        return not any(clash(probe, s) for s in self.slots)

    # -- 개구부 ------------------------------------------------------------

    def window(self, u, z, w, h, glass="glass", frame="frame", sill="trim", mullions=1, lit=False, blind=0.0,
               check=True, name="window"):
        """창 하나: 돌출 창틀 + 유리 + 중간 살 + 창대. 다른 요소와 겹치면 만들지 않고 False."""
        box = (u - w / 2 - 0.08, u + w / 2 + 0.08, z - 0.06, z + h, 0.0, 0.16)
        if check and not self.fits(OPENING, *box):
            return False
        fw, out = 0.07, 0.10
        self.box(u - w / 2, u + w / 2, z, z + fw, 0, out, frame)
        self.box(u - w / 2, u + w / 2, z + h - fw, z + h, 0, out, frame)
        self.box(u - w / 2, u - w / 2 + fw, z + fw, z + h - fw, 0, out, frame)
        self.box(u + w / 2 - fw, u + w / 2, z + fw, z + h - fw, 0, out, frame)
        for k in range(1, mullions + 1):
            mu = u - w / 2 + w * k / (mullions + 1)
            self.box(mu - 0.03, mu + 0.03, z + fw, z + h - fw, 0, out * 0.8, frame)
        self.box(u - w / 2 + fw, u + w / 2 - fw, z + fw, z + h - fw, 0, 0.03, "glass_lit" if lit else glass)
        if blind and not lit:
            drop = (h - 2 * fw) * blind
            self.box(u - w / 2 + fw, u + w / 2 - fw, z + h - fw - drop, z + h - fw, 0, 0.032, "blind")
        self.box(u - w / 2 - 0.08, u + w / 2 + 0.08, z - 0.06, z, 0, 0.16, sill)
        self.reserve(OPENING, *box, name=name)
        return True

    def _leaves(self, du, dw, z0, z1, leaf):
        """문짝: 양개(폭 1.4 m 이상) 또는 외짝. 울거미 + 하부 걸레받이 + 유리/판 + 손잡이"""
        double = dw >= 1.4
        leaves = [(du - dw / 2, du), (du, du + dw / 2)] if double else [(du - dw / 2, du + dw / 2)]
        st = 0.06
        for i, (a, b) in enumerate(leaves):
            self.box(a, a + st, z0, z1, 0, 0.06, "frame")
            self.box(b - st, b, z0, z1, 0, 0.06, "frame")
            self.box(a + st, b - st, z1 - 0.08, z1, 0, 0.06, "frame")
            self.box(a + st, b - st, z0, z0 + 0.22, 0, 0.06, "stainless")
            self.box(a + st, b - st, z0 + 0.22, z1 - 0.08, 0, 0.03, leaf)
            hu = (b - 0.14) if (not double or i == 0) else (a + 0.14)
            self.box(hu - 0.02, hu + 0.02, z0 + 0.85, z0 + 1.45, 0.06, 0.12, "metal")

    def storefront(self, u0, u1, z0, z1, bay=1.25, transom=2.55, doors=(), name="storefront"):
        """1층 상점 유리면. 멀리언은 문 양옆 문틀 사이 구간마다 따로 나눠 문을 가로지르지 않는다.
        doors: [(중심 u, 폭)]. 문 높이 = transom (문 위는 가로대와 欄間 유리)."""
        self.reserve(OPENING, u0, u1, z0, z1, 0.0, 0.14, name)
        zt = z0 + transom
        jamb = 0.07
        self.box(u0, u1, z0, z0 + 0.12, 0, 0.12, "frame")
        self.box(u0, u1, z1 - 0.10, z1, 0, 0.12, "frame")
        self.box(u0, u1, z0 + 0.12, z1 - 0.10, 0, 0.04, "glass_shop")
        cuts = []
        for du, dw in sorted(doors):
            a, b = du - dw / 2 - jamb, du + dw / 2 + jamb
            if a < u0 + 0.15 or b > u1 - 0.15 or any(not (b <= c0 or a >= c1) for c0, c1 in cuts):
                raise ValueError(f"{name}: 문 위치가 상점 유리면을 벗어나거나 겹칩니다 ({du}, {dw})")
            cuts.append((a, b))
            self.box(a, a + jamb, z0 + 0.12, z1 - 0.10, 0, 0.13, "frame")
            self.box(b - jamb, b, z0 + 0.12, z1 - 0.10, 0, 0.13, "frame")
            self._leaves(du, dw, z0 + 0.12, zt, "glass_door")
            self.box(du - dw / 2, du + dw / 2, 0.03, 0.05, 0.16, 1.1, "rubber", attached=False)  # 현관 매트
            self.reserve(FOREGROUND, du - dw / 2, du + dw / 2, 0.03, 0.05, 0.16, 1.1, name + "_mat")
        self.box(u0, u1, zt, zt + 0.08, 0, 0.10, "frame")
        segs, s = [], u0
        for a, b in cuts:
            segs.append((s, a))
            s = b
        segs.append((s, u1))
        for a, b in segs:
            length = b - a
            if length < 0.05:
                continue
            n = max(1, int(round(length / bay)))
            for k in range(n + 1):
                if (k == 0 and a != u0) or (k == n and b != u1):
                    continue  # 문틀이 이미 있다
                uu = min(max(a + length * k / n, u0 + 0.04), u1 - 0.04)
                self.box(uu - 0.04, uu + 0.04, z0 + 0.12, z1 - 0.10, 0, 0.12, "frame")

    def door(self, u, w, h, z0=0.03, leaf="glass_door", canopy=True, step=True, name="door"):
        """독립 출입문 (문틀 + 문짝 + 계단 + 작은 캐노피)"""
        if not self.fits(OPENING, u - w / 2 - 0.1, u + w / 2 + 0.1, z0, z0 + h + 0.1, 0, 0.12):
            raise ValueError(f"{name}: 다른 요소와 겹칩니다")
        self.reserve(OPENING, u - w / 2 - 0.1, u + w / 2 + 0.1, z0, z0 + h + 0.1, 0, 0.12, name)
        self.box(u - w / 2 - 0.1, u - w / 2, z0, z0 + h, 0, 0.12, "frame")
        self.box(u + w / 2, u + w / 2 + 0.1, z0, z0 + h, 0, 0.12, "frame")
        self.box(u - w / 2 - 0.1, u + w / 2 + 0.1, z0 + h, z0 + h + 0.1, 0, 0.12, "frame")
        self._leaves(u, w, z0, z0 + h, leaf)
        if step:
            self.box(u - w / 2 - 0.2, u + w / 2 + 0.2, 0.03, max(z0, 0.03) + 0.15, 0, 0.5, "concrete")
            self.reserve(FOREGROUND, u - w / 2 - 0.2, u + w / 2 + 0.2, 0.03, max(z0, 0.03) + 0.15, 0, 0.5,
                         name + "_step")
        if canopy:
            self.box(u - w / 2 - 0.35, u + w / 2 + 0.35, z0 + h + 0.25, z0 + h + 0.37, 0, 1.0, "trim")
            self.reserve(FOREGROUND, u - w / 2 - 0.35, u + w / 2 + 0.35, z0 + h + 0.25, z0 + h + 0.37, 0, 1.0,
                         name + "_canopy")

    def doorway(self, u, w, h, z0=0.03, name="doorway"):
        """문짝 없는 출입구 (화장실 등): 문틀 + 어두운 안쪽"""
        if not self.fits(OPENING, u - w / 2 - 0.1, u + w / 2 + 0.1, z0, z0 + h + 0.1, 0, 0.12):
            raise ValueError(f"{name}: 다른 요소와 겹칩니다")
        self.reserve(OPENING, u - w / 2 - 0.1, u + w / 2 + 0.1, z0, z0 + h + 0.1, 0, 0.12, name)
        self.box(u - w / 2, u + w / 2, z0, z0 + h, 0, 0.01, "opening")
        self.box(u - w / 2 - 0.1, u - w / 2, z0, z0 + h, 0, 0.12, "frame")
        self.box(u + w / 2, u + w / 2 + 0.1, z0, z0 + h, 0, 0.12, "frame")
        self.box(u - w / 2 - 0.1, u + w / 2 + 0.1, z0 + h, z0 + h + 0.1, 0, 0.12, "frame")

    def shutter(self, u0, u1, z0, z1, open_frac=0.85, name="shutter"):
        """롤업 셔터가 달린 점포 개구부: 어두운 안쪽 + 셔터 함 + 내려온 만큼의 셔터 + 양옆 가이드"""
        self.reserve(OPENING, u0, u1, z0, z1, 0.0, 0.36, name)
        house = 0.45
        self.box(u0, u1, z0, z1 - house, 0, 0.01, "opening")
        self.box(u0, u1, z1 - house, z1, 0, 0.36, "metal")
        drop = (1.0 - open_frac) * (z1 - house - z0)
        if drop > 0.05:
            self.box(u0 + 0.06, u1 - 0.06, z1 - house - drop, z1 - house, 0.04, 0.08, "shutter")
        for g in (u0, u1 - 0.06):
            self.box(g, g + 0.06, z0, z1 - house, 0, 0.1, "metal")

    def garage(self, u0, u1, z0, z1, strips=True, name="garage"):
        """드라이브인 주차 입구: 어두운 개구부 + 띠 커튼 + 상부 레일"""
        self.reserve(OPENING, u0, u1, z0, z1, 0.0, 0.16, name)
        self.box(u0, u1, z0, z1 - 0.1, 0, 0.02, "opening")
        self.box(u0 - 0.2, u0, z0, z1 + 0.2, 0, 0.3, "trim")
        self.box(u1, u1 + 0.2, z0, z1 + 0.2, 0, 0.3, "trim")
        self.box(u0, u1, z1 - 0.1, z1 + 0.2, 0, 0.3, "trim")
        if strips:
            uu, strip, gap = u0 + 0.05, 0.22, 0.03
            while uu + strip <= u1 - 0.05:
                self.box(uu, uu + strip, z0 + 0.32, z1 - 0.12, 0.10, 0.13, "curtain", attached=False)
                uu += strip + gap
            self.box(u0, u1, z1 - 0.14, z1 - 0.1, 0.02, 0.16, "metal_dark")
        self.reserve(TRIM, u0 - 0.2, u1 + 0.2, z0, z1 + 0.2, 0, 0.3, name + "_frame")

    # -- 띠 ---------------------------------------------------------------

    def band(self, z0, z1, out, mat, u_from=None, u_to=None, name="band"):
        """수평 띠 (층 띠 · 굽도리). 개구부 · 간판 · 설비가 있는 구간은 자동으로 끊는다."""
        a = -out if u_from is None else u_from
        b = self.width + out if u_to is None else u_to
        blocks = []
        for s in self.slots:
            if s.side != self.side or s.kind not in (OPENING, SIGN, FIXTURE, FOREGROUND):
                continue
            if s.z0 >= z1 - EPS or s.z1 <= z0 + EPS:
                continue
            if s.kind != OPENING and (s.d0 >= out - EPS or s.d1 <= EPS):
                continue
            blocks.append((s.u0 - 0.03, s.u1 + 0.03))
        placed = 0
        for p, q in subtract([(a, b)], blocks):
            if q - p < 0.08:
                continue
            self.box(p, q, z0, z1, 0, out, mat)
            self.reserve(TRIM, p, q, z0, z1, 0, out, name)
            placed += 1
        return placed
