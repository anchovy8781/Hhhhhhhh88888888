# 블렌더로 시티즈: 스카이라인 2 에셋 만들기

블렌더에서 모델링한 건물·소품을 **Cities: Skylines II 에셋 임포터**가 받아들이는 형태로
정리하는 가이드와 블렌더 애드온(`cs2_asset_tools`)입니다.

> 🏙️ **시티즈2 인게임 배치 키트:** [`cs2_ilsan/`](cs2_ilsan/) — 일산지 거리 실측 하이트맵 + 에셋 28종(상가 · 타니베이호텔 · 청년광장 · 해변 시설 · 소품, 텍스처 · LOD 포함) + 게임 좌표 배치표

> 📦 **파일로 받기:** GitHub **Actions → '일산지 CS2 키트 빌드'** 의 최근 실행 → 아래 **Artifacts**
> - `Ilsan_CS2_Kit` — 풀면 바로 쓰는 게임용 키트 폴더 (`CS2Assets` · `Heightmaps` · `docs` · `README.md`)
> - `Ilsan_CS2_zips` — 키트 전체 · 에셋만 · 하이트맵만 · 블렌더 애드온 zip + SHA256
>
> 푸시할 때마다 검사(겹침 · 부지 · 면 방향 · 배치) 후 자동으로 묶이고, `v` 로 시작하는 태그를 푸시하면 릴리스에도 첨부됩니다.
> 'Run workflow' 에서 `rebuild` 를 켜면 하이트맵과 에셋을 블렌더로 처음부터 다시 만듭니다. 로컬에서는 `python3 build_kit.py` → `dist/`.

> 🗺️ **예제 장면:** [`ulsan_ilsan/`](ulsan_ilsan/) — 울산 동구 **일산지 거리**(일산해수욕장 앞 해변 상가 거리)와 일산동 지형 블렌더 장면

> ⚠️ CS2 모딩 규격은 패치마다 바뀔 수 있습니다. 아래 내용은 공식 위키와 커뮤니티 문서를
> 바탕으로 정리했으니, 큰 작업 전에 작은 테스트 에셋으로 한 번 임포트해 보세요.

---

## 1. 전체 흐름

```
블렌더 모델링 ─▶ UV ─▶ 텍스처 (Substance/블렌더 베이크)
      │                         │
      ▼                         ▼
 메시 준비·LOD 생성      MaskMap / ControlMask 패킹
      └──────────┬──────────────┘
                 ▼
     <프로젝트 루트>/<에셋 이름>/  폴더로 FBX + PNG 내보내기
                 ▼
     게임 에디터 > Asset Importer 에서 프로젝트 루트 선택 → 임포트
```

## 2. 규칙 요약

### 단위·방향·원점
- **1 블렌더 단위 = 1 m.** 실제 크기로 만드세요 (2층 주택 높이 ≈ 6~8 m, 한 칸(셀) = 8 m).
- 변환(위치·회전·스케일)은 **모두 적용**(Ctrl+A)한 상태로 내보냅니다.
- 원점은 **바닥 면의 중앙**. 건물의 정면(도로 쪽)이 어느 축을 향해야 하는지는
  첫 테스트 임포트에서 확인하고 이후 모든 에셋에 똑같이 맞추세요.

### 파일 이름과 폴더
에셋 하나 = 폴더 하나. 메인 메시, LOD, 텍스처를 모두 같은 폴더에 둡니다.

```
CS2Assets/                    ← 임포터의 Project Root
└── MyBuilding/
    ├── MyBuilding.fbx        ← 메인 메시 (LOD0)
    ├── MyBuilding_LOD1.fbx
    ├── MyBuilding_LOD2.fbx
    ├── MyBuilding_BaseColor.png
    ├── MyBuilding_Normal.png
    ├── MyBuilding_MaskMap.png
    ├── MyBuilding_ControlMask.png   (선택: 색상 변형)
    └── MyBuilding_Emissive.png      (선택: 야간 발광)
```

- 텍스처는 **메시 이름 + 접미사**. 접미사는 **대소문자를 구분**합니다.
- 텍스처는 **정사각형**, 한 에셋 안에서 **모두 같은 해상도**, 2의 거듭제곱(1024, 2048 …) 권장.
- **채널당 8비트 PNG**만 쓰세요. 16비트는 임포트되지 않습니다.

### 텍스처 채널

| 파일 | 내용 |
|---|---|
| `_BaseColor` | 알베도(sRGB). 그림자/AO를 굽지 말고 순수 색만 |
| `_Normal` | 탄젠트 공간 노멀맵 (Unity 계열이므로 OpenGL/Y+ 방식이 일반적) |
| `_MaskMap` | **R** = Metallic, **G** = Coat(유광 코팅층), **B** = 건물 셰이더에서는 미사용, **A** = Glossiness(= 1 − Roughness) |
| `_ControlMask` | **R / G / B** = 게임 내 색상 변형 1 / 2 / 3 영역. 흰색인 부분이 BaseColor 위에 곱해져 색이 바뀝니다. **채널끼리 겹치지 않게** |
| `_Emissive` | 밤에 빛나는 창문·간판 등 |

> 지면 데칼·서피스(Surface) 에셋은 MaskMap 레이아웃이 다릅니다
> (R=Metallic, G=Metallic mask, B=Normal mask, A=Glossiness). 위 표는 **건물/소품** 기준입니다.

