"""일산지 광장 · 해변 시설 (사진 ①②③⑤⑥): 일산청년광장 바닥 구간 · 버스킹 무대, 백사장 삼각 조형물,
하천 하구 보행교, 해변 검은 난간, 해송 2종, 회전교차로 중앙섬, 'CCTV 주차단속' 노면 글자.

일산청년광장(2025년 7월 완공): 방어진순환도로에서 해수욕장으로 들어가는 주 진입로 130 m 를 보행 광장으로 바꿈 —
가운데 화단을 걷어내고 자연석 판석 · 회색 계열 포장, 턱 낮춘 연석, 버스킹 공간, 무선 충전 무드 벤치.
광장 구간(24 x 32 m)을 진입로 축을 따라 이어 놓고, 바다에서 가장 먼 끝에 무대 구간을 둔다.
백사장 삼각 조형물 · 회전교차로 중앙섬 모양은 사진에서 본 모습을 따른 추정이다.
"""

import math
import random

import props as PR
from designs import Building
from geom import BOTTOM, Facade

# ---------------------------------------------------------------------------
# 광장 공통: 판석 바닥, 가운데 공유 차로(턱 없는 연석 + 볼라드), 양옆 가로수 화분 · 무드 벤치 · 가로등
# ---------------------------------------------------------------------------


def plaza_base(b, lane_y1=16.0, trees=(-8.0, 8.0), benches=(0.0, -13.5, 13.5), lamps=(-4.0, 12.0), tree_x=7.6,
               tree_h=6.5, seed=0):
    m = b.m
    b.lot_slab("plaza_stone")
    hy = b.ld / 2 - 0.05
    m.box(-3.5, 3.5, -hy, min(lane_y1, hy), 0.03, 0.04, "plaza_stone_dark", skip=(BOTTOM,))   # 공유 차로
    m.box(-11.95, 11.95, -hy, -hy + 0.45, 0.03, 0.04, "plaza_stone_dark", skip=(BOTTOM,))     # 구간 경계 띠
    for sx in (-1, 1):
        a, c = sorted((sx * 3.5, sx * 3.8))
        m.box(a, c, -hy, min(lane_y1, hy), 0.03, 0.05, "granite", skip=(BOTTOM,))            # 턱 낮춘 연석
        y = -14.0
        while y < min(lane_y1, hy) - 1.0:
            PR.bollard(b.m, sx * 4.0, y)
            if y + 2.0 < min(lane_y1, hy) - 0.2:
                m.cylinder(sx * 3.65, y + 2.0, 0.06, 0.05, 0.056, "led_strip", n=8)          # 바닥 LED
            y += 4.0
        rng = random.Random(seed + sx)
        for ty in trees:
            PR.planter(m, sx * tree_x - 0.9, sx * tree_x + 0.9, ty - 1.5, ty + 1.5, seed=int(ty) + sx, shrubs=2)
            PR.broadleaf(m, sx * tree_x + rng.uniform(-0.1, 0.1), ty, 0.42, h=tree_h, seed=int(ty * 3) + sx)
        for by in benches:
            PR.led_bench(m, sx * tree_x, by, length=2.4, axis="y")
        for ly in lamps:
            PR.plaza_lamp(m, sx * 10.6, ly, arm=(-sx, 0.0))


def plaza01(text_fn=None):
    b = Building((3, 4), 24.0, 32.0, setback=0.0, seed=51, text_fn=text_fn)
    plaza_base(b)
    b.top = 7.0
    return b, "일산청년광장"


