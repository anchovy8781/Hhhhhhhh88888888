"""일산해수욕장 앞 거리(일산지 거리)의 기하 계산 (Blender 비의존, numpy 만 사용).

해안선을 DEM 의 0 m 경계에서 추적하고, 그 곡선을 따라 모래사장 → 방파 호안 →
산책로 → 도로 → 인도 → 상가 순서의 단면을 쓸어(sweep) 만든다.
오프셋은 해안선에서 육지 쪽으로 잰 거리(m)이다. 음수는 바다 쪽.
"""

import numpy as np

import terrain as T

# 해안선을 추적할 범위 (일산해수욕장 백사장, 위경도)
SHORE_BOX = (35.4952, 35.5003, 129.4290, 129.4350)

# 거리 단면 (해안선 기준 육지 쪽 오프셋, m)
SAND_END = 44.0       # 모래사장 끝 = 호안(옹벽)
PROMENADE_END = 53.0  # 해변 산책로(보도)
ROAD_END = 63.0       # 왕복 2차로
SIDEWALK_END = 67.0   # 상가 앞 인도
FRONTAGE = 68.0       # 건물 전면선
BACK_END = 110.0      # 건물 뒤 지면 끝


def trace_shoreline(dem, box=SHORE_BOX):
    """box 안의 각 행에서 가장 동쪽의 육지→바다 경계를 찾아 북→남 순서의 (x, y) 점열로 돌려준다."""
    X, Y = dem.grid_xy()
    lat, lon = dem.grid_latlon()
    south, north, west, east = box
    pts = []
    for r in range(dem.shape[0]):
        if not south <= lat[r, 0] <= north:
            continue
        cols = np.where((lon[r] >= west) & (lon[r] <= east))[0]
        h = dem.h[r, cols]
        cross = np.where((h[:-1] > 0) & (h[1:] <= 0))[0]
        if len(cross) == 0:
            continue
        i = cross[-1]
        h0, h1 = h[i], h[i + 1]
        f = h0 / (h0 - h1)  # 0 m 등고선 위치 선형 보간
        x = X[r, cols[i]] + f * (X[r, cols[i + 1]] - X[r, cols[i]])
        pts.append((x, Y[r, 0]))
    return np.array(pts, dtype=np.float64)


def cumulative(poly):
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def resample(poly, step):
    """곡선을 step(m) 간격으로 다시 샘플링"""
    s = cumulative(poly)
    st = np.linspace(0, s[-1], max(int(round(s[-1] / step)), 1) + 1)
    return np.stack([np.interp(st, s, poly[:, 0]), np.interp(st, s, poly[:, 1])], axis=1)


def smooth_poly(poly, window=9, passes=3):
    """양 끝점을 유지하는 이동 평균"""
    p = poly.copy()
    k = window // 2
    for _ in range(passes):
        pad = np.concatenate([np.repeat(p[:1], k, 0), p, np.repeat(p[-1:], k, 0)])
        kernel = np.ones(window) / window
        p = np.stack([np.convolve(pad[:, i], kernel, mode="valid") for i in range(2)], axis=1)
    return p


