"""일산해수욕장 주변 실제 브랜드 매장: 스타벅스 울산일산비치DT점, 테라스파크 2개 동(엔제리너스 · 파스쿠치 · 공차 /
봉구비어 · 드롭탑 · 오가다 · 꽃집), 홈플러스 울산동구점, GS25, CU.

실제 정보 (검색 기준)
  테라스파크  울산 동구 방어진순환도로 652 (일산동 945). 2011년 준공, 지하 1층 · 지상 4층, 5개 동이 이어진 '스트리트형 상가',
             일산해수욕장 바로 앞. 1층에 엔제리너스 · 파스쿠치 · 공차 · 봉구비어 · 드롭탑 · 오가다 등 (스타벅스 2011~2023)
  스타벅스 울산일산비치DT점  일산진11길 95. 드라이브스루 + 루프탑
  홈플러스 울산동구점  방어진순환도로 637 (일산동), 테라스파크 맞은편
간판은 상표 그림이 아니라 브랜드 색과 글자(나눔고딕)로 만든 근사치이고, 외관 세부는 각 브랜드 매장의 흔한 모습을 따른 추정이다.
"""

import math

import props as PR
from designs import BRICK, Building, render, side_details, sign
from geom import BOTTOM, FIXTURE, FOREGROUND, SIGN, Facade, rects_minus
from landmarks import glass_rail, plastic_table


def glow(color, strength=2.5, rough=0.35):
    """빛나는 채널 글자 · 띠"""
    return {"color": color, "rough": rough, "emit": tuple(min(1.0, c * 1.25 + 0.02) for c in color),
            "emit_strength": strength}


def solid(color, rough=0.6, metal=0.0):
    return {"color": color, "rough": rough, "metal": metal}


WHITE = glow((0.95, 0.95, 0.93), 2.5)
PANEL_DARK = {"color": (0.09, 0.09, 0.10), "color2": (0.07, 0.07, 0.08), "pattern": "panel", "scale": (1.0, 0.5),
              "mortar": 0.004, "mortar_color": (0.03, 0.03, 0.03), "rough": 0.4, "metal": 0.5}
PANEL_WHITE = {"color": (0.86, 0.86, 0.85), "color2": (0.82, 0.82, 0.81), "pattern": "panel", "scale": (1.2, 0.6),
               "mortar": 0.004, "mortar_color": (0.55, 0.55, 0.55), "rough": 0.35, "metal": 0.2}
WOOD_LOUVER = {"color": (0.40, 0.23, 0.11), "color2": (0.28, 0.15, 0.07), "pattern": "wood", "rough": 0.55, "bump": 0.1}
HAZARD = {"color": (0.92, 0.70, 0.02), "color2": (0.03, 0.03, 0.03), "pattern": "stripes", "scale": 0.25, "rough": 0.5}


def poster(f, u, z, w, h, d, board, text, letters, text_fn_b):
    """유리 안쪽에 붙인 포스터 (판 + 글자). d = 유리 앞면 깊이"""
    f.box(u - w / 2, u + w / 2, z, z + h, d, d + 0.006, board, attached=False)
    t = text_fn_b(text, w * 0.8, h * 0.55, 0.004)
    if t:
        f.text(t, u, z + h / 2, d + 0.006, letters, kind=None)


# ---------------------------------------------------------------------------
# 1. 스타벅스 울산일산비치DT점 — 3x4, 2층 + 루프탑. 드라이브스루 차로가 건물을 시계 반대로 감싼다
#    (운전석 왼쪽에 주문판 · 픽업 창): 오른쪽 차로로 들어와 뒤에서 주문, 왼쪽 면 픽업 창에서 받고 앞으로 나간다.
# ---------------------------------------------------------------------------

def emblem(f, u, z, r, d=0.0, green="sb_green", white="letters_sb", n=32):
    """원형 엠블럼: 초록 원판 + 흰 고리 + 초록 안쪽 + 흰 별 (상표 그림 대신 쓰는 근사치)"""
    f.disc(u, z, d, r, 0.10, green, n=n)
    f.disc(u, z, d + 0.10, r * 0.88, 0.015, white, n=n)
    f.disc(u, z, d + 0.115, r * 0.76, 0.015, green, n=n)
    f.poly(PR.star(u, z, r * 0.5, r * 0.2), d + 0.13, 0.025, white)


