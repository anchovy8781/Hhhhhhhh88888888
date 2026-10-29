"""에셋 목록 (bpy 없이 쓰는 메타데이터). designs.py 의 부지 크기와 같아야 한다 (테스트로 확인)."""

CELL = 8.0

# 이름: (부지 가로 셀, 세로 셀, 종류, 간판, 텍스처 해상도)
ASSETS = {
    "IlsanHoetjip01": (2, 3, "횟집", "바다횟집", 2048),
    "IlsanHoetjip02": (3, 3, "횟집", "동해회센터", 2048),
    "IlsanCrab01": (2, 3, "대게", "대게 · 킹크랩", 2048),
    "IlsanCafe01": (2, 3, "카페", "카페 파도", 2048),
    "IlsanChicken01": (2, 2, "치킨", "치킨 · 호프", 2048),
    "IlsanGrill01": (2, 2, "조개구이", "조개구이", 1024),
    "IlsanShop01": (2, 2, "상가", "편의점", 2048),
    "IlsanMixed01": (3, 3, "근린상가", "근린상가", 2048),
    "IlsanMarket01": (4, 3, "시장", "수산물 판매센터", 2048),
    "IlsanMotel01": (3, 4, "숙박", "호텔 일산", 2048),
    "IlsanPension01": (2, 3, "펜션", "바다펜션", 2048),
    "IlsanVilla01": (2, 3, "주거", "해송빌라", 2048),
    "IlsanToilet01": (2, 2, "화장실", "해변 화장실", 1024),
}

# 도로 육지 쪽 배치 순서 (북 -> 남으로 반복, 자리에 안 맞으면 다음 후보).
# 횟집 · 대게 · 조개구이가 많고 카페 · 치킨 · 숙박 · 펜션 · 근린상가가 섞인 해변 상가 분위기
SEQUENCE = ["IlsanHoetjip01", "IlsanCafe01", "IlsanCrab01", "IlsanGrill01", "IlsanMixed01", "IlsanHoetjip02",
            "IlsanChicken01", "IlsanPension01", "IlsanShop01", "IlsanMotel01", "IlsanHoetjip01", "IlsanMarket01",
            "IlsanVilla01", "IlsanCafe01", "IlsanCrab01", "IlsanChicken01", "IlsanHoetjip02", "IlsanPension01",
            "IlsanGrill01", "IlsanShop01"]

# 도로 바다 쪽(백사장 앞) 시설: (에셋, 해안선 길이 비율)
SEASIDE = [("IlsanToilet01", 0.30), ("IlsanToilet01", 0.72)]
