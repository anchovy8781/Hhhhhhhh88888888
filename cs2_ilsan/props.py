"""광장 · 해변 소품 조각 (블렌더 없이 동작): 해송, 가로수, 벤치, 가로등, 볼라드, 화분, 깃발, 선베드, 파라솔, 스피커.

모두 geom.Mesh 에 바로 조각을 더하고, 차지하는 영역(x0, x1, y0, y1, z0, z1)을 돌려준다.
옥상 예약(Building.roof_reserve)이나 부지 검사에 그대로 쓸 수 있다.
"""

import math
import random

from geom import Facade, Mesh


def pine(m, x, y, z=0.0, h=9.0, seed=0, lean=0.06, lean_dir=math.pi / 2, reach=2.0, fit=None,
         bark="pine_bark", leaf="pine_needles"):
    """해송(곰솔): 바다 쪽으로 기운 굽은 줄기 + 위쪽에 층층이 퍼진 납작한 잎 덩어리.
    lean = 줄기 높이 1 m 당 수평으로 기우는 양, reach = 가지 최대 길이 (잎 덩어리 반경은 그에 비례).
    fit = (x0, x1, y0, y1) 를 주면 나무 전체가 그 안에 들도록 밑동을 중심으로 수평으로 줄인다."""
    out, m = m, Mesh()
    rng = random.Random(seed)
    trunk_h = h * 0.8
    pts = []
    for k in range(6):
        t = k / 5
        off = lean * trunk_h * t ** 1.4
        wob = 0.0 if k == 0 else rng.uniform(-0.12, 0.12) * h / 10
        pts.append((x + math.cos(lean_dir) * off + wob, y + math.sin(lean_dir) * off - wob * 0.5, z + trunk_h * t))
    r0 = 0.2 * h / 10
    m.tube((x, y, z), (x, y, z + 0.5), r0 * 1.6, r0 * 1.05, bark, n=8)          # 뿌리 쪽 굵은 밑동
    for i in range(5):
        m.tube(pts[i], pts[i + 1], r0 * (1 - 0.6 * i / 5), r0 * (1 - 0.6 * (i + 1) / 5), bark, n=8)
    top = pts[-1]
    pads = [(top[0], top[1], top[2] + 0.4, 1.1 + 0.35 * reach, 0.85)]
    az0 = rng.uniform(0, 2 * math.pi)
    for k in range(9):                                       # 가지: 위로 갈수록 짧고, 끝과 중간에 잎 덩어리
        t = 0.4 + 0.6 * k / 8
        i = min(int(t * 5), 4)
        f = t * 5 - i
        base = tuple(pts[i][c] + (pts[i + 1][c] - pts[i][c]) * f for c in range(3))
        az = az0 + k * 2.4 + rng.uniform(-0.3, 0.3)
        length = reach * rng.uniform(0.65, 1.0) * (1.15 - 0.35 * t)
        end = (base[0] + math.cos(az) * length, base[1] + math.sin(az) * length, base[2] + length * 0.25)
        m.tube(base, end, 0.08 * h / 10, 0.035, bark, n=6)
        pads.append((end[0], end[1], end[2] + 0.12, 0.85 + 0.35 * length, rng.uniform(0.5, 0.75)))
        mid = tuple(base[c] + (end[c] - base[c]) * 0.55 for c in range(3))
        pads.append((mid[0], mid[1], mid[2] + 0.3, 0.6 + 0.2 * length, rng.uniform(0.4, 0.55)))
    for cx, cy, cz, r, rz in pads:
        m.ellipsoid(cx, cy, cz, r, r * 0.85, rz, leaf, nu=12, nv=5)
    xs = [v[0] for v in m.verts]
    ys = [v[1] for v in m.verts]
    k = 1.0
    if fit:
        for want, ext in ((fit[0] - x, min(xs) - x), (fit[1] - x, max(xs) - x),
                          (fit[2] - y, min(ys) - y), (fit[3] - y, max(ys) - y)):
            if ext * want > 0 and abs(ext) > abs(want):
                k = min(k, want / ext)
    out.merge(m, lambda v: (x + (v[0] - x) * k, y + (v[1] - y) * k, v[2]))
    return (x + (min(xs) - x) * k, x + (max(xs) - x) * k, y + (min(ys) - y) * k, y + (max(ys) - y) * k,
            z, max(v[2] for v in m.verts))


