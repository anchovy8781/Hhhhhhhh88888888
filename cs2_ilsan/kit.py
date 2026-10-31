"""블렌더 연결부: geom.Mesh -> 블렌더 메시, 입체 글자 메시, 절차적 재질.

면 방향은 geom 이 이미 바깥으로 맞춰 두므로 여기서는 법선을 다시 계산하지 않는다.
"""

import os

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
    me.polygons.foreach_set("use_smooth", [bool(x) for x in mesh.smooth])   # 곡면만 부드럽게 (뚜껑과의 경계는 각짐)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)   # 면 방향은 바뀌지 않는다
    # 전부 삼각형으로: 베이크한 탄젠트 공간 노멀맵과 FBX 에 내보내는 탄젠트가 같은 삼각형에서 나오도록
    # (글자 · 원기둥 뚜껑의 다각형은 FBX 탄젠트를 내보낼 수 없다)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
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
    cu.resolution_u = 6      # 글자 곡선 분할 (기본 12 는 폴리곤이 과함, 4 는 곡선이 각져 보임)
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
    # 글자 뒷면은 항상 간판 · 벽 · 유리에 붙어 보이지 않으므로 뺀다 (글자 삼각형의 약 1/3)
    keep = []
    for f in faces:
        nz = 0.0
        for i in range(len(f)):
            a, b = co[f[i]], co[f[(i + 1) % len(f)]]
            nz += (a[0] - b[0]) * (a[1] + b[1])
        if nz > -1e-9:
            keep.append(f)
    faces = keep
    lo, hi = co.min(0), co.max(0)
    co -= (lo + hi) / 2
    return [tuple(v) for v in co], faces, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]


def text_fn_for(font, logo_dir=None):
    """designs.Building 에 넘길 글자 함수: (문구, 최대 폭, 최대 높이, 두께) -> 글자 메시.
    fit.logo(키, 최대 폭, 최대 높이, 두께) 는 logos/<키>.svg 로고 조각 (없으면 None)"""
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

    def logo(key, max_w, max_h, depth=0.03):
        k = (key, round(max_w, 3), round(max_h, 3), round(depth, 3))
        if k not in cache:
            cache[k] = logo_parts(os.path.join(logo_dir or LOGO_DIR, key + ".svg"), max_w, max_h, depth,
                                  LOGO_TINT.get(key))
        return cache[k]
    fit.logo = logo
    return fit


# ---------------------------------------------------------------------------
# 로고 (SVG -> 색별 입체 조각)
# ---------------------------------------------------------------------------

LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos")
# 채움색이 없는(검정) 한 가지 색 SVG 를 칠할 브랜드 색 (선형 RGB)
LOGO_TINT = {"starbucks": (0.0, 0.125, 0.045)}
LOGO_LAYER = 0.002      # SVG 에서 나중에 그린 도형일수록 이만큼 앞으로 (겹친 색이 깜빡이지 않게)


def _svg_paths(path):
    """SVG 를 가져와 도형마다 (평면 삼각형 좌표 [(x, y)], 면, 선형 RGB) 를 그린 순서대로"""
    import addon_utils          # bpy 를 먼저 불러와야 쓸 수 있다
    addon_utils.enable("io_curve_svg", default_set=False)
    before_obj, before_mat = set(bpy.data.objects), set(bpy.data.materials)
    bpy.ops.import_curve.svg(filepath=path)
    new = sorted((o for o in bpy.data.objects if o not in before_obj), key=lambda o: o.name)
    for o in new:
        if o.type == 'CURVE':
            o.data.dimensions = '2D'
            o.data.fill_mode = 'BOTH'
            o.data.extrude = 0.0
            o.data.bevel_depth = 0.0
            o.data.resolution_u = 8
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in new:
        if o.type != 'CURVE':
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        mw = o.matrix_world
        pts = [tuple((mw @ v.co)[:2]) for v in me.vertices]
        faces = [tuple(p.vertices) for p in me.polygons]
        mat = o.data.materials[0] if len(o.data.materials) else None
        rgb = tuple(float(c) for c in mat.diffuse_color[:3]) if mat else (0.0, 0.0, 0.0)
        if faces:
            out.append((pts, faces, rgb))
        bpy.data.meshes.remove(me)
    for o in new:
        data = o.data
        bpy.data.objects.remove(o)
        if data is not None and data.users == 0:
            bpy.data.curves.remove(data)
    for m in set(bpy.data.materials) - before_mat:
        bpy.data.materials.remove(m)
    return out


def logo_parts(path, max_w, max_h, depth=0.03, tint=None):
    """SVG 로고 -> 색별 조각 [(verts, faces, 폭, 높이, 두께, 선형 RGB)]. 모든 조각이 같은 중심 · 배율을 써서
    그대로 겹쳐 놓으면 로고가 된다. 면은 앞면 + 옆면만 (뒷면은 간판에 붙어 보이지 않는다). 파일이 없으면 None"""
    if not os.path.isfile(path):
        return None
    paths = _svg_paths(path)
    if not paths:
        return None
    allp = np.array([p for pts, _, _ in paths for p in pts], dtype=np.float64)
    lo, hi = allp.min(0), allp.max(0)
    s = min(max_w / max(hi[0] - lo[0], 1e-9), max_h / max(hi[1] - lo[1], 1e-9))
    mid = (lo + hi) / 2
    w, h = (hi[0] - lo[0]) * s, (hi[1] - lo[1]) * s
    total = depth + LOGO_LAYER * (len(paths) - 1)
    groups = {}
    for k, (pts, faces, rgb) in enumerate(paths):
        if tint is not None and max(rgb) < 0.02:
            rgb = tint
        key = tuple(round(c, 4) for c in rgb)
        verts, fs = groups.setdefault(key, ([], []))
        xy = [((x - mid[0]) * s, (y - mid[1]) * s) for x, y in pts]
        zb, zf = -total / 2, -total / 2 + depth + LOGO_LAYER * k
        base = len(verts)
        verts += [(x, y, zf) for x, y in xy]                 # 앞면
        n = len(xy)
        verts += [(x, y, zb) for x, y in xy]                 # 옆면 아래 끝
        edges = {}
        for f in faces:
            area = sum(xy[f[i]][0] * xy[f[(i + 1) % len(f)]][1] - xy[f[(i + 1) % len(f)]][0] * xy[f[i]][1]
                       for i in range(len(f)))
            if abs(area) < 1e-12:
                continue
            f = f if area > 0 else tuple(reversed(f))      # 앞(+z)에서 반시계
            fs.append(tuple(base + i for i in f))
            for i in range(len(f)):
                a, b = f[i], f[(i + 1) % len(f)]
                edges[(a, b)] = edges.get((a, b), 0) + 1
        for (a, b) in edges:                                 # 경계 모서리: 반대 방향 짝이 없는 것
            if (b, a) not in edges:
                fs.append((base + n + a, base + n + b, base + b, base + a))
    return [(v, f, w, h, total, rgb) for rgb, (v, f) in groups.items()]


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

    if height_out is not None and "emit2" in spec:
        # 발광색도 무늬를 따라 바꾼다: 유리 너머 진열대 · 방마다 다른 불빛 (밤에 Emissive 맵으로 보인다)
        em = nt.nodes.new("ShaderNodeMixRGB")
        nt.links.new(height_out, em.inputs[0])
        em.inputs[1].default_value = (*spec["emit"], 1.0)
        em.inputs[2].default_value = (*spec["emit2"], 1.0)
        target = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        nt.links.new(em.outputs[0], target)
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
