"""일산지 사진 속 건물 (사진 ①②④⑤⑥): 타니베이호텔, 회전교차로 모퉁이 유리 상가 2종, 청년스테이지ON,
깃발 늘어선 횟집, 파란 지붕 상가.

designs.Building 과 같은 겹침 방지 규칙을 따른다. 저층부 위에 탑이 서는 건물은 Building.volume() 으로
몸체를 나눠 각 몸체의 면이 따로 예약된다 ('tower:front' 등).
실측 정보: 타니베이호텔 — 울산 동구 일산동 968-1, 지상 19층 · 지하 2층, 객실 147실(전 객실 바다 조망),
6층 인피니티 풀, 2층 레스토랑 '파도', 2023년 11월 개관. 청년스테이지ON — 해수욕장10길 34, 5층.
모퉁이 상가 · 파란 지붕 건물은 사진의 모습을 따른 추정 디자인이다.
"""

import math

import props as PR
from designs import BRICK, Building, render, side_details, sign, stripes, tile
from geom import BOTTOM, FIXTURE, FOREGROUND, SIGN, Facade, rects_minus

# ---------------------------------------------------------------------------
# 1. 타니베이호텔 — 7x4, 19층 (저층부 1~5층 유리 커튼월 + 6층 인피니티 풀 데크 + 7~19층 객실 탑)
# ---------------------------------------------------------------------------


def glass_rail(b, x0, x1, y0, y1, z, h=1.1, name="glass_rail"):
    """유리 난간: 유리판 + 스테인리스 손스침 + 기둥"""
    m = b.m
    m.box(x0, x1, y0, y1, z + 0.06, z + h - 0.06, "glass_rail")
    ex, ey = (0.02 if x1 - x0 < y1 - y0 else 0.0), (0.02 if x1 - x0 >= y1 - y0 else 0.0)
    m.box(x0 - ex, x1 + ex, y0 - ey, y1 + ey, z + h - 0.06, z + h, "stainless")
    length = max(x1 - x0, y1 - y0)
    n = max(int(length / 1.8), 1)
    for k in range(n + 1):
        t = k / n
        px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        px = min(max(px, x0 + 0.03), x1 - 0.03) if x1 - x0 > 0.06 else (x0 + x1) / 2
        py = min(max(py, y0 + 0.03), y1 - 0.03) if y1 - y0 > 0.06 else (y0 + y1) / 2
        m.box(px - 0.03, px + 0.03, py - 0.03, py + 0.03, z, z + 0.06, "stainless")
    b.roof_reserve(name, x0 - ex, x1 + ex, y0 - ey, y1 + ey, z, z + h)