def normals(poly):
    """진행 방향의 오른쪽 단위 법선"""
    t = np.gradient(poly, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    return np.stack([t[:, 1], -t[:, 0]], axis=1)


class Street:
    """해안선 곡선과 육지 쪽 법선, 도로 높이 프로파일"""

    def __init__(self, dem, step=2.0):
        raw = trace_shoreline(dem)
        if len(raw) < 4:
            raise ValueError("해안선을 찾지 못했습니다")
        self.poly = smooth_poly(resample(raw, step))
        self.n = normals(self.poly)
        # 법선이 육지(높은 쪽)를 향하도록
        mid = len(self.poly) // 2
        inland = self.poly[mid] + self.n[mid] * 80
        seaward = self.poly[mid] - self.n[mid] * 80
        if dem.sample(*self.latlon(dem, *inland)) < dem.sample(*self.latlon(dem, *seaward)):
            self.n = -self.n
        self.s = cumulative(self.poly)
        self.length = float(self.s[-1])
        road = np.array([dem.sample(*self.latlon(dem, *p))
                         for p in self.at_offset((PROMENADE_END + ROAD_END) / 2)])
        prof = np.convolve(np.pad(road, 20, mode="edge"), np.ones(41) / 41, mode="valid")
        self.road_z = np.maximum(prof, 3.0)

    @staticmethod
    def latlon(dem, x, y):
        lat = dem.lat0 + np.degrees(y / T.EARTH_RADIUS)
        lon = dem.lon0 + np.degrees(x / (T.EARTH_RADIUS * np.cos(np.radians(dem.lat0))))
        return float(lat), float(lon)

    def at_offset(self, d):
        return self.poly + self.n * d

    def frame(self, station, offset=0.0):
        """station(m) 위치의 (점 xy, 법선, 도로 높이)"""
        st = float(np.clip(station, 0, self.length))
        p = np.array([np.interp(st, self.s, self.poly[:, i]) for i in range(2)])
        n = np.array([np.interp(st, self.s, self.n[:, i]) for i in range(2)])
        n /= np.linalg.norm(n)
        return p + n * offset, n, float(np.interp(st, self.s, self.road_z))

    def strip(self, a, b, za, zb, s0=None, s1=None, step=None):
        """오프셋 a→b 사이의 띠 메시. za, zb 는 상수 또는 도로 높이 기준 함수(f(road_z)).

        s0, s1 로 일부 구간만 만들 수 있다. 반환: (verts (2K,3), faces (K-1,4))
        """
        if s0 is None and s1 is None:
            P, N, R = self.poly, self.n, self.road_z
        else:
            s0 = 0.0 if s0 is None else s0
            s1 = self.length if s1 is None else s1
            k = max(int(np.ceil((s1 - s0) / (step or 2.0))), 1) + 1
            st = np.linspace(s0, s1, k)
            P = np.stack([np.interp(st, self.s, self.poly[:, i]) for i in range(2)], axis=1)
            N = np.stack([np.interp(st, self.s, self.n[:, i]) for i in range(2)], axis=1)
            R = np.interp(st, self.s, self.road_z)
        ZA = za(R) if callable(za) else np.full(len(P), za, dtype=np.float64)
        ZB = zb(R) if callable(zb) else np.full(len(P), zb, dtype=np.float64)
        A = np.column_stack([P + N * a, ZA])
        B = np.column_stack([P + N * b, ZB])
        k = len(P)
        verts = np.concatenate([A, B])
        i = np.arange(k - 1)
        faces = np.stack([i, i + k, i + k + 1, i + 1], axis=1)  # a<b 일 때 위(+Z) 법선
        return verts, faces

    def project(self, points, chunk=4096):
        """점들의 (station, offset). 곡선 양 끝 바깥으로 투영되는 점은 interior=False."""
        a = self.poly[:-1]
        ab = np.diff(self.poly, axis=0)
        l2 = (ab ** 2).sum(1)
        seg = np.sqrt(l2)
        nseg = (self.n[:-1] + self.n[1:]) / 2
        out_s = np.empty(len(points))
        out_d = np.empty(len(points))
        interior = np.empty(len(points), dtype=bool)
        for c in range(0, len(points), chunk):
            p = points[c:c + chunk, None, :]
            t_raw = ((p - a) * ab).sum(-1) / l2
            t = np.clip(t_raw, 0, 1)
            proj = a + t[..., None] * ab
            d2 = ((p - proj) ** 2).sum(-1)
            k = d2.argmin(1)
            rows = np.arange(len(k))
            tk = t[rows, k]
            out_s[c:c + chunk] = self.s[k] + tk * seg[k]
            diff = p[:, 0, :] - proj[rows, k]
            sign = np.sign((diff * nseg[k]).sum(1))
            out_d[c:c + chunk] = sign * np.sqrt(d2[rows, k])
            interior[c:c + chunk] = ~(((k == 0) & (t_raw[rows, k] < 0))
                                      | ((k == len(seg) - 1) & (t_raw[rows, k] > 1)))
        return out_s, out_d, interior


# ---------------------------------------------------------------------------
# 상가 배치
# ---------------------------------------------------------------------------

SHOP_TYPES = {
    # 종류: (비율, 층수 범위, 폭 범위, 간판 후보)
    "횟집": (0.42, (2, 4), (9, 14), ["바다횟집", "해송횟집", "갈매기횟집", "동해물회", "파도횟집", "자연산활어"]),
    "카페": (0.26, (2, 4), (10, 16), ["카페 파도", "오션뷰", "BAKERY CAFE", "해변카페", "COFFEE"]),
    "숙박": (0.14, (5, 8), (12, 16), ["호텔 일산", "모텔 바다", "게스트하우스"]),
    "상가": (0.18, (2, 3), (8, 11), ["편의점", "조개구이", "대게 전문", "치킨"]),
}


def lay_lots(length, seed=7, margin=12.0, alley_gap=(55.0, 85.0), alley_width=7.0):
    """거리 길이를 따라 건물 구획과 골목을 나눈다.

    반환: [{"s0", "s1", "kind", "floors", "name"} ...], [골목 중앙 station ...]
    """
    rng = np.random.default_rng(seed)
    kinds = list(SHOP_TYPES)
    probs = np.array([SHOP_TYPES[k][0] for k in kinds])
    probs /= probs.sum()
    lots, alleys = [], []
    s = margin
    next_alley = s + rng.uniform(*alley_gap)
    while True:
        if s >= next_alley:
            alleys.append(s + alley_width / 2)
            s += alley_width
            next_alley = s + rng.uniform(*alley_gap)
            continue
        kind = kinds[rng.choice(len(kinds), p=probs)]
        _, floors, widths, names = SHOP_TYPES[kind]
        w = rng.uniform(*widths)
        if s + w > length - margin:
            break
        lots.append({
            "s0": s, "s1": s + w, "kind": kind,
            "floors": int(rng.integers(floors[0], floors[1] + 1)),
            "name": names[int(rng.integers(len(names)))],
            "depth": float(rng.uniform(12, 18)),
        })
        s += w + rng.uniform(0.0, 1.2)
    return lots, alleys
