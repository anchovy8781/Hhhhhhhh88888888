"""일산해수욕장 · 방어진순환도로 주변 프랜차이즈 · 동네 실제 상호 (고디테일).

  파리바게뜨 · 배스킨라빈스 · 컴포즈커피 · 이마트24 · BBQ 치킨      해변 상가에 흔한 프랜차이즈 (지점 위치는 근사)
  올리브영 · 다이소 3층 상가, GS칼텍스 주유소 + GS25           방어진순환도로 변
  일산새마을금고 (대학길 169) · 식당153 울산본점 (해물칼국수)    일산동 실제 상호
간판은 로고 그림 대신 브랜드 색 + 글자(나눔고딕)로 만든 근사치다.
"""

import math

import props as PR
from brands import HAZARD, PANEL_WHITE, WOOD_LOUVER, glow, poster, solid, store_front_details
from designs import BRICK, Building, render, side_details, sign
from geom import BOTTOM, FIXTURE, FOREGROUND, SIGN, Facade
from landmarks import glass_rail, plastic_table


def a_board(m, x, y, z=0.03, mat="sign", face="plate_white", letters=None, text_fn=None):
    """입간판 (A자 메뉴판): 양쪽 판 + 위 손잡이, 앞판에 글자"""
    m.slab([(x - 0.3, y - 0.25, z + 0.02), (x + 0.3, y - 0.25, z + 0.02), (x + 0.3, y - 0.02, z + 1.0),
            (x - 0.3, y - 0.02, z + 1.0)], 0.03, mat)
    m.slab([(x - 0.3, y + 0.02, z + 1.0), (x + 0.3, y + 0.02, z + 1.0), (x + 0.3, y + 0.25, z + 0.02),
            (x - 0.3, y + 0.25, z + 0.02)], 0.03, mat)
    m.box(x - 0.25, x + 0.25, y - 0.22, y - 0.2, z + 0.25, z + 0.85, face)
    if letters:
        Facade(m, "front", x - 0.25, x + 0.25, y - 0.24, y - 0.2).text(letters, 0.25, z + 0.55, 0.0, "letters_dark",
                                                                      kind=None)
    return x - 0.32, x + 0.32, y - 0.3, y + 0.3, z, z + 1.02


def wall_lamp(f, u, z, d0=0.0):
    """벽 조명 (상자 + 아래 발광면)"""
    f.box(u - 0.09, u + 0.09, z, z + 0.3, d0, d0 + 0.08, "metal_dark")
    f.box(u - 0.07, u + 0.07, z - 0.01, z, d0 + 0.02, d0 + 0.22, "lamp", attached=False)
    f.box(u - 0.09, u + 0.09, z, z + 0.03, d0 + 0.08, d0 + 0.24, "metal_dark", attached=False)
    f.reserve(FIXTURE, u - 0.1, u + 0.1, z - 0.02, z + 0.31, d0, d0 + 0.25, "wall_lamp")


# ---------------------------------------------------------------------------
# 공통: 2층 브랜드 매장 (1층 가게 + 2층 좌석 · 주거), 앞마당 테라스
# ---------------------------------------------------------------------------

def two_floor_store(lot, width, depth, setback, seed, text_fn, mats, g=4.3, u=3.2, roof_parapet=True):
    b = Building(lot, width, depth, setback=setback, seed=seed, text_fn=text_fn)
    b.mats.update(mats)
    b.lot_slab()
    b.shell(g + u)
    return b, g, u


def finish_store(b, g, levels=None, back_door=None, gas_z=3.5, roof_items=True):
    side_details(b, back_door_u=back_door, levels=levels or [g], side_n=2, gas_z=gas_z)
    b.ac_wall("back", b.w / 2, 1.4)
    b.plinth()
    b.parapet()
    if roof_items:
        z = b.height
        b.water_tank(b.x0 + 1.5, b.y1 - 1.5, z, r=0.7, h=1.2)
        b.ac_roof(b.x1 - 1.6, b.y1 - 1.0, z)
        b.ac_roof(b.x1 - 2.9, b.y1 - 1.0, z)
    b.finalize()


# ---------------------------------------------------------------------------
# 1. 파리바게뜨 — 2x2, 2층 베이커리 카페. 남색 + 금색 글자, 1층 빵 진열 유리 · 차양 · 테라스, 2층 카페 통유리
# ---------------------------------------------------------------------------

PB_NAVY = (0.02, 0.05, 0.16)
PB_GOLD = (0.80, 0.60, 0.25)