def tanibay(text_fn=None):
    b = Building((7, 4), 50.0, 24.0, setback=6.0, seed=31, text_fn=text_fn)    # x -25..25, y -10..14
    P = 22.5                                     # 1~5층 저층부 높이 (그 위 = 6층 풀 데크)
    T0 = P + 4.5                                 # 7층 바닥 (6층 = 스카이 라운지 + 수영장)
    FL, NF = 3.35, 13                            # 7~19층 객실 층고 · 층수
    T = T0 + FL * NF                             # 탑 지붕 70.55 m
    tx0, tx1, ty0, ty1 = -23.0, 23.0, -3.0, 10.0   # 객실 탑 (전 객실 바다 조망: 편복도형, 깊이 13 m)
    cx0, cx1, cy1 = -7.0, 7.0, 13.6                # 탑 뒤 엘리베이터 · 계단 코어
    b.mats.update({
        "wall": {"color": (0.50, 0.48, 0.45), "color2": (0.45, 0.43, 0.40), "pattern": "panel",
                 "scale": (1.2, 0.6), "mortar": 0.005, "mortar_color": (0.30, 0.29, 0.28), "rough": 0.45,
                 "bump": 0.1},
        "wall_side": {"color": (0.56, 0.54, 0.51), "color2": (0.51, 0.49, 0.46), "pattern": "panel",
                      "scale": (1.2, 0.6), "mortar": 0.005, "mortar_color": (0.33, 0.32, 0.30), "rough": 0.5,
                      "bump": 0.1, "grime": 0.1},
        "tower": {"color": (0.88, 0.88, 0.86), "color2": (0.84, 0.84, 0.82), "pattern": "panel",
                  "scale": (1.5, 3.35), "mortar": 0.004, "mortar_color": (0.62, 0.62, 0.62), "rough": 0.35,
                  "control": (1, 0, 0)},
        "canopy": {"color": (0.90, 0.90, 0.88), "rough": 0.3, "metal": 0.3},
        "crown": {"color": (0.20, 0.21, 0.23), "color2": (0.12, 0.13, 0.14), "pattern": "siding", "scale": 0.22,
                  "rough": 0.4, "metal": 0.7},
        "letters_hotel": {"color": (0.95, 0.95, 0.93), "rough": 0.3, "emit": (1.0, 0.97, 0.9), "emit_strength": 4.0},
        "letters_gold": {"color": (0.75, 0.58, 0.30), "rough": 0.25, "metal": 0.9, "emit": (1.0, 0.8, 0.45),
                         "emit_strength": 1.5},
        "sign": sign((0.10, 0.12, 0.16), 0.3),
    })
    m = b.m
    b.lot_slab()
    deck = (-25.0, 25.0, -10.0, ty0)
    b.shell(P, zones={"back": [(0.03, P, "wall_side")]},
            roof_holes=[(tx0, tx1, ty0, ty1), (cx0, cx1, ty1, cy1), deck])
    b.volume("tower", tx0, tx1, ty0, ty1, P, T,
             zones={"front": [(P, T, "tower")], "left": [(P, T, "tower")], "right": [(P, T, "tower")],
                    "back": [(P, T, "tower", 0.0, tx1 - cx1), (P, T, "tower", tx1 - cx0, tx1 - tx0)]})
    b.volume("core", cx0, cx1, ty1, cy1, P, T + 4.2,
             zones={"front": [(T + 1.28, T + 4.2, "wall_side")], "left": [(P, T + 4.2, "tower")],
                    "right": [(P, T + 4.2, "tower")], "back": [(P, T + 4.2, "tower")]})

    # -- 저층부 정면: 1층 로비 · 라운지 · 레스토랑, 2~5층 유리 커튼월, 포르트코셰르 캐노피 ---------------------
    f = b.face("front")
    podium_levels = [6.6 + k * 3.825 for k in range(4)]
    f.storefront(15.0, 35.0, 0.03, 5.6, bay=2.5, transom=3.2, doors=[(19.0, 1.8), (25.0, 2.4), (31.0, 1.8)],
                 name="lobby")
    f.storefront(0.6, 13.4, 0.03, 5.6, bay=2.2, transom=3.2, doors=[(7.0, 1.8)], name="lounge")
    f.storefront(36.6, 49.4, 0.03, 5.6, bay=2.2, transom=3.2, doors=[(43.0, 1.8)], name="restaurant")
    f.curtain(0.3, 49.7, 6.6, 21.9, 3.825, 2.5, spandrel=0.7, lit=0.35, rng=b.rng, name="podium_cw")
    b.wall_text("front", "LOUNGE · CAFE", 7.0, 6.1, 10.0, 0.45)
    b.wall_text("front", "RESTAURANT 파도 2F", 43.0, 6.1, 11.0, 0.45)
    cz = 5.75
    f.box(13.0, 37.0, cz, cz + 0.75, 0, 5.8, "canopy")                       # 포르트코셰르 (차 대는 곳 지붕)
    f.box(13.0, 37.0, cz + 0.75, cz + 0.8, 0, 5.85, "frame_dark", attached=False)
    t = b.letters("TANIBAY HOTEL", 18.0, 0.46, 0.05)
    if t:
        f.text(t, 25.0, cz + 0.375, 5.8, "letters_hotel", kind=None)
    for uu in range(16, 35, 3):
        for dd in (1.6, 4.0):
            f.box(uu - 0.25, uu + 0.25, cz - 0.02, cz, dd - 0.25, dd + 0.25, "lamp", attached=False)
    for uu in (14.0, 36.0):
        x, y = f.xy(uu, 5.2)
        m.cylinder(x, y, 0.3, 0.03, cz, "canopy", n=16)
        f.reserve(FOREGROUND, uu - 0.31, uu + 0.31, 0.03, cz - 0.03, 4.89, 5.51, "canopy_column")
    f.reserve(FOREGROUND, 13.0, 37.0, cz - 0.02, cz + 0.8, 0, 5.85, "porte_cochere")
    f.box(0.0, 50.0, 21.95, P, 0, 0.3, "canopy")                             # 수영장 넘침 홈통 · 상부 띠
    f.reserve(FIXTURE, 0.0, 50.0, 21.95, P, 0, 0.3, "pool_gutter")

    # -- 저층부 옆 · 뒤 ------------------------------------------------------------------------------
    lf = b.face("left")                                                     # u = 14 - y (정면 쪽 u = 24)
    lf.garage(2.5, 8.5, 0.03, 3.6, name="parking")
    b.lightbox("left", 5.5, 4.05, 2.8, 0.6, "P 주차장 B1 · B2", mat="sign")
    lf.storefront(12.6, 23.4, 0.03, 5.6, bay=2.2, transom=3.2, doors=[(15.0, 1.8)], name="lounge_side")
    lf.curtain(12.0, 23.88, 6.6, 21.9, 3.825, 2.4, spandrel=0.7, lit=0.35, rng=b.rng, name="podium_cw_l")
    rf = b.face("right")                                                    # u = y + 10 (정면 쪽 u = 0)
    rf.storefront(0.6, 11.4, 0.03, 5.6, bay=2.2, transom=3.2, doors=[(8.0, 1.8)], name="restaurant_side")
    rf.curtain(0.12, 12.0, 6.6, 21.9, 3.825, 2.4, spandrel=0.7, lit=0.35, rng=b.rng, name="podium_cw_r")
    rf.door(16.5, 1.2, 2.3, leaf="door_metal", name="staff")
    for zf in podium_levels:
        for uu in (2.5, 6.0, 9.5):
            lf.window(uu, zf + 0.9, 1.6, 1.5, lit=b.chance(0.3), blind=b.blind())
        for uu in (14.5, 18.0, 21.5):
            rf.window(uu, zf + 0.9, 1.6, 1.5, lit=b.chance(0.3), blind=b.blind())
    bk = b.face("back")                                                     # u = 25 - x
    bk.shutter(4.0, 8.5, 0.03, 4.6, open_frac=0.0, name="loading1")
    bk.shutter(9.5, 14.0, 0.03, 4.6, open_frac=0.6, name="loading2")
    bk.door(18.0, 1.2, 2.3, leaf="door_metal", name="service")
    bk.door(44.0, 1.0, 2.2, leaf="door_metal", canopy=False, name="exit")
    for zf in podium_levels:
        for i in range(9):
            bk.window(3.5 + i * 5.3, zf + 0.9, 1.6, 1.4, style="fixed" if i % 2 else "sliding", lit=b.chance(0.25))
    for k, uu in enumerate((22.5, 30.0, 36.0)):
        b.ac_wall("back", uu, 1.6, cage=k == 1)
    b.downpipe("back", 0.4, top=P + 0.9)
    b.downpipe("back", 49.6, top=P + 0.9)
    b.plinth(h=0.5)

    # -- 6층 인피니티 풀 데크 (저층부 지붕) -----------------------------------------------------------
    zd = P + 0.2
    pool = (-21.0, 21.0, -9.85, -5.6)
    coping = (-21.3, 21.3, -10.0, -5.3)
    for a, c, d0, d1 in rects_minus(*deck, [coping]):
        m.box(a, c, d0, d1, P, zd, "deck", skip=(BOTTOM,))
    for a, c, d0, d1 in rects_minus(*coping, [(-21.0, 21.0, -10.0, -5.6)]):
        m.box(a, c, d0, d1, P, zd, "granite", skip=(BOTTOM,))
    m.box(pool[0], pool[1], -10.0, pool[2], P, P + 0.16, "granite", skip=(BOTTOM,))   # 넘치는 가장자리
    m.box(*pool, P, P + 0.17, "pool_water", skip=(BOTTOM,))
    b.roof_reserve("pool_deck", -25.0, 25.0, -10.0, ty0, P, zd)
    for sx in (-1, 1):                                                      # 수영장 사다리
        lx = sx * 15.0
        for dx in (-0.25, 0.25):
            m.tube((lx + dx, -5.45, zd), (lx + dx, -5.45, zd + 0.9), 0.025, 0.025, "stainless", n=6)
            m.tube((lx + dx, -5.45, zd + 0.9), (lx + dx, -5.75, zd + 0.9), 0.025, 0.025, "stainless", n=6)
            m.tube((lx + dx, -5.75, zd + 0.9), (lx + dx, -5.75, P + 0.17), 0.025, 0.025, "stainless", n=6)
        b.roof_reserve("pool_ladder", lx - 0.3, lx + 0.3, -5.8, -5.4, zd, zd + 0.95)
    for k in range(9):                                                      # 선베드 (바다를 향해)
        lx = -18.0 + k * 4.5
        b.roof_reserve("lounger", *PR.lounger(m, lx, -4.2, zd, back="+y"))
    for lx in (-15.75, -6.75, 6.75, 15.75):
        PR.parasol(m, lx, -4.2, zd, r=1.05, h=2.5)
        b.roof_reserve("parasol_pole", lx - 0.23, lx + 0.23, -4.43, -3.97, zd, zd + 2.05)
        b.roof_reserve("parasol", lx - 1.05, lx + 1.05, -5.25, -3.15, zd + 2.05, zd + 2.5)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 24.7, sx * 21.9))
        b.roof_reserve("pool_planter", *PR.planter(m, x0, x1, -9.7, -6.2, z=zd, seed=3 + sx, shrubs=2))
        xr0, xr1 = sorted((sx * 24.97, sx * 24.93))
        glass_rail(b, xr0, xr1, -9.97, -3.05, zd, name="rail_side")
        xf0, xf1 = sorted((sx * 24.9, sx * 21.35))
        glass_rail(b, xf0, xf1, -9.97, -9.93, zd, name="rail_front")
    # 저층부 지붕 뒤쪽 난간벽 + 냉각탑
    for a, c, d0, d1 in ((-25.0, -24.78, ty0, 14.0), (24.78, 25.0, ty0, 14.0), (-24.78, 24.78, 13.78, 14.0)):
        m.box(a, c, d0, d1, P, P + 1.1, "wall_side", skip=(BOTTOM,))
        m.box(a, c, d0, d1, P + 1.1, P + 1.18, "trim")
        b.roof_reserve("podium_parapet", a, c, d0, d1, P, P + 1.18)
    for cxx in (-16.0, 16.0):
        m.box(cxx - 1.6, cxx + 1.6, 10.6, 13.4, P, P + 0.2, "metal_dark")
        m.box(cxx - 1.5, cxx + 1.5, 10.7, 13.3, P + 0.2, P + 2.4, "ac")
        m.cylinder(cxx, 12.0, 1.1, P + 2.4, P + 2.9, "metal_dark", n=20)
        m.cylinder(cxx, 12.0, 0.2, P + 2.9, P + 3.0, "metal", n=10)
        b.roof_reserve("cooling_tower", cxx - 1.6, cxx + 1.6, 10.6, 13.4, P, P + 3.0)

    # -- 탑: 6층 라운지 통유리, 7~19층 객실 (흰 세로 핀 + 층 차양) --------------------------------------
    tf = b.face("tower:front")                                              # u = x + 23
    tf.curtain(0.3, 45.7, P + 0.25, T0 - 0.2, 4.1, 2.3, spandrel=0.0, lit=0.6, rng=b.rng, name="sky_lounge")
    t = b.letters("SKY POOL & LOUNGE", 5.0, 0.4, 0.01)
    if t:
        tf.glass_text(t, 23.0, P + 3.6, recess=0.12)
    tf.curtain(0.3, 45.7, T0, T - 0.3, FL, 45.4 / 11, spandrel=0.55, fins=0.6, ledge=0.4, lit=0.45, rng=b.rng,
               name="rooms")
    for side, lounge, rooms, slot_u, vu in (("left", (4.5, 12.88), (8.7, 12.88), 1.5, 4.6),
                                            ("right", (0.12, 8.5), (0.12, 4.3), 11.5, 8.4)):
        tv = b.face("tower:" + side)                                        # 정면 쪽 모서리 객실도 유리
        tv.curtain(*lounge, P + 0.25, T0 - 0.2, 4.1, 2.1, spandrel=0.0, lit=0.6, rng=b.rng, name="sky_lounge_s")
        tv.curtain(*rooms, T0, T - 0.3, FL, 4.2, spandrel=0.55, ledge=0.4, lit=0.45, rng=b.rng, name="rooms_s")
        for k in range(NF):
            tv.window(slot_u, T0 + k * FL + 0.9, 0.8, 1.6, style="fixed", sill=None, lit=b.chance(0.5))
        zc = T - 2.6
        for ch in "타니베이호텔":                                              # 옆면 세로 채널 글자
            if b.wall_text("tower:" + side, ch, vu, zc, 3.0, 3.0, mat="letters_hotel", extrude=0.15):
                zc -= 3.5
    tb = b.face("tower:back")                                               # u = 23 - x, 코어 = u 16..30
    for k in range(NF):
        for uu in (2.5, 6.5, 10.5, 14.0, 32.0, 35.5, 39.5, 43.5):
            tb.window(uu, T0 + k * FL + 0.95, 1.2, 1.4, style="fixed", lit=b.chance(0.3))
    for uu in (2.5, 8.0, 13.5, 32.5, 38.0, 43.5):
        tb.window(uu, P + 1.2, 1.8, 2.0, style="fixed", lit=b.chance(0.5))
    cb = b.face("core:back")                                                # 계단참 창
    for k in range(NF):
        for uu in (3.5, 10.5):
            cb.window(uu, T0 + k * FL + 1.6, 0.7, 1.0, style="fixed", sill=None, lit=b.chance(0.4))
    for side in ("core:left", "core:right"):                                # 기계실 환기 루버
        cf = b.face(side)
        cf.box(0.5, cf.width - 0.5, T + 0.6, T + 3.4, 0, 0.06, "grille")
        cf.reserve(FIXTURE, 0.5, cf.width - 0.5, T + 0.6, T + 3.4, 0, 0.06, "louver")

    # -- 탑 옥상: 난간벽, 크라운 스크린 + 호텔 이름, 항공 장애등, 피뢰침 -----------------------------------
    b.mats["tower_parapet"] = b.mats["tower"]
    b.parapet(h=1.2, mat="tower_parapet", vol="tower")
    crown = (-19.0, 19.0, -1.5, 8.5)
    m.box(*crown, T, T + 3.8, "crown", skip=(BOTTOM,))
    m.box(crown[0] - 0.1, crown[1] + 0.1, crown[2] - 0.1, crown[3] + 0.1, T + 3.8, T + 4.0, "trim")
    b.roof_reserve("crown", crown[0] - 0.1, crown[1] + 0.1, crown[2] - 0.1, crown[3] + 0.1, T, T + 4.0)
    t = b.letters("TANIBAY HOTEL", 34.0, 2.3, 0.12)
    if t:
        Facade(m, "front", *crown).text(t, 19.0, T + 1.95, 0.0, "letters_hotel", kind=None)
    t = b.letters("TANIBAY", 8.6, 1.7, 0.1)
    if t:
        for side in ("left", "right"):
            Facade(m, side, *crown).text(t, 5.0, T + 1.95, 0.0, "letters_hotel", kind=None)
    for x, y in ((tx0 + 0.15, ty0 + 0.15), (tx1 - 0.15, ty0 + 0.15), (tx0 + 0.15, ty1 - 0.15), (tx1 - 0.15, ty1 - 0.15)):
        m.cylinder(x, y, 0.09, T + 1.28, T + 1.5, "lamp_red", n=8)
        b.roof_reserve("obstruction_light", x - 0.1, x + 0.1, y - 0.1, y + 0.1, T + 1.28, T + 1.5)
    m.tube((0.0, 11.8, T + 4.2), (0.0, 11.8, T + 8.5), 0.05, 0.02, "stainless", n=6)
    m.cylinder(-4.5, 11.8, 0.08, T + 4.2, T + 4.4, "lamp_red", n=8)
    m.cylinder(4.5, 11.8, 0.08, T + 4.2, T + 4.4, "lamp_red", n=8)
    b.top = max(b.top, T + 8.5)

    # -- 앞마당: 차량 승하차 차로, 표지석, 해송 화분, 볼라드 -----------------------------------------------
    m.box(-18.0, 18.0, -15.8, -11.2, 0.03, 0.04, "asphalt", skip=(BOTTOM,))
    for x0, x1 in ((-18.0, -17.85), (17.85, 18.0)):
        m.box(x0, x1, -15.8, -11.2, 0.04, 0.045, "paint_white", skip=(BOTTOM,))
    m.box(-27.9, -25.1, -15.8, 11.8, 0.03, 0.04, "asphalt", skip=(BOTTOM,))   # 지하주차장 진입로
    m.box(-26.6, -26.45, -15.0, 11.0, 0.04, 0.045, "paint_yellow", skip=(BOTTOM,))
    for x in (-17.0, -13.0, -9.0, 9.0, 13.0, 17.0):
        PR.bollard(m, x, -11.35)
    m.box(-24.8, -20.0, -15.4, -14.7, 0.03, 1.5, "granite", skip=(BOTTOM,))   # 표지석
    sf = Facade(m, "front", -24.8, -20.0, -15.4, -14.7)
    t = b.letters("TANIBAY HOTEL", 4.0, 0.42, 0.03)
    if t:
        sf.text(t, 2.4, 1.05, 0.0, "letters_gold", kind=None)
    t = b.letters("타니베이호텔", 2.6, 0.32, 0.03)
    if t:
        sf.text(t, 2.4, 0.5, 0.0, "letters_gold", kind=None)
    PR.planter(m, 21.6, 26.6, -15.7, -11.4, seed=8, shrubs=3)
    PR.pine(m, 24.1, -13.2, 0.42, h=6.5, seed=5, lean=0.05, lean_dir=0.0, reach=1.6, fit=(19.0, 27.9, -15.9, -10.4))
    b.finalize()
    return b, "타니베이호텔"