def starbucks_dt(text_fn=None):
    b = Building((3, 4), 15.0, 15.0, setback=7.0, seed=61, text_fn=text_fn)    # x -7.5..7.5, y -9..6
    b.mats.update({
        "wall": PANEL_DARK, "wall_side": PANEL_DARK,
        "sb_brick": dict(BRICK, color=(0.30, 0.12, 0.08), color2=(0.25, 0.10, 0.06)),
        "sb_wood": WOOD_LOUVER,
        "sb_green": sign((0.0, 0.16, 0.07), 0.6),
        "letters_sb": WHITE,
        "parasol_sb": solid((0.0, 0.16, 0.07), 0.7),
        "menu": {"color": (0.12, 0.10, 0.09), "color2": (0.85, 0.82, 0.75), "pattern": "tile", "scale": (0.42, 0.16),
                 "mortar": 0.02, "mortar_color": (0.9, 0.88, 0.8), "rough": 0.4, "emit": (1.0, 0.95, 0.85),
                 "emit_strength": 1.2},
        "hazard": HAZARD,
        "plate_white": solid((0.92, 0.92, 0.90), 0.5),
        "letters_black": solid((0.03, 0.03, 0.03), 0.5),
    })
    g, u = 4.5, 4.0
    H = g + u
    m = b.m
    b.lot_slab()
    b.shell(H, zones={s: [(0.03, 1.0, "sb_brick"), (1.0, H, "wall")] for s in ("front", "back", "left", "right")})
    # 정면: 1층 통유리 + 목재 루버 캐노피, 2층 세로 목재 핀 커튼월, 원형 엠블럼, STARBUCKS 글자
    f = b.face("front")
    f.storefront(0.5, 14.5, 0.03, 3.9, bay=1.6, transom=3.0, doors=[(4.0, 1.8)])
    b.canopy("front", 0.3, 14.7, 4.0, depth=2.2, mat="sb_wood")
    for k in range(14):                                                    # 캐노피 아래 목재 루버 살
        uu = 0.5 + k * 1.03
        f.box(uu, uu + 0.08, 3.86, 4.0, 0.25, 2.1, "sb_wood", attached=False)
    f.curtain(0.4, 10.5, g + 0.1, H - 0.9, 3.0, 1.5, fins=0.3, fin_mat="sb_wood", lit=0.6, rng=b.rng, name="cw2")
    emblem(f, 12.8, g + 1.6, 1.25)
    f.reserve(SIGN, 11.5, 14.1, g + 0.3, g + 2.9, 0, 0.2, "emblem")
    b.wall_text("front", "STARBUCKS", 5.45, H - 0.45, 9.5, 0.55, mat="letters_sb")
    t = b.letters("WiFi · 텀블러 할인 · 사이렌 오더", 3.6, 0.22, 0.005)
    if t:
        f.glass_text(t, 9.0, 2.2, recess=0.25)
    # 왼쪽 면 (나가는 차로): 앞 모서리 유리, 픽업 창 + 작은 캐노피 + PICK-UP 간판, 2층 유리 · 엠블럼
    lf = b.face("left")                                                    # u = 6 - y, 정면 쪽 u = 15
    lf.storefront(9.5, 14.5, 0.03, 3.9, bay=1.6, transom=3.0, name="glass_l")
    lf.curtain(6.0, 14.88, g + 0.1, H - 0.9, 3.0, 1.5, fins=0.3, fin_mat="sb_wood", lit=0.6, rng=b.rng,
               name="cw2_l")
    lf.window(6.0, 1.05, 2.0, 1.25, frame="frame_dark", name="pickup")
    b.canopy("left", 4.6, 7.4, 2.55, depth=1.1, mat="sb_green")
    b.lightbox("left", 6.0, 2.85, 2.2, 0.42, "PICK-UP", mat="sb_green", letters="letters_sb")
    emblem(lf, 2.6, g + 1.6, 1.1)
    lf.reserve(SIGN, 1.4, 3.8, g + 0.45, g + 2.75, 0, 0.2, "emblem_l")
    # 오른쪽 면 (들어오는 차로): 앞 모서리 유리, 2층 유리, 큰 엠블럼, DRIVE THRU 간판
    rf = b.face("right")                                                   # u = y + 9, 정면 쪽 u = 0
    rf.storefront(0.5, 5.5, 0.03, 3.9, bay=1.6, transom=3.0, name="glass_r")
    rf.curtain(0.12, 8.0, g + 0.1, H - 0.9, 3.0, 1.5, fins=0.3, fin_mat="sb_wood", lit=0.6, rng=b.rng,
               name="cw2_r")
    emblem(rf, 11.5, g + 1.6, 1.25)
    rf.reserve(SIGN, 10.2, 12.8, g + 0.3, g + 2.9, 0, 0.2, "emblem_r")
    b.lightbox("right", 10.5, 2.4, 3.4, 0.6, "DRIVE THRU", mat="sb_green", letters="letters_sb")
    # 뒤: 직원 문, 실외기, 2층 창, 주문판 · 미리 보는 메뉴판 · 스피커 기둥 (뒤 차로를 향해)
    bk = b.face("back")                                                    # u = 7.5 - x
    bk.door(13.5, 1.0, 2.2, leaf="door_metal", canopy=False, name="staff")
    for uu in (2.5, 6.0, 9.5, 13.0):
        bk.window(uu, g + 1.0, 1.4, 1.2, style="fixed", lit=b.chance(0.4))
    b.ac_wall("back", 1.6, 1.3, d=0.3)
    b.downpipe("back", 0.3, top=H + 0.5)
    for uu, w, h, header in ((4.5, 1.4, 1.2, None), (9.5, 2.6, 1.6, "MENU")):
        z0 = 0.9
        for pu in (uu - w / 2 + 0.1, uu + w / 2 - 0.1):
            bk.box(pu - 0.05, pu + 0.05, 0.03, z0 + h + 0.35, 0.92, 1.02, "metal_dark", attached=False)
        bk.box(uu - w / 2, uu + w / 2, z0, z0 + h, 0.9, 1.04, "menu", attached=False)
        bk.box(uu - w / 2, uu + w / 2, z0 + h, z0 + h + 0.28, 0.9, 1.04, "sb_green", attached=False)
        bk.box(uu - w / 2 - 0.05, uu + w / 2 + 0.05, z0 + h + 0.28, z0 + h + 0.36, 0.85, 1.1, "metal_dark",
               attached=False)
        if header:
            t = b.letters(header, w * 0.6, 0.2, 0.01)
            if t:
                bk.text(t, uu, z0 + h + 0.14, 1.04, "letters_sb", kind=None)
        bk.reserve(FOREGROUND, uu - w / 2 - 0.05, uu + w / 2 + 0.05, 0.03, z0 + h + 0.36, 0.85, 1.1, "menu_board")
    bk.box(11.4, 11.6, 0.03, 1.25, 0.92, 1.12, "metal_dark", attached=False)              # 스피커 기둥
    bk.box(11.3, 11.7, 1.25, 1.55, 0.88, 1.16, "sb_green", attached=False)
    bk.disc(11.5, 1.4, 1.16, 0.08, 0.01, "grille")
    bk.reserve(FOREGROUND, 11.3, 11.7, 0.03, 1.56, 0.88, 1.18, "speaker_post")
    b.gas_pipe("back", 3.6, 0.9)
    # 루프탑: 데크 + 유리 난간 + 초록 파라솔 테이블 + 화분 + 계단실(엠블럼) + 실외기
    b.parapet(h=0.35, mat="wall")
    z, pt = b.height, b.parapet_t
    m.box(b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y1 - 4.2, z, z + 0.12, "deck", skip=(BOTTOM,))
    b.roof_reserve("deck", b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y1 - 4.2, z, z + 0.12)
    zr = z + 0.12
    glass_rail(b, b.x0 + pt + 0.03, b.x1 - pt - 0.03, b.y0 + pt + 0.03, b.y0 + pt + 0.07, zr, name="rail_f")
    glass_rail(b, b.x0 + pt + 0.03, b.x0 + pt + 0.07, b.y0 + pt + 0.1, b.y1 - 4.25, zr, name="rail_l")
    glass_rail(b, b.x1 - pt - 0.07, b.x1 - pt - 0.03, b.y0 + pt + 0.1, b.y1 - 4.25, zr, name="rail_r")
    for tx, ty in ((-4.0, -6.0), (0.0, -6.0), (4.0, -6.0), (-2.4, -2.0), (2.4, -2.0)):
        b.roof_reserve("roof_cafe", *PR.cafe_set(m, tx, ty, zr, "parasol_sb", r=1.05))
    for px in (-5.9, 5.9):
        b.roof_reserve("roof_planter", *PR.planter(m, px - 0.6, px + 0.6, -2.9, -1.1, z=zr, seed=int(px), shrubs=1))
    top = b.stair_house(b.x0 + 0.6, b.x0 + 4.2, b.y1 - 3.8, b.y1 - 0.6, h=2.8)
    emblem(Facade(m, "front", b.x0 + 0.6, b.x0 + 4.2, b.y1 - 3.8, b.y1 - 0.6), 3.0, z + 1.6, 0.45, n=24)
    for i in range(3):
        b.ac_roof(b.x1 - 1.2 - i * 1.25, b.y1 - 1.0, z)
    b.top = max(b.top, top)
    # 부지: 드라이브스루 차로 (오른쪽 들어옴 -> 뒤 -> 왼쪽 나감) + 연석 + 화살표 + 바닥 글자 + 높이 제한 문
    e = 11.6
    for x0, x1, y0, y1 in ((8.0, e, -15.95, 8.0), (-e, e, 8.0, e), (-e, -8.0, -15.95, 8.0)):
        m.box(x0, x1, y0, y1, 0.03, 0.04, "asphalt", skip=(BOTTOM,))
    for x0, x1, y0, y1 in ((7.7, 8.0, -15.95, 7.7), (-8.0, -7.7, -15.95, 7.7), (-8.0, 8.0, 7.7, 8.0)):
        m.box(x0, x1, y0, y1, 0.03, 0.18, "granite", skip=(BOTTOM,))
    for x, y, a in ((9.8, -7.0, 0.0), (9.8, 3.0, 0.0), (3.0, 9.8, math.pi / 2), (-4.0, 9.8, math.pi / 2),
                    (-9.8, 1.0, math.pi), (-9.8, -11.0, math.pi)):
        PR.arrow(m, x, y, 0.04, a, length=2.6, width=0.45)
    PR.flat_text(m, b.letters("DRIVE THRU", 3.0, 0.7, 0.003), 9.8, -11.5, 0.04, "paint_white", 0.0, 1.8)
    PR.flat_text(m, b.letters("천천히", 2.6, 0.7, 0.003), -9.8, -5.0, 0.04, "paint_white", math.pi, 1.8)
    gy = -14.8                                                               # 높이 제한 문 (들어오는 차로)
    for gx in (7.8, 11.75):
        m.box(gx - 0.12, gx + 0.12, gy - 0.12, gy + 0.12, 0.03, 3.6, "metal_dark")
    m.box(7.8, 11.75, gy - 0.12, gy + 0.12, 2.6, 2.95, "hazard")
    m.box(8.4, 11.15, gy - 0.1, gy + 0.1, 2.95, 3.6, "sb_green")
    gf = Facade(m, "front", 8.4, 11.15, gy - 0.1, gy + 0.1)
    t = b.letters("DRIVE THRU", 2.4, 0.4, 0.02)
    if t:
        gf.text(t, 1.375, 3.275, 0.0, "letters_sb", kind=None)
    pf = Facade(m, "front", 8.9, 10.65, gy - 0.16, gy - 0.12)
    pf.box(0, 1.75, 2.63, 2.92, 0, 0.02, "plate_white")
    t = b.letters("높이제한 2.5m", 1.5, 0.2, 0.005)
    if t:
        pf.text(t, 0.875, 2.775, 0.02, "letters_black", kind=None)
    # 앞마당: 초록 파라솔 테이블 3 + 화분 + 기둥 간판 (원형 엠블럼 양면 + DRIVE THRU)
    for tu in (3.0, 7.5, 12.0):
        x, y = f.xy(tu, 4.0)
        PR.cafe_set(m, x, y, 0.03, "parasol_sb", r=1.1)
        f.reserve(FOREGROUND, tu - 1.1, tu + 1.1, 0.03, 2.4, 2.9, 5.1, "terrace")
    for tu in (0.5, 14.5):
        x, y = f.xy(tu, 5.3)
        PR.planter(m, x - 0.6, x + 0.6, y - 0.45, y + 0.45, seed=int(tu), shrubs=1)
        f.reserve(FOREGROUND, tu - 0.6, tu + 0.6, 0.03, 0.9, 4.85, 5.75, "planter")
    px, py = 6.75, -15.2
    m.box(px - 0.2, px + 0.2, py - 0.2, py + 0.2, 0.03, 4.6, "metal_dark")
    m.box(px - 0.7, px + 0.7, py - 0.12, py + 0.12, 3.3, 3.95, "sb_green")
    m.box(px - 1.05, px + 1.05, py - 0.08, py + 0.08, 4.4, 6.5, "metal_dark")
    for side in ("front", "back"):
        pfac = Facade(m, side, px - 1.05, px + 1.05, py - 0.08, py + 0.08)
        emblem(pfac, 1.05, 5.45, 0.98, n=28)
        tt = b.letters("DRIVE THRU", 1.2, 0.3, 0.01)
        if tt:
            Facade(m, side, px - 0.7, px + 0.7, py - 0.12, py + 0.12).text(tt, 0.7, 3.625, 0.0, "letters_sb", kind=None)
    f.reserve(FOREGROUND, 13.2, 15.4, 0.03, 6.5, 6.0, 6.4, "pylon")
    b.top = max(b.top, 6.5)
    b.finalize()
    return b, "스타벅스 울산일산비치DT점"