def paris_baguette(text_fn=None):
    b, g, u = two_floor_store((2, 2), 13.0, 10.0, 5.0, 71, text_fn, {
        "wall": {"color": PB_NAVY, "color2": (0.03, 0.06, 0.19), "pattern": "panel", "scale": (1.0, 0.6),
                 "mortar": 0.004, "mortar_color": (0.01, 0.02, 0.06), "rough": 0.35, "metal": 0.3},
        "wall_side": render((0.86, 0.84, 0.80), grime=0.15),
        "pb_board": sign(PB_NAVY, 0.3), "letters_pb": glow(PB_GOLD, 2.0, 0.25),
        "pb_gold": {"color": PB_GOLD, "rough": 0.25, "metal": 0.9},
        "awning": solid(PB_NAVY, 0.7), "parasol_pb": solid(PB_NAVY, 0.7),
        "plate_white": solid((0.92, 0.90, 0.85), 0.5), "letters_dark": solid((0.05, 0.05, 0.06), 0.4),
        "bread": {"color": (0.70, 0.42, 0.18), "color2": (0.55, 0.30, 0.12), "pattern": "noise", "scale": 12.0,
                  "rough": 0.6, "bump": 0.3},
    })
    f = b.face("front")
    f.storefront(0.5, 12.5, 0.03, 3.4, bay=1.3, transom=2.6, doors=[(9.6, 1.8)])
    b.sign_band("front", 0.25, 12.75, 3.55, 4.15, "PARIS BAGUETTE", "BAKERY · CAFE", out=0.28, mat="pb_board",
                letters="letters_pb")
    for zz in (3.5, 4.2):
        f.box(0.25, 12.75, zz, zz + 0.04, 0.0, 0.3, "pb_gold", attached=False)
    b.awning("front", 0.6, 8.4, 3.35, depth=1.6, drop=0.35, valance=0.2)
    for k in range(3):                                                   # 빵 진열대 (유리 안쪽 3단 선반 + 빵)
        uu = 1.5 + k * 2.4
        for lvl in range(3):
            zz = 0.75 + lvl * 0.45
            f.box(uu - 0.9, uu + 0.9, zz, zz + 0.03, -0.24, -0.06, "pb_gold", attached=False)
            for j in range(5):
                x, y = f.xy(uu - 0.72 + j * 0.36, -0.15)
                b.m.ellipsoid(x, y, zz + 0.09, 0.13, 0.07, 0.06, "bread", nu=8, nv=4)
    t = b.letters("빵 나오는 시간 07:30 · 11:00 · 15:00", 4.5, 0.18, 0.004)
    if t:
        f.glass_text(t, 4.0, 2.75, recess=0.25)
    for k, uu in enumerate((2.6, 6.2, 11.6)):
        if uu < 8.5:
            x, y = f.xy(uu, 3.3)
            PR.cafe_set(b.m, x, y, 0.03, "parasol_pb", r=1.15)
            f.reserve(FOREGROUND, uu - 1.15, uu + 1.15, 0.03, 2.4, 2.15, 4.45, "terrace")
    x, y = f.xy(11.8, 1.6)
    a_board(b.m, x, y, mat="pb_board", letters=b.letters("TODAY", 0.4, 0.12, 0.004))
    f.reserve(FOREGROUND, 11.45, 12.15, 0.03, 1.02, 1.3, 1.9, "a_board")
    f.curtain(0.4, 12.6, g + 0.15, g + u - 0.25, 2.8, 1.5, spandrel=0.25, lit=0.6, rng=b.rng, name="cafe2")
    t = b.letters("CAFE 2F", 2.0, 0.35, 0.004)
    if t:
        f.glass_text(t, 6.5, g + 1.9, recess=0.12)
    for uu in (0.25, 12.75):                                             # 금색 세로 기둥 장식
        f.box(uu - 0.12, uu + 0.12, g - 0.03, g + u, 0.0, 0.12, "pb_gold")
        f.reserve(FIXTURE, uu - 0.12, uu + 0.12, g - 0.03, g + u, 0.0, 0.12, "pilaster")
    finish_store(b, g, back_door=b.w - 2.0)
    return b, "파리바게뜨"


# ---------------------------------------------------------------------------
# 2. 배스킨라빈스 — 2x2, 1층 매장 + 2층 주거. 분홍 간판 · 31 원형 간판 · 대형 아이스크림 콘 조형물
# ---------------------------------------------------------------------------

BR_PINK = (0.80, 0.10, 0.35)
BR_BROWN = (0.22, 0.10, 0.06)


def baskin(text_fn=None):
    b, g, u = two_floor_store((2, 2), 12.0, 9.0, 5.0, 72, text_fn, {
        "wall": {"color": (0.92, 0.88, 0.86), "color2": (0.88, 0.84, 0.82), "pattern": "panel", "scale": (1.0, 0.5),
                 "mortar": 0.004, "mortar_color": (0.75, 0.7, 0.7), "rough": 0.4},
        "wall_side": render((0.86, 0.84, 0.82), grime=0.15),
        "br_board": sign((0.97, 0.94, 0.95), 0.4), "letters_br": glow(BR_PINK, 2.5),
        "br_pink": glow(BR_PINK, 1.0), "letters_brown": glow(BR_BROWN, 0.8),
        "parasol_br": solid(BR_PINK, 0.7), "cone": {"color": (0.78, 0.55, 0.25), "color2": (0.62, 0.40, 0.15),
                                                    "pattern": "tile", "scale": (0.12, 0.12), "mortar": 0.02,
                                                    "mortar_color": (0.5, 0.32, 0.12), "rough": 0.6},
        "scoop_pink": solid((0.95, 0.55, 0.65), 0.6), "scoop_mint": solid((0.55, 0.88, 0.72), 0.6),
        "scoop_choc": solid((0.30, 0.15, 0.08), 0.6),
    })
    m = b.m
    f = b.face("front")
    f.storefront(0.5, 11.5, 0.03, 3.3, bay=1.3, transom=2.5, doors=[(3.0, 1.8)])
    b.sign_band("front", 2.2, 11.8, 3.45, 4.15, "baskin robbins", "배스킨라빈스", out=0.28, mat="br_board",
                letters="letters_br")
    f.box(2.2, 11.8, 3.42, 3.47, 0.0, 0.3, "br_pink", attached=False)
    f.disc(1.1, 4.0, 0.0, 0.6, 0.25, "br_pink", n=28)                    # 31 원형 간판
    t = b.letters("31", 0.75, 0.5, 0.04)
    if t:
        f.text(t, 1.1, 4.0, 0.25, "letters", kind=None)
    f.reserve(SIGN, 0.45, 1.75, 3.35, 4.65, 0, 0.35, "logo_31")
    t = b.letters("오늘의 맛 31가지 · 아이스크림 케이크", 5.0, 0.2, 0.004)
    if t:
        f.glass_text(t, 7.6, 2.75, recess=0.25)
    for uu in (5.6, 9.3):
        x, y = f.xy(uu, 2.9)
        PR.cafe_set(m, x, y, 0.03, "parasol_br", r=1.1, chairs=3)
        f.reserve(FOREGROUND, uu - 1.1, uu + 1.1, 0.03, 2.4, 1.8, 4.0, "terrace")
    cx, cy = f.xy(1.0, 3.9)                                              # 대형 아이스크림 콘 (받침 + 콘 + 세 덩이)
    m.cylinder(cx, cy, 0.45, 0.03, 0.35, "br_pink", n=20)
    m.tube((cx, cy, 0.35), (cx, cy, 2.0), 0.05, 0.42, "cone", n=16)
    for k, (dz, mat) in enumerate(((2.25, "scoop_mint"), (2.75, "scoop_pink"), (3.2, "scoop_choc"))):
        r = 0.48 - k * 0.06
        m.ellipsoid(cx, cy, dz, r, r, r * 0.85, mat, nu=16, nv=8)
    f.reserve(FOREGROUND, 0.45, 1.55, 0.03, 3.6, 3.35, 4.45, "cone_sign")
    for i in range(3):
        uu = 1.0 + (b.w - 2.0) * (i + 0.5) / 3
        f.window(uu, g + 0.85, 2.3, 1.4, style="casement", lit=b.chance(0.5), blind=b.blind())
    finish_store(b, g, back_door=b.w - 2.0)
    return b, "배스킨라빈스"


# ---------------------------------------------------------------------------
# 3. 컴포즈커피 — 2x2, 단층 테이크아웃 매장. 노랑 패널 + 검정 글자, 주문 창, 벤치, 입간판, 배달 오토바이
# ---------------------------------------------------------------------------