# ---------------------------------------------------------------------------
# 2. 회전교차로 모퉁이 유리 상가 — 3x3, 7층. 광장 쪽 모서리를 유리로 감싸고 층마다 업종 간판 띠
# ---------------------------------------------------------------------------

TENANTS_A = [("대게 · 회 전문점", (0.62, 0.05, 0.03)), ("노래연습장", (0.75, 0.12, 0.45)), ("PC방", (0.10, 0.25, 0.70)),
             ("스크린골프", (0.08, 0.45, 0.25)), ("필라테스 · 요가", (0.85, 0.45, 0.05)), ("스카이라운지", (0.10, 0.12, 0.30))]
TENANTS_B = [("해물칼국수", (0.85, 0.30, 0.05)), ("일산치과", (0.05, 0.40, 0.55)), ("영어 · 수학학원", (0.20, 0.20, 0.60)),
             ("당구장", (0.08, 0.45, 0.25)), ("휘트니스", (0.80, 0.10, 0.10)), ("루프탑 카페", (0.35, 0.22, 0.12))]


def corner_tower(plaza, title, ground, tenants, vsign, seed, text_fn=None):
    """plaza = 광장이 있는 옆면 ('left' | 'right'). 정면(도로) + 광장 쪽 면이 유리, 반대쪽 · 뒤는 설비 면."""
    b = Building((3, 3), 22.0, 20.0, setback=2.0, seed=seed, text_fn=text_fn)    # x -11..11, y -10..10
    b.mats.update({
        "wall": {"color": (0.24, 0.26, 0.28), "color2": (0.21, 0.23, 0.25), "pattern": "panel", "scale": (1.2, 0.9),
                 "mortar": 0.005, "mortar_color": (0.10, 0.10, 0.11), "rough": 0.3, "metal": 0.6},
        "wall_side": render((0.78, 0.77, 0.74), grime=0.2),
        "sign_ground1": sign((0.10, 0.45, 0.30), 0.6),
        "sign_ground2": sign((0.30, 0.18, 0.10), 0.5),
        "sign_roof": sign((0.05, 0.10, 0.35), 0.9),
        "sign2": sign((0.75, 0.10, 0.10), 0.8),
    })
    for k, (_, col) in enumerate(tenants):
        b.mats[f"sign_t{k}"] = sign(col, 0.7)
    store, cafe = ground                       # (글자, 보조 문구, 판 색, 글자 색) — 1층 편의점 · 모퉁이 카페 브랜드
    for key, (_, _, board, letter) in (("1", store), ("2", cafe)):
        b.mats["sign_ground" + key] = sign(board, 0.6)
        b.mats["letters_ground" + key] = {"color": letter, "rough": 0.35,
                                          "emit": tuple(min(1.0, c * 1.25 + 0.02) for c in letter),
                                          "emit_strength": 2.2}
    other = "right" if plaza == "left" else "left"
    g, u = 4.6, 3.6
    floors = [g + k * u for k in range(6)]
    H = g + 6 * u
    b.lot_slab()
    b.shell(H, zones={plaza: [(0.03, H, "wall")]})
    W, D = b.w, b.d
    # 모서리 기준 좌표: 정면은 광장 모서리에서 잰 거리 t, 광장 면은 정면 모서리에서 잰 거리 s
    fu = (lambda t: W - t) if plaza == "right" else (lambda t: t)                        # noqa: E731
    su = (lambda s: s) if plaza == "right" else (lambda s: D - s)                        # noqa: E731
    span_f = lambda t0, t1: tuple(sorted((fu(t0), fu(t1))))                              # noqa: E731
    span_s = lambda s0, s1: tuple(sorted((su(s0), su(s1))))                              # noqa: E731
    f, p = b.face("front"), b.face(plaza)
    # 1층: 모서리 카페(정면 + 광장 면을 감싼 유리), 건물 로비 문, 편의점
    a0, a1 = span_f(0.12, 8.4)
    f.storefront(a0, a1, 0.03, 3.4, bay=1.4, doors=[(fu(6.4), 1.6)], name="corner_cafe")
    f.door(fu(10.0), 1.6, 2.4, leaf="glass_door", name="lobby")
    a0, a1 = span_f(11.6, 20.9)
    f.storefront(a0, a1, 0.03, 3.4, bay=1.3, doors=[(fu(18.8), 1.6)], name="store")
    a0, a1 = span_s(0.12, 12.0)
    p.storefront(a0, a1, 0.03, 3.4, bay=1.4, doors=[(su(9.5), 1.6)], name="corner_cafe_s", mat_depth=0.8)
    b.sign_band("front", *span_f(0.17, 8.4), 3.55, 4.45, cafe[0], cafe[1], mat="sign_ground2",
                letters="letters_ground2")
    b.sign_band("front", *span_f(11.6, 20.85), 3.55, 4.45, store[0], store[1], mat="sign_ground1",
                letters="letters_ground1")
    b.sign_band(plaza, *span_s(0.17, 12.0), 3.55, 4.45, cafe[0], cafe[1], mat="sign_ground2",
                letters="letters_ground2")
    b.lightbox("front", fu(10.0), 3.0, 2.0, 0.42, title, mat="sign_roof")
    # 2~7층: 층마다 업종 간판 띠 + 한 층 높이 유리 (정면 · 광장 면)
    for k, (zf, (name, _)) in enumerate(zip(floors, tenants)):
        b.sign_band("front", *span_f(0.17, 20.8), zf + 0.12, zf + 0.92, name, out=0.25, mat=f"sign_t{k}")
        nb, _ = f.curtain(*span_f(0.12, 20.85), zf + 1.05, zf + u - 0.12, u, 1.7, lit=0.5, rng=b.rng,
                          name="cw_front")
        b.sign_band(plaza, *span_s(0.17, 12.8), zf + 0.12, zf + 0.92, name, out=0.25, mat=f"sign_t{k}")
        p.curtain(*span_s(0.12, 12.85), zf + 1.05, zf + u - 0.12, u, 1.6, lit=0.5, rng=b.rng, name="cw_plaza")
        t = b.letters(f"{k + 2}F", 0.9, 0.5, 0.01)
        if t:
            f.glass_text(t, fu(1.0), zf + 2.6, recess=0.12)
    b.vertical_sign("front", fu(21.45), g + 0.4, H - 0.8, vsign, out=1.3, t=0.5)
    # 광장 면 뒤쪽: 계단실 (층마다 반층 창) + 옆 출입문
    p.door(su(16.0), 1.4, 2.3, leaf="glass_door", name="side_entry")
    for zf in floors:
        p.window(su(16.5), zf + 2.2, 1.0, 1.4, style="fixed", lit=b.chance(0.5))
    # 반대쪽 면 · 뒤: 창, 실외기, 우수관, 가스관
    o = b.face(other)                                                       # 반대쪽 면: u = D - su(정면에서 잰 거리)
    for zf in floors:
        for s in (4.0, 9.0, 14.5):
            o.window(D - su(s), zf + 1.0, 1.4, 1.3, lit=b.chance(0.4), blind=b.blind())
        for s in (6.6, 11.8):
            b.ac_wall(other, s, zf + 0.35, cage=b.chance(0.4))
    for zf in [0.03] + floors:
        for uu in (4.0, 11.0, 18.0):
            b.face("back").window(uu, zf + 1.2, 1.1, 1.0, sill=None if zf < 1 else "trim", style="fixed",
                                  grille=zf < 1, lit=b.chance(0.3))
    b.face("back").door(7.5, 1.0, 2.2, leaf="door_metal", name="back_door")
    for zf in floors[::2]:
        b.ac_wall("back", 14.5, zf + 0.4)
    b.downpipe(other, 0.35)
    b.downpipe(other, D - 0.35)
    b.downpipe("back", W - 0.35)
    b.gas_pipe(other, 3.9, D - 1.6)
    b.plinth()
    b.parapet(h=1.1)
    # 옥상: 정면 + 광장 쪽 ㄱ자 대형 간판, 계단실, 물탱크, 실외기
    z = b.height
    pt = b.parapet_t
    sy = b.y0 + pt + 0.6
    bx0, bx1 = b.x0 + 2.0, b.x1 - 2.0
    m = b.m
    for px in [bx0 + 0.3 + (bx1 - bx0 - 0.6) * k / 4 for k in range(5)]:
        m.box(px - 0.08, px + 0.08, sy + 0.25, sy + 0.41, z, z + 4.6, "metal_dark")
        m.beam((px, sy + 0.33, z + 3.2), (px, sy + 1.6, z + 0.05), 0.06, 0.06, "metal_dark")
    b.m.box(bx0, bx1, sy, sy + 0.25, z + 1.4, z + 4.4, "sign_roof")
    t = b.letters(title, (bx1 - bx0) * 0.84, 2.0, 0.08)
    if t:
        Facade(b.m, "front", bx0, bx1, sy, sy + 0.25).text(t, (bx1 - bx0) / 2, z + 2.9, 0.0, "letters", kind=None)
    b.roof_reserve("roof_sign", bx0 - 0.1, bx1 + 0.1, sy - 0.1, sy + 1.65, z, z + 4.6)
    px = (b.x1 - pt - 0.6) if plaza == "right" else (b.x0 + pt + 0.35)
    py0, py1 = sy + 2.0, b.y1 - 6.5
    b.m.box(px, px + 0.25, py0, py1, z + 1.4, z + 4.0, "sign_roof")
    t = b.letters(title, (py1 - py0) * 0.84, 1.7, 0.08)
    if t:
        Facade(b.m, plaza, px, px + 0.25, py0, py1).text(t, (py1 - py0) / 2, z + 2.7, 0.0, "letters", kind=None)
    for py in (py0 + 0.3, (py0 + py1) / 2, py1 - 0.3):
        qx = px - 0.18 if plaza == "right" else px + 0.25
        b.m.box(qx, qx + 0.18, py - 0.08, py + 0.08, z, z + 4.2, "metal_dark")
    b.roof_reserve("roof_sign_side", min(px, px - 0.2), px + 0.45, py0 - 0.1, py1 + 0.1, z, z + 4.2)
    hx0 = b.x0 + 1.0 if plaza == "right" else b.x1 - 4.6
    top = b.stair_house(hx0, hx0 + 3.6, b.y1 - 4.2, b.y1 - 0.6, h=3.0)
    b.water_tank(hx0 + 1.8, b.y1 - 2.4, top, r=0.8, h=1.3)
    for i in range(4):
        b.ac_roof(-3.6 + i * 1.3 if plaza == "right" else 3.6 - i * 1.3, b.y1 - 1.1, z)
    for i in range(3):
        b.ac_roof(-1.8 + i * 1.3, b.y1 - 3.0, z)
    b.finalize()
    return b, title