# ---------------------------------------------------------------------------
# 2. 테라스파크 — 4x3, 지상 4층. 층마다 3 m 씩 물러나 앞에 테라스가 생기는 계단형 상가.
#    1층 브랜드 카페 · 가게 (간판 · 차양 · 테라스 테이블), 2층 카페 좌석, 3~4층 학원 · 운동 · 병원, 세로 상가 안내판
# ---------------------------------------------------------------------------

TP = {
    1: {"seed": 62, "title": "테라스파크 A동",
        "wall": {"color": (0.78, 0.74, 0.68), "color2": (0.74, 0.70, 0.64), "pattern": "tile", "scale": (0.9, 0.45),
                 "mortar": 0.005, "mortar_color": (0.6, 0.57, 0.52), "rough": 0.5, "bump": 0.15},
        "shops": [  # u0, u1, 글자, 보조, 판 색, 글자 색, 문 u, 차양 색
            (0.5, 10.0, "ANGEL-IN-US", "COFFEE · 엔제리너스", (0.20, 0.06, 0.04), (0.98, 0.92, 0.80), 3.4,
             (0.28, 0.08, 0.05)),
            (10.6, 20.0, "PASCUCCI", "Caffè · 파스쿠치", (0.70, 0.02, 0.02), (0.98, 0.98, 0.95), 18.0,
             (0.70, 0.02, 0.02)),
            (20.6, 29.5, "Gong cha", "공차 · 밀크티", (0.78, 0.02, 0.03), (0.98, 0.98, 0.95), 27.5, None)],
        "glass2": ["ANGEL-IN-US 2F", "PASCUCCI 2F", "Gong cha"],
        "f3": [("필라테스 · 요가", (0.85, 0.45, 0.05)), ("수학 · 영어 학원", (0.10, 0.25, 0.60))],
        "f4": ("일산 스터디카페", (0.08, 0.40, 0.30)),
        "pylon": [("엔제리너스", (0.20, 0.06, 0.04)), ("파스쿠치", (0.70, 0.02, 0.02)), ("공차", (0.78, 0.02, 0.03)),
                  ("필라테스", (0.85, 0.45, 0.05)), ("학원", (0.10, 0.25, 0.60)), ("스터디카페", (0.08, 0.40, 0.30))]},
    2: {"seed": 63, "title": "테라스파크 C동",
        "wall": dict(BRICK, color=(0.46, 0.26, 0.18), color2=(0.40, 0.22, 0.15)),
        "shops": [
            (0.5, 8.5, "봉구비어", "BONGGU BEER", (0.05, 0.05, 0.06), (0.98, 0.80, 0.05), 2.2, (0.05, 0.05, 0.06)),
            (9.1, 18.5, "DROPTOP", "COFFEE · 드롭탑", (0.92, 0.92, 0.90), (0.10, 0.08, 0.07), 16.6,
             (0.25, 0.20, 0.17)),
            (19.1, 25.0, "오가다", "OGADA · 한방차", (0.12, 0.30, 0.16), (0.98, 0.95, 0.85), 22.0, None),
            (25.6, 29.5, "줄리런던", "FLOWER", (0.85, 0.80, 0.72), (0.15, 0.25, 0.15), 27.6, None)],
        "glass2": ["봉구비어 2F", "DROPTOP 2F", "OGADA"],
        "f3": [("일산 치과", (0.05, 0.40, 0.55)), ("PC방", (0.10, 0.25, 0.70))],
        "f4": ("코인노래방", (0.75, 0.12, 0.45)),
        "pylon": [("봉구비어", (0.05, 0.05, 0.06)), ("드롭탑", (0.25, 0.20, 0.17)), ("오가다", (0.12, 0.30, 0.16)),
                  ("꽃집", (0.85, 0.45, 0.55)), ("치과", (0.05, 0.40, 0.55)), ("노래방", (0.75, 0.12, 0.45))]},
}


