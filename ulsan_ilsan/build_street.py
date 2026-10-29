"""일산지 거리 — 일산해수욕장 앞 해변 상가 거리를 블렌더에 만든다.

실제 해안선(Copernicus DEM 0 m 경계)을 따라
  모래사장 → 호안·난간 → 해변 산책로(가로등·해송·벤치) → 왕복 2차로 → 인도 → 횟집·카페 상가
를 배치하고, 건너편 대왕암공원·울기등대 지형을 배경으로 둔다.

실행 방법
  1) 블렌더 Scripting 탭에서 이 파일을 열고 Run Script
  2) 명령줄:  blender --python build_street.py -- [옵션]

옵션 (명령줄에서만)
  --night             야경 (간판·창문·가로등 점등)
  --no-backdrop       배경 지형(대왕암공원 등) 생략
  --font PATH         간판 한글 폰트 (.ttf/.otf). 생략하면 맑은 고딕·나눔고딕 등을 자동 탐색
  --seed N            상가 배치 난수 (기본 7)
  --camera NAME       렌더 카메라: 거리_보행자 | 거리_해변 | 거리_조감 (기본 거리_보행자)
  --save PATH.blend / --render PATH.png / --engine cycles|eevee / --samples N
"""

import argparse
import glob
import math
import os
import sys

import bpy
import numpy as np


def _here():
    f = globals().get("__file__", "")
    if f and os.path.isfile(f):
        return os.path.dirname(os.path.abspath(f))
    for text in bpy.data.texts:
        if text.filepath.endswith("build_street.py"):
            return os.path.dirname(bpy.path.abspath(text.filepath))
    raise RuntimeError("build_street.py 위치를 찾을 수 없습니다. 파일을 저장한 뒤 실행하세요")


HERE = _here()
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_ilsan as B  # noqa: E402
import street as S  # noqa: E402
import terrain as T  # noqa: E402

ROOT = "일산지 거리"

FONT_CANDIDATES = [
    os.path.join(HERE, "fonts", "*.ttf"),
    os.path.join(HERE, "fonts", "*.otf"),
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    os.path.expanduser("~/Library/Fonts/NanumGothicBold.ttf"),
]

WALL_COLORS = [(0.80, 0.78, 0.72), (0.72, 0.64, 0.52), (0.55, 0.36, 0.26), (0.62, 0.64, 0.66),
               (0.85, 0.84, 0.80), (0.42, 0.45, 0.50), (0.78, 0.70, 0.58)]
SIGN_COLORS = {"횟집": [(0.05, 0.25, 0.75), (0.80, 0.10, 0.08), (0.05, 0.45, 0.30)],
               "카페": [(0.10, 0.08, 0.06), (0.85, 0.80, 0.70), (0.20, 0.35, 0.25)],
               "숙박": [(0.55, 0.10, 0.45), (0.10, 0.10, 0.35)],
               "상가": [(0.90, 0.55, 0.05), (0.10, 0.50, 0.20), (0.85, 0.15, 0.10)]}
CAR_COLORS = [(0.9, 0.9, 0.9), (0.05, 0.05, 0.05), (0.5, 0.52, 0.55), (0.55, 0.05, 0.05), (0.1, 0.2, 0.45)]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="build_street.py")
    p.add_argument("--night", action="store_true")
    p.add_argument("--no-backdrop", action="store_true")
    p.add_argument("--font")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--camera", default="거리_보행자")
    p.add_argument("--save")
    p.add_argument("--render")
    p.add_argument("--engine", choices=("cycles", "eevee"), default="eevee")
    p.add_argument("--samples", type=int, default=64)
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# 공용
# ---------------------------------------------------------------------------

def clear_previous():
    root = bpy.data.collections.get(ROOT)
    if root is None:
        return
    colls = [root] + list(root.children_recursive)
    for coll in colls:
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj)
    for coll in reversed(colls):
        bpy.data.collections.remove(coll)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.lights, bpy.data.cameras, bpy.data.materials):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def emissive(name, color, strength, roughness=0.3):
    """발광 머티리얼 (strength 0 이면 일반 재질)"""
    mat = B.material(name, color, roughness=roughness, noise=0)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    if strength > 0:
        B._set_input(bsdf, ["Emission Color", "Emission"], (*color, 1.0))
        B._set_input(bsdf, ["Emission Strength"], strength)
    return mat


