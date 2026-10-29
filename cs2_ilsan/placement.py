"""일산지 거리 위 에셋 배치 계획 (게임 좌표). bpy 없이 동작.

게임에서 '소형 2차로 도로'(폭 약 16 m)를 해변 도로 중심선을 따라 그리면,
도로 중심에서 ROAD_HALF 만큼 떨어진 곳이 부지 앞선이 된다.
육지 쪽(상가 줄)은 catalog.SEQUENCE, 바다 쪽(백사장 앞 시설)은 catalog.SEASIDE 로 채운다.
"""

import math

import numpy as np

import catalog
import street as S

ROAD_HALF = 8.0                      # 도로 중심 -> 부지 앞선 (CS2 소형 도로 반폭)
ROAD_CENTER = (S.PROMENADE_END + S.ROAD_END) / 2
GAP = 0.0                            # 부지 사이 간격 (CS2 부지는 셀 단위로 맞붙는다)


def frontage(st):
    """부지 앞선 곡선과 그 위 누적 길이(m), 해안선 station 과의 대응"""
    off = ROAD_CENTER + ROAD_HALF
    pts = st.at_offset(off)
    arc = S.cumulative(pts)
    return off, arc


def _rect(st, s_mid, off, width, depth, side="land"):
    """앞선 중앙 station 에서 도로를 향한 부지 사각형 (로컬 xy, 앞 두 점 먼저), 중심, 안쪽 방향 v.
    side='land' 면 부지가 육지 쪽(+n)으로, 'sea' 면 바다 쪽(-n)으로 들어간다. 정면 방향 = -v."""
    (fx, fy), n, z = st.frame(s_mid, off)
    v = np.asarray(n) * (1.0 if side == "land" else -1.0)
    t = np.array([v[1], -v[0]])
    c = np.array([fx, fy]) + v * depth / 2
    hw, hd = width / 2, depth / 2
    corners = np.array([c + t * a + v * b for a, b in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))])
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


def plan(st, alleys, margin=10.0, step=0.25):
    """부지 앞선 곡선 위에서 길이를 재며 골목 사이 구간을 SEQUENCE 순서로 채운다.

    곡선 바깥쪽(육지)으로 갈수록 길이가 늘어나므로 해안선 station 이 아니라 앞선 길이로 잰다.
    곡선이 안쪽으로 휜 곳에서는 이웃 부지 뒤쪽이 겹치므로, 겹치지 않을 때까지 앞으로 민다.
    반환: [{"asset", "a0", "a1", "s_mid", "width", "depth", "front_offset", "corners"} ...]
    """
    off, arc = frontage(st)
    to_arc = lambda s: float(np.interp(s, st.s, arc))  # noqa: E731
    to_s = lambda a: float(np.interp(a, arc, st.s))  # noqa: E731
    total = float(arc[-1])
    cuts = [margin] + sorted(to_arc(x) for x in alleys) + [total - margin]
    seq = list(catalog.SEQUENCE)
    k = 0
    out = []
    for i, (a, b) in enumerate(zip(cuts[:-1], cuts[1:])):
        pos = a + (4.0 if i > 0 else 0.0)              # 골목 반폭(약 4 m) 띄움
        end = b - (4.0 if i < len(cuts) - 2 else 0.0)
        prev = None
        tries = 0
        while tries < len(seq):
            name = seq[k % len(seq)]
            cw, cd = catalog.ASSETS[name][:2]
            w, d = cw * catalog.CELL, cd * catalog.CELL
            p = pos
            while p + w <= end:
                corners = _rect(st, to_s(p + w / 2), off, w, d)[0]
                if prev is None or not overlaps(prev, corners):
                    break
                p += step
            if p + w <= end:
                out.append({"asset": name, "side": "land", "a0": p, "a1": p + w, "s_mid": to_s(p + w / 2),
                            "width": w, "depth": d, "front_offset": off, "corners": corners})
                prev = corners
                pos = p + w + GAP
                k += 1
                tries = 0
            else:
                k += 1          # 이 자리에 안 맞으면 다음 후보
                tries += 1
    return out


def plan_seaside(st):
    """도로 바다 쪽 시설 (화장실 · 샤워장): 부지 앞선 = 도로 중심 - ROAD_HALF, 백사장 쪽으로 들어간다."""
    off = ROAD_CENTER - ROAD_HALF
    out = []
    for name, frac in catalog.SEASIDE:
        cw, cd = catalog.ASSETS[name][:2]
        w, d = cw * catalog.CELL, cd * catalog.CELL
        s_mid = frac * st.length
        corners = _rect(st, s_mid, off, w, d, "sea")[0]
        if any(overlaps(corners, o["corners"]) for o in out):
            raise ValueError(f"바다 쪽 시설 {name} 이(가) 다른 시설과 겹칩니다")
        out.append({"asset": name, "side": "sea", "s_mid": s_mid, "width": w, "depth": d, "front_offset": off,
                    "corners": corners})
    return out


def to_game(items, st, dem, to_xz, ground):
    """게임 좌표 (부지 중심 x, z), 회전, 지면 높이, 부지 사각형 모서리를 붙인다.
    ground(gx, gz) -> 그 위치의 게임 지형 높이 (하이트맵에서 샘플)."""
    for it in items:
        corners, c, v, _ = _rect(st, it["s_mid"], it["front_offset"], it["width"], it["depth"],
                                 it.get("side", "land"))
        gx, gz = to_xz(*S.Street.latlon(dem, *c))
        it["game_x"], it["game_z"] = round(gx, 2), round(gz, 2)
        it["rotation_deg"] = round(math.degrees(math.atan2(-v[0], -v[1])) % 360, 1)   # 정면 = 도로 쪽
        it["ground_m"] = round(float(ground(gx, gz)), 2)
        it["corners_game_xz"] = [[round(p, 2), round(q, 2)] for p, q in
                                 (to_xz(*S.Street.latlon(dem, *xy)) for xy in corners)]
    return items
