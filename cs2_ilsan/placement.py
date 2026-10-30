"""일산지 거리 위 에셋 배치 계획 (게임 좌표). bpy 없이 동작.

게임에서 '소형 2차로 도로'(폭 약 16 m)를 해변 도로 중심선을 따라 그리면,
도로 중심에서 ROAD_HALF 만큼 떨어진 곳이 부지 앞선이 된다.

거리 구성 (북 -> 남, 해안선 station 기준)
  - 해변 도로 육지 쪽: 고정 부지(타니베이호텔, 광장 모퉁이 유리 상가 2동)를 먼저 놓고,
    남은 구간을 catalog.SEQUENCE 로 채운다. 골목 · 광장 · 하천 자리는 비운다.
  - 일산청년광장: 거리 가운데에서 육지 쪽으로 뻗은 진입로(24 m x 128 m)를 광장 구간 4개로 채우고,
    양옆에 광장을 바라보는 상가(catalog.PLAZA_SIDES)를 세운다. 광장 입구 도로 위에 회전교차로 중앙섬.
  - 하천: 광장 남쪽을 가로질러 바다로 흐르는 물길. 육지 쪽 부지를 비우고 산책로에 보행교.
  - 해변 쪽: 화장실 2, 광장 축 끝 백사장의 삼각 조형물, 하천 보행교.
  - 소품: 백사장 가장자리 해송, 산책로의 검은 난간, 노면 글자 'CCTV 주차단속'.
모든 항목은 중심(center), 안쪽 방향 v(에셋의 +Y = 정면의 반대), 모서리(corners)를 가진다.
"""

import math

import numpy as np

import catalog
import street as S

ROAD_HALF = 8.0                      # 도로 중심 -> 부지 앞선 (CS2 소형 도로 반폭)
ROAD_CENTER = (S.PROMENADE_END + S.ROAD_END) / 2
GAP = 0.0                            # 부지 사이 간격 (CS2 부지는 셀 단위로 맞붙는다)

PLAZA_FRAC = 0.5                     # 광장 축 위치 (해안선 길이 비율)
PLAZA_HALF = 12.0                    # 광장 반폭 (3셀)
PLAZA_SEG = 32.0                     # 광장 구간 길이 (4셀)
STREAM_FROM_PLAZA = 55.0             # 하천 위치: 광장 축에서 남쪽으로 (m, 광장과 나란히 흐른다)
STREAM_HALF = 7.0                    # 하천 + 둑 반폭
HOTEL_FROM_PLAZA = -150.0            # 호텔 부지 중앙: 광장에서 북쪽으로 (앞선 길이 m)
PINE_OFFSET = 40.5                   # 해송 줄 (해안선에서, 호안 44 m 바로 바다 쪽 백사장)
RAIL_OFFSET = 49.7                   # 난간 줄 (도로 바다 쪽 끝 50 m 바로 안쪽 산책로)


def frontage(st):
    """부지 앞선 곡선과 그 위 누적 길이(m), 해안선 station 과의 대응"""
    off = ROAD_CENTER + ROAD_HALF
    pts = st.at_offset(off)
    arc = S.cumulative(pts)
    return off, arc


def rect(front_mid, v, width, depth):
    """앞선 중앙 front_mid 에서 v 방향으로 depth 만큼 들어간 width 폭 사각형 (앞 두 점 먼저)과 중심"""
    v = np.asarray(v, dtype=float)
    t = np.array([v[1], -v[0]])
    c = np.asarray(front_mid, dtype=float) + v * depth / 2
    hw, hd = width / 2, depth / 2
    return np.array([c + t * a + v * b for a, b in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]), c


def _rect(st, s_mid, off, width, depth, side="land"):
    """station 의 앞선 중앙에서 도로를 향한 부지 사각형 (로컬 xy, 앞 두 점 먼저), 중심, 안쪽 방향 v.
    side='land' 면 부지가 육지 쪽(+n)으로, 'sea' 면 바다 쪽(-n)으로 들어간다. 정면 방향 = -v."""
    (fx, fy), n, z = st.frame(s_mid, off)
    v = np.asarray(n) * (1.0 if side == "land" else -1.0)
    corners, c = rect((fx, fy), v, width, depth)
    return corners, c, v, z


def overlaps(p, q, eps=0.05):
    """두 볼록 사각형이 eps 이상 겹치는지 (분리축 검사)"""
    for poly in (p, q):
        for i in range(4):
            e = poly[(i + 1) % 4] - poly[i]
            ax = np.array([-e[1], e[0]]) / (np.hypot(*e) + 1e-12)
            pa, qa = p @ ax, q @ ax
            if pa.max() <= qa.min() + eps or qa.max() <= pa.min() + eps:
                return False
    return True