def add_mesh(name, coll, verts, faces, mats, mat_index=None, smooth=False):
    obj = B.mesh_object(name, coll, verts, faces, mats)
    if mat_index is not None:
        obj.data.polygons.foreach_set("material_index", list(mat_index))
    if not smooth:
        obj.data.polygons.foreach_set("use_smooth", [False] * len(obj.data.polygons))
    return obj


def box(x0, x1, y0, y1, z0, z1):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


class Builder:
    """여러 조각(정점, 면, 머티리얼 번호)을 한 메시로 모은다"""

    def __init__(self):
        self.verts, self.faces, self.mi = [], [], []

    def add(self, part, mat=0):
        v, f = part
        o = len(self.verts)
        self.verts += [tuple(p) for p in v]
        self.faces += [tuple(int(i) + o for i in face) for face in f]
        self.mi += [mat] * len(f)

    def build(self, name, coll, mats):
        return add_mesh(name, coll, self.verts, self.faces, mats, self.mi)


def heading(n):
    """건물 전면이 거리(-n, 바다 쪽)를 보도록 하는 Z 회전각. 로컬 +Y = 육지 쪽"""
    return math.atan2(-n[0], n[1])


def find_font(path=None):
    if path:
        return path if os.path.isfile(path) else None
    for pattern in FONT_CANDIDATES:
        for f in sorted(glob.glob(pattern)):
            return f
    return None


# ---------------------------------------------------------------------------
# 지면: 바다 바닥 · 모래 · 호안 · 산책로 · 도로 · 인도
# ---------------------------------------------------------------------------

def build_ground(st, coll, alleys):
    sand_top = lambda r: r - 1.4  # noqa: E731
    prom = lambda r: r + 0.2  # noqa: E731
    walk = lambda r: r + 0.15  # noqa: E731
    road = lambda r: r  # noqa: E731

    mats = [
        B.material("거리_해저모래", (0.45, 0.38, 0.26), roughness=0.9, noise=0.2),
        B.material("거리_모래", (0.56, 0.45, 0.30), roughness=0.85, noise=0.25),
        B.material("거리_호안", (0.50, 0.48, 0.45), roughness=0.9, noise=0.3),
        B.material("거리_산책로", (0.45, 0.30, 0.22), roughness=0.8, noise=0.3),
        B.material("거리_아스팔트", (0.06, 0.06, 0.065), roughness=0.85, noise=0.2),
        B.material("거리_보도블록", (0.36, 0.34, 0.32), roughness=0.85, noise=0.25),
        B.material("거리_연석", (0.70, 0.70, 0.68), roughness=0.7, noise=0),
    ]
    g = Builder()
    g.add(st.strip(-160, -25, -4.5, -0.6), 0)                     # 물속 모래
    g.add(st.strip(-25, 0, -0.6, 0.0), 1)                          # 젖은 모래
    g.add(st.strip(0, S.SAND_END, 0.0, sand_top), 1)               # 백사장
    g.add(st.strip(S.SAND_END, S.SAND_END, sand_top, prom), 2)     # 호안 옹벽 (바다를 향함)
    g.add(st.strip(S.SAND_END, S.PROMENADE_END, prom, prom), 3)    # 해변 산책로
    v, f = st.strip(S.PROMENADE_END, S.PROMENADE_END, road, prom)  # 연석 (도로를 향함)
    g.add((v, f), 6)
    g.add(st.strip(S.PROMENADE_END, S.ROAD_END, road, road), 4)    # 도로
    g.add(st.strip(S.ROAD_END, S.ROAD_END, road, walk), 6)         # 연석
    g.add(st.strip(S.ROAD_END, S.BACK_END, walk, walk), 5)         # 인도 · 건물 부지
    ground = g.build("거리_지면", coll, mats)

    # 차선: 중앙 황색 복선, 가장자리 백색 실선, 골목 앞 횡단보도
    yellow = B.material("거리_황색선", (0.85, 0.65, 0.05), roughness=0.6, noise=0)
    white = B.material("거리_백색선", (0.85, 0.85, 0.85), roughness=0.6, noise=0)
    m = Builder()
    lift = lambda r: r + 0.02  # noqa: E731
    mid = (S.PROMENADE_END + S.ROAD_END) / 2
    for off in (-0.25, 0.1):
        m.add(st.strip(mid + off, mid + off + 0.15, lift, lift), 0)
    for off in (S.PROMENADE_END + 0.4, S.ROAD_END - 0.55):
        m.add(st.strip(off, off + 0.15, lift, lift), 1)
    for s_c in alleys:
        for k in range(-3, 4):
            s0 = s_c + k * 1.0 - 0.25
            m.add(st.strip(S.PROMENADE_END + 0.8, S.ROAD_END - 0.8, lift, lift, s0, s0 + 0.5, step=0.5), 1)
    add_mesh("거리_차선", coll, m.verts, m.faces, [yellow, white], m.mi)
    return ground