def terrace_park(variant, text_fn=None):
    spec = TP[variant]
    b = Building((4, 3), 30.0, 20.0, setback=2.5, seed=spec["seed"], text_fn=text_fn)   # x -15..15, y -9.5..10.5
    b.mats.update({"wall": spec["wall"], "wall_side": render((0.84, 0.82, 0.78), grime=0.15),
                   "terrace_floor": dict(WOOD_LOUVER, color=(0.45, 0.30, 0.18))})
    m = b.m
    x0, x1, y0, y1 = b.x0, b.x1, b.y0, b.y1
    f1, f2, f3, f4 = 4.8, 8.8, 12.6, 16.4
    step = 3.0
    side_zone = lambda z0, z1: [(z0, z1, "wall_side")]                         # noqa: E731
    b.lot_slab()
    b.shell(f1, roof=None)
    for k, (key, za, zb) in enumerate((("f2", f1, f2), ("f3", f2, f3), ("f4", f3, f4))):
        yy = y0 + step * (k + 1)
        b.volume(key, x0, x1, yy, y1, za, zb, roof="roof" if key == "f4" else None,
                 zones={"front": [(za, zb, "wall")], "left": side_zone(za, zb), "right": side_zone(za, zb),
                        "back": side_zone(za, zb)})
    for k, (key, zb) in enumerate((("f1", f1), ("f2", f2), ("f3", f3))):        # 층마다 앞 테라스 데크
        ya, yb = y0 + step * k, y0 + step * (k + 1)
        m.box(x0, x1, ya, yb, zb, zb + 0.15, "terrace_floor", skip=(BOTTOM,))
        b.roof_reserve("terrace_" + key, x0, x1, ya, yb, zb, zb + 0.15)
    # 1층 브랜드 가게
    f = b.face("front")
    for i, (u0, u1, text, sub, board, letter, door_u, awn) in enumerate(spec["shops"]):
        b.mats[f"board{i}"] = sign(board, 0.6)
        b.mats[f"letters_tp{i}"] = glow(letter, 2.2)
        f.storefront(u0, u1, 0.03, 3.9, bay=1.5, transom=2.8, doors=[(door_u, 1.6)], name=f"shop{i}")
        b.sign_band("front", u0 + 0.05, u1 - 0.05, 4.0, 4.65, text, sub, out=0.3, mat=f"board{i}", letters=f"letters_tp{i}")
        if awn:
            b.mats[f"awning{i}"] = solid(awn, 0.7)
            b.awning("front", u0 + 0.2, u1 - 0.2, 3.8, depth=1.2, drop=0.3, valance=0.18, mat=f"awning{i}")
            b.mats[f"parasol{i}"] = solid(awn, 0.7)
            for tu in (u0 + 1.5, u1 - 1.5):
                if abs(tu - door_u) > 2.0 and u0 + 1.0 <= tu <= u1 - 1.0:
                    x, y = f.xy(tu, 1.55)
                    PR.cafe_set(m, x, y, 0.03, f"parasol{i}", r=0.88, chairs=2, h=2.3)
                    f.reserve(FOREGROUND, tu - 0.95, tu + 0.95, 0.03, 2.3, 0.6, 2.45, "cafe_set")
        t = b.letters(text, (u1 - u0) * 0.4, 0.3, 0.004)
        if t:
            f.glass_text(t, (u0 + door_u) / 2 if door_u - u0 > 3 else (door_u + u1) / 2, 2.1, recess=0.25)
    if variant == 2:                                                       # 꽃집 앞 꽃 양동이 계단 진열대
        b.mats["flower"] = {"color": (0.80, 0.25, 0.45), "color2": (0.95, 0.85, 0.20), "pattern": "noise",
                            "scale": 9.0, "rough": 0.8, "bump": 0.4}
        for k in range(3):
            f.box(25.75, 26.6, 0.03, 0.25 + k * 0.25, 0.4 + k * 0.3, 0.7 + k * 0.3, "wood", attached=False)
            f.box(25.8, 26.55, 0.25 + k * 0.25, 0.5 + k * 0.25, 0.42 + k * 0.3, 0.68 + k * 0.3, "flower",
                  attached=False)
        f.reserve(FOREGROUND, 25.75, 26.6, 0.03, 1.0, 0.4, 1.3, "flower_stand")
    # 세로 상가 안내판 (앞 왼쪽 모서리, 땅에 선 기둥)
    pu, pd = 0.6, 1.9
    f.box(pu - 0.45, pu + 0.45, 0.03, 7.4, pd - 0.2, pd + 0.2, "frame_dark", attached=False)
    zc = 7.1
    for k, (name, col) in enumerate(spec["pylon"]):
        b.mats[f"pylon{k}"] = sign(col, 0.6)
        f.box(pu - 0.42, pu + 0.42, zc - 0.85, zc - 0.05, pd + 0.2, pd + 0.24, f"pylon{k}", attached=False)
        t = b.letters(name, 0.7, 0.4, 0.01)
        if t:
            f.text(t, pu, zc - 0.45, pd + 0.24, "letters", kind=None)
        zc -= 0.95
    t = b.letters("TERRACE PARK", 0.75, 0.16, 0.01)
    if t:
        f.text(t, pu, 1.0, pd + 0.2, "letters", kind=None)
    f.reserve(FOREGROUND, pu - 0.46, pu + 0.46, 0.03, 7.4, pd - 0.21, pd + 0.26, "pylon")
    # 2층: 카페 좌석 통유리 (유리 글자), 테라스 테이블
    fr2 = b.face("f2:front")
    fr2.curtain(0.4, 29.6, f1 + 0.25, f2 - 0.3, 3.5, 1.5, spandrel=0.3, lit=0.6, rng=b.rng, name="cw_f2")
    for k, word in enumerate(spec["glass2"]):
        t = b.letters(word, 3.4, 0.4, 0.004)
        if t:
            fr2.glass_text(t, 5.0 + k * 10.0, f1 + 2.6, recess=0.12)
    zt = f1 + 0.15
    glass_rail(b, x0 + 0.05, x1 - 0.05, y0 + 0.04, y0 + 0.08, zt, name="rail_t1")
    for sx in (x0 + 0.04, x1 - 0.08):
        glass_rail(b, sx, sx + 0.04, y0 + 0.12, y0 + step - 0.05, zt, name="rail_t1_side")
    for k, tx in enumerate((-9.5, 0.0, 9.5)):
        b.mats[f"parasol_t{k}"] = solid(spec["shops"][min(k, len(spec["shops"]) - 1)][4], 0.7)
        b.roof_reserve("t1_cafe", *PR.cafe_set(m, tx, y0 + 1.5, zt, f"parasol_t{k}", r=1.0, chairs=3))
    # 3층: 학원 · 운동 간판 2 + 유리, 테라스 화분 · 벤치
    fr3 = b.face("f3:front")
    for (name, col), (u0, u1) in zip(spec["f3"], ((0.5, 14.6), (15.4, 29.5))):
        b.mats["sign_" + name] = sign(col, 0.7)
        b.sign_band("f3:front", u0, u1, f2 + 0.15, f2 + 0.8, name, out=0.22, mat="sign_" + name)
    fr3.curtain(0.4, 29.6, f2 + 0.95, f3 - 0.25, 2.85, 1.6, spandrel=0.25, lit=0.5, rng=b.rng, name="cw_f3")
    zt = f2 + 0.15
    glass_rail(b, x0 + 0.05, x1 - 0.05, y0 + step + 0.04, y0 + step + 0.08, zt, name="rail_t2")
    for sx in (x0 + 0.04, x1 - 0.08):
        glass_rail(b, sx, sx + 0.04, y0 + step + 0.12, y0 + 2 * step - 0.05, zt, name="rail_t2_side")
    for k, px in enumerate((-12.0, -4.0, 4.0, 12.0)):
        b.roof_reserve("t2_planter", *PR.planter(m, px - 1.0, px + 1.0, y0 + step + 0.6, y0 + step + 1.4, z=zt,
                                                  seed=k + variant, shrubs=2))
    for bx in (-8.0, 0.0, 8.0):
        b.roof_reserve("t2_bench", *PR.led_bench(m, bx, y0 + step + 2.2, zt, length=2.2))
    # 4층: 간판 + 유리, 테라스 화분 · 파라솔
    fr4 = b.face("f4:front")
    name, col = spec["f4"]
    b.mats["sign_f4"] = sign(col, 0.7)
    b.sign_band("f4:front", 4.0, 26.0, f3 + 0.15, f3 + 0.8, name, out=0.22, mat="sign_f4")
    fr4.curtain(0.4, 29.6, f3 + 0.95, f4 - 0.25, 2.85, 1.6, spandrel=0.25, lit=0.5, rng=b.rng, name="cw_f4")
    zt = f3 + 0.15
    glass_rail(b, x0 + 0.05, x1 - 0.05, y0 + 2 * step + 0.04, y0 + 2 * step + 0.08, zt, name="rail_t3")
    for sx in (x0 + 0.04, x1 - 0.08):
        glass_rail(b, sx, sx + 0.04, y0 + 2 * step + 0.12, y0 + 3 * step - 0.05, zt, name="rail_t3_side")
    for k, px in enumerate((-10.0, 10.0)):
        b.roof_reserve("t3_planter", *PR.planter(m, px - 1.2, px + 1.2, y0 + 2 * step + 0.6, y0 + 2 * step + 1.5,
                                                  z=zt, seed=k + 5, shrubs=3))
    b.mats["parasol_t4"] = solid(spec["f4"][1], 0.7)
    for tx in (-3.0, 3.0):
        b.roof_reserve("t3_cafe", *PR.cafe_set(m, tx, y0 + 2 * step + 1.5, zt, "parasol_t4", r=1.0, chairs=3))
    # 옆 · 뒤
    for side, vol_w in (("left", 20.0), ("right", 20.0)):
        sf = b.face(side)
        corner = (15.5, 19.5) if side == "left" else (0.5, 4.5)
        sf.storefront(*corner, 0.03, 3.9, bay=1.5, transom=2.8, name="shop_side")
        sf.door(vol_w / 2 if side == "left" else vol_w / 2, 1.4, 2.4, leaf="glass_door", name="hall")
        for key, za in (("f2", f1), ("f3", f2), ("f4", f3)):
            vf = b.face(f"{key}:{side}")
            for uu in [vf.width * (k + 0.5) / 3 for k in range(3)]:
                vf.window(uu, za + 1.0, 1.6, 1.6, lit=b.chance(0.5), blind=b.blind())
    bk = b.face("back")
    for uu in (4.0, 15.0, 26.0):
        bk.door(uu, 1.0, 2.2, leaf="door_metal", canopy=False, name="back_door")
    for uu in (8.0, 11.5, 19.5, 22.5):
        bk.window(uu, 1.3, 1.4, 1.0, style="fixed", grille=True, lit=0.0)
    for key, za in (("f2", f1), ("f3", f2), ("f4", f3)):
        vf = b.face(f"{key}:back")
        for k in range(6):
            vf.window(2.5 + k * 5.0, za + 1.1, 1.4, 1.3, lit=b.chance(0.4), blind=b.blind())
        for uu in (5.0, 15.0, 25.0):
            b.ac_wall(f"{key}:back", uu, za + 0.4, d=0.3)
    b.downpipe("back", 0.35, top=f4 + 0.9)
    b.downpipe("back", 29.65, top=f4 + 0.9)
    b.gas_pipe("back", 3.4, 1.2)
    b.plinth()
    # 옥상: 난간벽, 'TERRACE PARK' 옥상 글자 틀, 계단실, 물탱크, 실외기
    b.parapet(h=1.0, vol="f4")
    zr = f4
    gy = y0 + 3 * step + 0.6
    for px in (-9.0, -3.0, 3.0, 9.0):
        m.box(px - 0.06, px + 0.06, gy + 0.08, gy + 0.2, zr, zr + 2.4, "metal_dark")
    m.box(-10.0, 10.0, gy, gy + 0.08, zr + 1.0, zr + 2.3, "metal_dark")
    t = b.letters("TERRACE PARK", 18.0, 1.1, 0.08)
    if t:
        Facade(m, "front", -10.0, 10.0, gy, gy + 0.08).text(t, 10.0, zr + 1.65, 0.0, "letters", kind=None)
    b.roof_reserve("roof_sign", -10.1, 10.1, gy - 0.1, gy + 0.3, zr, zr + 2.4)
    top = b.stair_house(x1 - 4.6, x1 - 1.0, y1 - 4.2, y1 - 0.6, h=3.0)
    b.water_tank(x1 - 2.8, y1 - 2.4, top, r=0.8, h=1.3)
    for i in range(6):
        b.ac_roof(x0 + 1.6 + i * 1.3, y1 - 1.2, zr)
    b.finalize()
    return b, spec["title"]


