"""블렌더 연결부: geom.Mesh -> 블렌더 메시, 입체 글자 메시, 절차적 재질.

면 방향은 geom 이 이미 바깥으로 맞춰 두므로 여기서는 법선을 다시 계산하지 않는다.
"""

import math
import os
import re

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
            cache[k] = logo_parts(_logo_path(key, logo_dir), max_w, max_h, depth,
                                  LOGO_TINT.get(key), font)
        return cache[k]
    fit.logo = logo
    return fit


# ---------------------------------------------------------------------------
# 로고 (SVG -> 색별 입체 조각)
# ---------------------------------------------------------------------------

LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logos")
# 채움색이 없는(검정) 한 가지 색 SVG 를 칠할 브랜드 색 (선형 RGB)
LOGO_TINT = {"starbucks": (0.0, 0.125, 0.045), "bonggubeer": (0.955, 0.604, 0.004)}
LOGO_LAYER = 0.002      # SVG 에서 나중에 그린 도형일수록 이만큼 앞으로 (겹친 색이 깜빡이지 않게)


def _flatten_gradients(src):
    """fill="url(#id)" · fill:url(#id) 를 그 그라데이션 색 지점들의 평균색으로 바꾼 SVG 문자열"""
    grads = {}
    for gid, body in re.findall(r'<(?:linear|radial)Gradient[^>]*\bid="([^"]+)"[^>]*>(.*?)</(?:linear|radial)Gradient>',
                                src, re.S):
        cols = [c for c in re.findall(r'stop-color[:=]\s*"?(#[0-9a-fA-F]{3,6})', body)]
        if cols:
            rgb = [[int((c[1:] if len(c) == 7 else "".join(ch * 2 for ch in c[1:]))[i:i + 2], 16) for i in (0, 2, 4)]
                   for c in cols]
            grads[gid] = "#%02x%02x%02x" % tuple(round(sum(v[i] for v in rgb) / len(rgb)) for i in range(3))
    for gid, hexc in grads.items():
        src = re.sub(r"url\(#%s\)" % re.escape(gid), hexc, src)
    return src


def _prepare_svg(src):
    """블렌더 SVG 가져오기 전 정리: 그라데이션 -> 평균색, <defs> · clipPath · mask 정의 제거
    (가져오기는 정의 안의 잘라내기 경로도 검은 도형으로 그려 버린다)"""
    src = _flatten_gradients(src)
    src = re.sub(r"<defs\b.*?</defs>|<defs\b[^>]*/>", "", src, flags=re.S)
    src = re.sub(r"<(clipPath|mask)\b.*?</\1>", "", src, flags=re.S)
    return re.sub(r'\s(?:clip-path|mask)="[^"]*"', "", src)


def _svg_paths(path):
    """SVG 를 가져와 도형마다 (평면 삼각형 좌표 [(x, y)], 면, 선형 RGB) 를 그린 순서대로"""
    import addon_utils          # bpy 를 먼저 불러와야 쓸 수 있다
    import tempfile
    addon_utils.enable("io_curve_svg", default_set=False)
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    flat = _prepare_svg(src)
    if flat != src:                                  # 그라데이션 · 잘라내기 경로 정리본으로 가져온다
        fd, path = tempfile.mkstemp(suffix=".svg")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(flat)
    before_obj, before_mat = set(bpy.data.objects), set(bpy.data.materials)
    bpy.ops.import_curve.svg(filepath=path)
    if flat != src:
        os.remove(path)
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


def _logo_path(key, logo_dir=None):
    """logos/<키>.svg 가 있으면 그것, 없으면 logos/<키>.png (둘 다 없으면 None)"""
    base = os.path.join(logo_dir or LOGO_DIR, key)
    for ext in (".svg", ".png"):
        if os.path.isfile(base + ext):
            return base + ext
    return None


LOGO_AREA = 40000       # PNG 로고를 이 픽셀 수(가로 x 세로)로 맞춰 추적한다 (가장자리는 이 격자 계단이 된다)
LOGO_COLORS = 6         # PNG 로고에서 나눌 최대 색 수 (가장 많이 쓰인 색부터)
LOGO_MAX_FACES = 5000   # SVG 로고의 면이 이보다 많으면(아주 세밀한 원본) 그림으로 그린 뒤 PNG 처럼 추적한다