def near(poly, pt, margin):
    """점이 볼록 사각형에서 margin 안쪽(또는 안)에 있는지"""
    pt = np.asarray(pt)
    for i in range(4):
        e = poly[(i + 1) % 4] - poly[i]
        ax = np.array([e[1], -e[0]]) / (np.hypot(*e) + 1e-12)
        side = (poly - poly[i]) @ ax
        inward = -1.0 if side.sum() > 0 else 1.0    # ax 가 다각형 바깥을 향하도록
        if (pt - poly[i]) @ (ax * inward) > margin:
            return False
    return True


def cells(name):
    cw, cd = catalog.ASSETS[name][:2]
    return cw * catalog.CELL, cd * catalog.CELL


def item(name, side, corners, center, v, **extra):
    d = {"asset": name, "side": side, "corners": corners, "center": np.asarray(center, dtype=float),
         "v": np.asarray(v, dtype=float)}
    d.update(extra)
    return d


class Layout:
    """광장 · 하천 · 고정 부지의 위치 (모든 배치 함수가 공유)"""

    def __init__(self, st):
        self.st = st
        self.off, self.arc = frontage(st)
        self.s_p = PLAZA_FRAC * st.length
        (fx, fy), n, _ = st.frame(self.s_p, self.off)
        self.F = np.array([fx, fy])                    # 광장 축이 부지 앞선과 만나는 점
        self.n = np.asarray(n)                         # 광장 축 방향 (육지 쪽)
        self.t = np.array([n[1], -n[0]])               # 광장 가로 방향 (+ = 북쪽, 육지 쪽 부지의 +X)
        q = self.F - self.t * STREAM_FROM_PLAZA                     # 하천 축이 부지 앞선과 만나는 점
        self.s_st = float(st.project(q[None])[0][0])
        mouth = q - self.n * (self.off + 12.0)
        self.stream_poly, _ = rect(mouth, self.n, 2 * STREAM_HALF, self.off + 12.0 + 200.0)
        self.stream_line = [mouth, q + self.n * 200.0]
        self.road_center = st.frame(self.s_p, ROAD_CENTER)[0]

    def to_arc(self, s):
        return float(np.interp(s, self.st.s, self.arc))

    def to_s(self, a):
        return float(np.interp(a, self.arc, self.st.s))

    def lateral(self, pt):
        """광장 축 기준 (가로, 축 방향) 좌표"""
        d = np.asarray(pt) - self.F
        return float(d @ self.t), float(d @ self.n)

    def land_lot(self, name, a0):
        """해변 도로 육지 쪽 부지 (앞선 길이 a0 에서 시작)"""
        w, d = cells(name)
        s_mid = self.to_s(a0 + w / 2)
        corners, c, v, _ = _rect(self.st, s_mid, self.off, w, d)
        return item(name, "land", corners, c, v, a0=a0, a1=a0 + w, s_mid=s_mid, width=w, depth=d,
                    front_offset=self.off)


def plaza_segments(lay):
    """광장 구간 4개: 진입로 축을 따라 이어 놓는다 (정면 = 바다 쪽)"""
    out = []
    for k, name in enumerate(catalog.PLAZA_SEGMENTS):
        w, d = cells(name)
        corners, c = rect(lay.F + lay.n * PLAZA_SEG * k, lay.n, w, d)
        out.append(item(name, "plaza", corners, c, lay.n))
    return out


def plaza_sides(lay, obstacles, step=0.25):
    """광장을 바라보는 양옆 상가 (정면 = 광장 쪽). 모퉁이 상가 뒤에서 시작해 광장 끝까지."""
    out = []
    end = PLAZA_SEG * len(catalog.PLAZA_SEGMENTS)
    for sgn, names in ((1, catalog.PLAZA_SIDES["north"]), (-1, catalog.PLAZA_SIDES["south"])):
        v = lay.t * sgn
        p, k = 24.0, 0
        while k < 3 * len(names):
            name = names[k % len(names)]
            w, d = cells(name)
            q = p
            while q + w <= end:
                corners, c = rect(lay.F + lay.t * sgn * PLAZA_HALF + lay.n * (q + w / 2), v, w, d)
                if not any(overlaps(corners, o) for o in obstacles + [it["corners"] for it in out]):
                    break
                q += step
            k += 1
            if q + w > end:
                continue
            out.append(item(name, "plaza", corners, c, v, axial=q))
            p = q + w + GAP
    return out


