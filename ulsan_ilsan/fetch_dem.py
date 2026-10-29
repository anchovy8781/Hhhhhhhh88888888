"""Copernicus GLO-30 DEM 에서 울산 동구 일산동 일대를 잘라 data/ 에 저장한다.

    pip install numpy tifffile imagecodecs
    python3 fetch_dem.py

결과물(data/ilsan_dem.npy, data/ilsan_dem.json)은 저장소에 포함되어 있으므로
블렌더 장면을 만들 때는 이 스크립트를 다시 돌릴 필요가 없다.
"""

import json
import os
import tempfile
import urllib.request

import numpy as np

# 일산해수욕장 · 대왕암공원 · 방어진항 북쪽을 포함하는 영역 (WGS84)
BBOX = {"south": 35.483, "north": 35.508, "west": 129.412, "east": 129.452}

TILE = "Copernicus_DSM_COG_10_N35_00_E129_00_DEM"
URL = f"https://copernicus-dem-30m.s3.amazonaws.com/{TILE}/{TILE}.tif"
TILE_LAT, TILE_LON = 36.0, 129.0  # 타일 왼쪽 위 모서리
ATTRIBUTION = ("Copernicus DEM GLO-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH "
               "2014-2018 provided under COPERNICUS by the European Union and ESA")

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    import tifffile

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "tile.tif")
        print("다운로드:", URL)
        urllib.request.urlretrieve(URL, path)
        dem = tifffile.imread(path).astype(np.float32)

    rows, cols = dem.shape  # 1 arc-second = 1/3600 도
    r0 = int((TILE_LAT - BBOX["north"]) * rows)
    r1 = int((TILE_LAT - BBOX["south"]) * rows)
    c0 = int((BBOX["west"] - TILE_LON) * cols)
    c1 = int((BBOX["east"] - TILE_LON) * cols)
    crop = dem[r0:r1, c0:c1]

    # 픽셀 중심 좌표 기준의 실제 범위
    meta = {
        "north": TILE_LAT - (r0 + 0.5) / rows,
        "south": TILE_LAT - (r1 - 0.5) / rows,
        "west": TILE_LON + (c0 + 0.5) / cols,
        "east": TILE_LON + (c1 - 0.5) / cols,
        "shape": list(crop.shape),
        "units": "m (EGM2008)",
        "source": URL,
        "attribution": ATTRIBUTION,
    }
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    np.save(os.path.join(HERE, "data", "ilsan_dem.npy"), crop)
    with open(os.path.join(HERE, "data", "ilsan_dem.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"저장: {crop.shape}, 고도 {crop.min():.1f} ~ {crop.max():.1f} m")


if __name__ == "__main__":
    main()
