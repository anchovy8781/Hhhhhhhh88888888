"""울산 동구 일산동(일산해수욕장 · 대왕암공원) 장면을 블렌더에 만든다.

실행 방법
  1) 블렌더 Scripting 탭에서 이 파일을 열고 Run Script
  2) 명령줄:  blender --python build_ilsan.py -- [옵션]

옵션 (명령줄에서만)
  --upsample N        DEM 보간 배수 (기본 3, 약 9 m 격자)
  --exaggeration F    고도 과장 배율 (기본 1.0)
  --no-buildings      가상 건물 생략
  --no-trees          나무 생략
  --save PATH.blend   .blend 로 저장
  --render PATH.png   렌더해서 저장
  --engine cycles|eevee
  --samples N         렌더 샘플 수 (기본 64)
  --camera NAME       렌더할 카메라 (카메라 | 카메라_대왕암)
"""

import argparse
import math
import os
import sys

import bpy
import numpy as np


def _here():
    f = globals().get("__file__", "")
    if f and os.path.isfile(f):
        return os.path.dirname(os.path.abspath(f))
    for text in bpy.data.texts:  # 텍스트 에디터에서 실행한 경우
        if text.filepath.endswith("build_ilsan.py"):
            return os.path.dirname(bpy.path.abspath(text.filepath))
    raise RuntimeError("build_ilsan.py 위치를 찾을 수 없습니다. 파일을 저장한 뒤 실행하세요")


HERE = _here()
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import terrain as T  # noqa: E402

ROOT = "일산동"

# 분류별 지면 색 (sRGB 에 가까운 선형 값)
GROUND_COLORS = {
    T.SEA: (0.20, 0.17, 0.12),
    T.BEACH: (0.62, 0.50, 0.32),
    T.ROCK: (0.20, 0.14, 0.11),
    T.PARK_FOREST: (0.04, 0.08, 0.03),
    T.HILL_FOREST: (0.04, 0.09, 0.03),
    T.URBAN: (0.13, 0.13, 0.12),
    T.GRASS: (0.10, 0.16, 0.05),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="build_ilsan.py")
    p.add_argument("--upsample", type=int, default=3)
    p.add_argument("--exaggeration", type=float, default=1.0)
    p.add_argument("--no-buildings", action="store_true")
    p.add_argument("--no-trees", action="store_true")
    p.add_argument("--save")
    p.add_argument("--render")
    p.add_argument("--engine", choices=("cycles", "eevee"), default="eevee")
    p.add_argument("--samples", type=int, default=64)
    p.add_argument("--camera", default="카메라")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# 장면 / 컬렉션
# ---------------------------------------------------------------------------

def clear_previous():
    """이전 실행에서 만든 '일산동' 컬렉션과 그 안의 데이터만 지운다."""
    root = bpy.data.collections.get(ROOT)
    if root is None:
        return
    colls = [root] + list(root.children_recursive)
    for coll in colls:
        for obj in list(coll.objects):
            data = obj.data
            bpy.data.objects.remove(obj)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Light):
                    bpy.data.lights.remove(data)
                elif isinstance(data, bpy.types.Camera):
                    bpy.data.cameras.remove(data)
    for coll in reversed(colls):
        bpy.data.collections.remove(coll)
    for mat in list(bpy.data.materials):
        if mat.name.startswith("ILS_") and mat.users == 0:
            bpy.data.materials.remove(mat)


def collection(name, parent):
    coll = bpy.data.collections.new(name)
    parent.children.link(coll)
    return coll


def mesh_object(name, coll, verts, faces, materials=()):
    me = bpy.data.meshes.new(name)
    if isinstance(faces, np.ndarray):
        faces = faces.tolist()
    me.from_pydata(np.asarray(verts, dtype=np.float32).tolist(), [], [tuple(f) for f in faces])
    me.validate()
    for mat in materials:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# 머티리얼
# ---------------------------------------------------------------------------

def enable_nodes(idblock):
    """블렌더 5.0 부터는 항상 노드를 쓰므로 use_nodes 는 그 이전 버전에서만 켠다"""
    if bpy.app.version < (5, 0, 0):
        idblock.use_nodes = True


def _set_input(node, names, value):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return


