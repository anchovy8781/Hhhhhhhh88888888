"""배포용 파일 만들기 (블렌더 불필요): python3 build_kit.py -> dist/

  dist/Ilsan_CS2_Kit/         게임용 키트 폴더 (CS2Assets · Heightmaps · docs · README) — 액션 아티팩트로 그대로 올린다
  dist/Ilsan_CS2_Kit.zip      위 폴더 전체 압축
  dist/Ilsan_CS2Assets.zip    에셋 28종만 (풀어서 CS2 Asset Importer 의 Project Root 로 지정)
  dist/Ilsan_Heightmaps.zip   하이트맵 · 월드맵 · 오버레이 · 배치표 · 맵 정보
  dist/cs2_asset_tools.zip    블렌더 애드온 (편집 > 환경 설정 > 애드온 > 설치)
  dist/SHA256SUMS.txt

묶기 전에 catalog.json 의 에셋마다 FBX 3개(LOD0~2) · 텍스처 5장 · 정보 JSON 이 모두 있는지 확인하고,
하나라도 빠지면 실패한다.
"""

import hashlib
import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(ROOT, "cs2_ilsan")
DIST = os.path.join(ROOT, "dist")
SUFFIXES = (".fbx", "_LOD1.fbx", "_LOD2.fbx", "_BaseColor.png", "_Normal.png", "_MaskMap.png", "_ControlMask.png",
            "_Emissive.png", ".json")
MAPS = ("Ilsan_Heightmap.png", "Ilsan_Worldmap.png", "Ilsan_Overlay.png", "Ilsan_Placement.json",
        "Ilsan_Placement.md", "Ilsan_Map.json")


def check():
    """에셋 · 맵 파일이 빠짐없이 있는지. 반환: 에셋 목록 (catalog.json)"""
    with open(os.path.join(KIT, "CS2Assets", "catalog.json"), encoding="utf-8") as f:
        catalog = json.load(f)
    sys.path.insert(0, KIT)
    import catalog as cat  # noqa: E402  (bpy 없이 읽히는 목록)
    missing = [n for n in cat.ASSETS if n not in {a["name"] for a in catalog}]
    for a in catalog:
        folder = os.path.join(KIT, "CS2Assets", a["name"])
        missing += [a["name"] + s for s in SUFFIXES if not os.path.isfile(os.path.join(folder, a["name"] + s))]
    missing += [m for m in MAPS if not os.path.isfile(os.path.join(KIT, "Heightmaps", m))]
    if missing:
        raise SystemExit(f"빠진 파일이 있습니다: {missing}")
    return catalog


def zip_dir(path, out, arc_root):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, _, files in os.walk(path):
            for fn in sorted(files):
                full = os.path.join(base, fn)
                zf.write(full, os.path.join(arc_root, os.path.relpath(full, path)))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    catalog = check()
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    kit = os.path.join(DIST, "Ilsan_CS2_Kit")
    shutil.copytree(os.path.join(KIT, "CS2Assets"), os.path.join(kit, "CS2Assets"))
    os.makedirs(os.path.join(kit, "Heightmaps"))
    for m in MAPS:
        shutil.copy2(os.path.join(KIT, "Heightmaps", m), os.path.join(kit, "Heightmaps", m))
    shutil.copytree(os.path.join(KIT, "docs"), os.path.join(kit, "docs"))
    shutil.copy2(os.path.join(KIT, "README.md"), os.path.join(kit, "README.md"))

    outs = []
    for name, src, arc in (("Ilsan_CS2_Kit.zip", kit, "Ilsan_CS2_Kit"),
                           ("Ilsan_CS2Assets.zip", os.path.join(kit, "CS2Assets"), "CS2Assets"),
                           ("Ilsan_Heightmaps.zip", os.path.join(kit, "Heightmaps"), "Heightmaps")):
        zip_dir(src, os.path.join(DIST, name), arc)
        outs.append(name)
    addon = os.path.join(DIST, "cs2_asset_tools.zip")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in ("__init__.py", "core.py"):
            zf.write(os.path.join(ROOT, "cs2_asset_tools", fn), f"cs2_asset_tools/{fn}")
    outs.append("cs2_asset_tools.zip")
    with open(os.path.join(DIST, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        for name in outs:
            f.write(f"{sha256(os.path.join(DIST, name))}  {name}\n")

    lines = ["## 일산지 CS2 키트", "", f"에셋 {len(catalog)}종 · 하이트맵 · 배치표 · 블렌더 애드온", "",
             "| 파일 | 크기 |", "|---|---|"]
    for name in outs:
        lines.append(f"| `{name}` | {os.path.getsize(os.path.join(DIST, name)) / 1e6:.1f} MB |")
    lines += ["", "| 에셋 | 이름 | 종류 | 부지 | 높이 | 삼각형 LOD0 | 텍스처 |", "|---|---|---|---|---|---|---|"]
    for a in catalog:
        lines.append(f"| `{a['name']}` | {a['title']} | {a.get('type', 'building')} | "
                     f"{a['lot_cells'][0]}×{a['lot_cells'][1]} | {a['height_m']} m | {a['lod0_tris']:,} | {a['texture']} |")
    summary = "\n".join(lines) + "\n"
    with open(os.path.join(DIST, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(summary)
    for name in outs:
        print(f"{name}: {os.path.getsize(os.path.join(DIST, name)) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
