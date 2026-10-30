"""재질 정의 (순수 데이터). kit.make_material 이 블렌더 노드로 바꾼다.

spec 키
  color, color2        기본색 (선형 RGB)
  pattern              None | 'noise' | 'tile' | 'panel' | 'paver' | 'stripes' | 'siding' | 'wood' | 'seam'
  scale                패턴 크기 (m). tile/panel/paver 는 (가로, 세로)
  axis                 seam 패턴의 줄 방향 ('x' 또는 'y')
  mortar, mortar_color 줄눈 폭 · 색
  rough, metal         거칠기, 금속성
  emit, emit_strength  발광색, 세기
  emit2                무늬를 따라 발광색을 emit ~ emit2 로 바꾼다 (유리 너머 진열대 · 방마다 다른 불빛)
  bump                 범프 세기
  grime                아래쪽 오염 (0~1)
  control              ControlMask RGB (게임 색상 변형 영역: R = 도장 벽, G = 차양 · 천막 · 포인트색)
"""

BASE = {
    # 구조 · 마감
    "reveal": {"color": (0.70, 0.69, 0.66), "pattern": "noise", "scale": 3.0, "rough": 0.85},
    "opening": {"color": (0.025, 0.025, 0.028), "rough": 0.9},
    "trim": {"color": (0.72, 0.71, 0.68), "pattern": "noise", "scale": 4.0, "rough": 0.8},
    "concrete": {"color": (0.48, 0.47, 0.45), "pattern": "noise", "scale": 2.0, "rough": 0.9, "bump": 0.2},
    "stone_base": {"color": (0.28, 0.27, 0.27), "color2": (0.22, 0.21, 0.21), "pattern": "tile",
                   "scale": (0.6, 0.35), "mortar": 0.004, "rough": 0.35, "bump": 0.1},
    "roof": {"color": (0.12, 0.36, 0.22), "color2": (0.09, 0.28, 0.17), "pattern": "noise", "scale": 0.8,
             "rough": 0.6},                                  # 옥상 우레탄 방수 (초록)
    "paving": {"color": (0.42, 0.40, 0.38), "color2": (0.36, 0.33, 0.31), "pattern": "paver",
               "scale": (0.4, 0.2), "mortar": 0.02, "rough": 0.85, "bump": 0.3},
    # 창 · 문
    "frame": {"color": (0.55, 0.57, 0.60), "rough": 0.35, "metal": 0.9},
    "frame_dark": {"color": (0.08, 0.08, 0.09), "rough": 0.4, "metal": 0.8},
    "glass": {"color": (0.05, 0.07, 0.08), "rough": 0.05, "metal": 0.6},
    # 불 켜진 창: 방마다 다른 불빛 (발광색이 무늬를 따라 emit ~ emit2 사이에서 바뀐다)
    "glass_lit": {"color": (0.05, 0.07, 0.08), "color2": (0.06, 0.08, 0.09), "pattern": "noise", "scale": 0.35,
                  "rough": 0.05, "metal": 0.6, "emit": (1.0, 0.80, 0.52), "emit2": (0.42, 0.28, 0.15),
                  "emit_strength": 0.9},
    # 상점 유리: 유리 너머 진열대 · 천장 조명 (칸 = 진열대, 줄눈 = 선반 · 기둥). 엇갈리지 않는 격자여야
    # 블록 벽처럼 보이지 않는다
    "glass_shop": {"color": (0.09, 0.11, 0.12), "color2": (0.12, 0.13, 0.14), "pattern": "panel", "scale": (1.8, 0.42),
                   "mortar": 0.02, "mortar_color": (0.04, 0.04, 0.045), "rough": 0.06, "metal": 0.3,
                   "emit": (1.0, 0.86, 0.66), "emit2": (0.10, 0.08, 0.06), "emit_strength": 0.6},
    "glass_door": {"color": (0.08, 0.10, 0.10), "rough": 0.05, "metal": 0.4},
    "glass_frost": {"color": (0.55, 0.60, 0.62), "rough": 0.3, "metal": 0.1},
    "blind": {"color": (0.72, 0.68, 0.60), "color2": (0.66, 0.62, 0.55), "pattern": "siding", "scale": 0.04,
              "rough": 0.8},
    "grille": {"color": (0.12, 0.12, 0.13), "rough": 0.5, "metal": 0.8},
    "door_metal": {"color": (0.35, 0.37, 0.40), "rough": 0.45, "metal": 0.7},
    "door_wood": {"color": (0.36, 0.22, 0.12), "color2": (0.28, 0.16, 0.08), "pattern": "wood", "rough": 0.6},
    "shutter": {"color": (0.62, 0.64, 0.66), "color2": (0.50, 0.52, 0.54), "pattern": "siding", "scale": 0.08,
                "rough": 0.4, "metal": 0.8},
    "curtain": {"color": (0.12, 0.38, 0.26), "rough": 0.55},
    # 설비
    "metal": {"color": (0.70, 0.71, 0.72), "rough": 0.3, "metal": 1.0},
    "metal_dark": {"color": (0.15, 0.16, 0.17), "rough": 0.45, "metal": 0.8},
    "stainless": {"color": (0.80, 0.80, 0.80), "rough": 0.25, "metal": 1.0},
    "ac": {"color": (0.82, 0.82, 0.80), "rough": 0.5},
    "tank": {"color": (0.12, 0.30, 0.60), "rough": 0.4},
    "gas_pipe": {"color": (0.85, 0.62, 0.04), "rough": 0.4, "metal": 0.3},
    "lamp": {"color": (0.95, 0.90, 0.75), "rough": 0.2, "emit": (1.0, 0.85, 0.6), "emit_strength": 4.0},
    "rubber": {"color": (0.03, 0.03, 0.03), "rough": 0.9},
    # 간판 · 글자
    "letters": {"color": (0.95, 0.95, 0.92), "rough": 0.4, "emit": (1.0, 1.0, 0.95), "emit_strength": 3.0},
    "letters_glass": {"color": (0.92, 0.92, 0.90), "rough": 0.5, "emit": (1.0, 1.0, 0.95), "emit_strength": 1.0},
    # 해변 상가 소품
    "water": {"color": (0.05, 0.25, 0.35), "rough": 0.05, "emit": (0.2, 0.6, 0.9), "emit_strength": 0.6},
    "glass_tank": {"color": (0.35, 0.50, 0.55), "rough": 0.03, "metal": 0.1},
    "styrofoam": {"color": (0.88, 0.88, 0.86), "rough": 0.9},
    "basin_red": {"color": (0.65, 0.06, 0.05), "rough": 0.6},
    "plastic_red": {"color": (0.70, 0.08, 0.06), "rough": 0.5},
    "plastic_blue": {"color": (0.08, 0.25, 0.70), "rough": 0.5},
    "plastic_white": {"color": (0.85, 0.85, 0.83), "rough": 0.5},
    "wood": {"color": (0.42, 0.26, 0.14), "color2": (0.30, 0.18, 0.09), "pattern": "wood", "rough": 0.7,
             "bump": 0.1},
    "deck": {"color": (0.45, 0.30, 0.18), "color2": (0.35, 0.22, 0.12), "pattern": "wood", "rough": 0.7,
             "bump": 0.1},
    "parasol": {"color": (0.92, 0.90, 0.84), "rough": 0.7, "control": (0, 1, 0)},
    "parking_line": {"color": (0.85, 0.85, 0.82), "rough": 0.6},
    "vinyl": {"color": (0.55, 0.60, 0.60), "rough": 0.08, "metal": 0.1},
    # 커튼월 · 고층
    "glass_curtain": {"color": (0.09, 0.15, 0.19), "color2": (0.07, 0.12, 0.16), "pattern": "noise", "scale": 6.0,
                      "rough": 0.04, "metal": 0.75},
    "glass_curtain_lit": {"color": (0.10, 0.14, 0.16), "color2": (0.09, 0.12, 0.14), "pattern": "noise",
                          "scale": 0.3, "rough": 0.05, "metal": 0.5, "emit": (1.0, 0.86, 0.62),
                          "emit2": (0.40, 0.30, 0.18), "emit_strength": 0.9},
    "spandrel": {"color": (0.10, 0.11, 0.12), "rough": 0.2, "metal": 0.6},
    "fin": {"color": (0.86, 0.86, 0.84), "rough": 0.35, "metal": 0.4},
    # 광장 · 조경
    "plaza_stone": {"color": (0.56, 0.55, 0.53), "color2": (0.47, 0.46, 0.45), "pattern": "paver",
                    "scale": (1.2, 0.6), "mortar": 0.006, "mortar_color": (0.30, 0.30, 0.30), "rough": 0.7,
                    "bump": 0.15},
    "plaza_stone_dark": {"color": (0.30, 0.30, 0.31), "color2": (0.25, 0.25, 0.26), "pattern": "paver",
                         "scale": (0.9, 0.45), "mortar": 0.006, "mortar_color": (0.18, 0.18, 0.18), "rough": 0.7,
                         "bump": 0.15},
    "granite": {"color": (0.62, 0.60, 0.58), "color2": (0.52, 0.50, 0.49), "pattern": "noise", "scale": 8.0,
                "rough": 0.45, "bump": 0.1},
    "pine_bark": {"color": (0.22, 0.14, 0.09), "color2": (0.12, 0.08, 0.05), "pattern": "noise", "scale": 5.0,
                  "rough": 0.95, "bump": 0.8},
    "pine_needles": {"color": (0.06, 0.16, 0.06), "color2": (0.03, 0.09, 0.03), "pattern": "noise", "scale": 7.0,
                     "rough": 0.85, "bump": 0.6},
    "shrub": {"color": (0.10, 0.25, 0.07), "color2": (0.05, 0.15, 0.04), "pattern": "noise", "scale": 6.0,
              "rough": 0.85, "bump": 0.5},
    "soil": {"color": (0.16, 0.11, 0.07), "pattern": "noise", "scale": 4.0, "rough": 0.95, "bump": 0.3},
    "led_strip": {"color": (0.85, 0.90, 1.0), "rough": 0.2, "emit": (0.55, 0.75, 1.0), "emit_strength": 5.0},
    "rail_black": {"color": (0.03, 0.03, 0.035), "rough": 0.4, "metal": 0.7},
    "paint_yellow": {"color": (0.85, 0.62, 0.04), "rough": 0.6},
    "paint_white": {"color": (0.88, 0.88, 0.86), "rough": 0.6},
    "apron_red": {"color": (0.55, 0.10, 0.07), "color2": (0.45, 0.08, 0.05), "pattern": "noise", "scale": 3.0,
                  "rough": 0.8, "bump": 0.2},
    "asphalt": {"color": (0.06, 0.06, 0.065), "color2": (0.04, 0.04, 0.045), "pattern": "noise", "scale": 10.0,
                "rough": 0.9, "bump": 0.3},
    "sand": {"color": (0.62, 0.53, 0.38), "color2": (0.55, 0.46, 0.32), "pattern": "noise", "scale": 3.0,
             "rough": 0.95, "bump": 0.4},
    "stream_water": {"color": (0.04, 0.12, 0.13), "rough": 0.03, "metal": 0.2},
    "membrane": {"color": (0.93, 0.93, 0.91), "rough": 0.6, "control": (0, 1, 0)},
    "white_steel": {"color": (0.90, 0.90, 0.88), "rough": 0.3, "metal": 0.3},
    "pool_water": {"color": (0.05, 0.32, 0.42), "rough": 0.02, "emit": (0.15, 0.55, 0.75), "emit_strength": 0.5},
    "pool_tile": {"color": (0.70, 0.85, 0.88), "color2": (0.62, 0.78, 0.82), "pattern": "tile",
                  "scale": (0.25, 0.25), "mortar": 0.006, "mortar_color": (0.85, 0.85, 0.85), "rough": 0.2},
    "speaker": {"color": (0.04, 0.04, 0.045), "rough": 0.6},
    "tree_leaf": {"color": (0.16, 0.34, 0.10), "color2": (0.09, 0.22, 0.06), "pattern": "noise", "scale": 5.0,
                  "rough": 0.85, "bump": 0.5},
    "glass_rail": {"color": (0.45, 0.55, 0.56), "rough": 0.05, "metal": 0.2},
    "lamp_red": {"color": (0.8, 0.05, 0.03), "rough": 0.3, "emit": (1.0, 0.05, 0.02), "emit_strength": 6.0},
}
