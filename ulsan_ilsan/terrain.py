"""울산 동구 일산동 지형 처리 (Blender 비의존, numpy 만 사용).

DEM 격자는 북쪽 행이 먼저 오는 (rows, cols) 배열이고, 로컬 좌표는
영역 중심을 원점으로 x = 동쪽(m), y = 북쪽(m) 이다.
"""

import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EARTH_RADIUS = 6371008.8

# 토지 피복 분류
SEA, BEACH, ROCK, PARK_FOREST, HILL_FOREST, URBAN, GRASS = range(7)
CLASS_NAMES = ("바다", "모래사장", "해안 암석", "대왕암공원 송림", "산림", "시가지", "초지")

# 영역 경계 (위도/경도, 대략값). (south, north, west, east)
BEACH_BOX = (35.4950, 35.5010, 129.4265, 129.4350)   # 일산해수욕장 백사장
PARK_BOX = (35.4880, 35.4975, 129.4355, 129.4475)    # 대왕암공원 반도

# 랜드마크 (위도, 경도). 위치는 지도·DEM 지형으로 맞춘 근사값이다.
LANDMARKS = {
    "울기등대": (35.4935, 129.4412),
    "대왕암": (35.4914, 129.4460),
    "대왕교_육지쪽": (35.4921, 129.4449),
    "일산해수욕장": (35.4980, 129.4305),
}


class Dem:
    def __init__(self, heights, north, south, west, east):
        self.h = np.asarray(heights, dtype=np.float32)
        self.north, self.south, self.west, self.east = north, south, west, east
        self.lat0 = (north + south) / 2
        self.lon0 = (west + east) / 2

    @classmethod
    def load(cls, folder=os.path.join(HERE, "data"), name="ilsan_dem"):
        with open(os.path.join(folder, name + ".json"), encoding="utf-8") as f:
            meta = json.load(f)
        heights = np.load(os.path.join(folder, name + ".npy"))
        return cls(heights, meta["north"], meta["south"], meta["west"], meta["east"])

    @property
    def shape(self):
        return self.h.shape

    def to_local(self, lat, lon):
        """위경도 -> 로컬 (x 동쪽, y 북쪽) 미터. 수 km 범위라 등장방형 근사로 충분하다."""
        x = math.radians(lon - self.lon0) * EARTH_RADIUS * math.cos(math.radians(self.lat0))
        y = math.radians(lat - self.lat0) * EARTH_RADIUS
        return x, y

    def extent(self):
        """(x_min, x_max, y_min, y_max) 미터"""
        x0, y0 = self.to_local(self.south, self.west)
        x1, y1 = self.to_local(self.north, self.east)
        return x0, x1, y0, y1

    def grid_xy(self):
        """각 격자점의 로컬 좌표 (X, Y) 배열. 행 0 이 북쪽."""
        rows, cols = self.shape
        x0, x1, y0, y1 = self.extent()
        xs = np.linspace(x0, x1, cols)
        ys = np.linspace(y1, y0, rows)
        return np.meshgrid(xs, ys)

    def grid_latlon(self):
        rows, cols = self.shape
        lons = np.linspace(self.west, self.east, cols)
        lats = np.linspace(self.north, self.south, rows)
        return np.meshgrid(lats, lons, indexing="ij")

    def cell_size(self):
        """(dx, dy) 미터"""
        rows, cols = self.shape
        x0, x1, y0, y1 = self.extent()
        return (x1 - x0) / (cols - 1), (y1 - y0) / (rows - 1)

    def sample(self, lat, lon):
        """위경도 위치의 고도 (쌍선형 보간)"""
        rows, cols = self.shape
        r = (self.north - lat) / (self.north - self.south) * (rows - 1)
        c = (lon - self.west) / (self.east - self.west) * (cols - 1)
        r = min(max(r, 0.0), rows - 1.0)
        c = min(max(c, 0.0), cols - 1.0)
        r0, c0 = int(r), int(c)
        r1, c1 = min(r0 + 1, rows - 1), min(c0 + 1, cols - 1)
        fr, fc = r - r0, c - c0
        top = self.h[r0, c0] * (1 - fc) + self.h[r0, c1] * fc
        bot = self.h[r1, c0] * (1 - fc) + self.h[r1, c1] * fc
        return float(top * (1 - fr) + bot * fr)

    def upsampled(self, factor):
        """격자를 factor 배로 촘촘하게 (쌍선형) 만든 새 Dem"""
        return Dem(upsample(self.h, factor), self.north, self.south, self.west, self.east)