def material(name, color, roughness=0.8, noise=0.25, metallic=0.0, emission=None):
    """Principled BSDF + 노이즈로 색 변화를 준 간단한 머티리얼"""
    mat = bpy.data.materials.new("ILS_" + name)
    enable_nodes(mat)
    mat.diffuse_color = (*color, 1.0)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    _set_input(bsdf, ["Roughness"], roughness)
    _set_input(bsdf, ["Metallic"], metallic)
    if emission:
        _set_input(bsdf, ["Emission Color", "Emission"], (*emission, 1.0))
        _set_input(bsdf, ["Emission Strength"], 2.0)
    if noise > 0:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        _set_input(tex, ["Scale"], 0.05)
        _set_input(tex, ["Detail"], 6.0)
        coord = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        dark = tuple(c * (1 - noise) for c in color)
        ramp.color_ramp.elements[0].color = (*dark, 1.0)
        ramp.color_ramp.elements[1].color = (*color, 1.0)
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    return mat


def water_material():
    mat = bpy.data.materials.new("ILS_바다")
    enable_nodes(mat)
    mat.diffuse_color = (0.02, 0.10, 0.16, 1.0)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = (0.01, 0.07, 0.11, 1.0)
    _set_input(bsdf, ["Roughness"], 0.06)
    _set_input(bsdf, ["IOR"], 1.33)
    # 잔물결: 노이즈 -> 범프
    tex = nt.nodes.new("ShaderNodeTexNoise")
    _set_input(tex, ["Scale"], 0.08)
    _set_input(tex, ["Detail"], 8.0)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    _set_input(bump, ["Strength"], 0.15)
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------------------------------------------------------------------------
# 지형
# ---------------------------------------------------------------------------

def grid_faces(rows, cols):
    idx = np.arange(rows * cols).reshape(rows, cols)
    a = idx[:-1, :-1].ravel()
    b = idx[1:, :-1].ravel()
    c = idx[1:, 1:].ravel()
    d = idx[:-1, 1:].ravel()
    return np.stack([a, b, c, d], axis=1)  # 행 0 이 북쪽이므로 이 순서가 위쪽(+Z) 법선


def build_terrain(dem, cls, coast, exaggeration, coll):
    X, Y = dem.grid_xy()
    Z = dem.h * exaggeration
    rows, cols = dem.shape
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    faces = grid_faces(rows, cols)

    order = list(GROUND_COLORS)
    mats = [material(T.CLASS_NAMES[k], GROUND_COLORS[k], roughness=0.9 if k != T.BEACH else 0.7)
            for k in order]
    obj = mesh_object("지형", coll, verts, faces, mats)

    face_cls = cls[:-1, :-1].ravel()
    lookup = np.zeros(max(order) + 1, dtype=np.int32)
    for i, k in enumerate(order):
        lookup[k] = i
    obj.data.polygons.foreach_set("material_index", lookup[face_cls])
    obj.data.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
    obj.data.update()
    return obj


def build_sea(dem, coll, margin=40000.0):
    x0, x1, y0, y1 = dem.extent()
    verts = [(x0 - margin, y0 - margin, 0), (x1 + margin, y0 - margin, 0),
             (x1 + margin, y1 + margin, 0), (x0 - margin, y1 + margin, 0)]
    return mesh_object("바다", coll, verts, [(0, 1, 2, 3)], [water_material()])


# ---------------------------------------------------------------------------
# 나무 (정점 인스턴싱)
# ---------------------------------------------------------------------------

def cone(n, radius, z0, z1, offset=0):
    """원뿔 정점/면 (offset 은 정점 번호 시작값)"""
    verts = [(radius * math.cos(2 * math.pi * i / n), radius * math.sin(2 * math.pi * i / n), z0)
             for i in range(n)] + [(0, 0, z1)]
    faces = [(offset + i, offset + (i + 1) % n, offset + n) for i in range(n)]
    faces.append(tuple(offset + i for i in reversed(range(n))))
    return verts, faces


def pine_tree(name, coll, height, crown, trunk_mat, leaf_mat):
    """곰솔(해송) 느낌의 낮은 폴리곤 소나무. 원점이 밑동."""
    verts, faces = [], []
    n = 6
    tr = 0.25 * crown / 3
    for i in range(n):  # 줄기 (육각기둥)
        a = 2 * math.pi * i / n
        verts += [(tr * math.cos(a), tr * math.sin(a), 0), (tr * math.cos(a), tr * math.sin(a), height * 0.55)]
    for i in range(n):
        j = (i + 1) % n
        faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    trunk_faces = len(faces)
    for k, (z0, z1, r) in enumerate([(0.40, 0.80, 1.0), (0.62, 1.0, 0.7)]):
        v, f = cone(7, crown * r, height * z0, height * z1, offset=len(verts))
        verts += v
        faces += f
    obj = mesh_object(name, coll, verts, faces, [trunk_mat, leaf_mat])
    mi = [0] * trunk_faces + [1] * (len(faces) - trunk_faces)
    obj.data.polygons.foreach_set("material_index", mi)
    return obj