CP_YELLOW = (0.95, 0.72, 0.02)


def compose_coffee(text_fn=None):
    b = Building((2, 2), 10.0, 7.5, setback=5.5, seed=73, text_fn=text_fn)  # y -2.5..5
    b.mats.update({
        "wall": {"color": CP_YELLOW, "color2": (0.90, 0.66, 0.02), "pattern": "panel", "scale": (1.2, 0.6),
                 "mortar": 0.004, "mortar_color": (0.6, 0.45, 0.02), "rough": 0.35, "control": (1, 0, 0)},
        "wall_side": render((0.15, 0.15, 0.16), grime=0.1),
        "cp_board": sign((0.06, 0.06, 0.07), 0.2), "letters_cp": glow(CP_YELLOW, 2.5),
        "plate_white": solid((0.95, 0.95, 0.92), 0.5), "letters_dark": solid((0.05, 0.05, 0.06), 0.4),
        "bench_wood": WOOD_LOUVER,
    })
    m = b.m
    H = 4.4
    b.lot_slab()
    b.shell(H)
    f = b.face("front")
    f.storefront(0.5, 6.4, 0.03, 3.1, bay=1.2, transom=2.4, doors=[(1.6, 1.6)])
    f.window(8.3, 1.0, 2.0, 1.3, style="sliding", frame="frame_dark", glass="glass_shop", name="takeout")
    b.canopy("front", 7.0, 9.6, 2.55, depth=0.9, mat="cp_board")
    b.lightbox("front", 8.3, 2.85, 2.0, 0.36, "TAKE OUT", mat="cp_board", letters="letters_cp")
    b.sign_band("front", 0.3, 9.7, 3.35, 4.1, "COMPOSE COFFEE", out=0.25, mat="cp_board", letters="letters_cp")
    for k, (text, price) in enumerate((("아메리카노", "1,500"), ("카페라떼", "2,900"), ("자몽에이드", "3,500"))):
        poster(f, 2.9 + k * 1.05, 1.5, 0.9, 0.55, -0.215, "plate_white", f"{text} {price}", "letters_dark", b.letters)
    for k, bu in enumerate((3.2, 5.6)):                                  # 앞 벤치 (목재 좌판 + 검정 다리)
        f.box(bu - 0.9, bu + 0.9, 0.42, 0.48, 1.6, 2.0, "bench_wood", attached=False)
        for lu in (bu - 0.75, bu + 0.75):
            f.box(lu - 0.04, lu + 0.04, 0.03, 0.42, 1.65, 1.95, "metal_dark", attached=False)
        f.reserve(FOREGROUND, bu - 0.9, bu + 0.9, 0.03, 0.48, 1.6, 2.0, "bench")
    x, y = f.xy(8.3, 2.6)
    a_board(m, x, y, mat="cp_board", letters=b.letters("1+1", 0.4, 0.2, 0.004))
    f.reserve(FOREGROUND, 7.95, 8.65, 0.03, 1.02, 2.3, 2.9, "a_board")
    PR.scooter(m, -2.6, -7.2, box="plastic_white")
    for uu, z in ((0.25, 2.2), (9.75, 2.2)):
        wall_lamp(f, uu, z)
    b.downpipe("left", b.d - 0.3, top=H + 0.9)
    for s in ("left", "right"):                                         # 옆면 높은 띠창 (주방 · 창고 환기)
        b.windows(s, [0.03], 2, 1.4, 0.55, sill=2.3, margin=1.6, style="fixed", blinds=False, lit=0.3)
    b.face("back").door(2.0, 0.9, 2.1, leaf="door_metal", canopy=False, name="back")
    b.ac_wall("back", 6.0, 1.4)
    b.plinth(h=0.3)
    b.parapet(h=0.6, mat="wall_side")
    b.ac_roof(b.x1 - 1.4, b.y1 - 1.0, b.height)
    b.finalize()
    return b, "컴포즈커피"


# ---------------------------------------------------------------------------
# 4. 올리브영 · 다이소 — 3x3, 3층 상가. 1층 올리브영(연두), 2 · 3층 다이소(빨강) 통유리 + 큰 간판, 옥상 간판틀
# ---------------------------------------------------------------------------

OY_GREEN = (0.45, 0.66, 0.12)
DS_RED = (0.75, 0.02, 0.06)