def fixed_land(lay, obstacles, step=0.25):
    """광장 모퉁이 유리 상가 2동 (광장에서 바깥으로 밀어 겹치지 않게) + 타니베이호텔"""
    a_p = lay.to_arc(lay.s_p)
    out = []
    for name, sgn in (("IlsanCornerTower01", -1), ("IlsanCornerTower02", 1)):
        w, _ = cells(name)
        a0 = a_p + PLAZA_HALF if sgn > 0 else a_p - PLAZA_HALF - w
        it = lay.land_lot(name, a0)
        while any(overlaps(it["corners"], o) for o in obstacles):
            a0 += step * sgn
            it = lay.land_lot(name, a0)
        out.append(it)
    w, _ = cells("IlsanTanibayHotel")
    out.append(lay.land_lot("IlsanTanibayHotel", a_p + HOTEL_FROM_PLAZA - w / 2))
    return out


def _merge(blocks):
    out = []
    for a, b in sorted(blocks):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def plan(st, alleys, margin=10.0, step=0.25, layout=None):
    """해변 도로 육지 쪽 + 광장 부지 전체.

    부지 앞선 곡선 위에서 길이를 재며 (곡선 바깥쪽으로 갈수록 길이가 늘어나므로 station 이 아니라 앞선 길이)
    골목 · 광장 · 하천 · 고정 부지 사이 구간을 SEQUENCE 순서로 채운다. 곡선이 안쪽으로 휜 곳에서는
    이웃 부지 뒤쪽이 겹치므로 겹치지 않을 때까지 앞으로 민다.
    반환: 부지 목록 (해변 도로 쪽은 앞선 길이 순)
    """
    lay = layout or Layout(st)
    plaza = plaza_segments(lay)
    fixed = fixed_land(lay, [it["corners"] for it in plaza] + [lay.stream_poly])
    plaza += plaza_sides(lay, [it["corners"] for it in fixed] + [lay.stream_poly])
    obstacles = [it["corners"] for it in plaza + fixed] + [lay.stream_poly]
    total = float(lay.arc[-1])
    a_st = lay.to_arc(lay.s_st)
    blocks = [(lay.to_arc(x) - 4.0, lay.to_arc(x) + 4.0) for x in alleys]   # 골목 반폭 약 4 m
    blocks += [(it["a0"], it["a1"]) for it in fixed] + [(a_st - STREAM_HALF, a_st + STREAM_HALF)]
    blocks += [(-1e9, margin), (total - margin, 1e9)]
    free = []
    merged = _merge(blocks)
    for (_, a), (b, _) in zip(merged[:-1], merged[1:]):
        free.append((a, b))
    seq = list(catalog.SEQUENCE)
    k = 0
    out = list(fixed)
    for a, b in free:
        pos, prev = a, None
        tries = 0
        while tries < len(seq):
            name = seq[k % len(seq)]
            w, _ = cells(name)
            p = pos
            it = None
            while p + w <= b:
                it = lay.land_lot(name, p)
                if (prev is None or not overlaps(prev, it["corners"])) and \
                        not any(overlaps(it["corners"], o) for o in obstacles):
                    break
                p += step
            if p + w <= b:
                out.append(it)
                prev = it["corners"]
                pos = p + w + GAP
                k += 1
                tries = 0
            else:
                k += 1          # 이 자리에 안 맞으면 다음 후보
                tries += 1
    out.sort(key=lambda it: it["a0"])
    return out + plaza


def plan_seaside(st, layout=None):
    """도로 바다 쪽: 화장실 · 샤워장, 하천 보행교 (앞선 = 도로 중심 - ROAD_HALF, 백사장 쪽으로),
    광장 축 끝 백사장의 삼각 조형물 (앞선 = 해안선에서 30 m)."""
    lay = layout or Layout(st)
    off = ROAD_CENTER - ROAD_HALF
    spots = [(name, frac * st.length, off, "sea") for name, frac in catalog.SEASIDE]
    spots += [("IlsanStreamBridge", lay.s_st, off, "sea"), ("IlsanBeachLandmark", lay.s_p, 30.0, "beach")]
    out = []
    for name, s_mid, front, side in spots:
        w, d = cells(name)
        corners, c, v, _ = _rect(st, s_mid, front, w, d, "sea")
        if any(overlaps(corners, o["corners"]) for o in out):
            raise ValueError(f"바다 쪽 시설 {name} 이(가) 다른 시설과 겹칩니다")
        if name != "IlsanStreamBridge" and overlaps(corners, lay.stream_poly):
            raise ValueError(f"바다 쪽 시설 {name} 이(가) 하천과 겹칩니다")
        out.append(item(name, side, corners, c, v, s_mid=s_mid, width=w, depth=d, front_offset=front))
    return out


