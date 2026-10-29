"""블렌더 연결부: geom.Mesh -> 블렌더 메시, 입체 글자 메시, 절차적 재질.

면 방향은 geom 이 이미 바깥으로 맞춰 두므로 여기서는 법선을 다시 계산하지 않는다.
"""

import bmesh
import bpy
import numpy as np


def to_object(mesh, name, specs, collection=None):
    """geom.Mesh -> 블렌더 오브젝트. specs: {재질 이름: spec dict}"""
    me = bpy.data.meshes.new(name)
    me.from_pydata(mesh.verts, [], mesh.faces)
    me.validate()
    if len(me.polygons) != len(mesh.faces):
        raise RuntimeError(f"{name}: 메시 검증에서 면 {len(mesh.faces) - len(me.polygons)}개가 제거되었습니다")
    for n in mesh.mat_names:
        me.materials.append(make_material(f"{name}_{n}", specs[n]))
    me.polygons.foreach_set("material_index", mesh.mats)
    me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)   # 면 방향은 바뀌지 않는다
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# 글자
# ---------------------------------------------------------------------------

def text_mesh(text, font, size, extrude=0.04):
    """글자를 메시로. 반환 (verts 중심 기준, faces, 폭, 높이, 두께). 폰트가 없으면 None"""
    if font is None or not text:
        return None
    cu = bpy.data.curves.new("tmp_text", 'FONT')
    cu.body = text
    cu.font = font
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.resolution_u = 4      # 글자 곡선 분할 (기본 12 는 폴리곤이 과함)
    ob = bpy.data.objects.new("tmp_text", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    co = np.array([v.co[:] for v in me.vertices], dtype=np.float64)
    faces = [tuple(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    if len(co) == 0:
        return None
    lo, hi = co.min(0), co.max(0)
    co -= (lo + hi) / 2
    return [tuple(v) for v in co], faces, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]


def text_fn_for(font):
    """designs.Building 에 넘길 글자 함수: (문구, 최대 폭, 최대 높이, 두께) -> 글자 메시"""
    cache = {}

    def fit(text, max_w, max_h, extrude=0.05):
        key = (text, round(max_w, 3), round(max_h, 3), round(extrude, 3))
        if key not in cache:
            t = text_mesh(text, font, 1.0, extrude)
            if t is None:
                cache[key] = None
            else:
                s = min(max_w / max(t[2], 1e-6), max_h / max(t[3], 1e-6))
                cache[key] = text_mesh(text, font, s, extrude)
        return cache[key]
    return fit


# ---------------------------------------------------------------------------
# 절차적 재질 (베이크용) — spec 형식은 materials.py 참고
# ---------------------------------------------------------------------------

def _principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def _inp(node, names, value):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return node.inputs[n]


def _facade_uv(nt):
    """벽(X/Y 축 정렬)에 패턴을 세우기 위한 벡터: (x+y, z, 0)"""
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs[0])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = 'ADD'
    nt.links.new(sep.outputs[0], add.inputs[0])
    nt.links.new(sep.outputs[1], add.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(add.outputs[0], comb.inputs[0])
    nt.links.new(sep.outputs[2], comb.inputs[1])
    return comb.outputs[0], coord


def _bands(nt, vector, direction, width, c1, c2, sharp=True):
    """일정 간격 줄무늬 (사이딩 · 차양 · 금속 지붕 이음매)"""
    tex = nt.nodes.new("ShaderNodeTexWave")
    nt.links.new(vector, tex.inputs["Vector"])
    tex.wave_type = 'BANDS'
    tex.bands_direction = direction
    tex.wave_profile = 'SAW'
    _inp(tex, ["Scale"], 1.0 / width / 2)
    _inp(tex, ["Distortion"], 0.0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    if sharp:
        ramp.color_ramp.interpolation = 'CONSTANT'
    ramp.color_ramp.elements[0].color = c1
    ramp.color_ramp.elements[1].position = 0.88 if not sharp else 0.5
    ramp.color_ramp.elements[1].color = c2
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    return ramp.outputs["Color"], tex.outputs["Fac"]


def make_material(name, spec):
    mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = _principled(mat)
    c1 = (*spec.get("color", (0.8, 0.8, 0.8)), 1.0)
    c2 = (*spec.get("color2", tuple(x * 0.85 for x in c1[:3])), 1.0)
    _inp(bsdf, ["Roughness"], spec.get("rough", 0.7))
    _inp(bsdf, ["Metallic"], spec.get("metal", 0.0))
    if "emit" in spec:
        _inp(bsdf, ["Emission Color", "Emission"], (*spec["emit"], 1.0))
        _inp(bsdf, ["Emission Strength"], spec.get("emit_strength", 1.0))
    mat["control"] = list(spec.get("control", (0.0, 0.0, 0.0)))
    mat["metal"] = spec.get("metal", 0.0)

    pattern = spec.get("pattern")
    vec, coord = _facade_uv(nt)
    color_out = height_out = None
    if pattern == "noise":
        tex = nt.nodes.new("ShaderNodeTexNoise")
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        _inp(tex, ["Scale"], spec.get("scale", 1.5))
        _inp(tex, ["Detail"], 8.0)
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.35
        ramp.color_ramp.elements[1].position = 0.65
        ramp.color_ramp.elements[0].color = c2
        ramp.color_ramp.elements[1].color = c1
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        color_out, height_out = ramp.outputs["Color"], tex.outputs["Fac"]
    elif pattern in ("tile", "panel", "paver"):
        w, h = spec.get("scale", (0.45, 0.15))
        tex = nt.nodes.new("ShaderNodeTexBrick")
        nt.links.new(coord.outputs["Object"] if pattern == "paver" else vec, tex.inputs["Vector"])
        tex.offset = 0.0 if pattern == "panel" else 0.5
        _inp(tex, ["Scale"], 1.0)
        _inp(tex, ["Brick Width"], w)
        _inp(tex, ["Row Height"], h)
        _inp(tex, ["Mortar Size"], spec.get("mortar", 0.008))
        _inp(tex, ["Bias"], 0.0)
        _inp(tex, ["Color1"], c1)
        _inp(tex, ["Color2"], c2)
        _inp(tex, ["Mortar"], (*spec.get("mortar_color", tuple(x * 0.6 for x in c1[:3])), 1.0))
        noise = nt.nodes.new("ShaderNodeTexNoise")
        nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
        _inp(noise, ["Scale"], 3.0)
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = 'MULTIPLY'
        _inp(mix, ["Fac"], 0.25)
        nt.links.new(tex.outputs["Color"], mix.inputs[1])
        nt.links.new(noise.outputs["Color"], mix.inputs[2])
        color_out, height_out = mix.outputs[0], tex.outputs["Fac"]
    elif pattern == "stripes":          # 세로 줄무늬 (차양 · 천막)
        color_out, _ = _bands(nt, vec, 'X', spec.get("scale", 0.5), c1, c2)
    elif pattern == "siding":           # 가로 판재 (사이딩 · 셔터 · 블라인드)
        color_out, height_out = _bands(nt, vec, 'Y', spec.get("scale", 0.18), c1, c2, sharp=False)
    elif pattern == "seam":             # 금속 지붕 이음매
        direction = 'Y' if spec.get("axis", "y") == "y" else 'X'
        color_out, height_out = _bands(nt, coord.outputs["Object"], direction, spec.get("scale", 0.45), c1, c2,
                                       sharp=False)
    elif pattern == "wood":
        tex = nt.nodes.new("ShaderNodeTexWave")
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        tex.wave_type = 'BANDS'
        tex.bands_direction = 'Y'
        _inp(tex, ["Scale"], 6.0)
        _inp(tex, ["Distortion"], 6.0)
        _inp(tex, ["Detail"], 4.0)
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = c2
        ramp.color_ramp.elements[1].color = c1
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        color_out, height_out = ramp.outputs["Color"], tex.outputs["Fac"]

    if color_out is not None and spec.get("grime", 0) > 0:
        # 아래쪽(빗물 튀김) 오염: z 0~1.2 m 에서 어둡게
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coord.outputs["Object"], sep.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        _inp(mr, ["From Min"], 0.0)
        _inp(mr, ["From Max"], 1.2)
        _inp(mr, ["To Min"], spec["grime"])
        _inp(mr, ["To Max"], 0.0)
        nt.links.new(sep.outputs[2], mr.inputs[0])
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = 'MULTIPLY'
        nt.links.new(mr.outputs[0], mix.inputs[0])
        nt.links.new(color_out, mix.inputs[1])
        mix.inputs[2].default_value = (0.45, 0.42, 0.38, 1.0)
        color_out = mix.outputs[0]

    if color_out is not None:
        nt.links.new(color_out, bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = c1
    if height_out is not None and spec.get("bump", 0) > 0:
        bump = nt.nodes.new("ShaderNodeBump")
        _inp(bump, ["Strength"], spec["bump"])
        _inp(bump, ["Distance"], 0.02)
        nt.links.new(height_out, bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mat.diffuse_color = c1
    return mat