# 1층 실제 브랜드: (글자, 보조 문구, 간판 판 색, 글자 색)
CU_SIGN = ("CU", "24시간 · 택배 · ATM", (0.95, 0.95, 0.93), (0.13, 0.03, 0.27))
GS25_SIGN = ("GS25", "24시간 · 택배 · ATM", (0.95, 0.95, 0.93), (0.0, 0.17, 0.62))
MEGA_SIGN = ("MEGA COFFEE", "메가MGC커피", (0.95, 0.80, 0.02), (0.08, 0.06, 0.05))
EDIYA_SIGN = ("EDIYA COFFEE", "이디야커피", (0.02, 0.06, 0.22), (0.98, 0.98, 0.95))


def corner01(text_fn=None):
    return corner_tower("left", "일산스퀘어", (CU_SIGN, MEGA_SIGN), TENANTS_A, "노래방PC방", 41, text_fn)


def corner02(text_fn=None):
    return corner_tower("right", "비치타워", (GS25_SIGN, EDIYA_SIGN), TENANTS_B, "치과학원", 42, text_fn)


# ---------------------------------------------------------------------------
# 3. 청년스테이지ON — 2x3, 5층. 1층 라운지, 2~4층 창 + 목재 세로 루버, 5층 통유리, 옥상 정원
# ---------------------------------------------------------------------------

