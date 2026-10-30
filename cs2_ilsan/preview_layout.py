"""배치 검증용 미리보기: 하이트맵 지형 + 도로 + 배치표대로 놓은 CS2 에셋(FBX)을 블렌더에 재현한다.

    blender -b --python preview_layout.py -- --render layout.png [--night] [--camera aerial|street]
    blender -b --python preview_layout.py -- --photos docs/      # 사진 6장 구도 real_01~06.jpg + 브랜드 매장 brand_01~09.jpg

게임과 같은 좌표(맵 중심 원점, x 동쪽, z 북쪽 → 블렌더 x, y)와 높이(해수면 40 m → 블렌더 0 m)를 쓴다.
도로(노란 중앙선) · 회전교차로 고리 · 하천 물길의 물도 함께 놓는다.
"""

import argparse
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

PLAY = 14336.0
RES = 4096


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--maps", default=os.path.join(HERE, "Heightmaps"))
    p.add_argument("--assets", default=os.path.join(HERE, "CS2Assets"))
    p.add_argument("--render")
    p.add_argument("--night", action="store_true")
    p.add_argument("--camera", default="aerial", choices=("aerial", "street"))
    p.add_argument("--photos", help="사진 구도 6장(real_0N.jpg) + 실제 매장 9장(brand_0N.jpg)을 이 폴더에 렌더")
    p.add_argument("--only", help="--photos 중 일부 이름만 (예: real_01,brand_02)")
    p.add_argument("--samples", type=int, default=48)
    p.add_argument("--save")
    return p.parse_args(argv)


def mat(name, color, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def terrain(maps, info, half=1200.0):
    """하이트맵에서 거리 주변 (2*half m) 정사각형을 메시로"""
    img = bpy.data.images.load(os.path.join(maps, "Ilsan_Heightmap.png"))
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    hm = px.reshape(h, w, 4)[::-1, :, 0] * info["height_scale_m"] - info["sea_level_m"]  # 행 0 = 북
    mpp = PLAY / RES
    c = int(round(half / mpp))
    r0, c0 = RES // 2 - c, RES // 2 - c
    sub = hm[r0:r0 + 2 * c + 1, c0:c0 + 2 * c + 1]
    rows, cols = sub.shape
    xs = (np.arange(cols) + c0 + 0.5 - RES / 2) * mpp
    ys = (RES / 2 - (np.arange(rows) + r0 + 0.5)) * mpp
    X, Y = np.meshgrid(xs, ys)
    verts = np.stack([X.ravel(), Y.ravel(), sub.ravel()], 1)
    idx = np.arange(rows * cols).reshape(rows, cols)
    faces = np.stack([idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()], 1)
    me = bpy.data.meshes.new("terrain")
    me.from_pydata(verts.tolist(), [], faces.tolist())
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    me.materials.append(mat("ground", (0.20, 0.22, 0.12), 0.9))
    me.materials.append(mat("sand", (0.62, 0.52, 0.36), 0.8))
    # 해발 0~2.5 m 는 모래사장
    zc = verts[faces].mean(1)[:, 2]
    me.polygons.foreach_set("material_index", (zc < 2.5).astype(np.int32))
    o = bpy.data.objects.new("terrain", me)
    bpy.context.scene.collection.objects.link(o)
    sea = bpy.data.meshes.new("sea")
    sea.from_pydata([(-6000, -6000, 0), (6000, -6000, 0), (6000, 6000, 0), (-6000, 6000, 0)], [], [(0, 1, 2, 3)])
    sea.materials.append(mat("water", (0.02, 0.10, 0.15), 0.05))
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("sea", sea))

    def height(x, y):
        """지형 높이 (쌍선형)"""
        c = (x - xs[0]) / mpp
        r = (ys[0] - y) / mpp
        r0, c0 = int(np.clip(np.floor(r), 0, rows - 2)), int(np.clip(np.floor(c), 0, cols - 2))
        fr, fc = r - r0, c - c0
        return float(sub[r0, c0] * (1 - fr) * (1 - fc) + sub[r0, c0 + 1] * (1 - fr) * fc
                     + sub[r0 + 1, c0] * fr * (1 - fc) + sub[r0 + 1, c0 + 1] * fr * fc)
    return height