def instance_points(name, coll, points, proto):
    """points 의 각 정점에 proto 를 인스턴싱하는 오브젝트"""
    emitter = mesh_object(name, coll, points, [])
    emitter.instance_type = 'VERTS'
    proto.parent = emitter
    proto.hide_render = False
    emitter.show_instancer_for_render = False
    emitter.show_instancer_for_viewport = False
    return emitter


def build_trees(dem, cls, exaggeration, coll, rng):
    trunk = material("나무줄기", (0.12, 0.07, 0.04), noise=0)
    leaf = material("솔잎", (0.03, 0.09, 0.03), roughness=0.85, noise=0.3)
    protos = collection("나무 원형", coll)
    groups = [
        ("송림", T.PARK_FOREST, 8.0, [(13.0, 3.2), (10.0, 2.8), (15.0, 3.6)]),
        ("산림", T.HILL_FOREST, 12.0, [(11.0, 3.4), (9.0, 3.0), (13.0, 3.8)]),
    ]
    count = 0
    for label, klass, spacing, sizes in groups:
        pts = T.scatter(cls == klass, dem, spacing, seed=klass)
        pts[:, 2] = pts[:, 2] * exaggeration - 0.5
        variant = rng.integers(0, len(sizes), len(pts))
        for i, (h, crown) in enumerate(sizes):
            proto = pine_tree(f"{label}_소나무{i}", protos, h, crown, trunk, leaf)
            instance_points(f"{label}_{i}", coll, pts[variant == i], proto)
        count += len(pts)
    return count


# ---------------------------------------------------------------------------
# 건물 (가상 배치)
# ---------------------------------------------------------------------------