def youth_stage(text_fn=None):
    b = Building((2, 3), 14.0, 17.0, setback=4.0, seed=33, text_fn=text_fn)    # x -7..7, y -8..9
    b.mats.update({
        "wall": {"color": (0.92, 0.92, 0.90), "color2": (0.88, 0.88, 0.86), "pattern": "panel", "scale": (1.5, 1.2),
                 "mortar": 0.004, "mortar_color": (0.7, 0.7, 0.7), "rough": 0.4},
        "wall_side": render((0.86, 0.86, 0.84), grime=0.15),
        "sign_on": sign((0.98, 0.45, 0.10), 1.2),
        "letters_on": {"color": (0.98, 0.98, 0.95), "rough": 0.3, "emit": (1.0, 1.0, 0.95), "emit_strength": 3.0},
        "letters_dark": {"color": (0.08, 0.08, 0.10), "rough": 0.4},
    })
    g, u, top = 4.4, 3.5, 4.2
    floors = [g, g + u, g + 2 * u]
    z5 = g + 3 * u
    H = z5 + top
    b.lot_slab()
    b.shell(H)
    f = b.face("front")
    f.storefront(0.5, 13.5, 0.03, 3.8, bay=1.6, transom=2.7, doors=[(3.0, 1.8)], name="lounge")
    b.canopy("front", 0.3, 13.7, 3.95, depth=1.6, mat="wood")
    b.wall_text("front", "청년스테이지 ON", 7.0, 4.47, 8.0, 0.5, mat="letters_dark")
    for zf in floors:
        for uu in (2.6, 7.0, 11.4):
            f.window(uu, zf + 0.6, 2.6, 2.2, style="casement", lit=b.chance(0.55), blind=b.blind())
    for uu in (4.8, 9.2):                                                   # 목재 세로 루버
        for k in range(3):
            du = (k - 1) * 0.16
            f.box(uu + du - 0.04, uu + du + 0.04, g + 0.5, z5 - 0.1, 0, 0.35, "wood")
        f.reserve(FIXTURE, uu - 0.25, uu + 0.25, g + 0.5, z5 - 0.1, 0, 0.35, "louver")
    f.curtain(0.3, 13.7, z5 + 0.1, H - 0.2, top, 1.4, lit=0.7, rng=b.rng, name="top_glass")
    lf = b.face("left")                                                     # u = 9 - y (정면 쪽 u = 17)
    lf.curtain(12.0, 16.88, z5 + 0.1, H - 0.2, top, 1.6, lit=0.7, rng=b.rng, name="top_glass_l")
    lf.disc(8.5, z5 - 3.0, 0.0, 1.5, 0.3, "sign_on", n=28)                   # 둥근 'ON' 로고 간판
    t = b.letters("ON", 2.1, 1.2, 0.06)
    if t:
        lf.text(t, 8.5, z5 - 3.0, 0.3, "letters_on", kind=None)
    lf.reserve(SIGN, 6.95, 10.05, z5 - 4.55, z5 - 1.45, 0, 0.42, "logo_on")
    for zf in floors:
        for uu in (3.0, 13.5):
            lf.window(uu, zf + 0.9, 1.6, 1.5, lit=b.chance(0.5), blind=b.blind())
    lf.door(14.0, 1.2, 2.3, leaf="glass_door", canopy=False, name="side_door")
    for zf in floors:
        b.windows("right", [zf], 3, 1.4, 1.4, margin=2.0)
    b.windows("right", [z5], 3, 2.0, 2.4, sill=0.6, margin=2.0, style="fixed")
    b.windows("back", [0.03] + floors + [z5], 2, 1.2, 1.2, sill=1.1, margin=3.0)
    b.face("back").door(7.0, 1.0, 2.2, leaf="door_metal", name="back_door")
    b.downpipe("right", 0.35, top=H + 0.9)
    b.downpipe("right", b.d - 0.35, top=H + 0.9)
    b.gas_pipe("right", 3.5, b.d - 2.0)
    b.ac_wall("back", 11.0, 1.4)
    b.ac_wall("back", 3.0, g + u + 0.3, cage=True)
    b.bands([g, g + u, g + 2 * u, z5], ("left", "right"), h=0.12, out=0.05)
    b.plinth()
    b.parapet(h=0.35, mat="wall")
    # 옥상 정원: 데크, 유리 난간, 화분, 무드 벤치, 퍼걸러, 계단실
    m, z, pt = b.m, b.height, b.parapet_t
    m.box(b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y1 - 4.6, z, z + 0.12, "deck", skip=(BOTTOM,))
    b.roof_reserve("deck", b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y1 - 4.6, z, z + 0.12)
    zr = z + 0.12
    glass_rail(b, b.x0 + pt + 0.03, b.x1 - pt - 0.03, b.y0 + pt + 0.03, b.y0 + pt + 0.07, zr, name="rail_f")
    glass_rail(b, b.x0 + pt + 0.03, b.x0 + pt + 0.07, b.y0 + pt + 0.1, b.y1 - 4.65, zr, name="rail_l")
    glass_rail(b, b.x1 - pt - 0.07, b.x1 - pt - 0.03, b.y0 + pt + 0.1, b.y1 - 4.65, zr, name="rail_r")
    for x0 in (b.x0 + 0.6, b.x1 - 2.4):
        b.roof_reserve("planter", *PR.planter(m, x0, x0 + 1.8, b.y0 + 0.9, b.y0 + 2.0, z=zr, seed=int(x0), shrubs=2))
    for bx in (-3.0, 1.5):
        b.roof_reserve("bench", *PR.led_bench(m, bx, b.y0 + 4.2, zr, length=2.2))
    for px in (b.x0 + 1.2, b.x1 - 1.2):                                     # 퍼걸러 기둥 + 보 + 살
        for py in (b.y0 + 5.6, b.y0 + 9.6):
            m.box(px - 0.08, px + 0.08, py - 0.08, py + 0.08, zr, zr + 2.6, "wood")
    for py in (b.y0 + 5.6, b.y0 + 9.6):
        m.box(b.x0 + 1.0, b.x1 - 1.0, py - 0.08, py + 0.08, zr + 2.6, zr + 2.8, "wood")
    for k in range(12):
        px = b.x0 + 1.4 + k * (b.w - 2.8) / 11
        m.box(px - 0.04, px + 0.04, b.y0 + 5.3, b.y0 + 9.9, zr + 2.8, zr + 2.9, "wood")
    b.roof_reserve("pergola", b.x0 + 1.0, b.x1 - 1.0, b.y0 + 5.3, b.y0 + 9.9, zr, zr + 2.9)
    b.stair_house(b.x0 + 0.6, b.x0 + 4.0, b.y1 - 4.0, b.y1 - 0.6)
    for i in range(3):
        b.ac_roof(b.x1 - 1.2 - i * 1.25, b.y1 - 1.1, z)
    b.finalize()
    return b, "청년스테이지ON"


