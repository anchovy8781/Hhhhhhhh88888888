"""건물 기하 핵심 (블렌더 없이 동작): 메시 조각, 파사드 좌표계, 움푹 들어간 개구부, 배치 예약과 겹침 검사.

좌표: 미터, Z 위. 에셋 원점 = 부지 중심 지면. 건물 정면 = -Y (도로 쪽).

면 방향
  CS2 는 뒷면을 그리지 않으므로 면 방향이 틀리면 게임에서 구멍처럼 보인다.
  닫힌 조각(박스 · 원기둥 · 판 …)은 add_solid 가 부호 있는 부피로 방향을 검사해 바깥을 향하게 고치고,
  파사드 벽면과 개구부 안쪽 면(reveal)은 방향을 직접 계산해 만든다. 블렌더의 법선 재계산은 쓰지 않는다.

겹침 방지
  파사드에 붙는 모든 요소는 그 면 위의 사각 영역(u, z)과 벽에서의 깊이(d)를 '예약'한다.
  - OPENING    창 · 문 · 상점 유리 · 셔터 · 차고 입구 — 벽에 실제 구멍을 내고 안쪽으로 들어간다
  - SIGN       벽에 붙은 간판 · 글자 · 명판 · 픽토그램
  - FIXTURE    실외기 · 우수관 · 돌출 간판 · 발코니 바닥 · 외부 조명 · 계량기
  - FOREGROUND 앞에 서 있는 것 (차양 · 난간 · 수족관 · 테라스 가구 · 외부 계단) — 창 앞을 가려도 된다
  - TRIM       층 띠 · 굽도리 · 가스관 — 다른 요소를 자동으로 피해 끊어진다
  규칙: OPENING 은 FOREGROUND 외의 어떤 요소와도 면 투영(u, z)이 겹치면 안 되고,
        나머지끼리는 3차원(u, z, d)으로 겹치면 안 된다. TRIM 끼리는 검사하지 않는다.
"""

import math

BOTTOM, TOP, BACK, RIGHT, FRONT, LEFT = range(6)
BOX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]

OPENING, SIGN, FIXTURE, FOREGROUND, TRIM = "opening", "sign", "fixture", "foreground", "trim"
EPS = 0.005


def signed_volume(verts, faces):
    """닫힌 면 집합의 부호 있는 부피. 양수면 면들이 바깥을 향한다."""
    if not verts:
        return 0.0
    c = [sum(v[i] for v in verts) / len(verts) for i in range(3)]
    vol = 0.0
    for f in faces:
        p0 = [verts[f[0]][i] - c[i] for i in range(3)]
        for k in range(1, len(f) - 1):
            p1 = [verts[f[k]][i] - c[i] for i in range(3)]
            p2 = [verts[f[k + 1]][i] - c[i] for i in range(3)]
            vol += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1]) - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                    + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6.0
    return vol