def _srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _rects(mask):
    """True 픽셀 덩어리를 가로 줄 구간을 세로로 이어 붙인 직사각형 (r0, r1, c0, c1) 목록"""
    H, W = mask.shape
    out, active = [], {}
    for r in range(H + 1):
        runs = set()
        if r < H:
            c = 0
            while c < W:
                if mask[r, c]:
                    s = c
                    while c < W and mask[r, c]:
                        c += 1
                    runs.add((s, c))
                else:
                    c += 1
        for key in [k for k in active if k not in runs]:
            out.append((active.pop(key), r, key[0], key[1]))
        for key in runs:
            active.setdefault(key, r)
    return out


def _raster_paths(paths):
    """도형 목록을 LOGO_AREA 픽셀 그림(2배로 그린 뒤 줄여 가장자리를 부드럽게)으로 그려 PNG 처럼 다시 추적"""
    import tempfile
    from PIL import Image, ImageDraw
    allp = np.array([p for pts, _, _ in paths for p in pts], dtype=np.float64)
    lo, hi = allp.min(0), allp.max(0)
    W, H = hi - lo
    k = 2 * (LOGO_AREA / max(W * H, 1e-9)) ** 0.5
    im = Image.new("RGBA", (max(1, round(W * k)), max(1, round(H * k))), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for pts, faces, rgb in paths:
        srgb = [12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055 for c in rgb]
        col = tuple(int(round(255 * min(max(c, 0.0), 1.0))) for c in srgb) + (255,)
        for f in faces:
            d.polygon([((pts[i][0] - lo[0]) * k, (hi[1] - pts[i][1]) * k) for i in f], fill=col)
    im = im.resize((max(1, im.size[0] // 2), max(1, im.size[1] // 2)), Image.LANCZOS)
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    im.save(tmp)
    try:
        return _png_paths(tmp)
    finally:
        os.remove(tmp)


def _png_paths(path):
    """PNG 로고 -> 색마다 (격자 꼭짓점 [(x, -y)], 사각형 면, 선형 RGB). 각 색의 사각형은 같은 꼭짓점을 공유해
    안쪽 모서리가 서로 상쇄되므로 logo_parts 가 바깥 가장자리만 옆면으로 만든다"""
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    k = (LOGO_AREA / (im.size[0] * im.size[1])) ** 0.5
    if abs(k - 1) > 1e-6:                              # 작은 그림은 부드럽게 키운 뒤 나눠야 가장자리가 덜 각진다
        im = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float64) / 255.0
    opaque = a[..., 3] >= 0.5
    rgb = a[..., :3][opaque]
    if len(rgb) == 0:
        return []
    q = np.minimum((rgb * 255).astype(int) // 32, 7)
    key = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
    counts = np.bincount(key, minlength=512)
    top = [t for t in np.argsort(-counts) if counts[t] >= 0.01 * len(rgb)]
    centers, weights = [], []
    for t in top:                                     # 비슷한 색(가장자리 번짐 · 그림자)은 많은 쪽으로 합친다
        c, n = rgb[key == t].mean(0), counts[t]
        near = [i for i, m in enumerate(centers) if np.linalg.norm(m - c) < 0.12]
        if near:
            i = near[0]
            centers[i] = (centers[i] * weights[i] + c * n) / (weights[i] + n)
            weights[i] += n
        elif len(centers) < LOGO_COLORS:
            centers.append(c)
            weights.append(n)
    label = np.full(opaque.shape, -1)
    dist = np.stack([np.linalg.norm(rgb - c, axis=1) for c in centers], 1)
    label[opaque] = dist.argmin(1)
    out = []
    for j, c in enumerate(centers):
        verts, index, faces = [], {}, []

        def v(x, y):
            if (x, y) not in index:
                index[(x, y)] = len(verts)
                verts.append((float(x), float(-y)))
            return index[(x, y)]
        for r0, r1, c0, c1 in _rects(label == j):
            faces.append((v(c0, r0), v(c1, r0), v(c1, r1), v(c0, r1)))
        if faces:
            out.append((verts, faces, tuple(float(x) for x in _srgb_to_linear(c))))
    out.sort(key=lambda p: -len(p[1]))
    return out


SIMPLE_SVG = {"svg", "title", "desc", "g", "rect", "circle", "ellipse", "path", "text", "line", "polygon"}


def _hex_linear(c):
    """'#rgb' · '#rrggbb' -> 선형 RGB (없음 · none -> None)"""
    if not c or c == "none" or not c.startswith("#"):
        return {"white": (1.0, 1.0, 1.0), "black": (0.0, 0.0, 0.0)}.get(c)
    h = c[1:]
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    rgb = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return tuple(float(x) for x in _srgb_to_linear(rgb))


def _ring(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _rrect(x, y, w, h, r, n=6):
    """둥근 모서리 사각형 꼭짓점 (SVG 좌표, y 아래)"""
    r = max(0.0, min(r, w / 2, h / 2))
    if r < 1e-6:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _capsule(p, q, sw, round_cap, n=8):
    """선분 p-q 를 굵기 sw 로 칠한 다각형 (둥근 끝이면 반원)"""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy) or 1e-9
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    h = sw / 2
    if not round_cap:
        return [(p[0] + nx * h, p[1] + ny * h), (q[0] + nx * h, q[1] + ny * h),
                (q[0] - nx * h, q[1] - ny * h), (p[0] - nx * h, p[1] - ny * h)]
    a = math.atan2(ny, nx)
    pts = [(q[0] + h * math.cos(a - math.pi * i / n), q[1] + h * math.sin(a - math.pi * i / n)) for i in range(n + 1)]
    pts += [(p[0] + h * math.cos(a + math.pi - math.pi * i / n), p[1] + h * math.sin(a + math.pi - math.pi * i / n))
            for i in range(n + 1)]
    return pts


def _path_points(d):
    """M · L · H · V · Z (대 · 소문자) 만 쓰는 경로 -> [(점 목록, 닫힘)]. 다른 명령이 있으면 None"""
    toks = re.findall(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:[eE]-?\d+)?", d)
    subs, cur, x, y, cmd, i = [], None, 0.0, 0.0, None, 0
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz" and cur:
                subs.append((cur, True))
                cur = None
                continue
            if cmd not in "MmLlHhVvZz":
                return None
            continue
        rel = cmd.islower()
        if cmd in "Mm" or cmd in "Ll":
            nx_, ny_ = float(toks[i]), float(toks[i + 1])
            i += 2
            x, y = (x + nx_, y + ny_) if rel else (nx_, ny_)
            if cmd in "Mm":
                if cur:
                    subs.append((cur, False))
                cur = [(x, y)]
                cmd = "l" if rel else "L"
            else:
                cur.append((x, y))
        elif cmd in "Hh":
            v = float(toks[i]); i += 1
            x = x + v if rel else v
            cur.append((x, y))
        elif cmd in "Vv":
            v = float(toks[i]); i += 1
            y = y + v if rel else v
            cur.append((x, y))
        else:
            return None
    if cur:
        subs.append((cur, False))
    return subs


def _svg_simple(path, font):
    """사각형 · 원 · 직선 경로 · 글자만 쓰는 간단한 SVG (워드마크) -> 도형마다 (점, 면, 선형 RGB), 그린 순서대로.
    블렌더 SVG 가져오기가 버리는 <text> 와 테두리선(stroke)을 살린다. 지원하지 않는 요소가 있으면 None"""
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    els = list(root.iter())
    tags = [e.tag.split("}")[-1] for e in els]
    if not set(tags) <= SIMPLE_SVG:
        return None
    out = []

    def poly(pts, rgb, hole=None):
        """y 를 뒤집은 다각형 (hole 이 있으면 같은 꼭짓점 수의 안쪽 고리와 사각형 띠)"""
        if rgb is None or len(pts) < 3:
            return
        P = [(px, -py) for px, py in pts]
        if hole is None:
            out.append((P, [tuple(range(len(P)))], rgb))
            return
        Q = [(px, -py) for px, py in hole]
        n = len(P)
        out.append((P + Q, [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)], rgb))

    for e, tag in zip(els, tags):
        g = e.get
        fill, stroke = _hex_linear(g("fill", "#000")), _hex_linear(g("stroke", "none"))
        sw = float(g("stroke-width", "1"))
        if tag == "rect":
            x, y, w, h = (float(g(k, "0")) for k in ("x", "y", "width", "height"))
            r = float(g("rx", g("ry", "0")))
            poly(_rrect(x, y, w, h, r), fill)
            if stroke is not None:
                poly(_rrect(x - sw / 2, y - sw / 2, w + sw, h + sw, r + sw / 2), stroke,
                     _rrect(x + sw / 2, y + sw / 2, w - sw, h - sw, max(r - sw / 2, 0.0)))
        elif tag in ("circle", "ellipse"):
            cx, cy = float(g("cx", "0")), float(g("cy", "0"))
            rx = float(g("r", g("rx", "0")))
            ry = float(g("r", g("ry", "0")))
            poly(_ring(cx, cy, rx, ry), fill)
            if stroke is not None:
                poly(_ring(cx, cy, rx + sw / 2, ry + sw / 2), stroke, _ring(cx, cy, rx - sw / 2, ry - sw / 2))
        elif tag in ("path", "line", "polygon"):
            if tag == "path":
                subs = _path_points(g("d", ""))
                if subs is None:
                    return None
            elif tag == "line":
                subs = [([(float(g("x1", "0")), float(g("y1", "0"))), (float(g("x2", "0")), float(g("y2", "0")))],
                         False)]
            else:
                nums = [float(v) for v in re.findall(r"-?[\d.]+", g("points", ""))]
                subs = [(list(zip(nums[0::2], nums[1::2])), True)]
            if tag != "line" and g("fill") != "none" and fill is not None:
                for pts, _ in subs:
                    poly(pts, fill)
            if stroke is not None:
                rc = g("stroke-linecap") == "round"
                for pts, closed in subs:
                    seg = pts + ([pts[0]] if closed else [])
                    for a, b in zip(seg, seg[1:]):
                        poly(_capsule(a, b, sw, rc), stroke)
        elif tag == "text" and font is not None and (e.text or "").strip():
            t = text_mesh(e.text.strip(), font, float(g("font-size", "16")), 0.0)
            if t is None or fill is None:
                continue
            verts, faces, w, h, _ = t
            x, y, fs = float(g("x", "0")), float(g("y", "0")), float(g("font-size", "16"))
            cx = {"middle": x, "end": x - w / 2}.get(g("text-anchor", "start"), x + w / 2)
            cy = -(y - 0.36 * fs)                         # 기준선 위 대문자 높이의 가운데
            out.append(([(cx + vx, cy + vy) for vx, vy, _ in verts], [tuple(f) for f in faces], fill))
    return out


def logo_parts(path, max_w, max_h, depth=0.03, tint=None, font=None):
    """SVG 로고 -> 색별 조각 [(verts, faces, 폭, 높이, 두께, 선형 RGB)]. 모든 조각이 같은 중심 · 배율을 써서
    그대로 겹쳐 놓으면 로고가 된다. 면은 앞면 + 옆면만 (뒷면은 간판에 붙어 보이지 않는다). 파일이 없으면 None"""
    if not path or not os.path.isfile(path):
        return None
    if path.lower().endswith(".png"):
        paths = _png_paths(path)
    else:
        paths = _svg_simple(path, font)
        if paths is None:                              # 곡선 경로 등: 블렌더 SVG 가져오기
            paths = _svg_paths(path)
        if paths and sum(len(f) for _, f, _ in paths) > LOGO_MAX_FACES:
            traced = _raster_paths(paths)               # 면이 더 적을 때만 바꾼다 (잔무늬가 많으면 오히려 는다)
            if traced and sum(len(f) for _, f, _ in traced) < sum(len(f) for _, f, _ in paths):
                paths = traced
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
