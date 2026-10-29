"""에셋 목록 (bpy 없이 쓰는 메타데이터). assets.py 의 디자인과 부지 크기가 같아야 한다."""

CELL = 8.0

# 이름: (부지 가로 셀, 세로 셀, 종류, 간판)
ASSETS = {
    "IlsanHoetjip01": (2, 3, "횟집", "바다횟집"),
    "IlsanHoetjip02": (3, 3, "횟집", "동해회센터"),
    "IlsanCafe01": (2, 3, "카페", "카페 파도"),
    "IlsanMotel01": (3, 4, "숙박", "호텔 일산"),
    "IlsanShop01": (2, 2, "상가", "편의점"),
    "IlsanGrill01": (2, 2, "조개구이", "조개구이"),
}

# 거리 배치 순서 (북 -> 남으로 반복). 횟집이 많고 카페·숙박이 섞인 실제 해변 상가 분위기
SEQUENCE = ["IlsanHoetjip01", "IlsanCafe01", "IlsanHoetjip02", "IlsanGrill01", "IlsanHoetjip01",
            "IlsanMotel01", "IlsanShop01", "IlsanHoetjip02", "IlsanCafe01", "IlsanHoetjip01", "IlsanGrill01"]