def mesh(name, verts, faces, material):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.materials.append(material)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def main_road(info):
    """방어진순환도로 (광장 끝을 가로지르는 4차로) + 노란 중앙선"""
    road = info.get("main_road")
    if not road:
        return
    pts = road["centerline_game_xz"]
    P = np.array([[p["x"], p["z"]] for p in pts])
    Z = np.array([p["ground_m"] - info["sea_level_m"] for p in pts]) + ROAD_LIFT
    d = P[-1] - P[0]
    d /= np.linalg.norm(d)
    n = np.array([d[1], -d[0]])
    k = len(P)
    for name, a, b, dz, col in (("main_road", road["width_m"] / 2 - 2.0, -road["width_m"] / 2 + 2.0, 0.0,
                                 (0.05, 0.05, 0.055)),
                                ("main_center_l", 0.25, 0.1, 0.02, (0.85, 0.62, 0.04)),
                                ("main_center_r", -0.1, -0.25, 0.02, (0.85, 0.62, 0.04)),
                                ("main_walk_l", road["width_m"] / 2, road["width_m"] / 2 - 2.0, 0.12,
                                 (0.42, 0.40, 0.38)),
                                ("main_walk_r", -road["width_m"] / 2 + 2.0, -road["width_m"] / 2, 0.12,
                                 (0.42, 0.40, 0.38))):
        verts = [(x, y, z + dz) for (x, y), z in zip(P + n * a, Z)] + [(x, y, z + dz) for (x, y), z in zip(P + n * b, Z)]
        faces = [(i, i + 1, k + i + 1, k + i) for i in range(k - 1)]
        mesh(name, verts, faces, mat(name, col, 0.85))


def stream(info, height, width=7.0, n=80):
    """하천 물길의 물 (파인 물길 바닥보다 0.7 m 위, 하구는 해수면)"""
    (x0, y0), (x1, y1) = info["stream_xz"]
    d = np.array([x1 - x0, y1 - y0])
    d /= np.linalg.norm(d)
    side = np.array([d[1], -d[0]]) * width / 2
    verts = []
    for t in np.linspace(0, 1, n):
        p = np.array([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t])
        z = max(height(*p) + 0.7, 0.02)
        verts += [(*(p - side), z), (*(p + side), z)]
    faces = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(n - 1)]
    mesh("stream", verts, faces, mat("stream_water", (0.03, 0.12, 0.13), 0.04))


ROAD_LIFT = 0.3


def road(info, width=12.0):
    """도로 + 노란 중앙선 2줄 (회전교차로 안은 끊음) + 회전교차로 고리"""
    pts = info["street_centerline_game_xz"]
    P = np.array([[p["x"], p["z"]] for p in pts])
    Z = np.array([p["ground_m"] - info["sea_level_m"] for p in pts]) + ROAD_LIFT
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    k = len(P)

    def strip(name, a, b, dz, material, keep=None):
        verts = [(x, y, z + dz) for (x, y), z in zip(P + n * a, Z)] + [(x, y, z + dz) for (x, y), z in zip(P + n * b, Z)]
        faces = [(i, i + 1, k + i + 1, k + i) for i in range(k - 1) if keep is None or (keep[i] and keep[i + 1])]
        mesh(name, verts, faces, material)

    strip("road", width / 2, -width / 2, 0.0, mat("asphalt", (0.05, 0.05, 0.055), 0.85))
    rb = np.array(info["roundabout_xz"])
    keep = np.linalg.norm(P - rb, axis=1) > 17.0
    yellow = mat("center_line", (0.85, 0.62, 0.04), 0.6)
    strip("center_l", 0.25, 0.1, 0.02, yellow, keep)
    strip("center_r", -0.1, -0.25, 0.02, yellow, keep)
    zc = float(Z[np.argmin(np.linalg.norm(P - rb, axis=1))]) + 0.01
    ring = 48
    verts = [(rb[0] + r * math.cos(2 * math.pi * i / ring), rb[1] + r * math.sin(2 * math.pi * i / ring), zc)
             for r in (7.6, 16.0) for i in range(ring)]
    faces = [(i, (i + 1) % ring, ring + (i + 1) % ring, ring + i) for i in range(ring)]
    mesh("roundabout_ring", verts, faces, mat("asphalt_ring", (0.05, 0.05, 0.055), 0.85))
    return P, n


ON_ROAD = ("IlsanRoundabout", "IlsanRoadMarking01")      # 도로 면 위에 놓는 것


