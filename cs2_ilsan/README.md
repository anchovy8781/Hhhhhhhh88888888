# 일산지 거리 — 시티즈: 스카이라인 2 인게임 배치 키트

울산 동구 **일산해수욕장 앞 해변 상가 거리**를 시티즈2 안에 그대로 옮기기 위한 키트입니다.

| 구성 | 위치 | 내용 |
|---|---|---|
| **실측 맵** | `Heightmaps/` | 일산지 거리를 중심으로 한 실제 지형 하이트맵(14.336 km)과 월드맵(57.344 km) |
| **건물 에셋 6종** | `CS2Assets/` | 횟집 2종, 카페, 호텔, 편의점, 조개구이. 8 m 셀 부지 크기, 텍스처 5종, LOD 3단계 |
| **배치표** | `Heightmaps/Ilsan_Placement.md` | 실제 해변 곡선을 따라 놓은 33개 부지의 게임 좌표 · 회전 · 높이 |

<!-- ASSET_TABLE -->

---

## 1. 맵 만들기 (실측 지형)

![하이트맵](docs/heightmap.jpg)

1. `Heightmaps/Ilsan_Heightmap.png`, `Ilsan_Worldmap.png` 를
   `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\Heightmaps\` 에 복사합니다.
2. 게임 메인 메뉴 → **에디터** → 새 맵 → 지형(Terrain) 패널에서 **하이트맵 가져오기**로
   `Ilsan_Heightmap`, **월드맵 가져오기**로 `Ilsan_Worldmap` 을 고릅니다. 높이 배율은 기본값 **4096 m** 그대로 둡니다.
3. 바다 쪽 맵 가장자리에 **해수(Sea) 수원**을 놓고 수위를 **40 m** 로 맞춥니다.
   (하이트맵은 해수면을 40 m 로 올려 두어 해저 38 m 까지 표현합니다.)
4. 맵 중심(0, 0)이 일산지 거리 한가운데입니다. 북쪽이 위입니다.

| 항목 | 값 |
|---|---|
| 해상도 · 형식 | 4096 × 4096, 16-bit 회색조 PNG |
| 플레이 영역 | 14.336 km (3.5 m/px), 중심 35.4984° N, 129.4314° E |
| 월드맵 | 57.344 km (14 m/px), 가운데 1024 px = 플레이 영역 |
| 고도 | −38 m(해저) ~ 343 m (게임 높이 = 실제 고도 + 40 m) |

> **정확도:** 육지는 Copernicus GLO-30(30 m 격자) 실측 고도를 보간했습니다. 원본은 바다를 0 m 로 평평하게 채우므로
> **해저 지형은 해안에서 1:45 기울기로 깊어지게 추정**했습니다. 30 m 원본보다 세밀한 지형(옹벽, 계단 등)은 없습니다.

## 2. 도로와 부지 위치

![거리 오버레이](docs/heightmap_street.jpg)

`Ilsan_Overlay.png` (하이트맵과 같은 4096² 크기의 투명 PNG):
- **청록** = 실제 해안선 (고도 0 m)
- **노랑** = 해변 도로 중심선 → 게임에서 **소형 2차로 도로**를 이 선을 따라 그립니다
- **흰 선** = 부지 앞선 (도로 중심에서 8 m), **색 사각형** = 부지 (빨강 횟집 · 갈색 카페 · 보라 호텔 · 초록 편의점 · 주황 조개구이)

맵 위에 이미지를 겹쳐 보여 주는 모드를 쓰면 그대로 따라 그릴 수 있습니다.
정확한 숫자가 필요하면 `Ilsan_Placement.md` (사람용 표)와 `Ilsan_Placement.json` (모드·스크립트용)을 보세요.
`Ilsan_Map.json` 에는 도로 중심선을 5 m 간격으로 찍은 점(약 130개)의 게임 좌표와 지면 높이가 있습니다.

- 게임 좌표: 맵 중심 원점, **x = 동쪽, z = 북쪽** (m)
- 회전: 건물 정면(도로 쪽)이 향하는 방위, **북쪽 0°에서 시계 방향**
- 부지끼리는 겹치지 않게 검사했고(분리축 검사), 해변 곡선 안쪽에서는 앞쪽에 작은 틈이 생깁니다
- 골목(해수욕장○길 같은 이면도로) 7곳은 부지를 비워 두었습니다

## 3. 에셋 가져오기

1. `CS2Assets` 폴더를 원하는 곳에 둡니다 (각 에셋은 하위 폴더 하나).
2. 에디터 → **Asset Importer** → **Project Root** 를 `CS2Assets` 로 지정 → 에셋 폴더 선택 → 임포트.
3. 프리팹 설정에서 **부지 크기(셀)**를 위 표대로 맞추고 건물 종류(상업 등)를 고릅니다.

| 파일 | 내용 |
|---|---|
| `<이름>.fbx` | LOD0. 1 단위 = 1 m, 원점 = **부지 중심 지면**, 정면 = 블렌더 −Y (유니티 +Z) |
| `<이름>_LOD1.fbx`, `_LOD2.fbx` | 약 30 %, 7 % 삼각형. 같은 UV 라 같은 텍스처를 씁니다 |
| `_BaseColor` | 기본색 + 약한 AO (sRGB) |
| `_Normal` | 탄젠트 공간, OpenGL(Y+) |
| `_MaskMap` | R = 금속성, G = 코트(0), B = 0, A = 광택(1 − 거칠기) |
| `_ControlMask` | **R = 도장 벽**, **G = 차양 · 천막 · 파라솔 · 간판 띠** → 게임의 색상 변형이 이 영역에 곱해집니다 |
| `_Emissive` | 발광 영역: 간판 글자 · 간판 · 수족관 · 상점 유리 · 불 켜진 창 |
| `<이름>.json` | 부지 · 크기 · 높이 · 삼각형 수 |

> **확인이 필요한 점 (게임 버전에 따라 다를 수 있음)**
> - 정면 방향: 정면이 유니티 +Z 를 향합니다. 게임에서 건물이 도로를 등지면 임포터에서 180° 돌리세요.
> - LOD 텍스처: LOD 파일은 메인 텍스처를 공유하도록 만들었습니다. 임포터가 LOD 별 텍스처 이름을 요구하면
>   텍스처 5장을 `<이름>_LOD1_BaseColor.png` 처럼 복사하세요.
> - 부지 바닥판: 부지 전체에 얇은 포장 바닥(두께 0.33 m, 지면 위 3 cm)이 포함되어 있습니다.

## 4. 직접 다시 만들기

```bash
# 하이트맵 · 오버레이 · 배치표 (numpy, tifffile 필요 — DEM 타일을 자동으로 받습니다)
pip install numpy tifffile imagecodecs
python3 heightmap.py

