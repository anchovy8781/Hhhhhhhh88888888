"""건물 모델링 키트: 닫힌 박스 조각, 파사드 좌표계, 입체 글자, 절차적 재질.

좌표: 미터, Z 위. 에셋 원점 = 부지(lot) 중심 지면. 건물 정면은 -Y (도로 쪽).
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

# 박스 면 순서 (box_verts 의 정점 순서 기준)
BOTTOM, TOP, BACK, RIGHT, FRONT, LEFT = range(6)
_BOX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


class Mesh:
    """머티리얼 이름별로 조각을 모아 한 메시로 만든다."""

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
        o = len(self.verts)
        self.verts += [tuple(map(float, v)) for v in verts]
        self.faces += [tuple(int(i) + o for i in f) for f in faces]
        self.mats += [self._mi(mat)] * len(faces)

    def box(self, x0, x1, y0, y1, z0, z1, mat, skip=()):
        """축 정렬 박스. skip 에 BOTTOM/TOP/BACK(-Y)/RIGHT(+X)/FRONT(+Y)/LEFT(-X) 면 생략"""
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [face for i, face in enumerate(_BOX_FACES) if i not in skip]
        self.add(v, f, mat)

    def cylinder(self, cx, cy, r, z0, z1, mat, n=16, cap=True):
        ring = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        v = [(x, y, z0) for x, y in ring] + [(x, y, z1) for x, y in ring]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        if cap:
            f += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        self.add(v, f, mat)

    def cone(self, cx, cy, r, z0, z1, mat, n=16):
        v = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
        v.append((cx, cy, z1))
        f = [(i, (i + 1) % n, n) for i in range(n)] + [tuple(reversed(range(n)))]
        self.add(v, f, mat)

    def to_object(self, name, materials, collection=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        me.validate()
        for n in self.mat_names:
            me.materials.append(materials[n])
        me.polygons.foreach_set("material_index", self.mats[:len(me.polygons)])
        me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)  # 닫힌 조각마다 바깥쪽으로
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new(name, me)
        (collection or bpy.context.scene.collection).objects.link(obj)
        return obj


class Facade:
    """벽면 좌표계: u = 벽을 바라볼 때 오른쪽, z = 위, d = 벽에서 바깥쪽.

    side: 'front'(-Y 면), 'back'(+Y), 'left'(-X), 'right'(+X).
    """

    def __init__(self, mesh, side, x0, x1, y0, y1):
        self.m = mesh
        self.side = side
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

    def xy(self, u, d):
        return (self.o[0] + self.r[0] * u + self.n[0] * d, self.o[1] + self.r[1] * u + self.n[1] * d)

    def box(self, u0, u1, z0, z1, d0, d1, mat, attached=True):
        """벽에 붙은 박스. attached 면 벽 쪽(d0) 면은 생략 (보이지 않아 텍스처 낭비)"""
        xa, ya = self.xy(u0, d0)
        xb, yb = self.xy(u1, d1)
        x0, x1 = sorted((xa, xb))
        y0, y1 = sorted((ya, yb))
        skip = ()
        if attached and d0 <= 0.0:
            skip = {"front": (FRONT,), "back": (BACK,), "left": (RIGHT,), "right": (LEFT,)}[self.side]
        self.m.box(x0, x1, y0, y1, z0, z1, mat, skip)

    def text(self, letters, u, z, d, mat):
        """letters: text_mesh() 결과. (u, z) 가 글자 중심, d 는 벽면에서 띄우는 거리"""
        verts, faces, _w, _h, depth = letters
        out = []
        for lx, ly, lz in verts:
            x, y = self.xy(u + lx, d + depth / 2 + lz)
            out.append((x, y, z + ly))
        self.m.add(out, faces, mat)

    def window(self, u, z, w, h, glass="glass", frame="frame", sill="trim", mullions=1, lit=False, blind=0.0):
        """창 하나: 돌출 창틀 + 유리 + 중간 살 + 창대"""
        fw = 0.07
        out = 0.10
        self.box(u - w / 2, u + w / 2, z, z + fw, 0, out, frame)
        self.box(u - w / 2, u + w / 2, z + h - fw, z + h, 0, out, frame)
        self.box(u - w / 2, u - w / 2 + fw, z + fw, z + h - fw, 0, out, frame)
        self.box(u + w / 2 - fw, u + w / 2, z + fw, z + h - fw, 0, out, frame)
        for k in range(1, mullions + 1):
            mu = u - w / 2 + w * k / (mullions + 1)
            self.box(mu - 0.03, mu + 0.03, z + fw, z + h - fw, 0, out * 0.8, frame)
        self.box(u - w / 2 + fw, u + w / 2 - fw, z + fw, z + h - fw, 0, 0.03, "glass_lit" if lit else glass)
        if blind and not lit:
            # 안쪽 블라인드/커튼이 반쯤 내려온 창 (유리 바로 뒤가 아니라 유리 면에 얇게)
            drop = h * blind
            self.box(u - w / 2 + fw, u + w / 2 - fw, z + h - fw - drop, z + h - fw, 0, 0.032, "blind")
        self.box(u - w / 2 - 0.08, u + w / 2 + 0.08, z - 0.06, z, 0, 0.16, sill)

    def storefront(self, u0, u1, z0, z1, bay=1.25, transom=2.55, door=None):
        """1층 상점 유리면: 알루미늄 멀리언 격자 + 문"""
        self.box(u0, u1, z0, z0 + 0.12, 0, 0.12, "frame")
        self.box(u0, u1, z1 - 0.10, z1, 0, 0.12, "frame")
        self.box(u0, u1, z0 + transom, z0 + transom + 0.08, 0, 0.10, "frame")
        n = max(int(round((u1 - u0) / bay)), 1)
        for k in range(n + 1):
            uu = u0 + (u1 - u0) * k / n
            self.box(uu - 0.04, uu + 0.04, z0 + 0.12, z1 - 0.10, 0, 0.12, "frame")
        self.box(u0, u1, z0 + 0.12, z1 - 0.10, 0, 0.04, "glass_shop")
        if door is not None:
            du, dw = door
            self.box(du - dw / 2, du + dw / 2, z0 + 0.12, z0 + 2.3, 0, 0.07, "glass_door")
            self.box(du - 0.05, du + 0.05, z0 + 0.12, z0 + 2.3, 0, 0.14, "frame")
            for hu in (du - 0.18, du + 0.18):
                self.box(hu - 0.02, hu + 0.02, z0 + 0.9, z0 + 1.4, 0.07, 0.16, "metal")


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
    co[:, :2] -= (lo[:2] + hi[:2]) / 2
    return [tuple(v) for v in co], faces, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]


def fit_text(text, font, max_w, max_h, extrude=0.05):
    """간판 칸(max_w x max_h)에 맞는 크기로 글자 메시 생성"""
    t = text_mesh(text, font, 1.0, extrude)
    if t is None:
        return None
    _, _, w, h, _ = t
    s = min(max_w / max(w, 1e-6), max_h / max(h, 1e-6))
    return text_mesh(text, font, s, extrude)


# ---------------------------------------------------------------------------
# 절차적 재질 (베이크용)
# ---------------------------------------------------------------------------

def _principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def _inp(node, names, value):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return node.inputs[n]


def _facade_uv(nt):
    """벽(X/Y 축 정렬)에 패턴을 세우기 위한 벡터: (x+y, z, 0) — 바닥면은 (x, y)"""
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


def make_material(name, spec):
    """spec 키:
      color, color2      기본색 (선형 RGB)
      pattern            None | 'noise' | 'tile' | 'panel' | 'stripes' | 'paver' | 'wood'
      scale              패턴 크기 (m) — tile/panel/paver 는 (가로, 세로)
      rough, metal       거칠기, 금속성
      emit, emit_strength  발광색, 세기
      bump               범프 세기
      control            ControlMask RGB (색상 변형 영역)
      grime              아래쪽 오염(0~1)
    """
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
    color_out = None
    height_out = None
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
        if pattern == "paver":
            nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        else:
            nt.links.new(vec, tex.inputs["Vector"])
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
    elif pattern == "stripes":
        tex = nt.nodes.new("ShaderNodeTexWave")
        nt.links.new(vec, tex.inputs["Vector"])
        tex.wave_type = 'BANDS'
        tex.bands_direction = 'X'
        _inp(tex, ["Scale"], 1.0 / spec.get("scale", 0.5) / 2)
        _inp(tex, ["Distortion"], 0.0)
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = 'CONSTANT'
        ramp.color_ramp.elements[0].color = c1
        ramp.color_ramp.elements[1].position = 0.5
        ramp.color_ramp.elements[1].color = c2
        nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        color_out = ramp.outputs["Color"]
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
        _inp(mix, ["Color2"], (0.45, 0.42, 0.38, 1.0))
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


# 공통 재질 (이름 -> spec). 건물별로 'wall', 'wall_side', 'accent', 'awning', 'sign' 을 덮어쓴다.
BASE_MATERIALS = {
    "trim": {"color": (0.72, 0.71, 0.68), "pattern": "noise", "scale": 4.0, "rough": 0.8},
    "frame": {"color": (0.55, 0.57, 0.60), "rough": 0.35, "metal": 0.9},
    "frame_dark": {"color": (0.08, 0.08, 0.09), "rough": 0.4, "metal": 0.8},
    "glass": {"color": (0.05, 0.07, 0.08), "rough": 0.05, "metal": 0.6},
    "glass_lit": {"color": (0.05, 0.07, 0.08), "rough": 0.05, "metal": 0.6,
                  "emit": (1.0, 0.78, 0.50), "emit_strength": 0.8},
    "blind": {"color": (0.72, 0.68, 0.60), "color2": (0.66, 0.62, 0.55), "pattern": "stripes", "scale": 0.04,
              "rough": 0.8},
    "glass_shop": {"color": (0.12, 0.14, 0.14), "rough": 0.05, "metal": 0.3,
                   "emit": (1.0, 0.92, 0.80), "emit_strength": 0.5},
    "glass_door": {"color": (0.08, 0.10, 0.10), "rough": 0.05, "metal": 0.4},
    "metal": {"color": (0.70, 0.71, 0.72), "rough": 0.3, "metal": 1.0},
    "metal_dark": {"color": (0.15, 0.16, 0.17), "rough": 0.45, "metal": 0.8},
    "concrete": {"color": (0.48, 0.47, 0.45), "pattern": "noise", "scale": 2.0, "rough": 0.9, "bump": 0.2},
    "roof": {"color": (0.12, 0.36, 0.22), "color2": (0.09, 0.28, 0.17), "pattern": "noise", "scale": 0.8,
             "rough": 0.6},                                  # 옥상 우레탄 방수(초록)
    "paving": {"color": (0.42, 0.40, 0.38), "color2": (0.36, 0.33, 0.31), "pattern": "paver",
               "scale": (0.4, 0.2), "mortar": 0.02, "rough": 0.85, "bump": 0.3},
    "ac": {"color": (0.82, 0.82, 0.80), "rough": 0.5},
    "rubber": {"color": (0.03, 0.03, 0.03), "rough": 0.9},
    "water": {"color": (0.05, 0.25, 0.35), "rough": 0.05, "emit": (0.2, 0.6, 0.9), "emit_strength": 0.6},
    "letters": {"color": (0.95, 0.95, 0.92), "rough": 0.4, "emit": (1.0, 1.0, 0.95), "emit_strength": 3.0},
    "wood": {"color": (0.42, 0.26, 0.14), "color2": (0.30, 0.18, 0.09), "pattern": "wood", "rough": 0.7,
             "bump": 0.1},
    "plastic_red": {"color": (0.70, 0.08, 0.06), "rough": 0.5},
    "plastic_blue": {"color": (0.08, 0.25, 0.70), "rough": 0.5},
    "stainless": {"color": (0.80, 0.80, 0.80), "rough": 0.25, "metal": 1.0},
}