def terrace_park_a(text_fn=None):
    return terrace_park(1, text_fn)


def terrace_park_c(text_fn=None):
    return terrace_park(2, text_fn)


# ---------------------------------------------------------------------------
# 3. 홈플러스 울산동구점 — 8x6, 3층 대형마트 + 옥상 주차장. 유리 아트리움 정문 + 캐노피, 큰 Homeplus 글자,
#    빨강 · 주황 띠, 1층 임대 매장, 카트 보관대, 주차장 진입 경사로 입구, 뒤 하역장
# ---------------------------------------------------------------------------

HP_RED = (0.72, 0.02, 0.02)
HP_ORANGE = (0.92, 0.28, 0.01)


def homeplus(text_fn=None):
    b = Building((8, 6), 56.0, 38.0, setback=7.0, seed=64, text_fn=text_fn)    # x -28..28, y -17..21
    b.mats.update({
        "wall": PANEL_WHITE, "wall_side": dict(PANEL_WHITE, color=(0.80, 0.80, 0.79), color2=(0.76, 0.76, 0.75)),
        "hp_red": dict(glow(HP_RED, 1.2), rough=0.4), "hp_orange": dict(glow(HP_ORANGE, 1.0), rough=0.4),
        "letters_hp": glow(HP_RED, 3.5), "hp_canopy": solid((0.92, 0.92, 0.91), 0.35, 0.2),
        "sign_daiso": sign((0.75, 0.02, 0.05), 0.7), "sign_olive": sign((0.35, 0.55, 0.10), 0.6),
        "sign_lotteria": sign((0.75, 0.02, 0.02), 0.7), "sign_pharm": sign((0.05, 0.40, 0.20), 0.6),
        "sign_p": sign((0.02, 0.15, 0.55), 0.8), "parking_deck": dict(PANEL_WHITE, color=(0.25, 0.25, 0.26),
                                                                     color2=(0.22, 0.22, 0.23), scale=(5.0, 2.5)),
        "cross": {"color": (0.1, 0.9, 0.3), "rough": 0.3, "emit": (0.1, 1.0, 0.35), "emit_strength": 4.0},
        "hazard": HAZARD,
    })
    g, u = 6.0, 5.5
    H = g + 2 * u
    m = b.m
    b.lot_slab()
    b.shell(H)
    f = b.face("front")
    # 아트리움 정문: 1층 유리 + 2 · 3층 커튼월 + 두꺼운 캐노피(글자) + 기둥
    f.storefront(20.5, 35.5, 0.03, 5.4, bay=2.5, transom=3.4, doors=[(24.0, 2.4), (28.0, 2.4), (32.0, 2.4)],
                 name="atrium")
    f.curtain(20.5, 35.5, 6.7, 12.9, 3.1, 2.5, spandrel=0.4, lit=0.5, rng=b.rng, name="atrium_cw")
    f.box(19.5, 36.5, 5.6, 6.3, 0, 5.5, "hp_canopy")
    f.box(19.5, 36.5, 5.55, 5.6, 5.3, 5.5, "hp_red", attached=False)
    t = b.letters("Homeplus", 6.0, 0.48, 0.05)
    if t:
        f.text(t, 28.0, 5.95, 5.5, "letters_hp", kind=None)
    for uu in range(22, 35, 3):
        f.box(uu - 0.3, uu + 0.3, 5.58, 5.6, 1.5, 4.5, "lamp", attached=False)
    for uu in (20.1, 35.9):
        x, y = f.xy(uu, 5.1)
        m.cylinder(x, y, 0.3, 0.03, 5.6, "hp_canopy", n=16)
        f.reserve(FOREGROUND, uu - 0.31, uu + 0.31, 0.03, 5.5, 4.79, 5.41, "canopy_column")
    f.reserve(FOREGROUND, 19.5, 36.5, 5.55, 6.3, 0, 5.5, "canopy")
    b.wall_text("front", "Homeplus", 28.0, 15.0, 24.0, 3.0, mat="letters_hp", extrude=0.15)
    # 1층 임대 매장 (간판)
    for u0, u1, door, text, sub, mat in ((1.0, 9.0, 5.0, "다이소", "Daiso", "sign_daiso"),
                                          (10.0, 18.5, 14.2, "OLIVE YOUNG", "올리브영", "sign_olive"),
                                          (38.0, 46.0, 42.0, "롯데리아", "LOTTERIA", "sign_lotteria"),
                                          (47.0, 55.0, 51.0, "온누리약국", None, "sign_pharm")):
        f.storefront(u0, u1, 0.03, 4.4, bay=1.4, transom=2.9, doors=[(door, 1.8)], name="tenant")
        b.sign_band("front", u0, u1, 4.55, 5.3, text, sub, out=0.3, mat=mat)
    for a, c, d0, d1 in ((47.25, 47.85, 4.73, 4.97), (47.43, 47.67, 4.6, 5.1)):   # 약국 십자
        f.box(a, c, d0, d1, 0.3, 0.36, "cross", attached=False)
    # 빨강 · 주황 띠 (창 · 간판 · 캐노피를 피해 끊김)
    f.band(6.45, 6.75, 0.08, "hp_red", name="stripe_red")
    f.band(6.75, 6.9, 0.08, "hp_orange", name="stripe_orange")
    f.band(H - 0.7, H - 0.4, 0.08, "hp_red", name="stripe_top")
    # 앞마당: 카트 보관대 (지붕 + 기둥 + 카트 줄), 화분, 볼라드, P 기둥 간판
    cx0, cx1, cy0, cy1 = -26.5, -17.0, -23.2, -20.4
    PR.carts(m, cx0 + 0.6, cy0 + 0.6, 0.03, rows=9, per_row=5)
    for px in (cx0, cx1):
        for py in (cy0, cy1):
            m.box(px - 0.06, px + 0.06, py - 0.06, py + 0.06, 0.03, 2.5, "metal_dark")
    m.box(cx0 - 0.2, cx1 + 0.2, cy0 - 0.2, cy1 + 0.2, 2.5, 2.62, "hp_red")
    f.reserve(FOREGROUND, cx0 + 28 - 0.2, cx1 + 28 + 0.2, 0.03, 2.62, -17 - cy1 - 0.2, -17 - cy0 + 0.2, "cart_shelter")
    for k, px in enumerate((-12.0, 12.0)):
        PR.planter(m, px - 1.2, px + 1.2, -22.4, -20.6, seed=k, shrubs=2)
        PR.broadleaf(m, px, -21.5, 0.42, h=4.0, seed=k + 3)
        f.reserve(FOREGROUND, px + 28 - 2.2, px + 28 + 2.2, 0.03, 4.0, 3.6, 5.4, "tree")
    for k in range(7):
        PR.bollard(m, -6.0 + k * 2.0, -23.0)
    f.reserve(FOREGROUND, 21.9, 34.1, 0.03, 0.9, 5.9, 6.1, "bollards")
    pxx, pyy = 30.6, -22.5
    m.box(pxx - 0.25, pxx + 0.25, pyy - 0.25, pyy + 0.25, 0.03, 6.0, "metal_dark")
    m.box(pxx - 0.9, pxx + 0.9, pyy - 0.15, pyy + 0.15, 4.2, 6.0, "sign_p")
    pf = Facade(m, "front", pxx - 0.9, pxx + 0.9, pyy - 0.15, pyy + 0.15)
    for text, zc, h in (("P", 5.4, 0.8), ("옥상주차장", 4.55, 0.3)):
        t = b.letters(text, 1.5, h, 0.02)
        if t:
            pf.text(t, 0.9, zc, 0.0, "letters", kind=None)
    # 오른쪽 면: 옥상 주차장 진입 · 진출 입구 (안쪽 경사로), 비상구
    rf = b.face("right")                                                   # u = y + 17
    rf.garage(5.0, 12.0, 0.03, 4.2, strips=False, name="ramp_in")
    rf.garage(14.5, 21.5, 0.03, 4.2, strips=False, name="ramp_out")
    b.lightbox("right", 8.5, 4.75, 4.0, 0.7, "주차장 입구 ↑", mat="sign_p")
    b.lightbox("right", 18.0, 4.75, 4.0, 0.7, "출구", mat="sign_p")
    for k, gu in enumerate((5.0, 14.5)):                                   # 진입 높이 제한 띠
        rf.box(gu, gu + 7.0, 3.6, 3.85, -0.35, -0.1, "hazard", attached=False)
    rf.door(30.0, 1.2, 2.3, leaf="door_metal", name="exit_r")
    for zf in (g, g + u):
        for uu in (26.0, 33.0):
            rf.window(uu, zf + 1.6, 3.0, 1.2, style="fixed", lit=b.chance(0.4))
    # 왼쪽 면: 큰 Homeplus 글자, 띠, 비상구, 리본 창, 대형 광고판
    lf = b.face("left")                                                    # u = 21 - y, 정면 쪽 u = 38
    b.wall_text("left", "Homeplus", 26.0, 14.8, 16.0, 2.2, mat="letters_hp", extrude=0.12)
    lf.band(6.45, 6.75, 0.08, "hp_red", name="stripe_red")
    lf.band(6.75, 6.9, 0.08, "hp_orange", name="stripe_orange")
    for zf in (g, g + u):
        lf.window(10.0, zf + 1.4, 9.0, 1.4, style="fixed", lit=b.chance(0.5), name="ribbon")
    b.lightbox("left", 30.0, 1.5, 7.0, 3.2, "문화센터 회원 모집", mat="hp_orange")
    lf.door(4.0, 1.2, 2.3, leaf="door_metal", name="exit_l")
    # 뒤: 하역장 셔터 3 + 범퍼 + 하역 캐노피, 직원 문, 실외기
    bk = b.face("back")                                                    # u = 28 - x
    for k, u0 in enumerate((10.0, 16.0, 22.0)):
        bk.shutter(u0, u0 + 4.2, 1.2, 5.0, open_frac=0.0 if k else 0.7, name=f"dock{k}")
        bk.box(u0 - 0.6, u0 + 4.8, 0.03, 1.2, 0, 1.4, "concrete", attached=False)
        for bu in (u0 + 0.3, u0 + 3.7):
            bk.box(bu, bu + 0.25, 0.7, 1.15, 1.4, 1.6, "rubber", attached=False)
        bk.reserve(FOREGROUND, u0 - 0.6, u0 + 4.8, 0.03, 1.2, 0, 1.6, f"dock_platform{k}")
    b.canopy("back", 9.4, 26.8, 5.6, depth=2.6, mat="hp_canopy")
    bk.door(32.0, 1.0, 2.2, leaf="door_metal", name="staff")
    for uu in (38.0, 44.0, 50.0):
        b.ac_wall("back", uu, 1.4, cage=True)
    b.downpipe("back", 0.4, top=H + 0.9)
    b.downpipe("back", 55.6, top=H + 0.9)
    b.gas_pipe("back", 3.2, 36.0)
    b.plinth(h=0.5)
    # 옥상 주차장: 아스팔트 + 주차선 + 통로 화살표 + 조명 기둥 + 경사로 하우스 + 엘리베이터 유리 로비 + 카트 보관대
    b.parapet(h=1.2, mat="wall_side")
    z, pt = b.height, b.parapet_t
    m.box(b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y1 - pt, z, z + 0.08, "asphalt", skip=(BOTTOM,))
    b.roof_reserve("deck", b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y1 - pt, z, z + 0.08)
    zd = z + 0.08
    rows = ((b.y0 + pt + 0.3, 1), (-3.2, -1), (-3.0, 1), (b.y1 - pt - 0.3, -1))
    ramp = (16.0, 27.0, 6.0, 20.4)
    for y_base, sgn in rows:
        x = b.x0 + pt + 0.3
        while x < b.x1 - pt - 0.3:
            if not (ramp[0] - 0.5 < x < ramp[1] + 0.5 and ramp[2] - 1 < y_base < ramp[3] + 1):
                ya, yb = sorted((y_base, y_base + sgn * 5.0))
                m.box(x - 0.06, x + 0.06, ya, yb, zd, zd + 0.006, "paint_white", skip=(BOTTOM,))
            x += 2.5
    for px, py, a in ((-20.0, -9.8, -math.pi / 2), (0.0, -9.8, -math.pi / 2), (-10.0, 8.7, math.pi / 2),
                      (8.0, 8.7, math.pi / 2)):
        PR.arrow(m, px, py, zd, a, length=4.0, width=0.6)
    for px in (-24.0, -14.0, -4.0, 6.0):                                   # 조명 기둥 (맞붙은 주차 줄 사이)
        py = -3.1
        m.cylinder(px, py, 0.12, zd, zd + 7.0, "metal_dark", n=10)
        m.box(px - 0.5, px + 0.5, py - 0.2, py + 0.2, zd + 6.8, zd + 7.0, "metal_dark")
        m.box(px - 0.45, px + 0.45, py - 0.16, py + 0.16, zd + 6.76, zd + 6.8, "lamp")
        b.roof_reserve("light_pole", px - 0.5, px + 0.5, py - 0.2, py + 0.2, zd, zd + 7.0)
    m.box(ramp[0], ramp[1], ramp[2], ramp[3], z, z + 3.4, "wall_side", skip=(BOTTOM,))   # 경사로 하우스
    m.box(ramp[0] - 0.2, ramp[1] + 0.2, ramp[2] - 0.2, ramp[3] + 0.2, z + 3.4, z + 3.6, "hp_red")
    rh = Facade(m, "front", *ramp)
    rh.box(1.5, 9.5, z + 0.08, z + 2.9, 0, 0.02, "opening")
    rh.box(1.3, 9.7, z + 2.9, z + 3.15, 0, 0.1, "hazard")
    t = b.letters("↓ 출구 · 입구 ↑", 6.0, 0.3, 0.01)
    if t:
        rh.text(t, 5.5, z + 3.27, 0.0, "letters", kind=None)
    b.roof_reserve("ramp_house", ramp[0] - 0.2, ramp[1] + 0.2, ramp[2] - 0.2, ramp[3] + 0.2, zd, z + 3.6)
    lx0, lx1, ly0, ly1 = -4.0, 4.0, 13.0, 18.4                             # 엘리베이터 유리 로비
    m.box(lx0, lx1, ly0, ly1, zd, zd + 3.2, "glass_curtain", skip=(BOTTOM,))
    for px in (lx0, lx1):
        for py in (ly0, ly1):
            m.box(px - 0.08, px + 0.08, py - 0.08, py + 0.08, zd, zd + 3.2, "frame_dark")
    m.box(lx0 - 0.3, lx1 + 0.3, ly0 - 0.3, ly1 + 0.3, zd + 3.2, zd + 3.5, "hp_red")
    t = b.letters("Homeplus", 4.0, 0.25, 0.02)
    if t:
        Facade(m, "front", lx0 - 0.3, lx1 + 0.3, ly0 - 0.3, ly1 + 0.3).text(t, 4.3, zd + 3.35, 0.0, "letters",
                                                                           kind=None)
    b.roof_reserve("lobby", lx0 - 0.3, lx1 + 0.3, ly0 - 0.3, ly1 + 0.3, zd, zd + 3.5)
    for cx in (-20.0, 6.0):                                                # 옥상 카트 보관대
        PR.carts(m, cx, 13.6, zd, rows=3, per_row=4)
        m.box(cx - 0.5, cx + 2.4, 13.0, 15.2, zd + 2.3, zd + 2.4, "hp_red")
        for px in (cx - 0.5, cx + 2.4):
            m.box(px - 0.05, px + 0.05, 13.0, 13.1, zd, zd + 2.3, "metal_dark")
        b.roof_reserve("roof_carts", cx - 0.5, cx + 2.4, 13.0, 15.2, zd, zd + 2.4)
    b.top = max(b.top, zd + 7.0)
    b.finalize()
    return b, "홈플러스 울산동구점"