def olive_daiso(text_fn=None):
    b = Building((3, 3), 22.0, 17.0, setback=4.0, seed=74, text_fn=text_fn)   # y -8..9
    b.mats.update({
        "wall": PANEL_WHITE, "wall_side": render((0.84, 0.83, 0.80), grime=0.15),
        "oy_board": sign(OY_GREEN, 0.6), "letters_oy": glow((0.98, 0.98, 0.95), 2.5),
        "ds_board": sign(DS_RED, 0.7), "letters_ds": glow((0.98, 0.98, 0.95), 3.0),
        "ds_red": dict(glow(DS_RED, 0.6), rough=0.4), "oy_green": dict(glow(OY_GREEN, 0.6), rough=0.4),
        "basket": solid((0.75, 0.05, 0.08), 0.5),
    })
    g, u = 4.6, 4.0
    H = g + 2 * u
    b.lot_slab()
    b.shell(H)
    f = b.face("front")
    f.storefront(0.5, 15.5, 0.03, 3.8, bay=1.5, transom=2.8, doors=[(4.0, 2.0), (12.0, 1.8)], name="olive")
    b.sign_band("front", 0.3, 15.7, 3.95, 4.6, "OLIVE YOUNG", "올리브영", out=0.3, mat="oy_board",
                letters="letters_oy")
    f.door(18.6, 1.6, 2.4, leaf="glass_door", name="stair_hall")
    b.lightbox("front", 18.6, 3.0, 2.6, 0.5, "다이소 2 · 3층 ↑", mat="ds_board", letters="letters_ds")
    for k, uu in enumerate((6.5, 7.5, 8.5, 9.5)):                       # 유리 안 포스터
        poster(f, uu, 1.6, 0.8, 1.1, -0.215, "oy_green" if k % 2 else "ds_red", "SALE" if k % 2 else "1+1",
               "letters", b.letters)
    for k in range(2):                                                    # 문 앞 장바구니 더미
        x, y = f.xy(14.0 + k * 0.6, 0.6)
        for j in range(4):
            b.m.box(x - 0.25, x + 0.25, y - 0.18, y + 0.18, 0.03 + j * 0.06, 0.28 + j * 0.06, "basket")
    f.reserve(FOREGROUND, 13.7, 14.9, 0.03, 0.5, 0.4, 0.8, "baskets")
    for k, zf in enumerate((g, g + u)):                                  # 2 · 3층 다이소: 통유리 + 빨간 띠
        f.curtain(0.4, 21.6, zf + 0.95, zf + u - 0.2, 2.85, 1.6, spandrel=0.2, lit=0.7, rng=b.rng, name="daiso")
        f.box(0.0, 22.0, zf + 0.1, zf + 0.85, 0.0, 0.08, "ds_red")
        f.reserve(FIXTURE, 0.0, 22.0, zf + 0.1, zf + 0.85, 0.0, 0.08, "red_band")
    for zf in (g, g + u):                                                # 빨간 띠 위 글자
        for text, uu in (("Daiso", 11.0), ("다이소", 3.5), ("다이소", 18.5)):
            t = b.letters(text, 4.0, 0.55, 0.04)
            if t:
                f.text(t, uu, zf + 0.475, 0.08, "letters_ds", kind=None)
    lf = b.face("left")
    lf.curtain(9.0, 16.88, g + 0.95, H - 0.2, u, 1.6, spandrel=0.2, lit=0.7, rng=b.rng, name="daiso_l")
    b.wall_text("left", "Daiso", 4.5, H - 1.4, 5.0, 1.2, mat="ds_board")
    for zf in (g, g + u):
        for uu in (2.0, 6.5):
            b.face("right").window(uu, zf + 1.0, 1.6, 1.5, lit=b.chance(0.5), blind=b.blind())
    b.windows("back", [0.03, g, g + u], 3, 1.2, 1.1, sill=1.2, margin=3.0)
    b.face("back").door(4.0, 1.0, 2.2, leaf="door_metal", name="back")
    b.downpipe("right", 0.3, top=H + 0.9)
    b.downpipe("right", b.d - 0.3, top=H + 0.9)
    b.gas_pipe("right", 3.8, b.d - 2.0)
    for uu in (8.0, 12.0):
        b.ac_wall("back", uu, 1.4, cage=True)
    b.plinth()
    b.parapet(h=1.0)
    z, pt = b.height, b.parapet_t
    sy = b.y0 + pt + 0.6                                                  # 옥상 간판틀 (Daiso)
    for px in (-7.0, -2.3, 2.3, 7.0):
        b.m.box(px - 0.07, px + 0.07, sy + 0.2, sy + 0.34, z, z + 4.0, "metal_dark")
        b.m.beam((px, sy + 0.27, z + 3.0), (px, sy + 1.6, z + 0.05), 0.06, 0.06, "metal_dark")
    b.m.box(-8.0, 8.0, sy, sy + 0.2, z + 1.2, z + 3.9, "ds_board")
    t = b.letters("Daiso 다이소", 13.0, 1.8, 0.08)
    if t:
        Facade(b.m, "front", -8.0, 8.0, sy, sy + 0.2).text(t, 8.0, z + 2.55, 0.0, "letters_ds", kind=None)
    b.roof_reserve("roof_sign", -8.1, 8.1, sy - 0.1, sy + 1.65, z, z + 4.0)
    b.stair_house(b.x1 - 4.4, b.x1 - 0.8, b.y1 - 4.2, b.y1 - 0.6, h=3.0)
    for i in range(5):
        b.ac_roof(b.x0 + 1.6 + i * 1.3, b.y1 - 1.1, z)
    b.finalize()
    return b, "올리브영 · 다이소"


# ---------------------------------------------------------------------------
# 5. 이마트24 — 2x2, 편의점 + 2층. 노랑 · 검정 간판, 노랑 파라솔, 냉장고, 포스터, 택배함
# ---------------------------------------------------------------------------

def emart24(text_fn=None):
    b, g, u = two_floor_store((2, 2), 12.0, 9.0, 5.0, 75, text_fn, {
        "wall": render((0.20, 0.20, 0.21)), "wall_side": render((0.84, 0.82, 0.78)),
        "e24_board": sign((0.98, 0.78, 0.02), 0.6), "letters_e24": glow((0.06, 0.06, 0.06), 0.3),
        "parasol_e24": solid((0.98, 0.78, 0.02), 0.7), "poster_yellow": sign((0.98, 0.78, 0.02), 0.4),
        "poster_black": sign((0.06, 0.06, 0.06), 0.3), "letters_dark": solid((0.05, 0.05, 0.06), 0.4),
        "letters_yellow": glow((0.98, 0.80, 0.05), 1.5), "locker": solid((0.85, 0.30, 0.05), 0.5),
    })
    f = b.face("front")
    f.storefront(0.4, 11.6, 0.03, 3.0, bay=1.2, transom=2.4, doors=[(9.8, 1.6)])
    b.sign_band("front", 0.2, 11.8, 3.1, 3.95, "emart24", "24시간 · 택배 · ATM", out=0.3, mat="e24_board",
                letters="letters_e24")
    store_front_details(b, f, [(1.4, 1.2, 0.7, 0.9, "poster_black", "1+1", "letters_yellow"),
                               (2.6, 1.2, 0.7, 0.9, "poster_yellow", "2+1", "letters_dark"),
                               (5.2, 1.4, 0.8, 0.5, "poster_black", "택배", "letters_yellow")],
                        ["parasol_e24"], 7.9, (2.0, 4.8))
    x, y = f.xy(7.0, 3.6)                                                 # 무인 택배 보관함
    b.m.box(x - 0.9, x + 0.9, y - 0.3, y + 0.3, 0.03, 1.9, "locker")
    lf = Facade(b.m, "front", x - 0.9, x + 0.9, y - 0.3, y + 0.3)
    for r in range(4):
        for c in range(3):
            lf.box(0.1 + c * 0.55, 0.6 + c * 0.55, 0.15 + r * 0.42, 0.52 + r * 0.42, 0, 0.01, "frame_dark")
    f.reserve(FOREGROUND, 6.1, 7.9, 0.03, 1.9, 3.3, 3.9, "locker")
    for i in range(3):
        uu = 1.0 + (b.w - 2.0) * (i + 0.5) / 3
        f.window(uu, g + 0.85, 2.4, 1.4, lit=b.chance(0.5), grille=i == 2, blind=b.blind())
    finish_store(b, g, back_door=2.0)
    return b, "이마트24"


# ---------------------------------------------------------------------------
# 6. BBQ 치킨 — 2x2, 1층 매장 + 2층 주거. 빨강 간판, 차양, 테이블, 배달 오토바이 3대
# ---------------------------------------------------------------------------