def upsample(a, factor):
    """(R, C) -> ((R-1)*factor+1, (C-1)*factor+1) 쌍선형 보간"""
    a = np.asarray(a, dtype=np.float32)
    if factor == 1:
        return a.copy()
    rows, cols = a.shape
    r = np.linspace(0, rows - 1, (rows - 1) * factor + 1)
    c = np.linspace(0, cols - 1, (cols - 1) * factor + 1)
    r0 = np.minimum(r.astype(int), rows - 2)
    c0 = np.minimum(c.astype(int), cols - 2)
    fr = (r - r0)[:, None]
    fc = (c - c0)[None, :]
    a00 = a[r0][:, c0]
    a01 = a[r0][:, c0 + 1]
    a10 = a[r0 + 1][:, c0]
    a11 = a[r0 + 1][:, c0 + 1]
    return (a00 * (1 - fr) * (1 - fc) + a01 * (1 - fr) * fc
            + a10 * fr * (1 - fc) + a11 * fr * fc).astype(np.float32)


def smooth(a, passes=1):
    """3x3 평균 필터 (가장자리는 복제)"""
    a = np.asarray(a, dtype=np.float32)
    for _ in range(passes):
        p = np.pad(a, 1, mode="edge")
        a = sum(p[i:i + a.shape[0], j:j + a.shape[1]] for i in range(3) for j in range(3)) / 9.0
    return a


def slope(h, dx, dy):
    """경사 (rise/run, 무차원)"""
    gy, gx = np.gradient(h, dy, dx)
    return np.hypot(gx, gy)


def distance_to(mask, dx, dy):
    """mask 가 True 인 칸까지의 대략적 거리(m). 2-pass 챔퍼 거리 변환."""
    big = 1e9
    d = np.where(mask, 0.0, big)
    dd = math.hypot(dx, dy)
    rows, cols = d.shape
    for r in range(rows):  # 위 -> 아래, 왼 -> 오
        row = d[r]
        if r > 0:
            prev = d[r - 1]
            row = np.minimum(row, prev + dy)
            row[1:] = np.minimum(row[1:], prev[:-1] + dd)
            row[:-1] = np.minimum(row[:-1], prev[1:] + dd)
        for c in range(1, cols):
            if row[c - 1] + dx < row[c]:
                row[c] = row[c - 1] + dx
        d[r] = row
    for r in range(rows - 1, -1, -1):  # 아래 -> 위, 오 -> 왼
        row = d[r]
        if r < rows - 1:
            nxt = d[r + 1]
            row = np.minimum(row, nxt + dy)
            row[1:] = np.minimum(row[1:], nxt[:-1] + dd)
            row[:-1] = np.minimum(row[:-1], nxt[1:] + dd)
        for c in range(cols - 2, -1, -1):
            if row[c + 1] + dx < row[c]:
                row[c] = row[c + 1] + dx
        d[r] = row
    return d


def in_box(lat, lon, box):
    south, north, west, east = box
    return (lat >= south) & (lat <= north) & (lon >= west) & (lon <= east)


def sea_mask(h):
    """Copernicus DEM 은 바다를 정확히 0 으로 채운다. 음수 값(해안 오류)도 바다로 본다."""
    return h <= 0.0


def classify(dem):
    """격자별 토지 피복 분류와 해안 거리(m)를 돌려준다."""
    h = dem.h
    dx, dy = dem.cell_size()
    lat, lon = dem.grid_latlon()
    sea = sea_mask(h)
    coast = distance_to(sea, dx, dy)
    s = slope(h, dx, dy)

    cls = np.full(h.shape, GRASS, dtype=np.int8)
    cls[(h < 70) & (s < 0.25)] = URBAN
    cls[(h >= 45) | (s >= 0.35)] = HILL_FOREST
    park = in_box(lat, lon, PARK_BOX)
    cls[park] = PARK_FOREST
    cls[(coast < 25) & ((s > 0.3) | park)] = ROCK
    # 대왕암 바위섬 일대는 나무 없는 화강암
    rx, ry = dem.to_local(*LANDMARKS["대왕암"])
    X, Y = dem.grid_xy()
    cls[np.hypot(X - rx, Y - ry) < 90] = ROCK
    cls[in_box(lat, lon, BEACH_BOX) & (coast < 70) & (h < 8)] = BEACH
    cls[sea] = SEA
    return cls, coast