# ---------------------------------------------------------------------------
# 4 · 5. 편의점 — GS25 (2x2, 2층) · CU (2x2, 3층 다가구 1층). 간판, 유리 포스터, 파라솔 테이블, 아이스크림 냉장고,
#        택배 · ATM 안내, 분리수거함, 배달 오토바이
# ---------------------------------------------------------------------------

def store_front_details(b, f, posters, parasol_mats, freezer_u, table_us, d_table=2.6):
    m = b.m
    rec = 0.25
    for (u, z, w, h, board, text, letters) in posters:
        poster(f, u, z, w, h, -rec + 0.035, board, text, letters, b.letters)
    for k, tu in enumerate(table_us):
        plastic_table(b, f, tu, d_table, name="table")
        x, y = f.xy(tu, d_table)
        PR.parasol(m, x, y, 0.03, r=1.2, h=2.4, mat=parasol_mats[k % len(parasol_mats)])
        f.reserve(FOREGROUND, tu - 1.2, tu + 1.2, 1.9, 2.45, d_table - 1.2, d_table + 1.2, "parasol")
    x0, y0 = f.xy(freezer_u - 0.5, 0.25)
    x1, y1 = f.xy(freezer_u + 0.5, 0.95)
    PR.freezer(m, min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1))
    f.reserve(FOREGROUND, freezer_u - 0.5, freezer_u + 0.5, 0.03, 0.9, 0.25, 0.95, "freezer")