def broadleaf(m, x, y, z=0.0, h=6.5, seed=0, bark="pine_bark", leaf="tree_leaf"):
    """광장 가로수 (느티나무 모양): 곧은 줄기 + 세 갈래 가지 + 둥근 잎 덩어리"""
    rng = random.Random(seed)
    fork = z + h * 0.42
    m.tube((x, y, z), (x, y, fork), 0.15, 0.12, bark, n=8)
    crown = [(x, y, z + h * 0.78, h * 0.3, h * 0.22)]
    for k in range(3):
        a = k * 2.09 + rng.uniform(-0.3, 0.3)
        end = (x + math.cos(a) * h * 0.18, y + math.sin(a) * h * 0.18, z + h * 0.66)
        m.tube((x, y, fork - 0.1), end, 0.09, 0.05, bark, n=6)
        crown.append((end[0], end[1], end[2] + 0.4, h * 0.22, h * 0.17))
    for cx, cy, cz, r, rz in crown:
        m.ellipsoid(cx, cy, cz, r, r, rz, leaf, nu=12, nv=6)
    reach = max(math.hypot(cx - x, cy - y) + r for cx, cy, _, r, _ in crown)
    return x - reach, x + reach, y - reach, y + reach, z, max(cz + rz for _, _, cz, _, rz in crown)


def led_bench(m, x, y, z=0.03, length=2.4, axis="x"):
    """무선 충전 무드 벤치: 화강석 받침 + 목재 좌판 + 좌판 아래를 감싸는 LED 띠 + 충전 패드"""
    hl, hw = length / 2, 0.3
    if axis == "x":
        bx = lambda a0, a1, b0, b1, z0, z1, mat: m.box(x + a0, x + a1, y + b0, y + b1, z0, z1, mat)  # noqa: E731
    else:
        bx = lambda a0, a1, b0, b1, z0, z1, mat: m.box(x + b0, x + b1, y + a0, y + a1, z0, z1, mat)  # noqa: E731
    bx(-hl + 0.18, hl - 0.18, -0.21, 0.21, z, z + 0.36, "granite")
    bx(-hl + 0.2, hl - 0.2, -0.225, 0.225, z + 0.33, z + 0.37, "led_strip")
    bx(-hl, hl, -hw, hw, z + 0.37, z + 0.45, "wood")
    px, py = (x + hl - 0.3, y) if axis == "x" else (x, y + hl - 0.3)
    m.cylinder(px, py, 0.1, z + 0.45, z + 0.457, "led_strip", n=12)
    if axis == "x":
        return x - hl, x + hl, y - hw, y + hw, z, z + 0.46
    return x - hw, x + hw, y - hl, y + hl, z, z + 0.46


def plaza_lamp(m, x, y, z=0.03, h=5.6, arm=(0.0, -1.0)):
    """광장 가로등: 화강석 받침 + 가는 기둥 + 한쪽으로 뻗은 LED 막대 등기구"""
    m.cylinder(x, y, 0.2, z, z + 0.35, "granite", n=12)
    m.cylinder(x, y, 0.065, z + 0.35, z + h, "metal_dark", n=10)
    ax, ay = arm
    hx, hy = x + ax * 0.55, y + ay * 0.55
    m.beam((x, y, z + h - 0.05), (x + ax * 1.1, y + ay * 1.1, z + h - 0.05), 0.1, 0.08, "metal_dark")
    if abs(ax) > abs(ay):
        m.box(hx - 0.45, hx + 0.45, hy - 0.09, hy + 0.09, z + h - 0.16, z + h - 0.13, "lamp")
    else:
        m.box(hx - 0.09, hx + 0.09, hy - 0.45, hy + 0.45, z + h - 0.16, z + h - 0.13, "lamp")
    r = 1.15
    return x - r, x + r, y - r, y + r, z, z + h + 0.05


def bollard(m, x, y, z=0.03, h=0.85):
    m.cylinder(x, y, 0.08, z, z + h, "stainless", n=10)
    m.cylinder(x, y, 0.085, z + h - 0.18, z + h - 0.12, "paint_white", n=10)
    return x - 0.09, x + 0.09, y - 0.09, y + 0.09, z, z + h