def face_normal(verts, f):
    """다각형 면의 (정규화하지 않은) 법선 — 뉴웰 방법"""
    nx = ny = nz = 0.0
    for i in range(len(f)):
        a, b = verts[f[i]], verts[f[(i + 1) % len(f)]]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return nx, ny, nz


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
        """면 방향을 그대로 쓴다 (호출자가 책임)"""
        o = len(self.verts)
        self.verts += [tuple(float(c) for c in v) for v in verts]
        self.faces += [tuple(int(i) + o for i in f) for f in faces]
        self.mats += [self._mi(mat)] * len(faces)

    def add_solid(self, verts, faces, mat, skip=()):
        """닫힌 조각: 부피가 음수면 모든 면을 뒤집어 바깥을 향하게 한 뒤 skip 번째 면은 빼고 추가"""
        if signed_volume(verts, faces) < 0:
            faces = [tuple(reversed(f)) for f in faces]
        self.add(verts, [f for i, f in enumerate(faces) if i not in skip], mat)

    def merge(self, other, fn=None):
        """다른 Mesh 를 그대로 덧붙인다. fn(v) -> v 로 점을 옮길 수 있다 (면 방향이 바뀌지 않는 변환만)"""
        o = len(self.verts)
        self.verts += [tuple(fn(v)) if fn else v for v in other.verts]
        self.faces += [tuple(i + o for i in f) for f in other.faces]
        self.mats += [self._mi(other.mat_names[k]) for k in other.mats]

    def quad(self, a, b, c, d, mat):
        self.add([a, b, c, d], [(0, 1, 2, 3)], mat)

    def box(self, x0, x1, y0, y1, z0, z1, mat, skip=()):
        """축 정렬 박스. skip 에 BOTTOM/TOP/BACK(-Y)/RIGHT(+X)/FRONT(+Y)/LEFT(-X) 면 생략"""
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        z0, z1 = sorted((z0, z1))
        if x1 - x0 < 1e-6 or y1 - y0 < 1e-6 or z1 - z0 < 1e-6:
            return
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        self.add_solid(v, BOX_FACES, mat, skip)

    def cylinder(self, cx, cy, r, z0, z1, mat, n=16, cap=True):
        ring = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        v = [(x, y, z0) for x, y in ring] + [(x, y, z1) for x, y in ring]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        caps = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        self.add_solid(v, f + caps, mat, skip=() if cap else (n, n + 1))

    def cone(self, cx, cy, r, z0, z1, mat, n=16):
        v = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
        v.append((cx, cy, z1))
        self.add_solid(v, [(i, (i + 1) % n, n) for i in range(n)] + [tuple(reversed(range(n)))], mat)

    def slab(self, top, thickness, mat):
        """네 점(top)을 윗면으로 하는 두께 있는 판 (경사 지붕 등)"""
        bottom = [(x, y, z - thickness) for x, y, z in top]
        self.add_solid(bottom + list(top), BOX_FACES, mat)

    def tri_prism(self, a, b, c, offset, mat):
        """삼각형 a-b-c 를 offset 벡터만큼 밀어낸 닫힌 삼각기둥 (박공 벽)"""
        v = [a, b, c] + [tuple(p + o for p, o in zip(q, offset)) for q in (a, b, c)]
        self.add_solid(v, [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)], mat)

    def cylinder_x(self, x0, x1, cy, cz, r, mat, n=12):
        """X 축 방향 원기둥"""
        ring = [(cy + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        v = [(x0, y, z) for y, z in ring] + [(x1, y, z) for y, z in ring]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add_solid(v, f + [tuple(reversed(range(n))), tuple(range(n, 2 * n))], mat)

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
        self.add_solid(v, BOX_FACES, mat)

    def tube(self, p0, p1, r0, r1, mat, n=8, cap=True):
        """p0 -> p1 의 원뿔대 (나무 줄기 · 가지 · 깃대). r0, r1 = 양 끝 반지름"""
        ax = [b - a for a, b in zip(p0, p1)]
        length = math.sqrt(sum(c * c for c in ax))
        if length < 1e-6:
            return
        ax = [c / length for c in ax]
        ref = (0.0, 0.0, 1.0) if abs(ax[2]) < 0.95 else (1.0, 0.0, 0.0)
        e1 = _norm(_cross(ax, ref))
        e2 = _cross(ax, e1)
        v = []
        for p, r in ((p0, r0), (p1, r1)):
            for i in range(n):
                a = 2 * math.pi * i / n
                v.append(tuple(p[k] + r * (math.cos(a) * e1[k] + math.sin(a) * e2[k]) for k in range(3)))
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add_solid(v, f + [tuple(reversed(range(n))), tuple(range(n, 2 * n))], mat,
                       skip=() if cap else (n, n + 1))

    def extrude(self, pts, offset, mat):
        """평면 다각형 pts(3D 점, 순서대로)를 offset 벡터만큼 밀어낸 닫힌 기둥 (깃발 · 표지판 · 조형물)"""
        n = len(pts)
        v = [tuple(p) for p in pts] + [tuple(a + o for a, o in zip(p, offset)) for p in pts]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add_solid(v, f + [tuple(reversed(range(n))), tuple(range(n, 2 * n))], mat)

    def annulus(self, cx, cy, r0, r1, z0, z1, mat, n=40):
        """닫힌 고리 (회전교차로 띠 · 연석 · 나무 보호대)"""
        v = []
        for z in (z0, z1):
            for r in (r0, r1):
                v += [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z)
                      for i in range(n)]
        bi, bo, ti, to = 0, n, 2 * n, 3 * n
        f = []
        for i in range(n):
            j = (i + 1) % n
            f += [(ti + i, to + i, to + j, ti + j), (bi + i, bi + j, bo + j, bo + i),
                  (bo + i, bo + j, to + j, to + i), (bi + i, ti + i, ti + j, bi + j)]
        self.add_solid(v, f, mat)

    def heightfield(self, x0, x1, y0, y1, nx, ny, fn, thickness, mat):
        """윗면이 z = fn(x, y) 인 두께 있는 곡면 판 (막 구조 천막 · 아치 다리 상판)"""
        xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
        ys = [y0 + (y1 - y0) * j / ny for j in range(ny + 1)]
        top = [(x, y, fn(x, y)) for y in ys for x in xs]
        v = top + [(x, y, z - thickness) for x, y, z in top]
        k = len(top)
        idx = lambda i, j: j * (nx + 1) + i  # noqa: E731
        f = []
        for j in range(ny):
            for i in range(nx):
                a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
                f.append((a, b, c, d))
                f.append((k + d, k + c, k + b, k + a))
        ring = ([idx(i, 0) for i in range(nx)] + [idx(nx, j) for j in range(ny)] +
                [idx(i, ny) for i in range(nx, 0, -1)] + [idx(0, j) for j in range(ny, 0, -1)])
        for a, b in zip(ring, ring[1:] + ring[:1]):
            f.append((b, a, k + a, k + b))
        self.add_solid(v, f, mat)

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, mat, nu=16, nv=8):
        rings = [-math.pi / 2 + math.pi * j / nv for j in range(1, nv)]
        v = [(cx, cy, cz - rz)]
        for t in rings:
            for i in range(nu):
                a = 2 * math.pi * i / nu
                v.append((cx + rx * math.cos(t) * math.cos(a), cy + ry * math.cos(t) * math.sin(a),
                          cz + rz * math.sin(t)))
        v.append((cx, cy, cz + rz))
        f = [(0, (i + 1) % nu + 1, i + 1) for i in range(nu)]
        for k in range(len(rings) - 1):
            a0, a1 = 1 + k * nu, 1 + (k + 1) * nu
            f += [(a0 + i, a0 + (i + 1) % nu, a1 + (i + 1) % nu, a1 + i) for i in range(nu)]
        top, last = len(v) - 1, 1 + (len(rings) - 1) * nu
        f += [(last + i, last + (i + 1) % nu, top) for i in range(nu)]
        self.add_solid(v, f, mat)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(sum(c * c for c in a))
    return tuple(c / n for c in a)