# ---------------------------------------------------------------------------
# 4. 갈매기횟집 — 2x2, 2층. 원색 벽, 대형 천막 차양 + 기둥, 수족관, 바람개비 깃발 4개 (사진 ②)
# ---------------------------------------------------------------------------

FLAGS = [("활어회", "flag_red"), ("물회", "flag_blue"), ("대게", "flag_yellow"), ("매운탕", "flag_red")]


def plastic_table(b, f, u, d, name="table"):
    """플라스틱 원탁 + 빨간 의자 4개 (파사드 앞 u, d)"""
    m = b.m
    x, y = f.xy(u, d)
    m.cylinder(x, y, 0.45, 0.72, 0.76, "plastic_white", n=16)
    m.cylinder(x, y, 0.05, 0.03, 0.72, "metal_dark", n=8)
    m.cylinder(x, y, 0.3, 0.03, 0.06, "metal_dark", n=12)
    for a in range(4):
        ang = a * math.pi / 2 + 0.6
        cx, cy = x + 0.75 * math.cos(ang), y + 0.75 * math.sin(ang)
        m.box(cx - 0.2, cx + 0.2, cy - 0.2, cy + 0.2, 0.42, 0.46, "plastic_red")
        for lx, ly in ((-0.16, -0.16), (0.16, -0.16), (0.16, 0.16), (-0.16, 0.16)):
            m.box(cx + lx - 0.02, cx + lx + 0.02, cy + ly - 0.02, cy + ly + 0.02, 0.03, 0.42, "plastic_red")
    f.reserve(FOREGROUND, u - 0.97, u + 0.97, 0.03, 0.9, d - 0.97, d + 0.97, name)