def box_mesh(lots, exaggeration, sink=3.0):
    """lots: (N, 7) = x, y, z, 가로, 세로, 높이, 회전 -> 정점/면"""
    n = len(lots)
    corners = np.array([(-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)])
    x, y, z, w, d, h, rot = lots.T
    cos, sin = np.cos(rot)[:, None], np.sin(rot)[:, None]
    lx = corners[None, :, 0] * w[:, None]
    ly = corners[None, :, 1] * d[:, None]
    px = x[:, None] + lx * cos - ly * sin
    py = y[:, None] + lx * sin + ly * cos
    ground = z * exaggeration
    zb = np.repeat((ground - sink)[:, None], 4, axis=1)
    zt = np.repeat((ground + h)[:, None], 4, axis=1)
    bottom = np.stack([px, py, zb], axis=2)
    top = np.stack([px, py, zt], axis=2)
    verts = np.concatenate([bottom, top], axis=1).reshape(-1, 3)
    base = (np.arange(n) * 8)[:, None]
    local = np.array([[0, 3, 2, 1], [4, 5, 6, 7],
                      [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])
    faces = (base[:, None, :] + local[None, :, :]).reshape(-1, 4)
    return verts, faces


def build_buildings(dem, cls, coast, exaggeration, coll):
    lots = T.building_lots(cls, coast, dem)
    tall = lots[:, 5] >= 25
    mats = {
        "저층": material("저층건물", (0.42, 0.38, 0.33), roughness=0.75, noise=0.35),
        "아파트": material("아파트", (0.52, 0.50, 0.47), roughness=0.6, noise=0.25),
    }
    for label, sel in (("저층", ~tall), ("아파트", tall)):
        if sel.any():
            verts, faces = box_mesh(lots[sel], exaggeration)
            mesh_object(f"건물_{label}", coll, verts, faces, [mats[label]])
    return len(lots)


# ---------------------------------------------------------------------------
# 랜드마크
# ---------------------------------------------------------------------------

def prism(n, radius, z0, z1):
    verts = [(radius * math.cos(2 * math.pi * i / n + math.pi / n),
              radius * math.sin(2 * math.pi * i / n + math.pi / n), z) for z in (z0, z1) for i in range(n)]
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    faces += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    return verts, faces


def merge(parts):
    verts, faces, mats = [], [], []
    for (v, f), m in parts:
        o = len(verts)
        verts += list(v)
        faces += [tuple(i + o for i in face) for face in f]
        mats += [m] * len(f)
    return verts, faces, mats


def build_lighthouse(dem, exaggeration, coll):
    """울기등대 (흰색 팔각 등탑, 높이 약 24 m)"""
    lat, lon = T.LANDMARKS["울기등대"]
    x, y = dem.to_local(lat, lon)
    z = dem.sample(lat, lon) * exaggeration
    white = material("등대_흰색", (0.85, 0.85, 0.82), roughness=0.5, noise=0)
    glass = material("등대_등실", (0.9, 0.85, 0.6), roughness=0.1, noise=0, emission=(1.0, 0.9, 0.6))
    dark = material("등대_지붕", (0.05, 0.05, 0.05), roughness=0.4, noise=0)
    v, f, m = merge([
        (prism(8, 3.2, -3, 1), 0),       # 기단
        (prism(8, 2.4, 1, 20), 0),       # 등탑
        (prism(8, 3.0, 20, 21), 0),      # 전망대
        (prism(8, 1.6, 21, 23.5), 1),    # 등실
        (cone(8, 1.9, 23.5, 25.5), 2),   # 지붕
    ])
    obj = mesh_object("울기등대", coll, v, f, [white, glass, dark])
    obj.data.polygons.foreach_set("material_index", m)
    obj.location = (x, y, z)
    return obj


def rock(name, coll, radius, height, seed, mat):
    """노이즈로 울퉁불퉁하게 만든 화강암 바위"""
    rng = np.random.default_rng(seed)
    rings, segs = 5, 12
    verts = []
    for i in range(rings):
        t = i / rings
        r = radius * math.sqrt(1 - t * t)
        for j in range(segs):
            a = 2 * math.pi * j / segs
            k = 1 + rng.uniform(-0.25, 0.25)
            verts.append((r * k * math.cos(a), r * k * math.sin(a), height * t * (1 + rng.uniform(-0.1, 0.1))))
    apex = len(verts)
    verts.append((rng.uniform(-0.2, 0.2) * radius, rng.uniform(-0.2, 0.2) * radius, height))
    faces = []
    for i in range(rings - 1):
        for j in range(segs):
            a, b = i * segs + j, i * segs + (j + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    top = (rings - 1) * segs
    faces += [(top + j, top + (j + 1) % segs, apex) for j in range(segs)]
    faces.append(tuple(reversed(range(segs))))
    obj = mesh_object(name, coll, verts, faces, [mat])
    obj.data.polygons.foreach_set("use_smooth", [False] * len(faces))
    return obj


def build_daewangam(dem, exaggeration, coll):
    """대왕암 바위섬과 대왕교 (형태는 단순화한 근사)"""
    granite = material("대왕암_화강암", (0.30, 0.20, 0.15), roughness=0.95, noise=0.4)
    lat, lon = T.LANDMARKS["대왕암"]
    cx, cy = dem.to_local(lat, lon)
    rocks = [(0, 0, 22, 14), (-18, 10, 14, 9), (16, -12, 12, 8), (-6, -20, 10, 6)]
    for i, (dx, dy, r, h) in enumerate(rocks):
        o = rock(f"대왕암_{i}", coll, r, h * exaggeration, seed=10 + i, mat=granite)
        o.location = (cx + dx, cy + dy, -2.0)

    lat2, lon2 = T.LANDMARKS["대왕교_육지쪽"]
    sx, sy = dem.to_local(lat2, lon2)
    length = math.hypot(cx - sx, cy - sy)
    angle = math.atan2(cy - sy, cx - sx)
    deck_z = 9.0 * exaggeration
    steel = material("대왕교", (0.20, 0.25, 0.30), roughness=0.4, metallic=0.6, noise=0)
    hw = 1.5
    zb, zt = deck_z - 0.6, deck_z
    deck = ([(0, -hw, zb), (length, -hw, zb), (length, hw, zb), (0, hw, zb),
             (0, -hw, zt), (length, -hw, zt), (length, hw, zt), (0, hw, zt)],
            [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    parts = [(deck, 0)]
    for t in (0.33, 0.66):  # 교각
        v, f = prism(6, 0.8, -3, zb)
        parts.append((([(px + length * t, py, pz) for px, py, pz in v], f), 0))
    v, f, _ = merge(parts)
    bridge = mesh_object("대왕교", coll, v, f, [steel])
    bridge.location = (sx, sy, 0)
    bridge.rotation_euler = (0, 0, angle)
    return bridge


def build_markers(dem, exaggeration, coll):
    """아웃라이너에서 위치를 찾기 쉽게 랜드마크마다 빈 오브젝트를 둔다"""
    for name, (lat, lon) in T.LANDMARKS.items():
        x, y = dem.to_local(lat, lon)
        empty = bpy.data.objects.new(f"표시_{name}", None)
        empty.empty_display_type = 'SINGLE_ARROW'
        empty.empty_display_size = 40
        empty.location = (x, y, max(dem.sample(lat, lon), 0) * exaggeration)
        coll.objects.link(empty)


# ---------------------------------------------------------------------------
# 카메라 / 조명 / 렌더
# ---------------------------------------------------------------------------

def look_at(obj, target):
    from mathutils import Vector
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def build_camera_light(dem, coll, scene):
    # 바다 위 북동쪽 상공에서 일산만과 대왕암공원을 내려다보는 시점
    cam_data = bpy.data.cameras.new("카메라")
    cam_data.lens = 30
    cam_data.clip_end = 100000
    cam = bpy.data.objects.new("카메라", cam_data)
    cam.location = (2300.0, 1500.0, 650.0)
    coll.objects.link(cam)
    lat, lon = T.LANDMARKS["울기등대"]
    tx, ty = dem.to_local(lat, lon)
    look_at(cam, (tx - 450, ty + 250, 0))
    scene.camera = cam

    # 대왕암 · 대왕교 · 울기등대 근경
    close_data = bpy.data.cameras.new("카메라_대왕암")
    close_data.lens = 35
    close_data.clip_end = 100000
    close = bpy.data.objects.new("카메라_대왕암", close_data)
    rx, ry = dem.to_local(*T.LANDMARKS["대왕암"])
    close.location = (rx + 320.0, ry - 260.0, 110.0)
    coll.objects.link(close)
    look_at(close, (rx - 180, ry + 90, 5))

    sun_data = bpy.data.lights.new("태양", 'SUN')
    sun_data.energy = 4.0
    sun_data.angle = math.radians(1.0)
    sun = bpy.data.objects.new("태양", sun_data)
    sun.rotation_euler = (math.radians(50), 0, math.radians(140))  # 남동쪽 오전 해
    coll.objects.link(sun)

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    enable_nodes(world)
    bg = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
    if bg is not None:
        bg.inputs["Color"].default_value = (0.45, 0.60, 0.85, 1.0)
        bg.inputs["Strength"].default_value = 0.8


def setup_render(scene, engine, samples):
    if engine == "cycles":
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.device = 'CPU'
    else:
        names = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
        scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in names else 'BLENDER_EEVEE'
        if hasattr(scene, "eevee"):
            scene.eevee.taa_render_samples = samples
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX' if 'AgX' in [
        i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else 'Filmic'
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'METERS'


def set_viewport_clip():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.clip_end = 100000


# ---------------------------------------------------------------------------

def build(upsample=3, exaggeration=1.0, buildings=True, trees=True, engine="eevee", samples=64):
    scene = bpy.context.scene
    clear_previous()
    root = collection(ROOT, scene.collection)

    dem = T.prepare(T.Dem.load(), upsample)
    cls, coast = T.classify(dem)

    build_terrain(dem, cls, coast, exaggeration, collection("지형", root))
    build_sea(dem, root)
    stats = {"격자": dem.shape}
    rng = np.random.default_rng(42)
    if trees:
        stats["나무"] = build_trees(dem, cls, exaggeration, collection("나무", root), rng)
    if buildings:
        stats["건물(가상)"] = build_buildings(dem, cls, coast, exaggeration, collection("건물 (가상 배치)", root))
    marks = collection("랜드마크", root)
    build_lighthouse(dem, exaggeration, marks)
    build_daewangam(dem, exaggeration, marks)
    build_markers(dem, exaggeration, marks)
    build_camera_light(dem, root, scene)
    setup_render(scene, engine, samples)
    set_viewport_clip()
    print("일산동 장면 생성 완료:", stats)
    return stats


def main():
    args = parse_args()
    build(args.upsample, args.exaggeration, not args.no_buildings, not args.no_trees,
          args.engine, args.samples)
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save))
    if args.render:
        bpy.context.scene.camera = bpy.data.objects[args.camera]
        bpy.context.scene.render.filepath = os.path.abspath(args.render)
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
