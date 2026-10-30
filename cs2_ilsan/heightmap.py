"""시티즈: 스카이라인 2 맵 에디터용 실측 하이트맵 (울산 동구 일산지 중심).

    pip install numpy tifffile imagecodecs
    python3 heightmap.py                 # -> Heightmaps/ 에 PNG 3장 + 배치표

출력
  Ilsan_Heightmap.png   4096x4096 16-bit, 14.336 km (3.5 m/px)  - 플레이 영역
  Ilsan_Worldmap.png    4096x4096 16-bit, 57.344 km (14 m/px)   - 바깥 경관, 가운데 1024 px = 플레이 영역
  Ilsan_Overlay.png     4096x4096 RGBA  - 해안선 · 도로 중심선 · 에셋 부지 · 하천 · 해송 · 난간 참고 이미지
  Ilsan_Placement.json  에셋별 게임 좌표 · 회전 · 지면 높이 (부지 + 소품)
  Ilsan_Map.json        해수면 · 높이 배율 · 게임 좌표의 거리 위치 · 광장 · 하천 · 회전교차로

광장 남쪽 하천은 하이트맵에 폭 8 m · 깊이 1.8 m 물길로 파 둔다 (하구는 해수면 아래라 게임에서 바닷물이 들어온다).

CS2 하이트맵 규격(4096², 16-bit, 플레이 14.336 km, 월드 57.344 km, 높이 배율 4096 m)은
Terraining Heightmap Generator 의 CS2 설정과 Colossal Order 맵 에디터 개발 일지 기준이다.
"""

import argparse
import json
import math
import os
import sys
import urllib.request

import numpy as np


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ulsan_ilsan"))
import street as S  # noqa: E402
import terrain as T  # noqa: E402

import catalog  # noqa: E402
import placement  # noqa: E402
import pngio  # noqa: E402

PLAY_SIZE = 14336.0      # m
WORLD_SIZE = 57344.0     # m
RES = 4096
HEIGHT_SCALE = 4096.0    # m, 16-bit 전체 범위
SEA_LEVEL = 40.0         # 게임 안 해수면 높이 (해저를 40 m 까지 표현하기 위한 여유)
MAX_DEPTH = 38.0         # 해저 최대 깊이
SHELF_SLOPE = 1 / 45.0   # 해안에서 바깥으로 깊어지는 기울기 (해저 지형은 추정)

TILE = "Copernicus_DSM_COG_10_N35_00_E129_00_DEM"
TILE_URL = f"https://copernicus-dem-30m.s3.amazonaws.com/{TILE}/{TILE}.tif"
TILE_LAT, TILE_LON = 36.0, 129.0


def load_tile(cache):
    import tifffile

    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, TILE + ".tif")
    if not os.path.exists(path):
        print("다운로드:", TILE_URL)
        urllib.request.urlretrieve(TILE_URL, path)
    return tifffile.imread(path).astype(np.float32)


def street_center():
    """일산지 거리(해변 도로) 중간 지점의 위경도"""
    dem = T.prepare(T.Dem.load(), 3)
    st = S.Street(dem)
    (x, y), _, _ = st.frame(st.length / 2, (S.PROMENADE_END + S.ROAD_END) / 2)
    return S.Street.latlon(dem, x, y), st, dem


def window(lat0, lon0, size):
    """영역을 덮는 타일 행/열 범위 (여유 4 px)"""
    m_lat = math.pi / 180 * T.EARTH_RADIUS
    dlat = size / 2 / m_lat
    dlon = size / 2 / (m_lat * math.cos(math.radians(lat0)))
    return dlat, dlon