def hoetjip03(text_fn=None):
    b = Building((2, 2), 13.0, 10.0, setback=5.0, seed=34, text_fn=text_fn)    # y -3..7, 앞마당 5 m
    b.mats.update({
        "wall": render((0.18, 0.55, 0.62)),
        "wall_side": render((0.84, 0.82, 0.78)),
        "sign": sign((0.80, 0.06, 0.04), 0.7),
        "letters_yellow": {"color": (0.98, 0.85, 0.10), "rough": 0.4, "emit": (1.0, 0.9, 0.2), "emit_strength": 2.0},
        "tarp": stripes((0.95, 0.45, 0.05), (0.95, 0.93, 0.88), 0.55),
        "flag_red": {"color": (0.80, 0.06, 0.05), "rough": 0.6, "control": (0, 1, 0)},
        "flag_blue": {"color": (0.06, 0.25, 0.75), "rough": 0.6, "control": (0, 1, 0)},
        "flag_yellow": {"color": (0.95, 0.75, 0.05), "rough": 0.6, "control": (0, 1, 0)},
    })
    g, u = 4.0, 3.0
    b.lot_slab()
    b.shell(g + u)
    f = b.face("front")
    f.storefront(0.5, 12.5, 0.03, 3.1, bay=1.2, doors=[(9.8, 1.8)])
    b.sign_band("front", 0.25, 12.75, 3.2, 3.95, "갈매기횟집", "활어 · 물회 · 매운탕 · 포장", letters="letters_yellow")
    depth = 4.4
    b.awning("front", 0.4, 12.6, 3.0, depth=depth, drop=0.55, valance=0.25, mat="tarp")
    for uu in (0.6, 6.5, 12.4):                                             # 천막 앞 기둥
        f.box(uu - 0.04, uu + 0.04, 0.03, 2.45, depth - 0.12, depth - 0.04, "metal", attached=False)
        f.reserve(FOREGROUND, uu - 0.05, uu + 0.05, 0.03, 2.2, depth - 0.13, depth - 0.03, "tarp_pole")
    b.aquarium("front", 2.0, w=1.8, d0=0.45)
    b.aquarium("front", 4.4, w=1.8, d0=0.45)
    b.fish_props("front", 6.8, d=1.6)
    plastic_table(b, f, 11.0, 2.6)
    for (word, mat), uu in zip(FLAGS, (1.5, 4.0, 7.9, 10.4)):              # 바람개비 깃발 (도로 쪽)
        letters = [b.letters(ch, 0.42, 0.42, 0.01) for ch in word]
        x, y = f.xy(uu, 4.55)
        PR.feather_flag(b.m, x, y, 0.03, mat, letters, letter_mat="letters")
        f.reserve(FOREGROUND, uu - 0.3, uu + 0.3, 0.03, 0.3, 4.27, 4.83, "flag_base")
        f.reserve(FOREGROUND, uu - 0.03, uu + 0.65, 0.3, 3.73, 4.45, 4.6, "flag")
    for i in range(3):
        uu = 1.0 + (b.w - 2.0) * (i + 0.5) / 3
        f.window(uu, g + 0.8, 2.6, 1.5, lit=b.chance(0.5), grille=i != 1, blind=b.blind())
    b.lightbox("front", 0.3 + 0.35, g + 1.0, 0.5, 1.4, "단체", mat="sign")
    side_details(b, back_door_u=2.5, levels=[g], side_n=2, gas_z=3.5)
    b.ac_wall("back", 8.0, 1.4)
    b.bands([g], ("front", "left", "right"), mat="trim")
    b.plinth()
    b.parapet()
    z = b.height
    b.water_tank(b.x0 + 1.6, b.y1 - 1.6, z, r=0.7, h=1.2)
    b.ac_roof(1.5, b.y1 - 1.0, z)
    b.ac_roof(2.8, b.y1 - 1.0, z)
    b.m.cylinder(b.x1 - 1.5, b.y1 - 1.6, 0.04, z, z + 1.4, "metal", n=8)    # 위성 안테나
    b.m.ellipsoid(b.x1 - 1.5, b.y1 - 1.75, z + 1.45, 0.35, 0.08, 0.35, "plastic_white", nu=12, nv=6)
    b.roof_reserve("dish", b.x1 - 1.9, b.x1 - 1.1, b.y1 - 1.9, b.y1 - 1.5, z, z + 1.8)
    b.finalize()
    return b, "갈매기횟집"