def seabed(h, dx, dy, max_depth=25.0, gradient=0.03):
    """바다 칸을 육지에서 멀어질수록 깊게 (Copernicus 해수면은 평평한 0)"""
    sea = sea_mask(h)
    offshore = distance_to(~sea, dx, dy)
    depth = np.minimum(1.0 + offshore * gradient, max_depth)
    return np.where(sea, -depth, h).astype(np.float32)


def prepare(dem, upsample=3, smooth_passes=2):
    """원본 30 m 격자에서 바다를 해저 지형으로 바꾼 뒤 보간한다.

    해수면(0)을 사이에 둔 육지/해저 값이 함께 보간되므로 해안선이 계단 모양이 아니라
    부드러운 곡선(0 m 등고선)이 된다.
    """
    dx, dy = dem.cell_size()
    h = seabed(dem.h, dx, dy)
    out = Dem(h, dem.north, dem.south, dem.west, dem.east)
    if upsample > 1:
        out = out.upsampled(upsample)
        out.h = smooth(out.h, smooth_passes)
    return out


def scatter(mask, dem, spacing, seed=0, jitter=0.45):
    """mask 영역에 지터 격자로 점을 뿌린다. (N, 3) 로컬 좌표 (x, y, 지면고도)"""
    rng = np.random.default_rng(seed)
    x0, x1, y0, y1 = dem.extent()
    xs = np.arange(x0 + spacing / 2, x1, spacing)
    ys = np.arange(y0 + spacing / 2, y1, spacing)
    gx, gy = np.meshgrid(xs, ys)
    gx = gx + rng.uniform(-jitter, jitter, gx.shape) * spacing
    gy = gy + rng.uniform(-jitter, jitter, gy.shape) * spacing
    rows, cols = dem.shape
    c = np.clip(np.round((gx - x0) / (x1 - x0) * (cols - 1)).astype(int), 0, cols - 1)
    r = np.clip(np.round((y1 - gy) / (y1 - y0) * (rows - 1)).astype(int), 0, rows - 1)
    keep = mask[r, c]
    return np.stack([gx[keep], gy[keep], dem.h[r[keep], c[keep]]], axis=1)


def building_lots(cls, coast, dem, spacing=30.0, seed=1):
    """시가지 칸에 가상 건물 (x, y, z, 가로, 세로, 높이, 회전) 배열.

    실제 건물 위치가 아니라 OSM 없이 분위기를 내기 위한 절차적 배치다.
    해안에서 가까울수록 낮은 상가, 내륙일수록 높은 아파트가 섞이도록 한다.
    """
    rng = np.random.default_rng(seed)
    lots = scatter((cls == URBAN) & (coast > 35), dem, spacing, seed=seed, jitter=0.2)
    n = len(lots)
    if n == 0:
        return np.zeros((0, 7))
    rows, cols = dem.shape
    x0, x1, y0, y1 = dem.extent()
    c = np.clip(np.round((lots[:, 0] - x0) / (x1 - x0) * (cols - 1)).astype(int), 0, cols - 1)
    r = np.clip(np.round((y1 - lots[:, 1]) / (y1 - y0) * (rows - 1)).astype(int), 0, rows - 1)
    inland = np.clip(coast[r, c] / 600.0, 0, 1)
    tall = rng.random(n) < 0.03 + 0.12 * inland
    width = rng.uniform(9, 18, n)
    depth = rng.uniform(9, 16, n)
    height = np.where(tall, rng.uniform(30, 60, n), rng.uniform(4, 13, n))
    width[tall] = rng.uniform(30, 45, tall.sum())   # 판상형 아파트
    depth[tall] = rng.uniform(12, 15, tall.sum())
    rot = rng.choice([0.0, math.pi / 2], n) + rng.uniform(-0.15, 0.15, n)
    # 아파트는 이웃 칸과 겹치기 쉬우니 일부만 남긴다
    keep = ~tall | (rng.random(n) < 0.5)
    return np.column_stack([lots, width, depth, height, rot])[keep]