def bbq(text_fn=None):
    b, g, u = two_floor_store((2, 2), 12.5, 9.5, 5.0, 76, text_fn, {
        "wall": dict(BRICK, color=(0.40, 0.18, 0.12), color2=(0.34, 0.15, 0.10)),
        "wall_side": render((0.82, 0.78, 0.72)),
        "bbq_board": sign((0.80, 0.03, 0.04), 0.7), "letters_bbq": glow((0.98, 0.98, 0.95), 3.0),
        "awning": solid((0.80, 0.03, 0.04), 0.7), "letters_gold": glow((0.98, 0.78, 0.15), 1.5),
    })
    f = b.face("front")
    f.storefront(0.5, 12.0, 0.03, 3.1, bay=1.2, transom=2.4, doors=[(2.4, 1.6)])
    b.sign_band("front", 0.25, 12.25, 3.2, 4.0, "BBQ", "황금올리브치킨 · 배달 · 포장", out=0.3, mat="bbq_board",
                letters="letters_bbq")
    b.awning("front", 4.0, 12.0, 3.0, depth=1.8, drop=0.3, valance=0.2)
    t = b.letters("치킨대학 인증 · 생맥주", 4.0, 0.22, 0.004)
    if t:
        f.glass_text(t, 8.0, 2.6, recess=0.25)
    for uu in (6.2, 9.6):
        plastic_table(b, f, uu, 3.0, name="table")
    for sx in (-5.2, -2.9):                                               # 배달 오토바이 줄
        PR.scooter(b.m, sx, -7.6, box="plastic_red")
    for i in range(3):
        uu = 1.0 + (b.w - 2.0) * (i + 0.5) / 3
        f.window(uu, g + 0.85, 2.4, 1.4, lit=b.chance(0.5), blind=b.blind())
    b.ac_wall("front", b.w - 0.75, 1.0, d=0.3, bracket=False, tries=(0, -0.3))
    finish_store(b, g, back_door=b.w - 2.0)
    return b, "BBQ 치킨"


# ---------------------------------------------------------------------------
# 7. GS칼텍스 주유소 + GS25 — 5x4. 캐노피 + 주유기 섬 3, 가격 기둥 간판, 자동 세차장, 공기 주입기, 매장
# ---------------------------------------------------------------------------

GS_BLUE = (0.01, 0.12, 0.45)
GS_ORANGE = (0.95, 0.40, 0.02)


def dispenser(m, x, y, z):
    """주유기: 몸체 + 화면 + 노즐 3 (휘발유 노랑 · 경유 초록 · 고급 빨강) + 호스"""
    m.box(x - 0.45, x + 0.45, y - 0.25, y + 0.25, z, z + 1.9, "gs_white")
    m.box(x - 0.46, x + 0.46, y - 0.26, y + 0.26, z + 1.9, z + 2.05, "gs_blue")
    for side in (-1, 1):
        yy = y + side * 0.255
        m.box(x - 0.3, x + 0.3, min(yy, yy + side * 0.01), max(yy, yy + side * 0.01), z + 1.3, z + 1.7, "screen")
        for k, mat in enumerate(("nozzle_yellow", "nozzle_green", "nozzle_red")):
            nx = x - 0.28 + k * 0.28
            m.box(nx - 0.05, nx + 0.05, min(yy, yy + side * 0.12), max(yy, yy + side * 0.12), z + 0.8, z + 1.05, mat)
            m.tube((nx, yy + side * 0.1, z + 0.8), (nx + 0.05, yy + side * 0.35, z + 0.15), 0.02, 0.02, "rubber",
                   n=6)