def plaza_stage(text_fn=None):
    """광장 끝 구간: 버스킹 무대 + 흰 막 구조 천막(4 모서리가 솟은 뾰족 지붕) + 스피커 · 조명 트러스 + 객석 벤치"""
    b = Building((3, 4), 24.0, 32.0, setback=0.0, seed=52, text_fn=text_fn)
    b.mats.update({
        "sign": {"color": (0.06, 0.08, 0.14), "rough": 0.4},
        "letters_stage": {"color": (0.98, 0.98, 0.95), "rough": 0.3, "emit": (0.9, 0.95, 1.0), "emit_strength": 3.0},
        "stage_floor": {"color": (0.12, 0.12, 0.13), "color2": (0.09, 0.09, 0.10), "pattern": "wood", "rough": 0.5},
    })
    plaza_base(b, lane_y1=-0.5, trees=(-10.0, 10.0), benches=(-13.5,), lamps=(-2.0, 13.0), tree_x=9.4, tree_h=5.0)
    m = b.m
    sx0, sx1, sy0, sy1, sz = -6.0, 6.0, 2.0, 12.0, 0.75
    m.box(sx0, sx1, sy0, sy1, 0.03, sz, "stage_floor", skip=(BOTTOM,))
    for k, (y0, z1) in enumerate(((1.2, 0.29), (1.6, 0.52))):                         # 무대 앞 계단 2단
        m.box(-3.0, 3.0, y0, sy0 if k else 1.6, 0.03, z1, "granite", skip=(BOTTOM,))
    m.box(sx0, sx1, sy1 - 0.4, sy1, sz, 4.1, "sign")                                   # 배경 벽 + 글자
    back = Facade(m, "front", sx0, sx1, sy1 - 0.4, sy1)
    t = b.letters("일산청년광장", 9.0, 0.95, 0.06)
    if t:
        back.text(t, 6.0, 2.85, 0.0, "letters_stage", kind=None)
    t = b.letters("ILSAN YOUTH PLAZA · BUSKING STAGE", 8.0, 0.3, 0.03)
    if t:
        back.text(t, 6.0, 1.95, 0.0, "letters_stage", kind=None)
    for x in (-5.2, 5.2):
        PR.speaker(m, x, 2.7, sz)
    # 천막: 4 모서리 기둥 + 둘레 보 + 뾰족한 막 지붕
    tx, ty0, ty1 = 7.0, 1.0, 13.0
    tyc, hy = (ty0 + ty1) / 2, (ty1 - ty0) / 2
    for x in (-tx, tx):
        for y in (ty0, ty1):
            m.cylinder(x, y, 0.1, 0.03, 4.45, "white_steel", n=10)
            m.cylinder(x, y, 0.25, 0.03, 0.12, "granite", n=10)
    for y in (ty0, ty1):
        m.box(-tx, tx, y - 0.08, y + 0.08, 4.3, 4.45, "white_steel")
    for x in (-tx, tx):
        m.box(x - 0.08, x + 0.08, ty0 + 0.08, ty1 - 0.08, 4.3, 4.45, "white_steel")

    def membrane(x, y):
        rx, ry = abs(x) / tx, abs(y - tyc) / hy
        r, s = max(rx, ry), min(rx, ry)
        edge = 4.5 + 0.6 * s ** 2
        return edge + (8.2 - edge) * (1 - r) ** 1.8

    m.heightfield(-tx, tx, ty0, ty1, 14, 12, membrane, 0.05, "membrane")
    m.cone(0.0, tyc, 0.25, 8.12, 8.6, "white_steel", n=12)
    m.box(-tx + 0.3, tx - 0.3, ty0 + 0.3, ty0 + 0.42, 4.15, 4.3, "metal")              # 조명 트러스
    for x in (-4.5, -1.5, 1.5, 4.5):
        m.box(x - 0.12, x + 0.12, ty0 + 0.26, ty0 + 0.46, 3.85, 4.15, "metal_dark")
        m.box(x - 0.09, x + 0.09, ty0 + 0.24, ty0 + 0.26, 3.9, 4.1, "lamp")
    for by in (-3.0, -6.0):                                                            # 객석 벤치
        for bx in (-3.0, 3.0):
            PR.led_bench(m, bx, by, length=3.6)
    b.top = 8.6
    return b, "청년광장 버스킹 무대"


# ---------------------------------------------------------------------------
# 백사장 삼각 조형물 — 2x2. 흰 강철 삼각 틀 2겹(뒤 틀은 안쪽에 LED 띠), 화강석 받침 + 이름 글자
# ---------------------------------------------------------------------------