def gs25(text_fn=None):
    b = Building((2, 2), 12.0, 9.0, setback=5.0, seed=65, text_fn=text_fn)     # y -3..6, 앞마당 5 m
    b.mats.update({
        "wall": render((0.92, 0.92, 0.90)), "wall_side": render((0.86, 0.86, 0.84)),
        "gs_board": sign((0.95, 0.95, 0.93), 0.6), "letters_gs": glow((0.0, 0.17, 0.62), 2.5),
        "gs_cyan": glow((0.0, 0.35, 0.82), 1.5),
        "parasol_cass": solid((0.02, 0.12, 0.55), 0.7), "parasol_terra": solid((0.02, 0.25, 0.08), 0.7),
        "poster_red": sign((0.75, 0.03, 0.03), 0.4), "poster_yellow": sign((0.95, 0.80, 0.05), 0.4),
        "poster_blue": sign((0.02, 0.20, 0.60), 0.4), "letters_yellow": glow((0.98, 0.85, 0.1), 1.5),
        "letters_red": glow((0.75, 0.03, 0.03), 1.5),
        "bin_blue": solid((0.05, 0.25, 0.60)), "bin_green": solid((0.10, 0.45, 0.15)),
        "bin_yellow": solid((0.90, 0.70, 0.05)),
    })
    g, u = 4.2, 3.0
    b.lot_slab()
    b.shell(g + u)
    f = b.face("front")
    f.storefront(0.4, 11.6, 0.03, 3.0, bay=1.2, transom=2.4, doors=[(2.2, 1.6)])
    b.sign_band("front", 0.2, 11.8, 3.1, 3.95, "GS25", out=0.3, mat="gs_board", letters="letters_gs")
    f.box(0.2, 11.8, 3.12, 3.22, 0.3, 0.32, "gs_cyan", attached=False)
    f.box(0.2, 11.8, 3.83, 3.93, 0.3, 0.32, "letters_gs", attached=False)
    store_front_details(b, f, [(4.3, 1.2, 0.7, 0.9, "poster_red", "1+1", "letters_yellow"),
                               (5.5, 1.2, 0.7, 0.9, "poster_yellow", "2+1", "letters_red"),
                               (8.6, 1.4, 0.8, 0.5, "poster_blue", "택배", "letters"),
                               (10.6, 1.4, 0.7, 0.5, "poster_blue", "ATM", "letters")],
                        ["parasol_cass", "parasol_terra"], 0.9, (5.4, 8.1, 10.8))
    for k, mat in enumerate(("bin_blue", "bin_green", "bin_yellow")):     # 분리수거함
        f.box(3.5 + k * 0.62, 4.05 + k * 0.62, 0.03, 1.0, 4.2, 4.75, mat, attached=False)
    f.reserve(FOREGROUND, 3.5, 5.3, 0.03, 1.0, 4.2, 4.75, "bins")
    PR.scooter(b.m, -6.6, -7.4)
    for i in range(3):
        uu = 1.0 + (b.w - 2.0) * (i + 0.5) / 3
        f.window(uu, g + 0.85, 2.4, 1.4, lit=b.chance(0.5), grille=i == 1, blind=b.blind())
    side_details(b, back_door_u=b.w - 2.0, levels=[g], side_n=2, gas_z=3.5)
    b.ac_wall("back", 6.0, 1.4)
    b.bands([g], ("front", "left", "right"), h=0.12, out=0.05)
    b.plinth()
    b.parapet()
    z = b.height
    b.water_tank(b.x0 + 1.5, b.y1 - 1.5, z, r=0.7, h=1.2)
    b.ac_roof(2.0, b.y1 - 1.0, z)
    b.ac_roof(3.3, b.y1 - 1.0, z)
    b.finalize()
    return b, "GS25"