def gas_station(text_fn=None):
    b = Building((5, 4), 16.0, 9.0, setback=21.0, seed=77, text_fn=text_fn)   # 매장 x -8..8, y 5..14
    b.mats.update({
        "wall": {"color": (0.92, 0.92, 0.90), "rough": 0.4}, "wall_side": render((0.86, 0.86, 0.84)),
        "gs_white": solid((0.93, 0.93, 0.92), 0.35, 0.2), "gs_blue": glow(GS_BLUE, 0.8, 0.4),
        "gs_orange": glow(GS_ORANGE, 1.0, 0.4), "letters_gs": glow(GS_BLUE, 2.5),
        "letters_gsw": glow((0.98, 0.98, 0.95), 3.0), "letters_led": glow((1.0, 0.25, 0.05), 4.0),
        "letters_led2": glow((0.1, 1.0, 0.3), 4.0), "screen": glow((0.15, 0.35, 0.55), 1.5),
        "nozzle_yellow": solid((0.95, 0.75, 0.05)), "nozzle_green": solid((0.10, 0.55, 0.15)),
        "nozzle_red": solid((0.80, 0.05, 0.05)), "price_board": sign((0.03, 0.03, 0.04), 0.1),
        "forecourt": {"color": (0.55, 0.55, 0.53), "color2": (0.50, 0.50, 0.48), "pattern": "panel",
                      "scale": (4.0, 4.0), "mortar": 0.003, "mortar_color": (0.3, 0.3, 0.3), "rough": 0.8},
        "brush": {"color": (0.10, 0.30, 0.75), "color2": (0.05, 0.18, 0.50), "pattern": "stripes", "scale": 0.08,
                  "rough": 0.9},
        "gs_board": sign((0.95, 0.95, 0.93), 0.6), "letters_gs25": glow((0.0, 0.17, 0.62), 2.5),
        "hazard": HAZARD, "plate_white": solid((0.92, 0.92, 0.90), 0.5),
        "letters_dark": solid((0.05, 0.05, 0.06), 0.4), "poster_blue": sign((0.02, 0.20, 0.60), 0.4),
    })
    m = b.m
    H = 4.6
    b.lot_slab("asphalt")
    m.box(-14.0, 14.0, -13.5, 1.5, 0.03, 0.05, "forecourt", skip=(BOTTOM,))     # 캐노피 아래 콘크리트 판
    # 매장 (GS25)
    b.shell(H)
    f = b.face("front")
    f.storefront(0.5, 15.5, 0.03, 3.2, bay=1.3, transom=2.5, doors=[(3.0, 1.6)])
    b.sign_band("front", 0.25, 15.75, 3.35, 4.2, "GS25", "주유소 편의점 · 세차 결제", out=0.3, mat="gs_board",
                letters="letters_gs25")
    store_front_details(b, f, [(6.0, 1.2, 0.8, 0.9, "poster_blue", "세차 쿠폰", "letters"),
                               (7.2, 1.2, 0.8, 0.9, "poster_blue", "1+1", "letters")], ["gs_orange"], 1.0, ())
    b.face("left").door(3.0, 0.9, 2.1, leaf="door_metal", name="toilet_m")
    b.lightbox("left", 3.0, 2.55, 1.2, 0.35, "화장실", mat="gs_board", letters="letters_gs25")
    b.face("back").door(8.0, 0.9, 2.1, leaf="door_metal", name="back")
    b.windows("right", [0.03], 2, 1.2, 1.0, sill=1.3, margin=2.0)
    b.ac_wall("back", 4.0, 1.5)
    b.ac_wall("back", 12.0, 1.5)
    b.plinth(h=0.3)
    b.parapet(h=0.5, mat="wall_side")
    b.ac_roof(-3.0, b.y1 - 1.0, b.height)
    b.ac_roof(-1.7, b.y1 - 1.0, b.height)
    # 캐노피: 기둥 6 + 지붕판 + 흰 · 파랑 · 주황 띠 + GS칼텍스 글자 + 천장 조명
    cx0, cx1, cy0, cy1, cz = -13.0, 13.0, -13.0, 1.0, 5.4
    for px in (-8.0, 0.0, 8.0):
        for py in (-9.5, -3.5):
            m.box(px - 0.25, px + 0.25, py - 0.25, py + 0.25, 0.25, cz, "gs_white")
    m.box(cx0, cx1, cy0, cy1, cz, cz + 0.4, "gs_white", skip=())
    m.box(cx0 - 0.15, cx1 + 0.15, cy0 - 0.15, cy1 + 0.15, cz + 0.4, cz + 1.2, "gs_white")
    m.box(cx0 - 0.2, cx1 + 0.2, cy0 - 0.2, cy1 + 0.2, cz + 0.5, cz + 0.75, "gs_blue")
    m.box(cx0 - 0.22, cx1 + 0.22, cy0 - 0.22, cy1 + 0.22, cz + 0.75, cz + 0.85, "gs_orange")
    t = b.letters("GS칼텍스", 7.0, 0.32, 0.03)
    if t:
        Facade(m, "front", cx0 - 0.22, cx1 + 0.22, cy0 - 0.22, cy1 + 0.22).text(t, 13.22, cz + 1.02, 0.0,
                                                                              "letters_gs", kind=None)
        for side in ("left", "right"):
            Facade(m, side, cx0 - 0.22, cx1 + 0.22, cy0 - 0.22, cy1 + 0.22).text(t, 7.22, cz + 1.02, 0.0,
                                                                               "letters_gs", kind=None)
    for px in range(-11, 12, 4):
        for py in (-11.0, -6.5, -1.0):
            m.box(px - 0.6, px + 0.6, py - 0.3, py + 0.3, cz - 0.02, cz, "lamp")
    # 주유기 섬 3 (연석 + 기둥 보호대 + 주유기 2)
    for px in (-8.0, 0.0, 8.0):
        m.box(px - 0.7, px + 0.7, -11.0, -2.0, 0.05, 0.25, "concrete", skip=(BOTTOM,))
        for py in (-11.2, -1.8):
            m.cylinder(px, py, 0.12, 0.05, 1.1, "hazard", n=12)
        for py in (-7.5, -5.5):
            dispenser(m, px, py, 0.25)
        m.box(px - 0.15, px + 0.15, -4.4, -4.1, 0.25, 0.9, "nozzle_red")     # 소화기 함
    # 바닥 표시: 진입 · 진출 화살표, 정지선
    for px, ang in ((-11.0, 0.0), (11.0, math.pi)):
        PR.arrow(m, px, -8.0, 0.05, ang, length=3.0, width=0.5)
    PR.flat_text(m, b.letters("입구", 1.6, 0.6, 0.003), -16.0, -13.0, 0.05, "paint_white", 0.0, 1.6)
    PR.flat_text(m, b.letters("출구", 1.6, 0.6, 0.003), 16.0, -13.0, 0.05, "paint_white", math.pi, 1.6)
    # 가격 기둥 간판 (앞 왼쪽 모서리): GS칼텍스 머리판 + 유가 LED
    px, py = -17.5, -14.5
    m.box(px - 0.9, px + 0.9, py - 0.3, py + 0.3, 0.03, 0.5, "concrete")
    m.box(px - 0.8, px + 0.8, py - 0.25, py + 0.25, 0.5, 7.5, "gs_white")
    m.box(px - 0.82, px + 0.82, py - 0.27, py + 0.27, 5.6, 7.3, "gs_blue")
    m.box(px - 0.83, px + 0.83, py - 0.28, py + 0.28, 5.4, 5.6, "gs_orange")
    pf = Facade(m, "front", px - 0.83, px + 0.83, py - 0.28, py + 0.28)
    t = b.letters("GS칼텍스", 1.4, 0.4, 0.02)
    if t:
        pf.text(t, 0.83, 6.45, 0.0, "letters_gsw", kind=None)
    for k, (fuel, price, mat) in enumerate((("휘발유", "1,689", "letters_led"), ("경유", "1,559", "letters_led2"),
                                             ("고급", "1,949", "letters_led"))):
        zz = 4.6 - k * 1.2
        pf.box(0.08, 1.58, zz, zz + 1.0, 0.0, 0.03, "price_board")
        for txt, uu, w in ((fuel, 0.4, 0.55), (price, 1.1, 0.8)):
            t = b.letters(txt, w, 0.4 if txt == price else 0.22, 0.01)
            if t:
                pf.text(t, uu, zz + 0.5, 0.03, mat if txt == price else "letters_gsw", kind=None)
    # 자동 세차장 (오른쪽): 문형 프레임 + 지붕 + 회전 솔 2 + 간판
    wx0, wx1, wy0, wy1 = 13.5, 19.5, 0.0, 12.0
    for wx in (wx0, wx1 - 0.3):
        m.box(wx, wx + 0.3, wy0, wy1, 0.03, 4.2, "gs_white")
    m.box(wx0, wx1, wy0, wy1, 4.2, 4.5, "gs_white")
    m.box(wx0 - 0.05, wx1 + 0.05, wy0 - 0.06, wy0, 3.5, 4.5, "gs_blue")
    t = b.letters("자동세차", 3.5, 0.6, 0.03)
    if t:
        Facade(m, "front", wx0 - 0.05, wx1 + 0.05, wy0 - 0.06, wy0).text(t, 3.05, 4.0, 0.0, "letters_gsw", kind=None)
    m.box(wx0 + 0.35, wx1 - 0.35, 5.6, 5.9, 0.03, 3.4, "gs_blue")       # 세차 문형 기계
    for bx in (wx0 + 1.0, wx1 - 1.0):
        m.cylinder(bx, 5.0, 0.55, 0.15, 3.2, "brush", n=16)
    m.cylinder_x(wx0 + 0.6, wx1 - 0.6, 5.0, 3.5, 0.4, "brush", n=14)
    m.box(wx0 + 1.0, wx1 - 1.0, -1.6, -1.4, 0.03, 0.08, "paint_white")
    # 공기 주입기 · 휴지통
    m.box(-15.0, -14.6, 3.0, 3.4, 0.03, 1.4, "gs_blue")
    m.box(-15.1, -14.5, 2.9, 3.5, 1.4, 1.5, "gs_orange")
    m.tube((-14.8, 2.95, 1.0), (-14.0, 2.4, 0.1), 0.02, 0.02, "rubber", n=6)
    for k, mat in enumerate(("nozzle_yellow", "nozzle_green")):
        m.box(-12.6 + k * 0.6, -12.1 + k * 0.6, 3.0, 3.5, 0.03, 0.9, mat)
    b.top = max(b.top, 7.5)
    b.finalize()
    return b, "GS칼텍스 주유소"