def triangle_frame(m, cx, y, base_z, half, height, t, depth, mat, led=None):
    """XZ 평면의 속 빈 삼각 틀 (모서리를 맞대어 자른 세 토막). 정면 = -Y"""
    A, B, C = (cx - half, base_z), (cx + half, base_z), (cx, base_z + height)
    la, lb, lc = math.dist(B, C), math.dist(A, C), math.dist(A, B)
    per = la + lb + lc
    I = ((la * A[0] + lb * B[0] + lc * C[0]) / per, (la * A[1] + lb * B[1] + lc * C[1]) / per)
    area = abs((B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])) / 2
    r = 2 * area / per
    outer = [A, B, C]

    def shrink(k):
        return [(I[0] + (p[0] - I[0]) * (r - k) / r, I[1] + (p[1] - I[1]) * (r - k) / r) for p in outer]

    inner = shrink(t)
    for i in range(3):
        j = (i + 1) % 3
        quad = [outer[i], outer[j], inner[j], inner[i]]
        m.extrude([(px, y, pz) for px, pz in quad], (0, depth, 0), mat)
    if led:
        strip = shrink(t + 0.06)
        for i in range(3):
            j = (i + 1) % 3
            quad = [inner[i], inner[j], strip[j], strip[i]]
            m.extrude([(px, y + depth * 0.3, pz) for px, pz in quad], (0, depth * 0.4, 0), led)
    return outer


def beach_landmark(text_fn=None):
    b = Building((2, 2), 16.0, 16.0, setback=0.0, seed=53, text_fn=text_fn)
    b.mats["letters_beach"] = {"color": (0.10, 0.30, 0.55), "rough": 0.4, "emit": (0.3, 0.6, 1.0),
                               "emit_strength": 1.5}
    b.lot_slab("sand")
    m = b.m
    m.box(-5.8, 5.8, -1.1, 2.6, 0.03, 0.55, "granite", skip=(BOTTOM,))
    triangle_frame(m, 0.0, -0.6, 0.55, 5.0, 8.8, 0.62, 0.7, "white_steel")
    triangle_frame(m, 0.0, 1.3, 0.55, 3.4, 6.0, 0.42, 0.5, "white_steel", led="led_strip")
    pf = Facade(m, "front", -5.8, 5.8, -1.1, 2.6)
    t = b.letters("ILSAN BEACH", 7.0, 0.3, 0.03)
    if t:
        pf.text(t, 5.8, 0.29, 0.0, "letters_beach", kind=None)
    t = b.letters("일산해수욕장", 4.0, 0.3, 0.03)
    if t:
        Facade(m, "back", -5.8, 5.8, -1.1, 2.6).text(t, 5.8, 0.29, 0.0, "letters_beach", kind=None)
    for x in (-4.3, -2.4, 2.4, 4.3):                                                   # 위로 비추는 바닥등
        m.box(x - 0.15, x + 0.15, -0.95, -0.75, 0.55, 0.62, "metal_dark")
        m.box(x - 0.11, x + 0.11, -0.93, -0.77, 0.62, 0.63, "lamp")
    b.top = 9.4
    return b, "일산해수욕장 삼각 조형물"


# ---------------------------------------------------------------------------
# 하천 하구 보행교 — 2x2. 산책로(앞 6 m)를 가로지르는 나무 아치교 + 돌 호안 + 물길 (바다 쪽 = +Y)
# ---------------------------------------------------------------------------

def stream_bridge(text_fn=None):
    b = Building((2, 2), 16.0, 16.0, setback=0.0, seed=54, text_fn=text_fn)
    b.mats["stone_wall"] = {"color": (0.50, 0.48, 0.44), "color2": (0.40, 0.38, 0.35), "pattern": "tile",
                            "scale": (0.5, 0.3), "mortar": 0.012, "mortar_color": (0.30, 0.29, 0.27), "rough": 0.85,
                            "bump": 0.5}
    m = b.m
    e = 7.95
    for x0, x1 in ((-e, -3.6), (3.6, e)):
        m.box(x0, x1, -e, e, -0.3, 0.03, "sand", skip=(BOTTOM,))
        m.box(x0, x1, -e, -2.0, 0.03, 0.05, "paving", skip=(BOTTOM,))                  # 산책로 포장
    for x0, x1 in ((-3.6, -3.0), (3.0, 3.6)):
        m.box(x0, x1, -e, e, -0.3, 0.25, "stone_wall", skip=(BOTTOM,))                 # 호안
    m.box(-3.0, 3.0, -e, e, -0.3, -0.18, "stream_water", skip=(BOTTOM,))
    rng = random.Random(4)
    for _ in range(7):                                                                 # 물속 돌
        x, y = rng.uniform(-2.4, 2.4), rng.uniform(-1.0, 7.0)
        r = rng.uniform(0.25, 0.5)
        m.ellipsoid(x, y, -0.29 + r * 0.45, r, r * 0.8, r * 0.45, "granite", nu=10, nv=5)
    span, y0, y1 = 6.5, -6.2, -3.2
    deck = lambda x, y: 0.05 + 0.75 * math.cos(math.pi * x / (2 * span)) ** 2   # noqa: E731
    m.heightfield(-span, span, y0, y1, 16, 2, deck, 0.3, "deck")
    for ya, yb in ((y0 - 0.1, y0), (y1, y1 + 0.1)):                                    # 흰 옆보
        m.heightfield(-span, span, ya, yb, 16, 1, lambda x, y: deck(x, y) + 0.05, 0.35, "white_steel")
    for yr in (y0 + 0.05, y1 - 0.05):                                                  # 난간
        xs = [-span + 0.3 + (2 * span - 0.6) * k / 10 for k in range(11)]
        tops = []
        for x in xs:
            z = deck(x, 0)
            m.tube((x, yr, z), (x, yr, z + 1.0), 0.03, 0.03, "metal", n=6)
            tops.append((x, yr, z + 1.0))
        for p, q in zip(tops, tops[1:]):
            m.beam(p, q, 0.08, 0.06, "wood")
    for x in (-span - 0.5, span + 0.5):                                                # 다리 끝 바닥등
        for y in (y0 - 0.4, y1 + 0.4):
            m.cylinder(x, y, 0.1, 0.05, 0.85, "metal_dark", n=10)
            m.cylinder(x, y, 0.08, 0.85, 1.0, "lamp", n=10)
    b.top = 1.95
    return b, "하천 하구 보행교"


