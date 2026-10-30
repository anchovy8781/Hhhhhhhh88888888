"""UV 펼치기 → Cycles 베이크 → CS2 텍스처 세트 → LOD → FBX 내보내기 → 미리보기 렌더."""

import math
import os
import sys

import bmesh
import bpy
import numpy as np

import pngio

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from cs2_asset_tools import core  # noqa: E402


# ---------------------------------------------------------------------------
# UV
# ---------------------------------------------------------------------------

# UV 우선순위: 재질 이름(에셋 이름 뒤 부분)이 이 접두어로 시작하면 UV 섬을 그만큼 키워 텍스처를 더 준다.
# 작은 간판 글자 · 얇은 창틀이 몇 픽셀에 뭉개지지 않게 한다.
UV_PRIORITY = {"letters": 4.0, "frame": 1.5, "grille": 1.5, "metal": 1.3, "sign": 1.3, "picto": 2.0}


def unwrap(obj, margin=0.003, priority=UV_PRIORITY):
    """각진 건물에 맞게 Smart UV Project → 우선순위 재질의 섬 확대 → 섬 정리"""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    if priority:
        bpy.ops.object.mode_set(mode='OBJECT')
        scale_islands(obj, priority)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def scale_islands(obj, priority):
    """우선순위 재질 면들의 UV 섬(같은 UV 를 공유하며 이어진 면 묶음)을 각자 중심에서 확대"""
    me = obj.data
    factor = {}
    for i, m in enumerate(me.materials):
        key = m.name.split("_", 1)[1] if "_" in m.name else m.name
        for prefix, k in priority.items():
            if key.startswith(prefix):
                factor[i] = k
                break
    if not factor:
        return 0
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    faces = [f for f in bm.faces if f.material_index in factor]
    parent = {f.index: f.index for f in faces}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def uv_at(face, vert):
        for loop in face.loops:
            if loop.vert is vert:
                return loop[uv].uv
        return None

    for f in faces:
        for e in f.edges:
            for g in e.link_faces:
                if g is f or g.index not in parent or g.material_index != f.material_index:
                    continue
                same = all((uv_at(f, v) - uv_at(g, v)).length < 1e-6 for v in e.verts)
                if same:
                    ra, rb = find(f.index), find(g.index)
                    if ra != rb:
                        parent[ra] = rb
    islands = {}
    for f in faces:
        islands.setdefault(find(f.index), []).append(f)
    for group in islands.values():
        k = factor[group[0].material_index]
        loops = [loop for f in group for loop in f.loops]
        cx = sum(loop[uv].uv.x for loop in loops) / len(loops)
        cy = sum(loop[uv].uv.y for loop in loops) / len(loops)
        for loop in loops:
            loop[uv].uv.x = cx + (loop[uv].uv.x - cx) * k
            loop[uv].uv.y = cy + (loop[uv].uv.y - cy) * k
    bm.to_mesh(me)
    bm.free()
    return len(islands)


# ---------------------------------------------------------------------------
# 베이크
# ---------------------------------------------------------------------------