# ---------------------------------------------------------------------------
# 8. 일산새마을금고 (대학길 169) — 3x2, 3층. MG 파랑 · 주황, 1층 객장 통유리 + 365 자동화코너, 옥상 간판, 깃대
# ---------------------------------------------------------------------------

MG_BLUE = (0.02, 0.15, 0.50)
MG_ORANGE = (0.95, 0.45, 0.02)


def mg_bank(text_fn=None):
    b = Building((3, 2), 20.0, 11.0, setback=4.0, seed=78, text_fn=text_fn)    # y -4..7
    b.mats.update({
        "wall": {"color": (0.82, 0.80, 0.76), "color2": (0.78, 0.76, 0.72), "pattern": "tile", "scale": (1.2, 0.6),
                 "mortar": 0.004, "mortar_color": (0.6, 0.58, 0.55), "rough": 0.4, "bump": 0.1},
        "wall_side": render((0.84, 0.83, 0.80), grime=0.15),
        "mg_board": sign((0.96, 0.96, 0.95), 0.5), "letters_mg": glow(MG_BLUE, 2.5),
        "mg_blue": dict(glow(MG_BLUE, 0.6), rough=0.4), "mg_orange": dict(glow(MG_ORANGE, 1.0), rough=0.4),
        "letters_mgw": glow((0.98, 0.98, 0.95), 3.0), "flag_mg": solid(MG_BLUE, 0.6),
        "flag_mg2": solid(MG_ORANGE, 0.6),
    })
    g, u = 4.5, 3.4
    H = g + 2 * u
    m = b.m
    b.lot_slab()
    b.shell(H)
    f = b.face("front")
    f.storefront(0.5, 14.0, 0.03, 3.4, bay=1.5, transom=2.6, doors=[(5.0, 2.0)], name="lobby")
    f.storefront(14.6, 19.5, 0.03, 3.4, bay=1.2, transom=2.6, doors=[(17.0, 1.6)], name="atm")
    b.sign_band("front", 0.3, 14.2, 3.55, 4.35, "MG새마을금고", "일산새마을금고", out=0.3, mat="mg_board",
                letters="letters_mg")
    f.box(0.3, 14.2, 3.52, 3.57, 0.0, 0.32, "mg_orange", attached=False)
    b.lightbox("front", 17.05, 3.6, 4.6, 0.6, "365 자동화코너", mat="mg_blue", letters="letters_mgw")
    f.disc(1.0, 3.95, 0.3, 0.3, 0.04, "mg_orange", n=20)                   # 로고 점 (MG 주황)
    for zf in (g, g + u):
        f.curtain(1.5, 18.5, zf + 0.9, zf + 2.5, 1.6, 1.42, lit=0.6, rng=b.rng, name="ribbon")   # 띠창 (창살 12칸)
        f.box(0.0, 20.0, zf + 0.05, zf + 0.25, 0.0, 0.1, "mg_blue")
        f.reserve(FIXTURE, 0.0, 20.0, zf + 0.05, zf + 0.25, 0.0, 0.1, "blue_band")
    for k, fu in enumerate((1.6, 3.2, 4.8)):                               # 깃대 3 + 깃발
        x, y = f.xy(fu, 3.4)
        m.cylinder(x, y, 0.04, 0.03, 7.0, "metal", n=8)
        m.cylinder(x, y, 0.07, 7.0, 7.1, "metal", n=8)
        m.box(x + 0.05, x + 1.25, y - 0.01, y + 0.01, 5.9, 6.8, "flag_mg" if k != 1 else "flag_mg2")
        f.reserve(FOREGROUND, fu - 0.1, fu + 1.3, 0.03, 7.1, 3.3, 3.5, "flagpole")
    for k in range(5):
        PR.bollard(m, *f.xy(7.5 + k * 1.6, 3.6))
    f.reserve(FOREGROUND, 7.4, 14.0, 0.03, 0.9, 3.5, 3.7, "bollards")
    for zf in (g, g + u):
        for uu in (2.5, 8.5):
            b.face("left").window(uu, zf + 1.0, 1.4, 1.4, lit=b.chance(0.5), blind=b.blind())
            b.face("right").window(uu, zf + 1.0, 1.4, 1.4, lit=b.chance(0.5), blind=b.blind())
    b.windows("back", [g, g + u], 4, 1.2, 1.1, sill=1.1, margin=2.5)
    b.face("back").door(4.0, 1.0, 2.2, leaf="door_metal", name="back")
    b.downpipe("left", 0.3, top=H + 0.9)
    b.gas_pipe("right", 3.8, b.d - 1.5)
    for uu in (10.0, 15.0):
        b.ac_wall("back", uu, 1.4, cage=True)
    b.plinth()
    b.parapet(h=0.9)
    z, pt = b.height, b.parapet_t
    sy = b.y0 + pt + 0.5                                                   # 옥상 간판: 일산새마을금고
    for px in (-6.0, 0.0, 6.0):
        m.box(px - 0.07, px + 0.07, sy + 0.18, sy + 0.32, z, z + 3.0, "metal_dark")
        m.beam((px, sy + 0.25, z + 2.2), (px, sy + 1.4, z + 0.05), 0.06, 0.06, "metal_dark")
    m.box(-7.0, 7.0, sy, sy + 0.18, z + 0.9, z + 2.9, "mg_blue")
    m.box(-7.0, 7.0, sy - 0.02, sy, z + 0.9, z + 1.1, "mg_orange")
    t = b.letters("일산새마을금고", 11.0, 1.2, 0.06)
    if t:
        Facade(m, "front", -7.0, 7.0, sy, sy + 0.18).text(t, 7.0, z + 2.0, 0.0, "letters_mgw", kind=None)
    b.roof_reserve("roof_sign", -7.1, 7.1, sy - 0.1, sy + 1.45, z, z + 3.0)
    b.stair_house(b.x0 + 0.6, b.x0 + 3.8, b.y1 - 3.4, b.y1 - 0.6)
    for i in range(4):
        b.ac_roof(b.x1 - 1.4 - i * 1.3, b.y1 - 1.0, z)
    b.finalize()
    return b, "일산새마을금고"


