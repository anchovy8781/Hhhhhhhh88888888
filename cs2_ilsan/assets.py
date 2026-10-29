"""일산지 거리 상가 — 시티즈: 스카이라인 2 건물 에셋 생성기 (13종).

    blender -b --python assets.py -- [옵션]
    (또는 bpy 모듈이 있는 파이썬:  python assets.py -- [옵션])

옵션
  --only NAME[,NAME]  일부만 (예: IlsanHoetjip01)
  --tex N             텍스처 해상도 강제 (기본: catalog.py 의 에셋별 값)
  --font PATH         간판 한글 폰트 (생략 시 맑은 고딕 · 애플 SD 고딕 · 나눔고딕 자동 탐색)
  --out DIR           출력 폴더 (기본 ./CS2Assets) — CS2 Asset Importer 의 Project Root 로 지정
  --preview DIR       미리보기 렌더 저장 폴더 (생략 시 렌더 안 함)
  --no-bake           베이크 생략 (모델만 확인할 때, --save-blend 와 함께)

에셋마다 <out>/<이름>/ 에
  <이름>.fbx, <이름>_LOD1.fbx, <이름>_LOD2.fbx,
  <이름>_BaseColor/_Normal/_MaskMap/_ControlMask/_Emissive.png, <이름>.json
을 만든다. 원점 = 부지 중심 지면, 정면 = 도로 쪽(-Y), 1 단위 = 1 m, 부지는 8 m 셀 단위.
만들기 전에 designs.validate() 로 겹침 · 부지 이탈 · 재질 누락을 검사하고, 하나라도 있으면 중단한다.
"""

import argparse
import glob
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bake  # noqa: E402
import catalog  # noqa: E402
import designs  # noqa: E402
import kit  # noqa: E402
import materials  # noqa: E402

FONT_CANDIDATES = [
    os.path.join(HERE, "fonts", "*.ttf"), os.path.join(HERE, "fonts", "*.otf"),
    "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/NanumGothicBold.ttf", os.path.expanduser("~/Library/Fonts/NanumGothicBold.ttf"),
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]


def find_font(path=None):
    if path:
        return path if os.path.isfile(path) else None
    for pattern in FONT_CANDIDATES:
        for f in sorted(glob.glob(pattern)):
            return f
    return None


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="assets.py")
    p.add_argument("--only")
    p.add_argument("--tex", type=int)
    p.add_argument("--font")
    p.add_argument("--out", default=os.path.join(HERE, "CS2Assets"))
    p.add_argument("--preview")
    p.add_argument("--no-bake", action="store_true")
    p.add_argument("--save-blend")
    return p.parse_args(argv)


def make_asset(name, font_path, out_root, tex=None, preview_dir=None, do_bake=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    font = bpy.data.fonts.load(font_path) if font_path else None
    b, title = designs.DESIGNS[name](kit.text_fn_for(font))
    cw, cd, kind, _, cat_tex = catalog.ASSETS[name]
    if tuple(b.lot) != (cw, cd):
        raise ValueError(f"{name}: 부지 크기가 catalog.py 와 다릅니다")
    report = designs.validate(b)
    issues = {k: v for k, v in report.items() if v}
    if issues:
        raise ValueError(f"{name}: 검사 실패 {issues}")
    specs = dict(materials.BASE)
    specs.update(b.mats)
    obj = kit.to_object(b.m, name, specs)
    tex = tex or cat_tex
    info = {"name": name, "title": title, "kind": kind, "lot_cells": [cw, cd], "lot_m": [b.lw, b.ld],
            "footprint_m": [round(b.w, 2), round(b.d, 2)], "height_m": round(float(obj.dimensions.z), 2),
            "lod0_tris": bake.tri_count(obj), "openings": sum(1 for s in b.slots if s.kind == "opening"),
            "texture": tex}
    if not do_bake:
        return obj, info
    out_dir = os.path.join(out_root, name)
    bake.unwrap(obj)
    paths = bake.bake_texture_set(obj, name, out_dir, size=tex)
    src_names = bake.tag_source_materials(obj)
    mat = bake.baked_material(name, paths)
    bake.replace_materials(obj, mat)
    bake.export_fbx(obj, os.path.join(out_dir, name + ".fbx"))
    lods = []
    for level, drop, letters_ratio in ((1, bake.LOD1_DROP, 0.3), (2, bake.LOD2_DROP, None)):
        lod = bake.make_lod(obj, f"{name}_LOD{level}", 1.0, drop, src_names, letters_ratio)
        bake.export_fbx(lod, os.path.join(out_dir, lod.name + ".fbx"))
        lods.append(bake.tri_count(lod))
        lod.hide_render = True
    info["lod_tris"] = lods
    with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    if preview_dir:
        os.makedirs(preview_dir, exist_ok=True)
        bake.preview(obj, b.lw, b.ld, os.path.join(preview_dir, name + ".png"))
        bake.set_night(mat, 6.0)
        bake.preview(obj, b.lw, b.ld, os.path.join(preview_dir, name + "_night.png"), night=True)
    return obj, info


def main():
    args = parse_args()
    font_path = find_font(args.font)
    print("간판 폰트:", font_path or "없음 (글자 생략)")
    names = args.only.split(",") if args.only else list(designs.DESIGNS)
    infos = []
    for name in names:
        obj, info = make_asset(name, font_path, args.out, args.tex, args.preview, not args.no_bake)
        print(json.dumps(info, ensure_ascii=False))
        infos.append(info)
        if args.save_blend:
            os.makedirs(os.path.abspath(args.save_blend), exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(args.save_blend), name + ".blend"))
    if not args.no_bake and not args.only:
        with open(os.path.join(args.out, "catalog.json"), "w", encoding="utf-8") as f:
            json.dump(infos, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
