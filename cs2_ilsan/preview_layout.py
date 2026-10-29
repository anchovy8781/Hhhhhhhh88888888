"""배치 검증용 미리보기: 하이트맵 지형 + 도로 + 배치표대로 놓은 CS2 에셋(FBX)을 블렌더에 재현한다.

    blender -b --python preview_layout.py -- --render layout.png [--night]

게임과 같은 좌표(맵 중심 원점, x 동쪽, z 북쪽 → 블렌더 x, y)와 높이(해수면 40 m → 블렌더 0 m)를 쓴다.
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


def terrain(maps, info, half=700.0):
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
    sea.from_pydata([(-5000, -5000, 0), (5000, -5000, 0), (5000, 5000, 0), (-5000, 5000, 0)], [], [(0, 1, 2, 3)])
    sea.materials.append(mat("water", (0.02, 0.10, 0.15), 0.05))
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("sea", sea))
    return sub, xs, ys


def road(info, width=12.0):
    pts = info["street_centerline_game_xz"]
    P = np.array([[p["x"], p["z"]] for p in pts])
    Z = np.array([p["ground_m"] - info["sea_level_m"] for p in pts]) + 0.15
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    L = P + n * width / 2
    R = P - n * width / 2
    k = len(P)
    verts = [(x, y, z) for (x, y), z in zip(L, Z)] + [(x, y, z) for (x, y), z in zip(R, Z)]
    faces = [(i, i + 1, k + i + 1, k + i) for i in range(k - 1)]
    me = bpy.data.meshes.new("road")
    me.from_pydata(verts, [], faces)
    me.materials.append(mat("asphalt", (0.05, 0.05, 0.055), 0.85))
    bpy.context.scene.collection.objects.link(bpy.data.objects.new("road", me))
    return P, n


def place(items, assets, night):
    cache = {}
    for i, it in enumerate(items):
        name = it["asset"]
        if name not in cache:
            folder = os.path.join(assets, name)
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
        o.location = (it["game_x"], it["game_z"], it["ground_m"] - 40.0)
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


def light(night):
    sc = bpy.context.scene
    sd = bpy.data.lights.new("sun", 'SUN')
    s = bpy.data.objects.new("sun", sd)
    s.rotation_euler = (math.radians(50), 0, math.radians(135))
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
    terrain(a.maps, info)
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


if __name__ == "__main__":
    main()