def cu(text_fn=None):
    b = Building((2, 2), 12.5, 9.5, setback=4.5, seed=66, text_fn=text_fn)     # y -3.5..6, 1층 편의점 + 2 · 3층 다가구
    b.mats.update({
        "wall": dict(BRICK, color=(0.55, 0.38, 0.28), color2=(0.48, 0.33, 0.24)), "wall_side": render((0.82, 0.78, 0.72)),
        "cu_board": sign((0.95, 0.95, 0.93), 0.6), "letters_cu": glow((0.13, 0.03, 0.27), 2.5),
        "cu_green": glow((0.40, 0.62, 0.04), 1.5),
        "parasol_terra": solid((0.02, 0.25, 0.08), 0.7), "parasol_cu": solid((0.13, 0.03, 0.27), 0.7),
        "poster_purple": sign((0.13, 0.03, 0.27), 0.4), "poster_green": sign((0.40, 0.62, 0.04), 0.4),
        "poster_white": sign((0.92, 0.92, 0.90), 0.3), "letters_dark": solid((0.05, 0.05, 0.06), 0.4),
        "atm_blue": sign((0.02, 0.20, 0.60), 0.5), "solar": {"color": (0.03, 0.05, 0.12), "color2": (0.6, 0.6, 0.65),
                                                             "pattern": "tile", "scale": (0.5, 0.3), "mortar": 0.01,
                                                             "mortar_color": (0.6, 0.6, 0.65), "rough": 0.1,
                                                             "metal": 0.5},
    })
    g, u = 4.2, 2.9
    levels = [g, g + u]
    b.lot_slab()
    b.shell(g + 2 * u)
    f = b.face("front")
    f.storefront(0.4, 12.1, 0.03, 3.0, bay=1.2, transom=2.4, doors=[(10.2, 1.6)])
    b.sign_band("front", 0.2, 12.3, 3.1, 3.95, "CU", out=0.3, mat="cu_board", letters="letters_cu")
    f.box(0.2, 12.3, 3.12, 3.24, 0.3, 0.32, "cu_green", attached=False)
    store_front_details(b, f, [(1.5, 1.2, 0.7, 0.9, "poster_purple", "1+1", "letters"),
                               (2.7, 1.2, 0.7, 0.9, "poster_green", "2+1", "letters_dark"),
                               (5.4, 1.4, 1.0, 0.5, "poster_white", "택배 · 반값택배", "letters_dark"),
                               (7.0, 1.4, 0.8, 0.5, "poster_purple", "ATM", "letters")],
                        ["parasol_terra", "parasol_cu"], 8.6, (2.0, 4.8))
    x, y = f.xy(7.5, 3.2)                                                  # ATM 부스
    b.m.box(x - 0.6, x + 0.6, y - 0.6, y + 0.6, 0.03, 2.3, "atm_blue")
    af = Facade(b.m, "front", x - 0.6, x + 0.6, y - 0.6, y + 0.6)
    af.box(0.25, 0.95, 0.9, 1.8, 0, 0.03, "glass_shop")
    t = b.letters("ATM", 0.8, 0.25, 0.01)
    if t:
        af.text(t, 0.6, 2.05, 0.0, "letters", kind=None)
    f.reserve(FOREGROUND, 6.9, 8.1, 0.03, 2.3, 2.6, 3.8, "atm")
    PR.scooter(b.m, 4.9, -7.6)
    for zf in levels:
        b.balcony("front", 0.8, 5.6, zf, depth=1.1)
        f.window(3.2, zf + 0.05, 2.4, 2.1, sill=None, lit=b.chance(0.4), blind=b.blind())
        f.window(9.4, zf + 0.9, 2.6, 1.4, lit=b.chance(0.4), blind=b.blind())
        b.ac_wall("front", 7.0, zf + 0.5, cage=True)
    b.face("left").door(3.0, 1.0, 2.2, leaf="door_metal", name="house")
    side_details(b, back_door_u=None, levels=levels, side_n=2, gas_side="right", gas_z=3.6)
    b.bands(levels, ("front", "left", "right"), h=0.1, out=0.05)
    b.plinth()
    b.parapet()
    z = b.height
    m = b.m
    for k in range(3):                                                     # 옥상 태양광 판
        px = b.x0 + 1.2 + k * 1.9
        m.slab([(px, b.y0 + 1.4, z + 0.4), (px + 1.7, b.y0 + 1.4, z + 0.4), (px + 1.7, b.y0 + 2.6, z + 1.0),
                (px, b.y0 + 2.6, z + 1.0)], 0.04, "solar")
        for py in (b.y0 + 1.5, b.y0 + 2.5):
            m.box(px + 0.8, px + 0.9, py - 0.05, py + 0.05, z, z + (0.4 if py < b.y0 + 2 else 0.95), "metal")
        b.roof_reserve("solar", px - 0.02, px + 1.72, b.y0 + 1.38, b.y0 + 2.62, z, z + 1.02)
    b.water_tank(b.x1 - 1.6, b.y1 - 1.6, z, r=0.75, h=1.2)
    b.stair_house(b.x0 + 0.6, b.x0 + 3.4, b.y1 - 3.2, b.y1 - 0.6)
    b.finalize()
    return b, "CU"


DESIGNS = {
    "IlsanStarbucksDT": starbucks_dt,
    "IlsanTerracePark01": terrace_park_a,
    "IlsanTerracePark02": terrace_park_c,
    "IlsanHomeplus": homeplus,
    "IlsanGS25": gs25,
    "IlsanCU": cu,
}