def _setup_cycles(samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.bake.margin = 16
    sc.render.bake.margin_type = 'EXTEND'
    sc.render.bake.use_selected_to_active = False
    sc.render.bake.target = 'IMAGE_TEXTURES'


def _target(obj, img):
    """모든 재질에 대상 이미지 노드를 활성으로 둔다"""
    nodes = []
    for slot in obj.material_slots:
        nt = slot.material.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.nodes.active = node
        nodes.append((nt, node))
    return nodes


def _cleanup(nodes):
    for nt, node in nodes:
        nt.nodes.remove(node)


def _pixels(img):
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return buf.reshape(h, w, 4)[::-1].copy()  # 행 0 = 위쪽


def _new_image(name, size):
    img = bpy.data.images.new(name, size, size, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    return img


def bake_native(obj, kind, size, samples=1):
    _setup_cycles(samples)
    img = _new_image(f"bake_{kind}", size)
    nodes = _target(obj, img)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    kwargs = {"type": kind}
    if kind == 'NORMAL':
        kwargs.update(normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z')
    bpy.ops.object.bake(**kwargs)
    _cleanup(nodes)
    px = _pixels(img)
    bpy.data.images.remove(img)
    return px


def bake_socket(obj, size, socket=None, const=None):
    """재질의 특정 입력(socket) 값 또는 재질별 상수(const(mat)->RGB)를 발광으로 바꿔 EMIT 베이크"""
    _setup_cycles(1)
    img = _new_image("bake_socket", size)
    saved = []
    for slot in obj.material_slots:
        mat = slot.material
        nt = mat.node_tree
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 1.0
        if const is not None:
            em.inputs["Color"].default_value = (*const(mat), 1.0)
        else:
            inp = bsdf.inputs[socket]
            if inp.is_linked:
                nt.links.new(inp.links[0].from_socket, em.inputs["Color"])
            else:
                v = inp.default_value
                em.inputs["Color"].default_value = tuple(v) if hasattr(v, "__len__") else (v, v, v, 1.0)
        old = out.inputs["Surface"].links[0].from_socket
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        saved.append((nt, out, old, em))
    nodes = _target(obj, img)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type='EMIT')
    _cleanup(nodes)
    for nt, out, old, em in saved:
        nt.links.new(old, out.inputs["Surface"])
        nt.nodes.remove(em)
    px = _pixels(img)
    bpy.data.images.remove(img)
    return px


def bake_texture_set(obj, name, out_dir, size=2048, ao_samples=32, ao_strength=0.45):
    """CS2 텍스처 5종을 out_dir 에 저장하고 경로 dict 를 돌려준다"""
    os.makedirs(out_dir, exist_ok=True)
    # AO 를 위해 바닥면 임시 추가
    ground = bpy.data.objects.new("tmp_ground", bpy.data.meshes.new("tmp_ground"))
    ground.data.from_pydata([(-200, -200, -0.01), (200, -200, -0.01), (200, 200, -0.01), (-200, 200, -0.01)],
                            [], [(0, 1, 2, 3)])
    bpy.context.scene.collection.objects.link(ground)

    color = bake_socket(obj, size, socket="Base Color")[..., :3]
    rough = bake_socket(obj, size, socket="Roughness")[..., 0]
    metal = bake_socket(obj, size, socket="Metallic")[..., 0]
    control = bake_socket(obj, size, const=lambda m: tuple(m.get("control", (0, 0, 0))))[..., :3]
    emit = bake_native(obj, 'EMIT', size)[..., :3]
    normal = bake_native(obj, 'NORMAL', size)[..., :3]
    ao = bake_native(obj, 'AO', size, ao_samples)[..., 0]
    bpy.data.objects.remove(ground)

    color = color * (1.0 - ao_strength * (1.0 - ao))[..., None]
    paths = {}

    def save(suffix, arr):
        p = os.path.join(out_dir, core.texture_name(name, suffix))
        pngio.write_rgb8(p, arr)
        paths[suffix] = p

    save("_BaseColor", pngio.to_u8(pngio.linear_to_srgb(color)))
    save("_Normal", pngio.to_u8(normal))
    mask = core.pack_maskmap((size, size), metallic=metal, roughness=rough)  # R 금속, G 코트, A 광택
    save("_MaskMap", pngio.to_u8(mask))
    save("_ControlMask", pngio.to_u8(control))
    save("_Emissive", pngio.to_u8(pngio.linear_to_srgb(emit / max(1.0, float(emit.max())))))
    return paths


# ---------------------------------------------------------------------------
# 베이크 결과 재질 · LOD · 내보내기
# ---------------------------------------------------------------------------

def baked_material(name, paths):
    """베이크한 텍스처로 만든 단일 재질 (FBX 와 미리보기용)"""
    mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')

    def tex(suffix, non_color=True):
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(paths[suffix], check_existing=True)
        if non_color:
            node.image.colorspace_settings.name = 'Non-Color'
        return node

    nt.links.new(tex("_BaseColor", False).outputs["Color"], bsdf.inputs["Base Color"])
    mask = tex("_MaskMap")
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(mask.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[0], bsdf.inputs["Metallic"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    nt.links.new(mask.outputs["Alpha"], inv.inputs[1])
    nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex("_Normal").outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    em = tex("_Emissive", False)
    for key in ("Emission Color", "Emission"):
        if key in bsdf.inputs:
            nt.links.new(em.outputs["Color"], bsdf.inputs[key])
            break
    bsdf.inputs["Emission Strength"].default_value = 0.0
    mat["emission_node"] = True
    return mat


def set_night(mat, strength):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Emission Strength"].default_value = strength


def replace_materials(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.data.polygons.foreach_set("material_index", [0] * len(obj.data.polygons))


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# LOD 마다 지우는 디테일 (재질 이름 접두어). 작은 닫힌 조각(실외기 등)을 Collapse 로 줄이면 찌그러지므로
# 디테일은 통째로 지우고, 남은 면은 같은 평면끼리만 합친다.
LOD1_DROP = ("letters_glass", "blind", "grille", "rubber", "lamp", "crab_eye", "parking_line", "mailbox", "basin",
             "styrofoam", "plastic", "gas_pipe", "led_strip", "speaker")
LOD2_DROP = LOD1_DROP + ("letters", "frame", "metal", "ac", "stainless", "vinyl", "glass_tank", "water", "picto",
                         "parasol", "curtain", "glass_rail", "flower")


def tag_source_materials(obj):
    """베이크 재질로 바꾸기 전에 면마다 원래 재질 번호를 'src_mat' 속성으로 남긴다 (LOD 디테일 제거용)"""
    me = obj.data
    attr = me.attributes.new("src_mat", 'INT', 'FACE')
    attr.data.foreach_set("value", [p.material_index for p in me.polygons])
    return [m.name.split("_", 1)[1] if "_" in m.name else m.name for m in me.materials]


def _decimated_part(src_obj, keep, ratio):
    """src_obj 메시에서 keep(bmesh 면 -> bool) 면만 남긴 사본을 Collapse 로 줄인 메시"""
    tmp = src_obj.copy()
    tmp.data = src_obj.data.copy()
    bpy.context.scene.collection.objects.link(tmp)
    bm = bmesh.new()
    bm.from_mesh(tmp.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f, bm)], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(tmp.data)
    bm.free()
    mod = tmp.modifiers.new("dec", 'DECIMATE')
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    data = tmp.data
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(data)
    return me


def make_lod(obj, name, ratio=1.0, drop=(), src_names=None, letters_ratio=None):
    """LOD: drop 에 해당하는 재질의 면 삭제 → 같은 평면 합치기 → (letters_ratio) 글자만 Collapse 로 줄이기
    → (ratio < 1 이면) 전체 Decimate(Collapse). UV 를 유지하므로 같은 텍스처를 쓴다."""
    lod = obj.copy()
    lod.data = obj.data.copy()
    lod.name = name
    lod.data.name = name
    bpy.context.scene.collection.objects.link(lod)
    bm = bmesh.new()
    bm.from_mesh(lod.data)
    if drop and src_names:
        layer = bm.faces.layers.int.get("src_mat")
        doomed = [f for f in bm.faces if src_names[f[layer]].startswith(tuple(drop))]
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts, edges=bm.edges,
                             delimit={'UV', 'MATERIAL'})
    bm.to_mesh(lod.data)
    bm.free()
    if letters_ratio and src_names:
        def is_letter(f, bm_):
            return src_names[f[bm_.faces.layers.int.get("src_mat")]].startswith("letters")
        letters = _decimated_part(lod, is_letter, letters_ratio)
        bm = bmesh.new()
        bm.from_mesh(lod.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if is_letter(f, bm)], context='FACES')
        bm.from_mesh(letters)                                 # 줄인 글자를 다시 합친다
        bm.to_mesh(lod.data)
        bm.free()
        bpy.data.meshes.remove(letters)
    me = lod.data
    if ratio < 1.0:
        mod = lod.modifiers.new("lod", 'DECIMATE')
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(lod.evaluated_get(dg))
        old = lod.data
        lod.modifiers.clear()
        lod.data = me
        bpy.data.meshes.remove(old)
    me.name = name
    bm = bmesh.new()                       # 평면 정리로 생긴 다각형이 남아 있으면 삼각형으로 (FBX 탄젠트)
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(me)
    bm.free()
    return lod


def export_fbx(obj, path):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z', axis_up='Y', bake_space_transform=True,
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True,
        add_leaf_bones=False, bake_anim=False, path_mode='STRIP', embed_textures=False,
    )


# ---------------------------------------------------------------------------
# 미리보기
# ---------------------------------------------------------------------------

def preview(obj, lot_w, lot_d, path, night=False, samples=48, res=(1280, 960)):
    sc = bpy.context.scene
    coll = bpy.data.collections.new("preview")
    sc.collection.children.link(coll)
    # 부지 경계가 보이는 바닥 + 앞 도로
    gm = bpy.data.materials.new("pv_ground")
    if bpy.app.version < (5, 0, 0):
        gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs["Base Color"].default_value = \
        (0.30, 0.30, 0.29, 1)
    rm = bpy.data.materials.new("pv_road")
    if bpy.app.version < (5, 0, 0):
        rm.use_nodes = True
    next(n for n in rm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs["Base Color"].default_value = \
        (0.05, 0.05, 0.055, 1)
    for nm, mat, (x0, x1, y0, y1, z) in (("pv_ground", gm, (-80, 80, -lot_d / 2, 80, -0.02)),
                                          ("pv_road", rm, (-80, 80, -lot_d / 2 - 12, -lot_d / 2, -0.03))):
        me = bpy.data.meshes.new(nm)
        me.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [], [(0, 1, 2, 3)])
        me.materials.append(mat)
        o = bpy.data.objects.new(nm, me)
        coll.objects.link(o)

    cam_d = bpy.data.cameras.new("pv_cam")
    cam_d.lens = 35
    cam = bpy.data.objects.new("pv_cam", cam_d)
    coll.objects.link(cam)
    dims = obj.dimensions
    dist = max(dims.x, dims.z * 1.3, 14) * 1.55
    cam.location = (dist * 0.55, -lot_d / 2 - dist * 0.95, dims.z * 0.45 + 2.0)
    from mathutils import Vector
    target = Vector((0, -lot_d / 4, dims.z * 0.42))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam

    sun_d = bpy.data.lights.new("pv_sun", 'SUN')
    sun = bpy.data.objects.new("pv_sun", sun_d)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    coll.objects.link(sun)
    world = sc.world or bpy.data.worlds.new("World")
    sc.world = world
    if bpy.app.version < (5, 0, 0):
        world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    if night:
        sun_d.energy = 0.02
        bg.inputs["Color"].default_value = (0.01, 0.015, 0.04, 1)
        bg.inputs["Strength"].default_value = 0.5
    else:
        sun_d.energy = 4.0
        bg.inputs["Color"].default_value = (0.55, 0.68, 0.90, 1)
        bg.inputs["Strength"].default_value = 0.9

    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = 'AgX'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in list(coll.objects):
        bpy.data.objects.remove(o)
    bpy.data.collections.remove(coll)