### LOD
- 메인 메시 외에 `_LOD1`, `_LOD2` … 를 단계마다 폴리곤을 줄여서 만듭니다 (보통 단계마다 절반 이하).
- 멀리서 보이는 실루엣만 유지하면 됩니다. 작은 디테일(난간, 창틀 돌출)은 LOD1부터 과감히 제거하세요.

## 3. 애드온 설치

```bash
python3 build_addon.py        # → dist/cs2_asset_tools.zip
```

블렌더 3.6 이상: **편집 > 환경설정 > 애드온 > 설치(Install from Disk)** 에서 zip 선택 → 체크해서 활성화.
3D 뷰포트에서 **N** 키 → **CS2** 탭이 생깁니다.

## 4. 애드온 사용법

1. **기본**
   - `에셋 이름`(예: `MyBuilding`)과 `프로젝트 루트` 폴더를 지정합니다.
   - **씬 단위 설정** – Metric / 스케일 1.0 / 미터로 맞춥니다.
   - 모델을 선택하고 **메인 메시 준비** – 변환 적용, 원점을 바닥 중앙으로, 월드 원점 배치,
     이름을 에셋 이름으로 변경. (여러 파트라면 먼저 Ctrl+J 로 합치세요.)
2. **LOD** – 개수와 단계별 비율(0.5 = 단계마다 절반)을 정하고 **LOD 생성**.
   `CS2_LODs` 컬렉션에 `MyBuilding_LOD1` … 이 만들어집니다. 다시 누르면 교체됩니다.
   자동 Decimate 결과가 지저분하면 직접 수정하거나 손으로 만든 메시에 같은 이름을 붙여도 됩니다.
3. **텍스처 패킹**
   - Metallic / Coat / Roughness(또는 Glossiness) 흑백 맵을 지정하고 **MaskMap 패킹**.
     비워 둔 채널은 기본값(Metallic 0, Coat 0, Glossiness 0.5)으로 채워집니다.
   - 색상 변형 영역 마스크 1~3장을 지정하고 **ControlMask 패킹**. 채널이 겹치면 경고합니다.
   - BaseColor / Normal / Emissive 는 베이크한 PNG 를 `<이름>_BaseColor.png` 처럼 이름 붙여 같은 폴더에 넣으세요.
4. **검사** – LOD별 삼각형 수, 변환 적용 여부, UV 유무, N-gon, 바닥 높이, LOD 감소 여부,
   텍스처 이름·정사각형·해상도 통일·8비트 여부를 확인해 패널에 표시합니다.
5. **FBX 내보내기** – 메인 메시와 각 LOD를 개별 FBX 로 저장합니다.
   (Scale: FBX All, Forward −Z / Up Y, Apply Transform 옵션)
   게임에서 에셋이 누워 있거나 90° 돌아가 있으면 `Apply Transform` 체크를 바꿔 다시 비교해 보세요.

## 5. 게임으로 가져오기

1. 게임 메인 메뉴에서 **에디터** 를 열고 상단 툴바의 **Asset Importer** 를 누릅니다.
2. **Project Root** 를 위의 `CS2Assets` 폴더로, 그 안의 `MyBuilding` 폴더를 선택해 임포트합니다.
3. 임포트된 프리팹에서 건물 종류(주거/상업 등), 부지 크기, 색상 변형 등을 설정하고 저장 →
   Paradox Mods 로 업로드할 수 있습니다.

## 6. 자주 하는 실수

| 증상 | 원인 / 해결 |
|---|---|
| 에셋이 엄청 크거나 작음 | 단위 스케일이 1.0 이 아니거나 스케일 미적용 → 씬 단위 설정 + 메인 메시 준비 |
| 에셋이 땅에 묻히거나 떠 있음 | 원점이 바닥 중앙이 아님 |
| 텍스처가 안 붙음 | 접미사 대소문자 오타, 메시 이름과 텍스처 이름 불일치 |
| 임포트 실패 | 16비트 PNG, 정사각형이 아닌 텍스처, 텍스처 해상도 불일치 |
| 너무 번들번들/무광 | MaskMap 의 A 채널은 Glossiness. Roughness 맵을 반전 없이 넣었는지 확인 |
| 색상 변형이 이상하게 섞임 | ControlMask 채널이 서로 겹침 |
| 그림자가 깨지거나 검은 면 | 노멀 방향 뒤집힘 (Shift+N 로 재계산), 겹친 면 제거 |

## 7. 개발

```bash
python3 -m unittest discover -s tests   # 블렌더 없이 패킹/검사/지형 로직 테스트
```

- `cs2_asset_tools/core.py` – 블렌더 비의존 로직 (이름 규칙, 채널 패킹, 텍스처 검사)
- `cs2_asset_tools/__init__.py` – 블렌더 UI 와 오퍼레이터

## 참고 자료
- [Cities Skylines 2 Wiki – Assets: Importing](https://cs2.paradoxwikis.com/Assets:_Importing)
- [Cities Skylines 2 Wiki – Asset Pipeline: Surfaces](https://cs2.paradoxwikis.com/Asset_Pipeline:_Surfaces)
- [Paradox – Adding Custom Assets (개발 일지)](https://www.paradoxinteractive.com/games/cities-skylines-ii/news/adding-custom-assets)
- [CSL Modding – CS2 Textures](https://cslmodding.info/cs2/textures/)
- [CSL Modding – Building Asset Creation](https://cslmodding.info/asset/building/)
- [DanOkami/CS2-Exporter-for-Blender](https://github.com/DanOkami/CS2-Exporter-for-Blender) – 참고할 만한 다른 블렌더 애드온