def plan_props(st, lots, layout=None, seed=3):
    """부지 없는 소품: 회전교차로 중앙섬, 해송 줄, 난간 토막, 노면 글자 (정면 = 도로 쪽)"""
    lay = layout or Layout(st)
    rng = np.random.default_rng(seed)
    out = [item("IlsanRoundabout", "center", rect(lay.road_center - lay.n * 8.0, lay.n, 16.0, 16.0)[0],
                lay.road_center, lay.n)]
    sea = [it["corners"] for it in lots if it["side"] in ("sea", "beach")]

    def frame(s, off):
        (x, y), n, _ = st.frame(s, off)
        return np.array([x, y]), np.asarray(n)

    def blocked(pt, margin):
        if any(near(c, pt, margin) for c in sea) or near(lay.stream_poly, pt, margin):
            return True
        lx, _ = lay.lateral(pt)
        return abs(lx) < PLAZA_HALF + margin

    # 해송: 백사장 가장자리를 따라 약 9 m 간격 (시설 · 하천 · 광장 축 앞은 비움)
    s, k = 6.0, 0
    while s < st.length - 6.0:
        off = PINE_OFFSET + rng.uniform(-1.2, 1.2)
        pt, n = frame(s, off)
        if not blocked(pt, 5.0):
            name = "IlsanPine01" if k % 3 != 2 else "IlsanPine02"
            out.append(item(name, "prop", rect(pt - (-n) * 4.0, -n, 8.0, 8.0)[0], pt, -n, s_mid=s))
            k += 1
        s += 9.0 + rng.uniform(-1.5, 1.5)
    # 난간: 8 m 토막을 이어 붙임. 시설 앞 · 광장 입구 · 하천은 비우고 64 m 마다 해변 내려가는 틈 2 m
    rail_pts = st.at_offset(RAIL_OFFSET)
    arc = S.cumulative(rail_pts)
    a = 4.0
    seg = 0
    while a + 8.0 < arc[-1] - 4.0:
        p0 = np.array([np.interp(a, arc, rail_pts[:, i]) for i in range(2)])
        p1 = np.array([np.interp(a + 8.0, arc, rail_pts[:, i]) for i in range(2)])
        mid = (p0 + p1) / 2
        tdir = (p1 - p0) / np.linalg.norm(p1 - p0)
        v = np.array([-tdir[1], tdir[0]])                 # 로컬 +X = 진행 방향 이 되도록 v 를 잡는다
        if v @ (frame(np.interp(a, arc, st.s), 0)[1]) > 0:
            v = -v                                        # 뒤(+Y)가 바다 쪽
        lx, _ = lay.lateral(mid)
        gap = seg % 8 == 7
        if not gap and not blocked(p0, 1.0) and not blocked(p1, 1.0) and abs(lx) > 20.0:
            out.append(item("IlsanBeachRail", "prop", rect(mid - v * 4.0, v, 8.0, 8.0)[0], mid, v,
                            s_mid=float(np.interp(a + 4.0, arc, st.s))))
        a += 8.0 + (2.0 if gap else 0.0)
        seg += 1
    # 노면 글자: 광장(회전교차로) 앞 양방향 차로 — 글자 아래쪽(-Y)이 다가오는 차를 본다
    for ds, lane in ((-38.0, ROAD_CENTER + 2.4), (38.0, ROAD_CENTER - 2.4)):
        s = lay.s_p + ds
        pt, n = frame(s, lane)
        nxt, _ = frame(s + (1.0 if ds < 0 else -1.0), lane)
        v = (nxt - pt) / np.linalg.norm(nxt - pt)         # 진행 방향
        out.append(item("IlsanRoadMarking01", "prop", rect(pt - v * 4.0, v, 8.0, 8.0)[0], pt, v, s_mid=s))
    return out


def to_game(items, st, dem, to_xz, ground):
    """게임 좌표 (중심 x, z), 회전, 지면 높이, 사각형 모서리를 붙인다.
    ground(gx, gz) -> 그 위치의 게임 지형 높이 (하이트맵에서 샘플)."""
    for it in items:
        c, v = it["center"], it["v"]
        gx, gz = to_xz(*S.Street.latlon(dem, *c))
        tip = to_xz(*S.Street.latlon(dem, *(c + v)))
        vx, vz = tip[0] - gx, tip[1] - gz
        it["game_x"], it["game_z"] = round(gx, 2), round(gz, 2)
        it["rotation_deg"] = round(math.degrees(math.atan2(-vx, -vz)) % 360, 1)   # 정면(-v)이 향하는 방위
        it["ground_m"] = round(float(ground(gx, gz)), 2)
        it["corners_game_xz"] = [[round(p, 2), round(q, 2)] for p, q in
                                 (to_xz(*S.Street.latlon(dem, *xy)) for xy in it["corners"])]
    return items