def seabed_tile(tile, lat0, lon0, size, step=1):
    """원본 30 m 격자에서 바다(0)를 해저 지형으로 바꾼 잘라낸 타일과 그 원점(행, 열).

    원본 해상도에서 해저를 만든 뒤 보간해야 0 m 해안선이 계단 모양이 되지 않는다.
    step>1 이면 거리 계산만 성기게 한다 (월드맵용).
    """
    rows, cols = tile.shape
    dlat, dlon = window(lat0, lon0, size)
    r0 = int((TILE_LAT - (lat0 + dlat)) * rows) - 4
    r1 = int((TILE_LAT - (lat0 - dlat)) * rows) + 5
    c0 = int((lon0 - dlon - TILE_LON) * cols) - 4
    c1 = int((lon0 + dlon - TILE_LON) * cols) + 5
    if r0 < 0 or c0 < 0 or r1 > rows or c1 > cols:
        raise ValueError("영역이 DEM 타일 밖으로 나갑니다")
    h = tile[r0:r1, c0:c1].copy()
    cell_y = T.EARTH_RADIUS * math.pi / 180 / rows
    cell_x = cell_y * math.cos(math.radians(lat0))
    sea = h <= 0.0
    small = sea[::step, ::step]
    dist = T.distance_to(~small, cell_x * step, cell_y * step)
    if step > 1:
        dist = np.repeat(np.repeat(dist, step, 0), step, 1)[:h.shape[0], :h.shape[1]]
    depth = np.minimum(1.0 + dist * SHELF_SLOPE, MAX_DEPTH)
    return np.where(sea, -depth, h).astype(np.float32), r0, c0


def sample_grid(tile, lat0, lon0, size, res, step=1):
    """중심(lat0, lon0), 한 변 size(m)의 북쪽이 위인 정사각 격자에 (해저 처리한) DEM 을 쌍선형 샘플링.
    픽셀 중심 기준. 반환 (res, res), 행 0 = 북쪽."""
    rows, cols = tile.shape
    sub, sr, sc = seabed_tile(tile, lat0, lon0, size, step)
    half = size / 2
    px = (np.arange(res) + 0.5) / res * size - half
    m_lat = math.pi / 180 * T.EARTH_RADIUS
    m_lon = m_lat * math.cos(math.radians(lat0))
    lats = lat0 - px / m_lat          # 행: 북 -> 남
    lons = lon0 + px / m_lon
    r = (TILE_LAT - lats) * rows - 0.5 - sr
    c = (lons - TILE_LON) * cols - 0.5 - sc
    r0 = np.floor(r).astype(int).clip(0, sub.shape[0] - 2)
    c0 = np.floor(c).astype(int).clip(0, sub.shape[1] - 2)
    fr = (r - r0)[:, None]
    fc = (c - c0)[None, :]
    out = np.empty((res, res), dtype=np.float32)
    for i in range(0, res, 512):  # 메모리 절약
        sl = slice(i, i + 512)
        a = sub[r0[sl, None], c0[None, :]]
        b = sub[r0[sl, None], c0[None, :] + 1]
        cc = sub[r0[sl, None] + 1, c0[None, :]]
        d = sub[r0[sl, None] + 1, c0[None, :] + 1]
        f = fr[sl]
        out[sl] = (a * (1 - f) * (1 - fc) + b * (1 - f) * fc + cc * f * (1 - fc) + d * f * fc)
    return out


def to_u16(h):
    v = (h + SEA_LEVEL) / HEIGHT_SCALE * 65535.0
    return np.clip(np.round(v), 0, 65535).astype(">u2")


def game_xy(lat, lon, lat0, lon0):
    """게임 월드 좌표 (x 동쪽, z 북쪽, m). 맵 중심이 원점."""
    m_lat = math.pi / 180 * T.EARTH_RADIUS
    return (lon - lon0) * m_lat * math.cos(math.radians(lat0)), (lat - lat0) * m_lat


def ground_sampler(play):
    """게임 좌표 (x 동, z 북) -> 하이트맵 지형의 게임 높이 (해수면 = SEA_LEVEL). 쌍선형."""
    k = RES / PLAY_SIZE

    def ground(gx, gz):
        c = gx * k + RES / 2 - 0.5
        r = RES / 2 - gz * k - 0.5
        r0, c0 = int(np.floor(r)), int(np.floor(c))
        fr, fc = r - r0, c - c0
        a, b = play[r0, c0], play[r0, c0 + 1]
        cc, d = play[r0 + 1, c0], play[r0 + 1, c0 + 1]
        h = a * (1 - fr) * (1 - fc) + b * (1 - fr) * fc + cc * fr * (1 - fc) + d * fr * fc
        return float(h) + SEA_LEVEL
    return ground


