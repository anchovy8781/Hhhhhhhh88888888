"""에셋 목록 (bpy 없이 쓰는 메타데이터). designs.py 의 부지 크기와 같아야 한다 (테스트로 확인)."""

CELL = 8.0

# 이름: (부지 가로 셀, 세로 셀, 종류, 간판, 텍스처 해상도)
ASSETS = {
    "IlsanHoetjip01": (2, 3, "횟집", "바다횟집", 2048),
    "IlsanHoetjip02": (3, 3, "횟집", "동해회센터", 2048),
    "IlsanCrab01": (2, 3, "대게", "대게 · 킹크랩", 2048),
    "IlsanCafe01": (2, 3, "카페", "카페 파도", 2048),
    "IlsanChicken01": (2, 2, "치킨", "교촌치킨", 2048),
    "IlsanGrill01": (2, 2, "조개구이", "조개구이", 1024),
    "IlsanShop01": (2, 2, "편의점", "세븐일레븐", 2048),
    "IlsanMixed01": (3, 3, "근린상가", "근린상가", 2048),
    "IlsanMarket01": (4, 3, "시장", "수산물 판매센터", 2048),
    "IlsanMotel01": (3, 4, "숙박", "호텔 일산", 2048),
    "IlsanPension01": (2, 3, "펜션", "바다펜션", 2048),
    "IlsanVilla01": (2, 3, "주거", "해송빌라", 2048),
    "IlsanToilet01": (2, 2, "화장실", "해변 화장실", 1024),
    # 사진 속 건물 · 시설 (landmarks.py, plaza.py)
    "IlsanTanibayHotel": (7, 4, "호텔", "타니베이호텔", 4096),
    "IlsanCornerTower01": (3, 3, "상업빌딩", "일산스퀘어", 2048),
    "IlsanCornerTower02": (3, 3, "상업빌딩", "비치타워", 2048),
    "IlsanYouthStage": (2, 3, "청년공간", "청년스테이지ON", 2048),
    "IlsanHoetjip03": (2, 2, "횟집", "갈매기횟집", 2048),
    "IlsanBlueRoof01": (2, 2, "상가", "해변슈퍼", 2048),
    "IlsanPlaza01": (3, 4, "광장", "일산청년광장", 2048),
    "IlsanPlazaStage": (3, 4, "광장", "청년광장 버스킹 무대", 2048),
    "IlsanBeachLandmark": (2, 2, "조형물", "삼각 조형물", 1024),
    "IlsanStreamBridge": (2, 2, "다리", "하천 하구 보행교", 1024),
    "IlsanBeachRail": (1, 1, "소품", "해변 난간", 512),
    "IlsanPine01": (1, 1, "조경", "해송 (큰 나무)", 1024),
    "IlsanPine02": (1, 1, "조경", "해송 (굽은 나무)", 1024),
    "IlsanRoundabout": (2, 2, "교통", "회전교차로 중앙섬", 1024),
    "IlsanRoadMarking01": (1, 1, "교통", "CCTV 주차단속", 512),
    # 실제 브랜드 매장 (brands.py)
    "IlsanStarbucksDT": (3, 4, "카페", "스타벅스 울산일산비치DT점", 2048),
    "IlsanTerracePark01": (4, 3, "상가", "테라스파크 A동", 2048),
    "IlsanTerracePark02": (4, 3, "상가", "테라스파크 C동", 2048),
    "IlsanHomeplus": (8, 6, "대형마트", "홈플러스 울산동구점", 4096),
    "IlsanGS25": (2, 2, "편의점", "GS25", 2048),
    "IlsanCU": (2, 2, "편의점", "CU", 2048),
}

# CS2 에서 가져올 때의 종류: building(부지 있는 건물) · plaza(광장 · 공원 부지) · prop(부지 없는 소품)
TYPE = {name: "building" for name in ASSETS}
TYPE.update({n: "plaza" for n in ("IlsanPlaza01", "IlsanPlazaStage", "IlsanBeachLandmark", "IlsanStreamBridge")})
TYPE.update({n: "prop" for n in ("IlsanBeachRail", "IlsanPine01", "IlsanPine02", "IlsanRoundabout",
                                 "IlsanRoadMarking01")})

# 도로 육지 쪽 배치 순서 (북 -> 남으로 반복, 자리에 안 맞으면 다음 후보).
# 횟집 · 대게 · 조개구이가 많고 카페 · 치킨 · 숙박 · 펜션 · 근린상가가 섞인 해변 상가 분위기
SEQUENCE = ["IlsanHoetjip01", "IlsanCafe01", "IlsanCrab01", "IlsanGrill01", "IlsanMotel01", "IlsanHoetjip02",
            "IlsanChicken01", "IlsanPension01", "IlsanShop01", "IlsanMixed01", "IlsanHoetjip01", "IlsanMarket01",
            "IlsanVilla01", "IlsanHoetjip03", "IlsanCafe01", "IlsanCrab01", "IlsanChicken01", "IlsanHoetjip02",
            "IlsanPension01", "IlsanHoetjip03", "IlsanGrill01", "IlsanCU"]

# 도로 바다 쪽(백사장 앞) 시설: (에셋, 해안선 길이 비율)
SEASIDE = [("IlsanToilet01", 0.30), ("IlsanToilet01", 0.72)]

# 일산청년광장: 진입로 축을 따라 바다 쪽부터 놓는 광장 구간 (32 m 씩, 마지막이 버스킹 무대)
PLAZA_SEGMENTS = ["IlsanPlaza01", "IlsanPlaza01", "IlsanPlaza01", "IlsanPlazaStage"]

# 광장 양옆 상가 (광장을 바라본다). 모퉁이 유리 상가 뒤에서 광장 끝 쪽으로 차례로
PLAZA_SIDES = {
    "north": ["IlsanTerracePark01", "IlsanTerracePark02", "IlsanYouthStage", "IlsanHoetjip03"],
    "south": ["IlsanGS25", "IlsanBlueRoof01", "IlsanMixed01", "IlsanCrab01", "IlsanChicken01"],
}