def place(items, assets, night):
    cache = {}
    for i, it in enumerate(items):
        name = it["asset"]
        if name not in cache:
            folder = os.path.join(assets, name)
            if not os.path.exists(os.path.join(folder, name + ".fbx")):
                print("FBX 없음, 건너뜀:", name)
                cache[name] = None
        if cache.get(name, 0) is None:
            continue
        if name not in cache:
            before = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=os.path.join(folder, name + ".fbx"))
            obj = next(o for o in bpy.data.objects if o not in before)
            obj.matrix_world = obj.matrix_world  # 가져온 변환 유지
            bpy.context.view_layer.update()
            # 블렌더에서 만든 원래 방향(Z 위)으로 되돌린 메시
            obj.data.transform(obj.matrix_basis)
            obj.matrix_basis.identity()
            paths = {s: os.path.join(folder, f"{name}{s}.png")
                     for s in ("_BaseColor", "_Normal", "_MaskMap", "_ControlMask", "_Emissive")}
            m = bake.baked_material(name + "_pv", paths)
            if night:
                bake.set_night(m, 6.0)
            bake.replace_materials(obj, m)
            obj.hide_render = True
            obj.hide_set(True)
            cache[name] = obj
        src = cache[name]
        o = bpy.data.objects.new(f"{i:02d}_{name}", src.data)
        lift = ROAD_LIFT + 0.015 if name in ON_ROAD else 0.0
        o.location = (it["game_x"], it["game_z"], it["ground_m"] - 40.0 + lift)
        o.rotation_euler = (0, 0, math.pi - math.radians(it["rotation_deg"]))
        bpy.context.scene.collection.objects.link(o)


def camera(kind, P, n):
    from mathutils import Vector
    cd = bpy.data.cameras.new("cam")
    cd.clip_end = 20000
    cam = bpy.data.objects.new("cam", cd)
    bpy.context.scene.collection.objects.link(cam)
    mid = len(P) // 2
    if kind == "aerial":
        cd.lens = 32
        pos = P[mid] - n[mid] * 260
        cam.location = (pos[0], pos[1], 140)
        target = Vector((P[mid][0] + n[mid][0] * 40, P[mid][1] + n[mid][1] * 40, 8))
    else:
        cd.lens = 22
        i = int(len(P) * 0.35)
        pos = P[i] + n[i] * 6.5
        nxt = P[i + 4] + n[i + 4] * 10
        cam.location = (pos[0], pos[1], 6.0)
        target = Vector((nxt[0], nxt[1], 7.0))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam


def look(cam, pos, target, lens):
    from mathutils import Vector
    cam.data.lens = lens
    cam.location = Vector(pos)
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()