STREAM_DEPTH = 1.8      # 하천 물길 깊이 (m)
STREAM_BED = 4.0        # 물길 바닥 반폭 (m)
STREAM_BANK = 8.0       # 둑 경사 폭 (m)


def carve_stream(h, line_xz):
    """하이트맵(행 0 = 북)에 하천 물길을 판다. line_xz = 게임 좌표 (하구, 상류 끝). 바다(0 m 이하)는 그대로."""
    (x0, z0), (x1, z1) = line_xz
    k = RES / PLAY_SIZE
    pad = int((STREAM_BED + STREAM_BANK) * k) + 2
    c0 = int(min(x0, x1) * k + RES / 2) - pad
    c1 = int(max(x0, x1) * k + RES / 2) + pad
    r0 = int(RES / 2 - max(z0, z1) * k) - pad
    r1 = int(RES / 2 - min(z0, z1) * k) + pad
    rr, cc = np.mgrid[r0:r1 + 1, c0:c1 + 1]
    gx = (cc + 0.5 - RES / 2) / k
    gz = (RES / 2 - rr - 0.5) / k
    ax, az = x1 - x0, z1 - z0
    t = np.clip(((gx - x0) * ax + (gz - z0) * az) / (ax * ax + az * az), 0, 1)
    d = np.hypot(gx - (x0 + t * ax), gz - (z0 + t * az))
    w = np.clip(1 - (d - STREAM_BED) / STREAM_BANK, 0, 1)
    w = w * w * (3 - 2 * w)
    sub = h[r0:r1 + 1, c0:c1 + 1]
    h[r0:r1 + 1, c0:c1 + 1] = np.where(sub > 0, sub - STREAM_DEPTH * w, sub)
    return h


def draw_overlay(h, st, dem, lat0, lon0, items, extras=None):
    """해안선(청록) · 도로 중심선(노랑) · 에셋 부지(종류별 색 윤곽, 앞선은 흰색) · 하천(파랑) ·
    해송(초록 점) · 난간(진회색 선) · 회전교차로(빨강 원)를 그린 참고 이미지"""
    rgba = np.zeros((RES, RES, 4), dtype=np.uint8)
    sea = h <= 0
    edge = sea & ~(np.roll(sea, 1, 0) & np.roll(sea, -1, 0) & np.roll(sea, 1, 1) & np.roll(sea, -1, 1))
    rgba[edge] = (0, 220, 255, 255)
    px_per_m = RES / PLAY_SIZE

    def to_px(gx, gz):
        return gx * px_per_m + RES / 2, RES / 2 - gz * px_per_m

    def line(p0, p1, color):
        n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1])) * 2) + 1
        for t in np.linspace(0, 1, n):
            x = int(round(p0[0] + (p1[0] - p0[0]) * t))
            y = int(round(p0[1] + (p1[1] - p0[1]) * t))
            if 0 <= x < RES and 0 <= y < RES:
                rgba[y, x] = color

    colors = {"횟집": (255, 80, 60, 255), "대게": (255, 40, 120, 255), "조개구이": (255, 170, 0, 255),
              "카페": (170, 110, 60, 255), "치킨": (255, 230, 60, 255), "상가": (80, 200, 90, 255),
              "근린상가": (60, 160, 255, 255), "시장": (40, 90, 255, 255), "숙박": (200, 80, 220, 255),
              "펜션": (150, 220, 255, 255), "주거": (200, 200, 200, 255), "화장실": (0, 255, 160, 255),
              "호텔": (255, 120, 255, 255), "상업빌딩": (0, 220, 255, 255), "청년공간": (255, 140, 0, 255),
              "광장": (230, 230, 230, 255), "조형물": (255, 255, 255, 255), "다리": (120, 160, 255, 255)}
    extras = extras or {}
    if "stream_xz" in extras:
        a, b = (to_px(*p) for p in extras["stream_xz"])
        for o in (-1, 0, 1):
            line((a[0] + o, a[1]), (b[0] + o, b[1]), (40, 120, 255, 255))
    prev = None
    for s in np.arange(0, st.length, 1.0):
        (x, y), _, _ = st.frame(s, placement.ROAD_CENTER)
        p = to_px(*game_xy(*S.Street.latlon(dem, x, y), lat0, lon0))
        if prev is not None:
            line(prev, p, (255, 220, 0, 255))
        prev = p
    for it in items:
        c = [to_px(*xz) for xz in it["corners_game_xz"]]
        name = it["asset"]
        if name in ("IlsanPine01", "IlsanPine02"):
            x, y = (int(round(q)) for q in to_px(it["game_x"], it["game_z"]))
            rgba[y - 1:y + 2, x - 1:x + 2] = (40, 200, 60, 255)
        elif name == "IlsanBeachRail":
            line(((c[0][0] + c[3][0]) / 2, (c[0][1] + c[3][1]) / 2), ((c[1][0] + c[2][0]) / 2,
                 (c[1][1] + c[2][1]) / 2), (60, 60, 60, 255))
        elif name == "IlsanRoadMarking01":
            x, y = (int(round(q)) for q in to_px(it["game_x"], it["game_z"]))
            rgba[y - 1:y + 2, x - 1:x + 2] = (255, 200, 0, 255)
        elif name == "IlsanRoundabout":
            cx, cy = to_px(it["game_x"], it["game_z"])
            r = 7.6 * px_per_m
            pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)]
            for p, q in zip(pts, pts[1:]):
                line(p, q, (255, 40, 40, 255))
        else:
            col = colors.get(catalog.ASSETS[name][2], (255, 255, 255, 255))
            line(c[0], c[1], (255, 255, 255, 255))
            for i in (1, 2, 3):
                line(c[i], c[(i + 1) % 4], col)
    return rgba