# 건물 에셋 (블렌더 3.6+ / 5.0.1 에서 확인). 간판 폰트는 맑은 고딕 → 나눔고딕 순으로 자동 탐색
blender -b --python assets.py -- --tex 2048 --preview previews
blender -b --python assets.py -- --only IlsanCafe01 --tex 4096   # 한 채만, 4K 텍스처

# 배치 검증: 하이트맵 지형 + 도로 + 배치표대로 놓은 FBX 를 렌더
blender -b --python preview_layout.py -- --render layout.png
```

- 간판 문구 · 색 · 층수 · 벽 재질: `assets.py` 의 디자인 함수 (`hoetjip01` …)
- 부지 크기 · 거리 배치 순서: `catalog.py` (`ASSETS`, `SEQUENCE`)
- 재질 정의: `kit.py` 의 `BASE_MATERIALS` (패턴 · 거칠기 · 금속성 · 발광 · ControlMask 채널)

## 5. 무엇이 실제이고 무엇이 가상인가

| 실측 | 근사 · 가상 |
|---|---|
| 지형 고도, 해안선, 해변 곡선, 도로 위치·높이 | 해저 깊이 (추정) |
| 거리 길이 약 660 m, 골목 간격 (해안선 기준 배치) | **가게 이름 · 간판 · 건물 디자인은 가상** — 실제 가게를 재현하지 않았습니다 |
| | 부지 순서 (`catalog.SEQUENCE` 반복) |

실제 가게 사진이나 이름을 알려 주시면 간판과 외관을 그 건물에 맞춰 바꿀 수 있습니다.

## 데이터 · 규격 출처

- 고도: Copernicus DEM GLO-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018,
  provided under COPERNICUS by the European Union and ESA (AWS Open Data `copernicus-dem-30m`)
- CS2 하이트맵 규격: Colossal Order 맵 에디터 개발 일지(4096², 16-bit, PNG/TIFF, 월드맵 가운데 1024² = 플레이 영역),
  Terraining Heightmap Generator 의 CS2 설정(57.344 km 월드, 높이 배율 4096)
- CS2 텍스처 접미사: Cities Skylines 2 Wiki · CSL Modding 문서
- 간판 폰트(미리보기 렌더): 나눔고딕 (SIL Open Font License)