def photo_cameras(info, items, P, n, height):
    """사진 6장과 같은 구도: (파일 이름, 카메라 위치, 바라보는 점, 렌즈 mm)"""
    a0, a1 = (np.array(info["plaza"][k]) for k in ("axis_start_xz", "axis_end_xz"))
    ax = (a1 - a0) / np.linalg.norm(a1 - a0)               # 광장 축 (육지 쪽)
    tp = np.array([ax[1], -ax[0]])                          # 광장 가로 (+ = 북쪽, 일산스퀘어 쪽)
    R = np.array(info["roundabout_xz"])
    ir = int(np.argmin(np.linalg.norm(P - R, axis=1)))
    zr = info["street_centerline_game_xz"][ir]["ground_m"] - info["sea_level_m"] + ROAD_LIFT

    def at(name):
        it = next(i for i in items if i["asset"] == name)
        return np.array([it["game_x"], it["game_z"]]), it["ground_m"] - info["sea_level_m"], it["rotation_deg"]

    def p3(xy, z):
        return (float(xy[0]), float(xy[1]), float(z))

    tower, tz, _ = at("IlsanCornerTower01")
    hotel, hz, hrot = at("IlsanTanibayHotel")
    front = np.array([math.sin(math.radians(hrot)), math.cos(math.radians(hrot))])
    beach = hotel + front * 84
    i2, i2t = ir + 19, ir + 7
    lane = lambda i: P[i] - n[i] * 2.4                       # noqa: E731  바다 쪽 차로 (북쪽으로 달림)
    z2 = info["street_centerline_game_xz"][i2]["ground_m"] - info["sea_level_m"] + ROAD_LIFT
    def facing(name, dist, side=0.0, h=4.0, look_up=4.0, lens=24):
        """실제 브랜드 매장 정면에서 dist m 떨어진 곳 (side = 정면 기준 오른쪽으로 비킴)"""
        c, gz, rot = at(name)
        fr = np.array([math.sin(math.radians(rot)), math.cos(math.radians(rot))])
        rt = np.array([fr[1], -fr[0]])
        pos = c + fr * dist + rt * side
        return p3(pos, max(height(*pos), gz) + h), p3(c, gz + look_up), lens

    brands = [("brand_01",) + facing("IlsanTerracePark01", 26.0, -14.0, 1.7, 5.5, 22),
              ("brand_02",) + facing("IlsanStarbucksDT", 30.0, 12.0, 3.0, 3.5, 24),
              ("brand_03",) + facing("IlsanHomeplus", 70.0, -18.0, 9.0, 8.0, 26),
              ("brand_04",) + facing("IlsanGS25", 15.0, -6.0, 1.7, 2.5, 22),
              ("brand_05",) + facing("IlsanGasStation", 36.0, 12.0, 4.5, 3.0, 22),
              ("brand_06",) + facing("IlsanBaskin", 20.0, -13.0, 1.7, 3.5, 22),
              ("brand_07",) + facing("IlsanOliveDaiso", 30.0, 9.0, 1.7, 7.5, 22),
              ("brand_08",) + facing("IlsanSikdang153", 19.0, -7.0, 1.7, 4.0, 22),
              ("brand_09",) + facing("IlsanMGBank", 24.0, 7.0, 1.7, 5.0, 22)]
    return brands + [
        ("real_01", p3(R - ax * 15 - tp * 21, zr + 4.5), p3(tower, tz + 12), 20),
        ("real_02", p3(lane(i2), z2 + 1.5), p3(lane(i2t), z2 + 2.6), 24),
        ("real_03", p3(R - ax * 480 + tp * 120, 230), p3(R + ax * 40, 0), 30),
        ("real_04", p3(beach, max(height(*beach), 0.0) + 1.7), p3(hotel, hz + 30), 26),
        ("real_05", p3(R - ax * 150 - tp * 70, 95), p3(R + ax * 35 - tp * 15, 0), 28),
        ("real_06", p3(R + ax * 175 + tp * 5, zr + 42), p3(R + ax * 45, zr), 30),
    ]


def light(night):
    sc = bpy.context.scene
    sd = bpy.data.lights.new("sun", 'SUN')
    s = bpy.data.objects.new("sun", sd)
    s.rotation_euler = (math.radians(50), 0, math.radians(72))      # 동남동 아침 해 (바다 쪽에서)
    sc.collection.objects.link(s)
    w = sc.world or bpy.data.worlds.new("World")
    sc.world = w
    if bpy.app.version < (5, 0, 0):
        w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    if night:
        sd.energy = 0.03
        bg.inputs["Color"].default_value = (0.01, 0.015, 0.04, 1)
        bg.inputs["Strength"].default_value = 0.5
    else:
        sd.energy = 4.0
        bg.inputs["Color"].default_value = (0.55, 0.68, 0.9, 1)
        bg.inputs["Strength"].default_value = 0.9


def main():
    a = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with open(os.path.join(a.maps, "Ilsan_Map.json"), encoding="utf-8") as f:
        info = json.load(f)
    with open(os.path.join(a.maps, "Ilsan_Placement.json"), encoding="utf-8") as f:
        items = json.load(f)
    height = terrain(a.maps, info)
    stream(info, height)
    main_road(info)
    P, n = road(info)
    place(items, a.assets, a.night)
    camera(a.camera, P, n)
    light(a.night)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.view_settings.view_transform = 'AgX'
    if a.save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save))
    if a.render:
        sc.render.filepath = os.path.abspath(a.render)
        bpy.ops.render.render(write_still=True)
    if a.photos:
        os.makedirs(a.photos, exist_ok=True)
        sc.render.resolution_x, sc.render.resolution_y = 1600, 900
        sc.render.image_settings.file_format = 'JPEG'
        sc.render.image_settings.quality = 88
        only = set(a.only.split(",")) if a.only else None
        for name, pos, target, lens in photo_cameras(info, items, P, n, height):
            if only and name not in only:
                continue
            look(sc.camera, pos, target, lens)
            sc.render.filepath = os.path.join(os.path.abspath(a.photos), name + ".jpg")
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