SIDE_NAMES = {"land": "해변 도로 상가 줄", "plaza": "청년광장", "sea": "도로 바다 쪽", "beach": "백사장",
              "center": "도로 위", "prop": "소품"}


def write_placement_md(path, items):
    lines = ["# 일산지 거리 에셋 배치표", "",
             "게임 좌표: 맵 중심 원점, x = 동쪽, z = 북쪽 (m). 회전 = 에셋 정면(-Y)이 향하는 방위, "
             "북쪽 0° 에서 시계 방향. 지면 = 게임 높이 (해수면 40 m).", "",
             "## 부지 (건물 · 광장 · 해변 시설)", "",
             "| # | 위치 | 에셋 | 이름 | 부지(셀) | x | z | 회전 | 지면 |", "|---|---|---|---|---|---|---|---|---|"]
    lots = [it for it in items if it["side"] not in ("prop", "center")]
    props = [it for it in items if it["side"] in ("prop", "center")]
    for i, it in enumerate(lots, 1):
        cw, cd, kind, title = catalog.ASSETS[it["asset"]][:4]
        lines.append(f"| {i} | {SIDE_NAMES[it['side']]} | `{it['asset']}` | {title} | {cw}×{cd} | {it['game_x']:.1f} "
                     f"| {it['game_z']:.1f} | {it['rotation_deg']:.1f}° | {it['ground_m']:.1f} m |")
    lines += ["", "## 소품 (부지 없음)", "",
              "해송은 백사장 가장자리, 난간은 8 m 토막을 도로 바다 쪽 산책로에 이어 붙인다 (회전 = 정면이 도로 쪽).", "",
              "| # | 에셋 | 이름 | x | z | 회전 | 지면 |", "|---|---|---|---|---|---|---|"]
    for i, it in enumerate(props, 1):
        title = catalog.ASSETS[it["asset"]][3]
        lines.append(f"| {i} | `{it['asset']}` | {title} | {it['game_x']:.1f} | {it['game_z']:.1f} "
                     f"| {it['rotation_deg']:.1f}° | {it['ground_m']:.1f} m |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


KEEP = ("asset", "side", "s_mid", "axial", "width", "depth", "game_x", "game_z", "rotation_deg", "ground_m",
        "corners_game_xz")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "Heightmaps"))
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    (lat0, lon0), st, dem = street_center()
    tile = load_tile(args.cache)

    print("플레이 영역 샘플링…")
    play = T.smooth(sample_grid(tile, lat0, lon0, PLAY_SIZE, RES), 2)
    print("월드맵 샘플링…")
    world = sample_grid(tile, lat0, lon0, WORLD_SIZE, RES, step=4)
    # 월드맵 가운데 1024 px 은 플레이 영역과 정확히 같게
    c0 = RES * 3 // 8
    world[c0:c0 + RES // 4, c0:c0 + RES // 4] = play.reshape(RES // 4, 4, RES // 4, 4).mean((1, 3))

    pngio.write_gray16(os.path.join(args.out, "Ilsan_Worldmap.png"), to_u16(world))

    _, alleys = S.lay_lots(st.length)
    lay = placement.Layout(st)
    lots = placement.plan(st, alleys, layout=lay) + placement.plan_seaside(st, lay)
    items = lots + placement.plan_props(st, lots, lay)
    to_xz = lambda la, lo: game_xy(la, lo, lat0, lon0)  # noqa: E731
    ground = ground_sampler(play.copy())   # 지면 높이는 하천을 파기 전 지형 (다리 · 도로는 물길 위로 지나간다)
    placement.to_game(items, st, dem, to_xz, ground)
    stream_xz = [to_xz(*S.Street.latlon(dem, *p)) for p in lay.stream_line]
    carve_stream(play, stream_xz)
    pngio.write_gray16(os.path.join(args.out, "Ilsan_Heightmap.png"), to_u16(play))
    pngio.write_rgb8(os.path.join(args.out, "Ilsan_Overlay.png"),
                     draw_overlay(play, st, dem, lat0, lon0, items, {"stream_xz": stream_xz}))
    with open(os.path.join(args.out, "Ilsan_Placement.json"), "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in it.items() if k in KEEP} for it in items], f, ensure_ascii=False, indent=2)

    write_placement_md(os.path.join(args.out, "Ilsan_Placement.md"), items)

    road_mid = (S.PROMENADE_END + S.ROAD_END) / 2
    pts = []
    for s in np.append(np.arange(0, st.length, 5.0), st.length):  # 5 m 간격
        (x, y), _, _ = st.frame(s, road_mid)
        gx, gz = game_xy(*S.Street.latlon(dem, x, y), lat0, lon0)
        pts.append({"station_m": round(float(s), 1), "x": round(gx, 1), "z": round(gz, 1),
                    "ground_m": round(ground(gx, gz), 2)})
    info = {
        "center_lat": lat0, "center_lon": lon0,
        "playable_km": PLAY_SIZE / 1000, "world_km": WORLD_SIZE / 1000, "resolution": RES,
        "height_scale_m": HEIGHT_SCALE, "sea_level_m": SEA_LEVEL,
        "elevation_range_m": [float(play.min()), float(play.max())],
        "street_length_m": round(st.length, 1),
        "street_centerline_game_xz": pts,
        "plaza": {"axis_start_xz": [round(c, 1) for c in to_xz(*S.Street.latlon(dem, *lay.F))],
                  "axis_end_xz": [round(c, 1) for c in to_xz(*S.Street.latlon(dem, *(lay.F + lay.n * 128)))],
                  "width_m": 2 * placement.PLAZA_HALF, "length_m": 128.0},
        "roundabout_xz": [round(c, 1) for c in to_xz(*S.Street.latlon(dem, *lay.road_center))],
        "stream_xz": [[round(c, 1) for c in p] for p in stream_xz],
        "note": "게임 좌표: 맵 중심 원점, x=동쪽, z=북쪽. ground_m 은 그 위치 하이트맵 지형의 게임 높이(해수면 40 m). "
                "하천(stream_xz)은 하이트맵에 물길로 파여 있고, 해변 도로는 그 위를 다리로 건넌다.",
    }
    with open(os.path.join(args.out, "Ilsan_Map.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"완료: 고도 {play.min():.1f} ~ {play.max():.1f} m, 거리 {st.length:.0f} m → {args.out}")


if __name__ == "__main__":
    main()