# ---------------------------------------------------------------------------
# 예약 슬롯과 겹침 규칙
# ---------------------------------------------------------------------------

class Slot:
    __slots__ = ("side", "kind", "u0", "u1", "z0", "z1", "d0", "d1", "name", "recess", "hole")

    def __init__(self, side, kind, u0, u1, z0, z1, d0, d1, name="", recess=0.0, hole=None):
        """recess > 0 이면 벽에 구멍을 낸다. 구멍 범위는 hole=(u0, u1, z0, z1), 없으면 슬롯 범위."""
        self.side, self.kind, self.name, self.recess = side, kind, name, recess
        self.hole = hole
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
    return [(slots[i], slots[j]) for i in range(len(slots)) for j in range(i + 1, len(slots))
            if clash(slots[i], slots[j])]


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


def rects_minus(x0, x1, y0, y1, holes):
    """사각형 (x0..x1, y0..y1) 에서 구멍 사각형들을 뺀 나머지를 사각형 목록으로 (옥상 · 데크 바닥)"""
    xs = sorted({x0, x1} | {c for h in holes for c in (h[0], h[1]) if x0 < c < x1})
    ys = sorted({y0, y1} | {c for h in holes for c in (h[2], h[3]) if y0 < c < y1})
    out = []
    for ya, yb in zip(ys[:-1], ys[1:]):
        row = None
        for xa, xb in zip(xs[:-1], xs[1:]):
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            hit = any(h[0] < mx < h[1] and h[2] < my < h[3] for h in holes)
            if hit:
                if row:
                    out.append(tuple(row))
                row = None
            elif row:
                row[1] = xb
            else:
                row = [xa, xb, ya, yb]
        if row:
            out.append(tuple(row))
    return out


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
    """벽면 좌표계: u = 벽을 바라볼 때 오른쪽, z = 위, d = 벽에서 바깥쪽 (음수 = 벽 안쪽).

    side: 'front'(-Y 면), 'back'(+Y), 'left'(-X), 'right'(+X).  r × z = n 이 되도록 잡혀 있어
    (u0,z0)→(u1,z0)→(u1,z1)→(u0,z1) 순서의 사각형은 항상 바깥(n)을 향한다.
    slots: 건물 전체가 공유하는 예약 목록.
    key: 예약을 구분하는 면 이름 (기본 = side). 한 건물에 몸체가 여럿이면(저층부 + 탑) 'tower:front' 처럼
         몸체마다 다른 key 를 써서 서로 다른 평면의 요소끼리 비교하지 않게 한다.
    """

    def __init__(self, mesh, side, x0, x1, y0, y1, slots=None, key=None):
        self.m = mesh
        self.side = side
        self.key = key or side
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

    def p(self, u, z, d):
        x, y = self.xy(u, d)
        return (x, y, z)

    def box(self, u0, u1, z0, z1, d0, d1, mat, attached=True):
        """박스. attached 면 벽(또는 개구부 안쪽 면)에 닿는 뒷면(작은 d 쪽)은 생략 — 보이지 않아 텍스처 낭비"""
        xa, ya = self.xy(u0, d0)
        xb, yb = self.xy(u1, d1)
        skip = ()
        if attached:
            skip = {"front": (FRONT,), "back": (BACK,), "left": (RIGHT,), "right": (LEFT,)}[self.side]
        self.m.box(xa, xb, ya, yb, z0, z1, mat, skip)

    def quad(self, u0, u1, z0, z1, d, mat):
        """바깥(n)을 향한 벽면 사각형"""
        self.m.quad(self.p(u0, z0, d), self.p(u1, z0, d), self.p(u1, z1, d), self.p(u0, z1, d), mat)

    def disc(self, u, z, d, r, depth, mat, n=14):
        """벽에 붙은 원판 (실외기 팬 그릴, 픽토그램 머리 등)"""
        ring = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        v = [self.p(u + a, z + b, dd) for dd in (d, d + depth) for a, b in ring]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.m.add_solid(v, f + [tuple(reversed(range(n))), tuple(range(n, 2 * n))], mat)

    def poly(self, pts, d, depth, mat):
        """벽면 위 다각형 [(u, z)] 을 d 에서 바깥으로 depth 만큼 밀어낸 조각 (로고 별 · 화살표 등)"""
        off = (self.n[0] * depth, self.n[1] * depth, 0.0)
        self.m.extrude([self.p(u, z, d) for u, z in pts], off, mat)

    def text(self, letters, u, z, d, mat, kind=SIGN, name="letters"):
        """letters = (verts, faces, 폭, 높이, 두께). (u, z) 가 글자 중심, d 는 글자 뒷면 위치.
        kind=None 이면 예약하지 않는다 (이미 예약된 간판 · 유리 위에 붙일 때)."""
        verts, faces, w, h, depth = letters
        self.m.add([self.p(u + lx, z + ly, d + depth / 2 + lz) for lx, ly, lz in verts], faces, mat)
        if kind:
            self.reserve(kind, u - w / 2, u + w / 2, z - h / 2, z + h / 2, d, d + depth, name)

    # -- 예약 --------------------------------------------------------------

    def reserve(self, kind, u0, u1, z0, z1, d0=0.0, d1=0.0, name="", recess=0.0, hole=None):
        s = Slot(self.key, kind, u0, u1, z0, z1, d0, d1, name, recess, hole)
        self.slots.append(s)
        return s

    def fits(self, kind, u0, u1, z0, z1, d0=0.0, d1=0.0, margin=0.0):
        probe = Slot(self.key, kind, u0, u1, z0, z1, d0, d1)
        if probe.u0 < -margin - EPS or probe.u1 > self.width + margin + EPS:
            return False
        return not any(clash(probe, s) for s in self.slots)

    def hole(self, u0, u1, z0, z1, recess, name, d_out=0.06):
        """벽에 구멍을 낼 개구부 예약. 겹치면 ValueError (설계 오류)"""
        if u0 < 0.12 or u1 > self.width - 0.12:
            raise ValueError(f"{self.key}:{name}: 벽 모서리에 너무 가깝습니다 (u {u0:.2f}-{u1:.2f})")
        if not self.fits(OPENING, u0, u1, z0, z1, -recess, d_out):
            hits = [s for s in self.slots if clash(Slot(self.key, OPENING, u0, u1, z0, z1, -recess, d_out), s)]
            raise ValueError(f"{self.key}:{name}: 다른 요소와 겹칩니다 {hits}")
        return self.reserve(OPENING, u0, u1, z0, z1, -recess, d_out, name, recess)

    # -- 벽면 생성 ----------------------------------------------------------

    def walls(self, zones, reveal="reveal", back="opening"):
        """zones = [(z0, z1, 재질)] 또는 [(z0, z1, 재질, u0, u1)] 높이(· 가로) 구간마다 벽을 만들되,
        개구부 자리는 비우고 개구부마다 안쪽 면(양옆 · 위 · 아래)과 안쪽 끝면을 만든다.
        u 범위를 주면 그 밖은 비운다 (다른 몸체에 가려지는 부분)."""
        holes = [(s.hole or (s.u0, s.u1, s.z0, s.z1), s.recess)
                 for s in self.slots if s.side == self.key and s.recess > 0]
        for zone in zones:
            za, zb, mat = zone[:3]
            span = (zone[3], zone[4]) if len(zone) > 3 else (0.0, self.width)
            zs = sorted({za, zb} | {z for (h, _) in holes for z in (h[2], h[3]) if za + EPS < z < zb - EPS})
            merged = []
            for z0, z1 in zip(zs[:-1], zs[1:]):
                blocks = sorted((h[0], h[1]) for (h, _) in holes if h[2] <= z0 + EPS and h[3] >= z1 - EPS)
                free = subtract([span], blocks)
                if merged and merged[-1][2] == free:
                    merged[-1][1] = z1
                else:
                    merged.append([z0, z1, free])
            for z0, z1, free in merged:
                for u0, u1 in free:
                    if u1 - u0 > 1e-4 and z1 - z0 > 1e-4:
                        self.quad(u0, u1, z0, z1, 0.0, mat)
        for h, r in holes:
            self._reveal(h, r, reveal, back)

    def _reveal(self, h, r, mat, back):
        u0, u1, z0, z1 = h
        P = self.p
        self.m.quad(P(u0, z0, 0), P(u0, z0, -r), P(u0, z1, -r), P(u0, z1, 0), mat)   # 왼쪽 (+u 향함)
        self.m.quad(P(u1, z0, 0), P(u1, z1, 0), P(u1, z1, -r), P(u1, z0, -r), mat)   # 오른쪽 (-u 향함)
        self.m.quad(P(u0, z1, 0), P(u0, z1, -r), P(u1, z1, -r), P(u1, z1, 0), mat)   # 윗면 (아래 향함)
        self.m.quad(P(u0, z0, 0), P(u1, z0, 0), P(u1, z0, -r), P(u0, z0, -r), mat)   # 아랫면 (위 향함)
        self.quad(u0, u1, z0, z1, -r, back)                                          # 안쪽 끝 (바깥 향함)

    # -- 창 ----------------------------------------------------------------

    def window(self, u, z, w, h, style="sliding", lit=False, blind=0.0, grille=False, recess=0.15,
               frame="frame", glass="glass", sill="trim", check=True, name="window"):
        """움푹 들어간 창. style: 'sliding'(이중 미닫이) | 'casement'(중간 살) | 'fixed'.
        다른 요소와 겹치면 만들지 않고 False."""
        u0, u1, z1 = u - w / 2, u + w / 2, z + h
        if sill:
            probe = (u0 - 0.08, u1 + 0.08, z - 0.06, z1, -recess, 0.08)
        else:  # 발코니 창호(바닥까지 내려오는 문) — 창대 없음
            probe = (u0, u1, z, z1, -recess, 0.0)
        if check and not self.fits(OPENING, *probe):
            return False
        if probe[0] < 0.12 or probe[1] > self.width - 0.12:
            return False
        self.reserve(OPENING, *probe, name=name, recess=recess, hole=(u0, u1, z, z1))  # 창대까지 예약, 구멍은 창 크기
        b = -recess
        fw = 0.06
        # 바깥 창틀 (개구부 안쪽 끝에 붙음)
        self.box(u0, u1, z, z + fw, b, b + 0.09, frame)
        self.box(u0, u1, z1 - fw, z1, b, b + 0.09, frame)
        self.box(u0, u0 + fw, z + fw, z1 - fw, b, b + 0.09, frame)
        self.box(u1 - fw, u1, z + fw, z1 - fw, b, b + 0.09, frame)
        g = "glass_lit" if lit else glass
        iu0, iu1, iz0, iz1 = u0 + fw, u1 - fw, z + fw, z1 - fw
        if style == "sliding":
            mid = (iu0 + iu1) / 2
            for (a, c, d0) in ((iu0, mid + 0.03, b + 0.045), (mid - 0.03, iu1, b + 0.005)):
                sw = 0.045
                self.box(a, c, iz0, iz0 + sw, d0, d0 + 0.04, frame)
                self.box(a, c, iz1 - sw, iz1, d0, d0 + 0.04, frame)
                self.box(a, a + sw, iz0 + sw, iz1 - sw, d0, d0 + 0.04, frame)
                self.box(c - sw, c, iz0 + sw, iz1 - sw, d0, d0 + 0.04, frame)
                self.box(a + sw, c - sw, iz0 + sw, iz1 - sw, d0 + 0.015, d0 + 0.025, g, attached=False)
        else:
            self.box(iu0, iu1, iz0, iz1, b, b + 0.02, g)
            if style == "casement":
                self.box(u - 0.025, u + 0.025, iz0, iz1, b, b + 0.08, frame)
        if blind and not lit:
            drop = (iz1 - iz0) * blind
            self.box(iu0, iu1, iz1 - drop, iz1, b + 0.09, b + 0.095, "blind", attached=False)
        # 창대 (밖으로 6 cm 돌출, 위가 개구부 바닥보다 3 cm 높아 면이 겹치지 않음)
        if sill:
            self.box(u0 - 0.08, u1 + 0.08, z - 0.06, z + 0.03, b + 0.09, 0.06, sill, attached=False)
        if grille:  # 방범창: 세로 살
            gd0, gd1 = -0.03, -0.01
            self.box(u0 + 0.02, u1 - 0.02, z1 - 0.07, z1 - 0.04, gd0, gd1, "grille", attached=False)
            self.box(u0 + 0.02, u1 - 0.02, z + 0.06, z + 0.09, gd0, gd1, "grille", attached=False)
            n = max(int(w / 0.13), 2)
            for k in range(1, n):
                gu = u0 + w * k / n
                self.box(gu - 0.01, gu + 0.01, z + 0.06, z1 - 0.04, gd0, gd1, "grille", attached=False)
        return True

    def curtain(self, u0, u1, z0, z1, floor_h, bay, recess=0.12, spandrel=0.0, fins=0.0, fin_every=1,
                ledge=0.0, lit=0.3, rng=None, glass="glass_curtain", lit_glass="glass_curtain_lit",
                spandrel_mat="spandrel", frame="frame", fin_mat="fin", name="curtain"):
        """커튼월: 벽을 뚫은 개구부 하나 안에 층마다 스팬드럴(불투명 띠) + 유리, 세로 멀리언, 층 가로대.
        fins > 0 이면 멀리언 자리마다(fin_every 칸마다) 밖으로 튀어나온 세로 핀, ledge > 0 이면 층마다 가로 차양.
        핀 · 차양은 개구부 예약 깊이에 포함되므로 다른 요소와 겹치지 않는다. 유리는 칸마다 켜짐(lit)이 다르다."""
        d_out = max(fins, ledge, 0.06)
        self.hole(u0, u1, z0, z1, recess, name, d_out=d_out)
        b = -recess
        nb = max(1, int(round((u1 - u0) / bay)))
        nf = max(1, int(round((z1 - z0) / floor_h)))
        bw, fh = (u1 - u0) / nb, (z1 - z0) / nf
        for j in range(nf):
            za, zb = z0 + j * fh, z0 + (j + 1) * fh
            if spandrel > 0:
                self.quad(u0, u1, za, za + spandrel, b + 0.03, spandrel_mat)
            for i in range(nb):
                g = lit_glass if (rng is not None and rng.random() < lit) else glass
                self.quad(u0 + i * bw, u0 + (i + 1) * bw, za + spandrel, zb, b + 0.02, g)
        for i in range(nb + 1):
            uu = min(max(u0 + i * bw, u0 + 0.035), u1 - 0.035)
            self.box(uu - 0.035, uu + 0.035, z0, z1, b, b + 0.11, frame)
        for j in range(nf + 1):
            zz = min(max(z0 + j * fh, z0 + 0.04), z1 - 0.04)
            self.box(u0, u1, zz - 0.04, zz + 0.04, b, b + 0.10, frame)
        if fins > 0:
            for i in range(0, nb + 1, fin_every):
                uu = min(max(u0 + i * bw, u0 + 0.07), u1 - 0.07)
                self.box(uu - 0.06, uu + 0.06, z0, z1, b + 0.11, fins, fin_mat)
        if ledge > 0:
            for j in range(1, nf + 1):
                zz = z0 + j * fh
                self.box(u0, u1, zz - 0.14, min(zz + 0.08, z1), b + 0.10, ledge, fin_mat)
        return nb, nf

    def glass_text(self, letters, u, z, recess=0.15):
        """창 유리에 붙인 시트 글자 (예약 없음 — 창 안쪽)"""
        self.text(letters, u, z, -recess + 0.1, "letters_glass", kind=None)

    # -- 문 · 상점 ----------------------------------------------------------

    def _leaves(self, du, dw, z0, z1, leaf, d):
        """문짝 (d = 문짝 뒷면 깊이): 양개(폭 1.4 m 이상) 또는 외짝. 울거미 + 걸레받이 + 유리/판 + 손잡이"""
        double = dw >= 1.4
        leaves = [(du - dw / 2, du), (du, du + dw / 2)] if double else [(du - dw / 2, du + dw / 2)]
        st = 0.06
        for i, (a, b) in enumerate(leaves):
            self.box(a, a + st, z0, z1, d, d + 0.06, "frame")
            self.box(b - st, b, z0, z1, d, d + 0.06, "frame")
            self.box(a + st, b - st, z1 - 0.08, z1, d, d + 0.06, "frame")
            self.box(a + st, b - st, z0, z0 + 0.22, d, d + 0.06, "stainless")
            self.box(a + st, b - st, z0 + 0.22, z1 - 0.08, d, d + 0.03, leaf)
            hu = (b - 0.14) if (not double or i == 0) else (a + 0.14)
            self.box(hu - 0.02, hu + 0.02, z0 + 0.85, z0 + 1.45, d + 0.06, d + 0.12, "metal", attached=False)

    def storefront(self, u0, u1, z0, z1, bay=1.25, transom=2.55, doors=(), recess=0.25, kick=0.35,
                   name="storefront", mat_depth=1.1):
        """1층 상점: 벽을 뚫고 25 cm 들어간 유리면. 멀리언은 문 양옆 문틀 사이 구간마다 따로 나눠
        문을 가로지르지 않는다. 문 높이 = transom, 문 위는 가로대와 欄間 유리. doors: [(중심 u, 폭)]"""
        self.hole(u0, u1, z0, z1, recess, name)
        b = -recess
        zt = z0 + transom
        jamb = 0.07
        cuts = []
        for du, dw in sorted(doors):
            a, c = du - dw / 2 - jamb, du + dw / 2 + jamb
            if a < u0 + 0.15 or c > u1 - 0.15 or any(not (c <= p or a >= q) for p, q in cuts):
                raise ValueError(f"{name}: 문 위치가 상점 유리면을 벗어나거나 겹칩니다 ({du}, {dw})")
            cuts.append((a, c))
        segs, s = [], u0
        for a, c in cuts:
            segs.append((s, a))
            s = c
        segs.append((s, u1))
        # 유리 구간: 하부 석재 걸레받이 + 유리 + 멀리언 (문 자리는 건너뜀)
        for a, c in segs:
            length = c - a
            if length < 0.05:
                continue
            self.box(a, c, z0, z0 + kick, b, b + 0.14, "stone_base")
            self.box(a, c, z0 + kick, zt, b, b + 0.03, "glass_shop")
            n = max(1, int(round(length / bay)))
            for k in range(n + 1):
                if (k == 0 and a != u0) or (k == n and c != u1):
                    continue  # 그 자리는 문틀
                uu = min(max(a + length * k / n, u0 + 0.04), u1 - 0.04)
                self.box(uu - 0.04, uu + 0.04, z0 + kick, zt, b, b + 0.12, "frame")
        # 문: 문틀 + 문짝 + 현관 매트
        for (a, c), (du, dw) in zip(cuts, sorted(doors)):
            self.box(a, a + jamb, z0, zt, b, b + 0.13, "frame")
            self.box(c - jamb, c, z0, zt, b, b + 0.13, "frame")
            self._leaves(du, dw, z0 + 0.02, zt, "glass_door", b + 0.04)
            self.box(du - dw / 2, du + dw / 2, 0.03, 0.05, 0.05, mat_depth, "rubber", attached=False)
            self.reserve(FOREGROUND, du - dw / 2, du + dw / 2, 0.03, 0.05, 0.05, mat_depth, name + "_mat")
        # 가로대 위 欄間 유리 (문 위까지 전체 폭) + 상부 틀
        self.box(u0, u1, zt, zt + 0.08, b, b + 0.12, "frame")
        self.box(u0, u1, zt + 0.08, z1 - 0.10, b, b + 0.03, "glass_shop")
        self.box(u0, u1, z1 - 0.10, z1, b, b + 0.12, "frame")
        nt = max(1, int(round((u1 - u0) / (bay * 2))))
        for k in range(1, nt):
            uu = u0 + (u1 - u0) * k / nt
            self.box(uu - 0.03, uu + 0.03, zt + 0.08, z1 - 0.10, b, b + 0.10, "frame")

    def door(self, u, w, h, z0=0.03, leaf="glass_door", canopy=True, step=True, lamp=True, recess=0.2,
             name="door"):
        """독립 출입문: 벽을 뚫은 문틀 + 문짝 + 계단 + 캐노피 + 벽등"""
        self.hole(u - w / 2 - 0.1, u + w / 2 + 0.1, z0, z0 + h + 0.1, recess, name)
        b = -recess
        self.box(u - w / 2 - 0.1, u - w / 2, z0, z0 + h, b, b + 0.14, "frame")
        self.box(u + w / 2, u + w / 2 + 0.1, z0, z0 + h, b, b + 0.14, "frame")
        self.box(u - w / 2 - 0.1, u + w / 2 + 0.1, z0 + h, z0 + h + 0.1, b, b + 0.14, "frame")
        self._leaves(u, w, z0, z0 + h, leaf, b + 0.04)
        if step and z0 <= 0.2:
            self.box(u - w / 2 - 0.2, u + w / 2 + 0.2, 0.03, 0.18, 0.0, 0.5, "concrete", attached=False)
            self.reserve(FOREGROUND, u - w / 2 - 0.2, u + w / 2 + 0.2, 0.03, 0.18, 0.0, 0.5, name + "_step")
        if canopy:
            cz = z0 + h + 0.3
            self.box(u - w / 2 - 0.35, u + w / 2 + 0.35, cz, cz + 0.12, 0, 1.0, "trim")
            self.reserve(FOREGROUND, u - w / 2 - 0.35, u + w / 2 + 0.35, cz, cz + 0.12, 0, 1.0, name + "_canopy")
        if lamp:
            lu = u + w / 2 + 0.45
            if self.fits(FIXTURE, lu - 0.1, lu + 0.1, z0 + 1.8, z0 + 2.1, 0, 0.16):
                self.box(lu - 0.08, lu + 0.08, z0 + 1.8, z0 + 2.1, 0, 0.06, "metal_dark")
                self.box(lu - 0.06, lu + 0.06, z0 + 1.84, z0 + 2.06, 0.06, 0.15, "lamp", attached=False)
                self.reserve(FIXTURE, lu - 0.1, lu + 0.1, z0 + 1.8, z0 + 2.1, 0, 0.16, name + "_lamp")

    def doorway(self, u, w, h, z0=0.03, recess=1.2, name="doorway"):
        """문짝 없는 깊은 출입구 (화장실 등): 안쪽은 어둡게"""
        self.hole(u - w / 2, u + w / 2, z0, z0 + h, recess, name)
        self.box(u - w / 2 - 0.1, u + w / 2 + 0.1, z0 + h, z0 + h + 0.1, 0, 0.05, "frame")
        self.reserve(FIXTURE, u - w / 2 - 0.1, u + w / 2 + 0.1, z0 + h, z0 + h + 0.1, 0, 0.05, name + "_head")

    def shutter(self, u0, u1, z0, z1, open_frac=0.85, recess=0.3, name="shutter"):
        """롤업 셔터 점포: 벽을 뚫은 개구부 + 위 셔터 함(벽 밖) + 내려온 만큼의 셔터 + 가이드 레일"""
        house = 0.45
        self.hole(u0, u1, z0, z1 - house, recess, name)
        self.box(u0 - 0.05, u1 + 0.05, z1 - house, z1, 0, 0.36, "metal")
        self.reserve(FIXTURE, u0 - 0.05, u1 + 0.05, z1 - house, z1, 0, 0.36, name + "_house")
        drop = (1.0 - open_frac) * (z1 - house - z0)
        if drop > 0.05:
            self.box(u0 + 0.06, u1 - 0.06, z1 - house - drop, z1 - house, -0.06, -0.02, "shutter", attached=False)
        for g in (u0, u1 - 0.06):
            self.box(g, g + 0.06, z0, z1 - house, -0.08, 0.0, "metal", attached=False)

    def garage(self, u0, u1, z0, z1, strips=True, recess=0.4, name="garage"):
        """드라이브인 주차 입구: 벽을 뚫은 개구부 + 띠 커튼 + 테두리"""
        self.hole(u0, u1, z0, z1, recess, name)
        for a, c in ((u0 - 0.2, u0), (u1, u1 + 0.2)):
            self.box(a, c, z0, z1 + 0.2, 0, 0.2, "trim")
        self.box(u0 - 0.2, u1 + 0.2, z1, z1 + 0.2, 0, 0.2, "trim")
        self.reserve(FIXTURE, u0 - 0.2, u0, z0, z1 + 0.2, 0, 0.2, name + "_frame_l")
        self.reserve(FIXTURE, u1, u1 + 0.2, z0, z1 + 0.2, 0, 0.2, name + "_frame_r")
        self.reserve(FIXTURE, u0, u1, z1, z1 + 0.2, 0, 0.2, name + "_frame_t")
        if strips:
            uu, strip, gap = u0 + 0.05, 0.22, 0.03
            while uu + strip <= u1 - 0.05:
                self.box(uu, uu + strip, z0 + 0.32, z1 - 0.06, -0.12, -0.09, "curtain", attached=False)
                uu += strip + gap
            self.box(u0, u1, z1 - 0.06, z1, -0.14, -0.06, "metal_dark", attached=False)

    # -- 띠 · 배관 ----------------------------------------------------------

    def band(self, z0, z1, out, mat, u_from=None, u_to=None, name="band"):
        """수평 띠 (층 띠 · 굽도리 · 가스관). 개구부 · 간판 · 설비가 있는 구간은 자동으로 끊는다."""
        a = -out if u_from is None else u_from
        b = self.width + out if u_to is None else u_to
        blocks = []
        for s in self.slots:
            if s.side != self.key or s.kind not in (OPENING, SIGN, FIXTURE, FOREGROUND):
                continue
            if s.z0 >= z1 - EPS or s.z1 <= z0 + EPS:
                continue
            if s.kind != OPENING and (s.d0 >= out - EPS or s.d1 <= EPS):
                continue
            blocks.append((s.u0 - 0.03, s.u1 + 0.03))
        placed = 0
        for p, q in subtract([(a, b)], sorted(blocks)):
            if q - p < 0.08:
                continue
            self.box(p, q, z0, z1, 0, out, mat)
            self.reserve(TRIM, p, q, z0, z1, 0, out, name)
            placed += 1
        return placed