# ---------------------------------------------------------------------------
# 해변 난간 — 1x1, 8 m 한 토막 (사진 ②의 도로 바다 쪽 검은 철제 난간). x 방향으로 이어 붙인다.
# ---------------------------------------------------------------------------

def beach_rail(text_fn=None):
    b = Building((1, 1), 8.0, 8.0, setback=0.0, seed=55, text_fn=text_fn)
    m = b.m
    posts = [-3.92 + k * 2.0 for k in range(4)]                                       # 다음 토막의 첫 기둥이 끝 기둥
    for x in posts:
        m.box(x - 0.08, x + 0.08, -0.08, 0.08, 0.0, 0.02, "rail_black")
        m.box(x - 0.035, x + 0.035, -0.035, 0.035, 0.02, 1.1, "rail_black")
        m.box(x - 0.05, x + 0.05, -0.05, 0.05, 1.1, 1.14, "rail_black")
    for z0, z1 in ((1.04, 1.1), (0.55, 0.59), (0.12, 0.16)):
        m.box(-4.0, 4.0, -0.03, 0.03, z0, z1, "rail_black")
    x = -3.85
    while x < 3.95:
        if min(abs(x - p) for p in posts) > 0.06:
            m.box(x - 0.009, x + 0.009, -0.009, 0.009, 0.16, 1.04, "rail_black")
        x += 0.15
    b.top = 1.14
    return b, "해변 난간"


# ---------------------------------------------------------------------------
# 해송 — 1x1. 바다 쪽(+Y)으로 기운 곰솔 두 그루
# ---------------------------------------------------------------------------

def pine01(text_fn=None):
    b = Building((1, 1), 8.0, 8.0, setback=0.0, seed=56, text_fn=text_fn)
    box = PR.pine(b.m, 0.0, -0.6, 0.0, h=9.0, seed=3, lean=0.06, lean_dir=math.pi / 2, reach=2.2,
                  fit=(-3.95, 3.95, -3.95, 3.95))
    b.top = box[5]
    return b, "해송 (큰 나무)"


def pine02(text_fn=None):
    b = Building((1, 1), 8.0, 8.0, setback=0.0, seed=57, text_fn=text_fn)
    box = PR.pine(b.m, -0.4, -0.9, 0.0, h=7.2, seed=9, lean=0.1, lean_dir=math.pi / 2 - 0.4, reach=2.0,
                  fit=(-3.95, 3.95, -3.95, 3.95))
    b.top = box[5]
    return b, "해송 (굽은 나무)"


# ---------------------------------------------------------------------------
# 회전교차로 중앙섬 — 2x2. 붉은 화물차 턱(에이프런) + 노란 띠, 화강석 연석, 꽃 화단, 흰 돛 조형물
# ---------------------------------------------------------------------------