# ---------------------------------------------------------------------------
# 5. 해변슈퍼 — 2x2, 2층. 크림색 벽, 파란 금속 박공 지붕 (사진 ⑥의 파란 지붕 건물), 1층 가게 + 주택 출입문
# ---------------------------------------------------------------------------

def blueroof01(text_fn=None):
    b = Building((2, 2), 12.0, 9.5, setback=3.5, seed=35, text_fn=text_fn)     # y -4.5..5
    b.mats.update({
        "wall": render((0.90, 0.84, 0.70)),
        "wall_side": render((0.88, 0.83, 0.71)),
        "roof_tile": {"color": (0.08, 0.28, 0.62), "color2": (0.06, 0.22, 0.52), "pattern": "seam", "axis": "x",
                      "scale": 0.42, "rough": 0.35, "metal": 0.6, "control": (0, 1, 0)},
        "sign": sign((0.06, 0.25, 0.60), 0.6),
        "awning": stripes((0.06, 0.25, 0.62), (0.92, 0.92, 0.90), 0.45),
        "plant": {"color": (0.12, 0.30, 0.08), "color2": (0.30, 0.10, 0.25), "pattern": "noise", "scale": 8.0,
                  "rough": 0.8, "bump": 0.4},
    })
    g, u = 3.6, 2.9
    H = g + u
    b.lot_slab()
    b.shell(H, roof=None)
    f = b.face("front")
    f.storefront(0.5, 8.0, 0.03, 2.9, bay=1.25, transom=2.3, doors=[(2.0, 1.6)])
    f.door(10.0, 1.0, 2.2, leaf="door_wood", name="house")
    b.sign_band("front", 0.25, 8.25, 2.98, 3.5, "해변슈퍼", out=0.25)
    b.awning("front", 0.6, 7.9, 2.8, depth=1.8, drop=0.35, valance=0.22)
    for uu in (1.5, 3.4):                                                   # 가게 앞 진열대 · 아이스크림 냉장고
        f.box(uu - 0.7, uu + 0.7, 0.03, 0.85, 1.9, 2.5, "plastic_white", attached=False)
        f.reserve(FOREGROUND, uu - 0.7, uu + 0.7, 0.03, 0.85, 1.9, 2.5, "stand")
    f.box(5.0, 6.4, 0.03, 0.9, 1.9, 2.6, "ac", attached=False)
    f.box(5.05, 6.35, 0.9, 0.92, 1.95, 2.55, "glass_shop", attached=False)
    f.reserve(FOREGROUND, 5.0, 6.4, 0.03, 0.95, 1.9, 2.6, "freezer")
    for i, uu in enumerate((2.2, 6.0, 9.8)):
        if f.window(uu, g + 0.85, 1.8, 1.3, style="casement", lit=b.chance(0.5), blind=b.blind()) and i != 1:
            f.box(uu - 0.95, uu + 0.95, g + 0.62, g + 0.79, 0.08, 0.38, "wood", attached=False)   # 창 화분대
            f.box(uu - 0.9, uu + 0.9, g + 0.79, g + 0.95, 0.12, 0.34, "plant", attached=False)
            f.reserve(FOREGROUND, uu - 0.95, uu + 0.95, g + 0.62, g + 0.95, 0.08, 0.38, "flower_box")
    side_details(b, back_door_u=b.w - 2.0, levels=[g], side_n=1, gas_z=3.2)
    b.ac_wall("back", 4.0, 1.4)
    b.bands([g], ("front", "left", "right"), h=0.12, out=0.05)
    b.plinth(h=0.35)
    b.gable_roof("x", rise=2.2, overhang=0.55, mat="roof_tile")
    b.finalize()
    return b, "해변슈퍼"


DESIGNS = {
    "IlsanTanibayHotel": tanibay,
    "IlsanCornerTower01": corner01,
    "IlsanCornerTower02": corner02,
    "IlsanYouthStage": youth_stage,
    "IlsanHoetjip03": hoetjip03,
    "IlsanBlueRoof01": blueroof01,
}