def build_railing(st, coll):
    """호안 위 난간: 2 m 간격 기둥 + 상단 손잡이"""
    mat = B.material("거리_난간", (0.75, 0.77, 0.80), roughness=0.3, metallic=0.8, noise=0)
    b = Builder()
    off = S.SAND_END + 0.3
    top = lambda r: r + 1.2  # noqa: E731
    for s in np.arange(1.0, st.length, 2.0):
        (x, y), n, r = st.frame(s, off)
        b.add(box(x - 0.04, x + 0.04, y - 0.04, y + 0.04, r + 0.2, r + 1.2))
    b.add(st.strip(off - 0.04, off + 0.04, top, top))
    b.add(st.strip(off, off, lambda r: r + 1.12, top))
    b.add(st.strip(off, off, lambda r: r + 0.65, lambda r: r + 0.7))
    return b.build("거리_난간", coll, [mat])


# ---------------------------------------------------------------------------
# 상가
# ---------------------------------------------------------------------------

def building_parts(lot, w, rng):
    """로컬 좌표(전면 y=0, 거리 쪽 -Y)의 상가 건물 조각들.
    머티리얼: 0 외벽, 1 유리, 2 간판, 3 지붕·테두리, 4 차양
    """
    d = lot["depth"]
    floors = lot["floors"]
    ground_h = 4.2
    upper_h = 3.1
    height = ground_h + (floors - 1) * upper_h
    hw = w / 2
    parts = [(box(-hw, hw, 0, d, -1.0, height), 0),
             (box(-hw - 0.15, hw + 0.15, -0.15, d + 0.15, height, height + 0.35), 3)]
    # 1층 통유리 상점 + 간판
    parts.append((box(-hw + 0.5, hw - 0.5, -0.04, 0.0, 0.1, 3.4), 1))
    parts.append((box(-hw * 0.88, hw * 0.88, -0.35, -0.05, 3.55, 4.5), 2))
    if lot["kind"] in ("횟집", "상가") and rng.random() < 0.6:
        parts.append((box(-hw + 0.3, hw - 0.3, -1.8, 0.0, 3.25, 3.4), 4))  # 차양
    # 위층 창
    for f in range(1, floors):
        z0 = ground_h + (f - 1) * upper_h + 0.8
        if lot["kind"] == "카페" and f <= 2:
            parts.append((box(-hw + 0.4, hw - 0.4, -0.05, 0.0, z0 - 0.5, z0 + 2.0), 1))
            continue
        n_win = max(int(w // 3.2), 1)
        span = w / n_win
        for i in range(n_win):
            cx = -hw + span * (i + 0.5)
            parts.append((box(cx - 0.8, cx + 0.8, -0.06, 0.0, z0, z0 + 1.5), 1))
    if lot["kind"] == "숙박":  # 옥상 세로 간판
        parts.append((box(-0.6, 0.6, -0.4, -0.1, height - 6.0, height + 1.5), 2))
    return parts, height


def build_shops(st, coll, lots, font, night, seed):
    rng = np.random.default_rng(seed)
    glow = 4.0 if night else 0.0
    walls = [B.material(f"외벽{i}", c, roughness=0.8, noise=0.15) for i, c in enumerate(WALL_COLORS)]
    glass = emissive("유리", (0.06, 0.08, 0.09) if not night else (0.9, 0.6, 0.3), 0.35 if night else 0,
                     roughness=0.05)
    trim = B.material("테두리", (0.25, 0.25, 0.26), roughness=0.6, noise=0)
    awning_colors = [(0.70, 0.10, 0.08), (0.10, 0.30, 0.65), (0.15, 0.45, 0.25)]
    awnings = [B.material(f"차양{i}", c, roughness=0.7, noise=0) for i, c in enumerate(awning_colors)]
    sign_mats = {}
    text_mat = emissive("간판글씨", (1.0, 1.0, 1.0), 6.0 if night else 0.5, roughness=0.4)
    font_data = bpy.data.fonts.load(font, check_existing=True) if font else None

    for i, lot in enumerate(lots):
        w = lot["s1"] - lot["s0"]
        s_c = (lot["s0"] + lot["s1"]) / 2
        (x, y), n, r = st.frame(s_c, S.FRONTAGE)
        parts, height = building_parts(lot, w, rng)
        sign_color = SIGN_COLORS[lot["kind"]][int(rng.integers(len(SIGN_COLORS[lot["kind"]])))]
        key = (lot["kind"], sign_color)
        if key not in sign_mats:
            sign_mats[key] = emissive(f"간판_{lot['kind']}{len(sign_mats)}", sign_color, glow + 0.3)
        b = Builder()
        for part, mat in parts:
            b.add(part, mat)
        mats = [walls[int(rng.integers(len(walls)))], glass, sign_mats[key], trim,
                awnings[int(rng.integers(len(awnings)))]]
        obj = b.build(f"상가{i:02d}_{lot['kind']}_{lot['name']}", coll, mats)
        obj.location = (x, y, r + 0.15)
        obj.rotation_euler = (0, 0, heading(n))
        lot["height"] = height

        if font_data is not None:
            curve = bpy.data.curves.new(f"간판글씨{i:02d}", 'FONT')
            curve.body = lot["name"]
            curve.font = font_data
            curve.align_x = 'CENTER'
            curve.align_y = 'CENTER'
            curve.size = 0.62
            curve.extrude = 0.02
            curve.materials.append(text_mat)
            txt = bpy.data.objects.new(f"간판글씨{i:02d}_{lot['name']}", curve)
            txt.parent = obj
            txt.location = (0, -0.4, 4.03)
            txt.rotation_euler = (math.radians(90), 0, 0)
            coll.objects.link(txt)
            # 간판보다 넓으면 줄인다
            bpy.context.view_layer.update()
            span = txt.dimensions.x
            if span > w * 0.8:
                txt.scale = (w * 0.8 / span,) * 3


# ---------------------------------------------------------------------------
# 가로 시설물: 가로등 · 해송 · 벤치 · 자동차
# ---------------------------------------------------------------------------

def streetlight_proto(coll, night):
    pole = B.material("가로등_기둥", (0.20, 0.22, 0.25), roughness=0.4, metallic=0.7, noise=0)
    lamp = emissive("가로등_등", (1.0, 0.85, 0.6), 25.0 if night else 0.5)
    b = Builder()
    v, f = B.prism(8, 0.09, 0, 8.0)
    b.add((v, f), 0)
    # 로컬 -Y 쪽(도로)으로 뻗은 팔과 등기구
    b.add(box(-0.05, 0.05, -1.6, 0.0, 7.8, 7.9), 0)
    b.add(box(-0.25, 0.25, -1.9, -1.2, 7.55, 7.75), 1)
    obj = b.build("가로등_원형", coll, [pole, lamp])
    obj.hide_render = True
    obj.hide_viewport = True
    return obj


def place_linked(proto, name, coll, loc, rot_z, scale=1.0):
    obj = bpy.data.objects.new(name, proto.data)
    obj.location = loc
    obj.rotation_euler = (0, 0, rot_z)
    obj.scale = (scale,) * 3
    coll.objects.link(obj)
    return obj


def build_furniture(st, coll, night, rng):
    protos = B.collection("원형", coll)
    protos.hide_render = True
    light = streetlight_proto(protos, night)
    trunk = B.material("해송_줄기", (0.18, 0.10, 0.06), noise=0)
    leaf = B.material("해송_잎", (0.04, 0.12, 0.04), roughness=0.85, noise=0.3)
    pines = [B.pine_tree(f"해송_원형{i}", protos, h, c, trunk, leaf)
             for i, (h, c) in enumerate([(9.0, 2.8), (11.0, 3.2), (7.5, 2.4)])]
    wood = B.material("벤치_목재", (0.40, 0.24, 0.12), roughness=0.7, noise=0.2)
    metal = B.material("벤치_다리", (0.15, 0.15, 0.16), roughness=0.4, metallic=0.7, noise=0)
    bb = Builder()
    bb.add(box(-0.9, 0.9, -0.22, 0.22, 0.42, 0.48), 0)
    bb.add(box(-0.9, 0.9, 0.18, 0.24, 0.5, 0.9), 0)
    for sx in (-0.75, 0.75):
        bb.add(box(sx - 0.04, sx + 0.04, -0.2, 0.2, 0.0, 0.42), 1)
    bench = bb.build("벤치_원형", protos, [wood, metal])

    lamp_s = np.arange(15.0, st.length - 5, 30.0)
    for i, s in enumerate(lamp_s):
        (x, y), n, r = st.frame(s, S.PROMENADE_END - 0.6)
        # 팔이 도로 쪽(+n)을 향하도록: 로컬 -Y = +n
        place_linked(light, f"가로등{i:02d}", coll, (x, y, r + 0.2), math.atan2(n[0], -n[1]))
        if night:
            ld = bpy.data.lights.new(f"가로등빛{i:02d}", 'POINT')
            ld.energy = 900
            ld.color = (1.0, 0.82, 0.55)
            lo = bpy.data.objects.new(f"가로등빛{i:02d}", ld)
            px, py = np.array([x, y]) + n * 1.5
            lo.location = (px, py, r + 7.3)
            coll.objects.link(lo)
    for i, s in enumerate(np.arange(30.0, st.length - 5, 15.0)):
        if abs((s - 15.0) % 30.0) < 1:  # 가로등 자리 피하기
            continue
        (x, y), n, r = st.frame(s + rng.uniform(-3, 3), S.SAND_END + 2.5)
        proto = pines[int(rng.integers(len(pines)))]
        place_linked(proto, f"해송{i:02d}", coll, (x, y, r + 0.2), rng.uniform(0, 6.28), rng.uniform(0.85, 1.15))
    for i, s in enumerate(np.arange(22.0, st.length - 5, 30.0)):
        (x, y), n, r = st.frame(s, S.SAND_END + 1.4)
        place_linked(bench, f"벤치{i:02d}", coll, (x, y, r + 0.2), heading(n))  # 바다를 보고 앉음


def build_cars(st, coll, rng, count=9):
    tyre = B.material("타이어", (0.02, 0.02, 0.02), roughness=0.9, noise=0)
    window = B.material("차창", (0.02, 0.03, 0.04), roughness=0.05, noise=0)
    lanes = [S.PROMENADE_END + 2.6, S.ROAD_END - 2.6]
    for i in range(count):
        color = CAR_COLORS[int(rng.integers(len(CAR_COLORS)))]
        paint = B.material(f"차체{i}", color, roughness=0.25, metallic=0.5, noise=0)
        b = Builder()
        L, W = rng.uniform(4.3, 4.9), 1.85
        b.add(box(-L / 2, L / 2, -W / 2, W / 2, 0.3, 1.0), 0)
        b.add(box(-L * 0.28, L * 0.22, -W / 2 + 0.08, W / 2 - 0.08, 1.0, 1.48), 1)
        for wx in (-L * 0.32, L * 0.32):
            for wy in (-W / 2 - 0.02, W / 2 - 0.2):
                b.add(box(wx - 0.33, wx + 0.33, wy, wy + 0.22, 0.0, 0.66), 2)
        car = b.build(f"자동차{i}", coll, [paint, window, tyre])
        lane = int(rng.integers(2))
        s = rng.uniform(20, st.length - 20)
        (x, y), n, r = st.frame(s, lanes[lane])
        (x2, y2), _, _ = st.frame(s + 1.0, lanes[lane])
        # n 은 진행 방향(+station)의 오른쪽이므로 우측 통행이면 육지 쪽 차로가 +station 방향
        ang = math.atan2(y2 - y, x2 - x) + (math.pi if lane == 0 else 0.0)
        car.location = (x, y, r)
        car.rotation_euler = (0, 0, ang)


# ---------------------------------------------------------------------------
# 배경 (대왕암공원 · 울기등대 · 주변 지형)
# ---------------------------------------------------------------------------

def build_backdrop(st, dem, coll):
    cls, coast = T.classify(dem)
    X, Y = dem.grid_xy()
    pts = np.column_stack([X.ravel(), Y.ravel()])
    s, off, interior = st.project(pts)
    corridor = (interior & (off > -170) & (off < S.BACK_END)).reshape(dem.shape)
    bg = T.Dem(dem.h.copy(), dem.north, dem.south, dem.west, dem.east)
    bg.h[corridor] = -30.0  # 거리 구간은 지형을 비워 둔다
    cls = cls.copy()
    cls[corridor] = T.SEA
    # 거리만 보이도록 배경에는 가상 건물을 두지 않는다 (지형 · 숲 · 랜드마크만)
    B.build_terrain(bg, cls, coast, 1.0, coll)
    B.build_trees(bg, cls, 1.0, B.collection("배경_나무", coll), np.random.default_rng(3))
    B.build_lighthouse(dem, 1.0, coll)
    B.build_daewangam(dem, 1.0, coll)


# ---------------------------------------------------------------------------
# 카메라 · 조명
# ---------------------------------------------------------------------------

def add_camera(name, coll, loc, target, lens):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start = 0.1
    data.clip_end = 100000
    cam = bpy.data.objects.new(name, data)
    cam.location = loc
    coll.objects.link(cam)
    B.look_at(cam, target)
    return cam


def build_cameras(st, coll):
    L = st.length
    (px, py), n, r = st.frame(L * 0.30, S.ROAD_END + 1.8)
    (tx, ty), _, tr = st.frame(L * 0.30 + 70, S.PROMENADE_END + 2)
    walker = add_camera("거리_보행자", coll, (px, py, r + 1.65), (tx, ty, tr + 2.5), 24)
    (px, py), n, r = st.frame(L * 0.45, 18)
    (tx, ty), _, tr = st.frame(L * 0.45 + 35, S.FRONTAGE + 4)
    sand_z = (r - 1.4) * 18 / S.SAND_END
    add_camera("거리_해변", coll, (px, py, sand_z + 1.6), (tx, ty, tr + 9), 26)
    (px, py), n, r = st.frame(L * 0.45, -170)
    (tx, ty), _, tr = st.frame(L * 0.52, S.FRONTAGE)
    add_camera("거리_조감", coll, (px, py, 55.0), (tx, ty, tr + 4), 30)
    return walker


def setup_world(scene, coll, night):
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    B.enable_nodes(world)
    bg = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
    sun_data = bpy.data.lights.new("거리_태양", 'SUN')
    sun = bpy.data.objects.new("거리_태양", sun_data)
    coll.objects.link(sun)
    if night:
        if bg is not None:
            bg.inputs["Color"].default_value = (0.012, 0.02, 0.05, 1.0)
            bg.inputs["Strength"].default_value = 0.6
        sun_data.energy = 0.05  # 달빛
        sun_data.color = (0.6, 0.7, 1.0)
        sun.rotation_euler = (math.radians(60), 0, math.radians(200))
    else:
        if bg is not None:
            bg.inputs["Color"].default_value = (0.50, 0.66, 0.90, 1.0)
            bg.inputs["Strength"].default_value = 0.9
        sun_data.energy = 4.5
        sun_data.angle = math.radians(1.0)
        sun.rotation_euler = (math.radians(48), 0, math.radians(125))  # 오전, 바다 쪽(동남)에서 비춤


# ---------------------------------------------------------------------------

def build(night=False, backdrop=True, font=None, seed=7, engine="eevee", samples=64):
    scene = bpy.context.scene
    clear_previous()
    root = B.collection(ROOT, scene.collection)
    dem = T.prepare(T.Dem.load(), 3)
    st = S.Street(dem)
    lots, alleys = S.lay_lots(st.length, seed=seed)
    rng = np.random.default_rng(seed)

    build_ground(st, B.collection("지면·도로", root), alleys)
    build_railing(st, root)
    font_path = find_font(font)
    build_shops(st, B.collection("상가", root), lots, font_path, night, seed)
    build_furniture(st, B.collection("가로시설물", root), night, rng)
    build_cars(st, B.collection("자동차", root), rng)
    B.build_sea(dem, root)
    if backdrop:
        build_backdrop(st, dem, B.collection("배경", root))
    scene.camera = build_cameras(st, root)
    setup_world(scene, root, night)
    B.setup_render(scene, engine, samples)
    B.set_viewport_clip()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_start = 0.1
    stats = {"거리 길이(m)": round(st.length), "상가": len(lots), "골목": len(alleys),
             "간판 폰트": os.path.basename(font_path) if font_path else "없음 (글씨 생략)"}
    print("일산지 거리 생성 완료:", stats)
    return stats


def main():
    args = parse_args()
    build(args.night, not args.no_backdrop, args.font, args.seed, args.engine, args.samples)
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save))
    if args.render:
        bpy.context.scene.camera = bpy.data.objects[args.camera]
        bpy.context.scene.render.filepath = os.path.abspath(args.render)
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