def roundabout(text_fn=None):
    b = Building((2, 2), 16.0, 16.0, setback=0.0, seed=58, text_fn=text_fn)
    b.mats["flower"] = {"color": (0.75, 0.20, 0.45), "color2": (0.95, 0.80, 0.20), "pattern": "noise",
                        "scale": 9.0, "rough": 0.8, "bump": 0.4}
    m = b.m
    m.annulus(0.0, 0.0, 5.2, 7.6, 0.0, 0.08, "apron_red", n=48)
    m.annulus(0.0, 0.0, 7.4, 7.56, 0.08, 0.085, "paint_yellow", n=48)
    for k in range(16):                                                                # 노란 방사 표시
        a = 2 * math.pi * k / 16
        ca, sa = math.cos(a), math.sin(a)
        pts = [(ca * r - sa * w, sa * r + ca * w, 0.08) for r, w in ((5.6, -0.1), (5.6, 0.1), (7.1, 0.1), (7.1, -0.1))]
        m.extrude(pts, (0, 0, 0.005), "paint_yellow")
    m.annulus(0.0, 0.0, 5.0, 5.25, 0.0, 0.3, "granite", n=48)
    m.cylinder(0.0, 0.0, 5.0, 0.0, 0.22, "soil", n=48)
    rng = random.Random(7)
    for k in range(14):                                                                # 관목 · 꽃 고리
        a = 2 * math.pi * k / 14
        r = 3.9
        mat = "flower" if k % 2 else "shrub"
        m.ellipsoid(r * math.cos(a), r * math.sin(a), 0.32, 0.75, 0.75, 0.38 + rng.uniform(0, 0.1), mat, nu=10, nv=5)
    m.cylinder(0.0, 0.0, 1.1, 0.22, 0.6, "granite", n=20)
    for k, (h, rr) in enumerate(((4.6, 0.9), (3.7, 0.8), (2.9, 0.7))):                 # 흰 돛 조형물 3장
        a = 2 * math.pi * k / 3 + 0.3
        ca, sa = math.cos(a), math.sin(a)
        nx, ny = -sa * 0.06, ca * 0.06
        pts = [(ca * 0.15 - nx, sa * 0.15 - ny, 0.6), (ca * rr - nx, sa * rr - ny, 0.6),
               (ca * 0.2 - nx, sa * 0.2 - ny, 0.6 + h)]
        m.extrude(pts, (2 * nx, 2 * ny, 0), "white_steel")
    for k in range(3):
        a = 2 * math.pi * k / 3 + 1.35
        x, y = 1.6 * math.cos(a), 1.6 * math.sin(a)
        m.box(x - 0.12, x + 0.12, y - 0.12, y + 0.12, 0.22, 0.32, "metal_dark")
        m.box(x - 0.09, x + 0.09, y - 0.09, y + 0.09, 0.32, 0.33, "lamp")
    b.top = 5.3
    return b, "회전교차로 중앙섬"


# ---------------------------------------------------------------------------
# 노면 글자 'CCTV 주차단속' — 1x1. 차로(폭 3.5 m) 위에 길쭉하게 (먼 줄 = CCTV, 가까운 줄 = 주차단속)
# ---------------------------------------------------------------------------

def road_marking(text_fn=None, stretch=2.2):
    b = Building((1, 1), 8.0, 8.0, setback=0.0, seed=59, text_fn=text_fn)
    m = b.m
    for text, yc, w in (("CCTV", 1.6, 2.6), ("주차단속", -1.8, 3.2)):
        t = b.letters(text, w, 1.15, 0.004)
        if t is None:
            m.box(-w / 2, w / 2, yc - 1.0, yc + 1.0, 0.001, 0.006, "paint_yellow")
            continue
        verts, faces, _, _, depth = t
        m.add([(lx, yc + ly * stretch, 0.002 + depth / 2 + lz) for lx, ly, lz in verts], faces, "paint_yellow")
    b.top = 0.01
    return b, "노면 글자 CCTV 주차단속"


DESIGNS = {
    "IlsanPlaza01": plaza01,
    "IlsanPlazaStage": plaza_stage,
    "IlsanBeachLandmark": beach_landmark,
    "IlsanStreamBridge": stream_bridge,
    "IlsanBeachRail": beach_rail,
    "IlsanPine01": pine01,
    "IlsanPine02": pine02,
    "IlsanRoundabout": roundabout,
    "IlsanRoadMarking01": road_marking,
}
