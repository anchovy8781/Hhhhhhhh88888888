# 실제 브랜드 로고 (SVG · PNG)

이 폴더에 `<키>.svg` 를 넣고 에셋을 다시 구우면, 그 브랜드 간판의 문구 자리에 **실제 로고**가 입체로 붙습니다
(간판 글자처럼 도형이라 텍스처 해상도와 상관없이 또렷합니다). 파일이 없는 브랜드는 지금처럼 브랜드 색 + 글자로 만듭니다.

- 형식: **SVG** (채움 색이 있는 도형 · `<text>` 글자 · 테두리선 · 그라데이션은 평균색) 또는 **PNG** (투명 배경, 색별로 격자 추적).
  그린 순서대로 조금씩 앞으로 쌓이므로 겹친 색도 깜빡이지 않습니다.
- 로고가 간판 바탕색에 묻히면(밝기 대비 3:1 미만) 그 간판은 흰 바탕이 되고 보조 문구는 로고 색이 됩니다.
- 채움 색이 없는 한 가지 색(검정) SVG 는 `kit.LOGO_TINT` 의 브랜드 색으로 칠합니다.
- 크기 · 비율은 자동으로 간판 자리에 맞춥니다 (가로 · 세로 중 꽉 차는 쪽 기준). 세로형 · 원형 엠블럼(가로 / 세로 < 1.6)은
  간판 왼쪽에 크게 두고 오른쪽에 매장 이름을 씁니다.
- 아주 세밀한 SVG(면 5,000개 초과)는 그림으로 그려 색별로 다시 추적해 면 수를 줄입니다 (더 적어질 때만).
- 다시 굽기: `blender -b --python assets.py -- --only IlsanGS25,IlsanCornerTower02` (해당 에셋만)

상표 사용: 이 키트는 상표권자의 사용 허가를 받은 **비영리** 프로젝트로 실제 상표를 씁니다 (저장소 소유자 확인).
다른 곳에 다시 배포할 때는 각 상표의 사용 조건을 따르세요.

| 키 (`<키>.svg`) | 브랜드 | 쓰이는 곳 | 파일 |
|---|---|---|---|
| `starbucks` | 스타벅스 사이렌 | `IlsanStarbucksDT` 원형 엠블럼 5곳 (정면 · 양옆 · 계단실 · 기둥 간판) | ✅ 실제 로고 (Simple Icons 도형) |
| `starbucks_wordmark` | STARBUCKS 글자 로고 | `IlsanStarbucksDT` 정면 글자 | |
| `homeplus` | 홈플러스 | `IlsanHomeplus` 정면 · 옆 큰 글자 | ✅ 실제 로고 (제공 파일) |
| `gs25` | GS25 | `IlsanGS25`, `IlsanCornerTower02` 1층, `IlsanGasStation` 매장 | ✅ 워드마크 시안 (제공 파일) |
| `gscaltex` | GS칼텍스 | `IlsanGasStation` 캐노피 3면 · 가격 기둥 | ✅ 워드마크 시안 (제공 파일) |
| `cu` | CU | `IlsanCU`, `IlsanCornerTower01` 1층 | ✅ 워드마크 시안 (제공 파일) |
| `7eleven` | 세븐일레븐 | `IlsanShop01` | ✅ 워드마크 시안 (제공 파일) |
| `emart24` | 이마트24 | `IlsanEmart24` | ✅ 워드마크 시안 (제공 파일) |
| `parisbaguette` | 파리바게뜨 | `IlsanParisBaguette` | ✅ 실제 로고 (제공 PNG) |
| `baskinrobbins` | 배스킨라빈스 | `IlsanBaskin` | ✅ 실제 로고 (제공 SVG, BR 엠블럼 + 이름) |
| `composecoffee` | 컴포즈커피 | `IlsanCompose` | ✅ 워드마크 시안 (제공 파일) |
| `megacoffee` | 메가MGC커피 | `IlsanCornerTower01` 1층 | ✅ 워드마크 시안 (제공 파일) |
| `ediya` | 이디야커피 | `IlsanCornerTower02` 1층 | ✅ 실제 로고 (제공 SVG, 원형 엠블럼 + 이름) |
| `oliveyoung` | 올리브영 | `IlsanOliveDaiso` 1층 | ✅ 실제 로고 (제공 SVG) |
| `daiso` | 다이소 | `IlsanOliveDaiso` 옆 · 옥상 간판 | ✅ 실제 로고 (제공 SVG) |
| `bbq` | BBQ | `IlsanBBQ` | ✅ 실제 로고 (제공 파일, 금색 그라데이션은 평균색) |
| `kyochon` | 교촌치킨 | `IlsanChicken01` | ✅ 실제 로고 (제공 SVG) |
| `kimbapcheonguk` | 김밥천국 | `IlsanMixed01` 1층 | ✅ 실제 로고 (제공 SVG) |
| `mg` | MG새마을금고 | `IlsanMGBank` 1층 간판 | ✅ 워드마크 시안 (제공 파일) |
| `angelinus` | 엔제리너스 | `IlsanTerracePark01` 1층 | ✅ 워드마크 시안 (제공 파일) |
| `pascucci` | 파스쿠찌 | `IlsanTerracePark01` 1층 | ✅ 실제 로고 (제공 SVG, 원형 엠블럼 + 이름) |
| `gongcha` | 공차 | `IlsanTerracePark01` 1층 | ✅ 실제 로고 (제공 SVG, 아주 세밀해 그림으로 추적) |
| `bonggubeer` | 봉구비어 | `IlsanTerracePark02` 1층 | ✅ 실제 로고 (제공 이미지 93×30 을 PNG 로 추적, 노랑으로 칠함) |
| `droptop` | 드롭탑 | `IlsanTerracePark02` 1층 | ✅ 실제 로고 (제공 SVG, 엠블럼 + 이름) |
| `ogada` | 오가다 | `IlsanTerracePark02` 1층 | ✅ 워드마크 시안 (제공 파일) |

간판 문구와 키의 연결은 `designs.BRAND_LOGOS` 에 있습니다.

'워드마크 시안'은 함께 받은 brand_svgs_23.zip 의 파일로, 그 안내문대로 공식 원본 로고가 아니라 브랜드 색 글자 + 밑줄 · 바탕으로 만든
스타일화된 시안입니다 (`pascucci.svg` 의 글자 오타 'P社SCUCCI' 는 PASCUCCI 로 고쳤습니다). 공식 SVG 를 같은 이름으로 덮어쓰면 그대로 바뀝니다.