# ---------------------------------------------------------------------------
# 9. 식당153 울산본점 — 2x3, 2층 해물칼국수 집 (일산해수욕장 앞 바다 조망). 흰 벽 + 목재, 2층 통유리 + 발코니,
#    1층 조개 수조 · 대기 의자, 큰 상호 글자
# ---------------------------------------------------------------------------

def sikdang153(text_fn=None):
    b = Building((2, 3), 14.0, 14.0, setback=4.5, seed=79, text_fn=text_fn)    # y -7.5..6.5
    b.mats.update({
        "wall": render((0.93, 0.92, 0.90), grime=0.1), "wall_side": render((0.90, 0.89, 0.87), grime=0.15),
        "wood_cladding": {"color": (0.44, 0.27, 0.14), "color2": (0.34, 0.20, 0.10), "pattern": "stripes",   # 세로 판재
                          "scale": 0.14, "rough": 0.6},
        "letters_153": glow((0.08, 0.20, 0.40), 1.2),
        "letters_153s": glow((0.75, 0.25, 0.05), 1.5), "sign": sign((0.92, 0.88, 0.80), 0.3),
        "bench_wood": WOOD_LOUVER, "clam": {"color": (0.75, 0.70, 0.62), "color2": (0.45, 0.40, 0.35),
                                            "pattern": "noise", "scale": 20.0, "rough": 0.6, "bump": 0.4},
    })
    g, u = 4.2, 4.0
    H = g + u
    m = b.m
    b.lot_slab()
    b.shell(H, zones={"front": [(0.03, g, "wood_cladding"), (g, H, "wall")]})
    f = b.face("front")
    f.storefront(0.5, 9.0, 0.03, 3.4, bay=1.4, transom=2.6, doors=[(7.8, 1.8)])
    b.wall_text("front", "식당153", 11.4, 3.0, 4.2, 1.1, mat="letters_153", extrude=0.1)
    b.wall_text("front", "해물칼국수 · 울산본점", 11.4, 1.8, 4.0, 0.4, mat="letters_153s")
    f.curtain(0.3, 13.7, g + 0.2, H - 0.25, 3.5, 1.7, spandrel=0.0, lit=0.7, rng=b.rng, name="seaview")
    b.balcony("front", 0.3, 13.7, g, depth=1.4, rail="bars")
    for k in range(2):                                                    # 조개 수조 2 (스테인리스 + 물 + 조개)
        uu = 2.2 + k * 2.6
        b.aquarium("front", uu, w=2.0, d0=0.45, depth=0.8)
        for j in range(6):
            x, y = f.xy(uu - 0.75 + j * 0.3, 0.85)
            m.ellipsoid(x, y, 0.8, 0.09, 0.07, 0.04, "clam", nu=8, nv=4)
    for bu in (10.0, 12.6):                                               # 대기 의자
        f.box(bu - 1.0, bu + 1.0, 0.42, 0.48, 2.2, 2.6, "bench_wood", attached=False)
        for lu in (bu - 0.85, bu + 0.85):
            f.box(lu - 0.04, lu + 0.04, 0.03, 0.42, 2.25, 2.55, "metal_dark", attached=False)
        f.reserve(FOREGROUND, bu - 1.0, bu + 1.0, 0.03, 0.48, 2.2, 2.6, "bench")
    for uu in (0.25, 13.75):
        wall_lamp(f, uu, 2.4)
    for zf in (0.03, g):
        b.face("left").window(4.0, zf + 1.0, 1.6, 1.4, lit=b.chance(0.5), blind=b.blind())
        b.face("left").window(9.0, zf + 1.0, 1.6, 1.4, lit=b.chance(0.5), blind=b.blind())
    b.face("right").door(10.5, 1.0, 2.2, leaf="door_metal", name="kitchen")
    b.windows("back", [0.03, g], 3, 1.2, 1.1, sill=1.2, margin=2.5)
    b.downpipe("left", b.d - 0.3, top=H + 0.9)
    b.gas_pipe("right", 3.6, 4.0)
    b.ac_wall("back", 7.0, 1.4)
    b.plinth(h=0.3)
    b.parapet(h=0.4, mat="wall")
    z, pt = b.height, b.parapet_t                                         # 옥상 테라스 (바다 조망)
    m.box(b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y0 + 6.0, z, z + 0.12, "deck", skip=(BOTTOM,))
    b.roof_reserve("deck", b.x0 + pt, b.x1 - pt, b.y0 + pt, b.y0 + 6.0, z, z + 0.12)
    zr = z + 0.12
    glass_rail(b, b.x0 + pt + 0.03, b.x1 - pt - 0.03, b.y0 + pt + 0.03, b.y0 + pt + 0.07, zr, name="rail_f")
    for tx in (-3.5, 0.0, 3.5):
        b.roof_reserve("roof_cafe", *PR.cafe_set(m, tx, b.y0 + 3.2, zr, "parasol", r=1.1))
    b.stair_house(b.x1 - 4.0, b.x1 - 0.6, b.y1 - 3.6, b.y1 - 0.6, h=2.8)
    b.water_tank(b.x0 + 1.6, b.y1 - 1.6, z, r=0.7, h=1.2)
    b.finalize()
    return b, "식당153 울산본점"


DESIGNS = {
    "IlsanParisBaguette": paris_baguette,
    "IlsanBaskin": baskin,
    "IlsanCompose": compose_coffee,
    "IlsanOliveDaiso": olive_daiso,
    "IlsanEmart24": emart24,
    "IlsanBBQ": bbq,
    "IlsanGasStation": gas_station,
    "IlsanMGBank": mg_bank,
    "IlsanSikdang153": sikdang153,
}