def planter(m, x0, x1, y0, y1, z=0.03, h=0.45, rim=0.12, seed=0, shrubs=3):
    """화강석 화분 (걸터앉는 높이): 테두리 4면 + 흙 + 관목 덩어리"""
    rng = random.Random(seed)
    m.box(x0, x1, y0, y0 + rim, z, z + h, "granite")
    m.box(x0, x1, y1 - rim, y1, z, z + h, "granite")
    m.box(x0, x0 + rim, y0 + rim, y1 - rim, z, z + h, "granite")
    m.box(x1 - rim, x1, y0 + rim, y1 - rim, z, z + h, "granite")
    m.box(x0 + rim, x1 - rim, y0 + rim, y1 - rim, z, z + h - 0.06, "soil")
    w, d = x1 - x0 - 2 * rim, y1 - y0 - 2 * rim
    for k in range(shrubs):
        cx = x0 + rim + w * (k + 0.5) / shrubs
        cy = (y0 + y1) / 2 + rng.uniform(-0.15, 0.15) * d
        r = min(w / shrubs, d) * 0.42
        m.ellipsoid(cx, cy, z + h - 0.06 + r * 0.45, r, r * 0.9, r * 0.6, "shrub", nu=10, nv=5)
    return x0, x1, y0, y1, z, z + h + max(w, d) * 0.4


def feather_flag(m, x, y, z, mat, letters=(), letter_mat="letters", h=3.7, w=0.62):
    """바람개비 깃발(세로 배너): 물통 받침 + 깃대 + 위가 둥근 배너 (정면 = -Y), letters = 위에서부터 한 자씩"""
    m.box(x - 0.28, x + 0.28, y - 0.28, y + 0.28, z, z + 0.12, "plastic_white")
    m.cylinder(x, y, 0.16, z + 0.12, z + 0.3, "plastic_white", n=10)
    m.cylinder(x, y, 0.018, z + 0.3, z + h, "metal", n=6)
    zb, zt = z + 0.9, z + h - 0.05
    arc_r = w * 1.2
    pts = [(x + 0.02, y, zb), (x + w, y, zb + 0.08)]
    for k in range(7):
        a = math.pi / 2 * k / 6
        pts.append((x + 0.02 + (w - 0.02) * math.cos(a), y, zt - arc_r + arc_r * math.sin(a)))
    m.extrude(pts, (0, 0.012, 0), mat)
    f = Facade(m, "front", x, x + w, y, y + 0.012)
    zc = zt - arc_r * 0.55
    for t in letters:
        if t is None:
            continue
        f.text(t, w / 2 + 0.01, zc, 0.0, letter_mat, kind=None)
        zc -= t[3] + 0.08
    return x - 0.3, x + w + 0.02, y - 0.3, y + 0.3, z, z + h


def lounger(m, x, y, z, back="+y"):
    """선베드: 금속 다리 + 좌판 쿠션 + 기울인 등받이. back = 등받이 쪽 (+y 면 바다(-Y)를 본다)"""
    s = 1 if back == "+y" else -1
    y0, y1 = y - 0.95 * s, y + 0.95 * s
    ya, yb = sorted((y0, y + 0.35 * s))
    for lx in (x - 0.28, x + 0.28):
        for ly in (y0 + 0.1 * s, y + 0.3 * s, y1 - 0.1 * s):
            m.box(lx - 0.02, lx + 0.02, ly - 0.02, ly + 0.02, z, z + 0.3, "metal")
    m.box(x - 0.33, x + 0.33, ya, yb, z + 0.3, z + 0.4, "plastic_white")
    yc0, yc1 = y + 0.35 * s, y1
    m.slab([(x - 0.33, yc0, z + 0.42), (x + 0.33, yc0, z + 0.42), (x + 0.33, yc1, z + 0.95),
            (x - 0.33, yc1, z + 0.95)], 0.08, "plastic_white")
    lo, hi = sorted((y0, y1))
    return x - 0.34, x + 0.34, lo, hi, z, z + 0.96


def parasol(m, x, y, z, r=1.3, h=2.5, mat="parasol"):
    m.cylinder(x, y, 0.22, z, z + 0.08, "metal_dark", n=12)
    m.cylinder(x, y, 0.03, z + 0.08, z + h, "metal", n=8)
    m.cone(x, y, r, z + h - 0.45, z + h, mat, n=16)
    return x - r, x + r, y - r, y + r, z, z + h


def speaker(m, x, y, z, facing="-y"):
    """무대 스피커: 삼각대 + 상자 + 앞면 그릴"""
    for a in range(3):
        ang = a * 2.09 + 0.5
        m.beam((x + 0.45 * math.cos(ang), y + 0.45 * math.sin(ang), z), (x, y, z + 1.3), 0.03, 0.03, "metal_dark")
    m.box(x - 0.3, x + 0.3, y - 0.25, y + 0.25, z + 1.3, z + 2.1, "speaker")
    if facing == "-y":
        Facade(m, "front", x - 0.3, x + 0.3, y - 0.25, y + 0.25).box(0.06, 0.54, 1.4, 2.0, 0, 0.01, "grille")
    return x - 0.46, x + 0.46, y - 0.46, y + 0.46, z, z + 2.1
