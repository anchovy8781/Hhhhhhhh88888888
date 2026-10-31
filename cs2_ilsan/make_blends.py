"""에셋마다 시티즈2 업로드용 블렌더 파일 만들기 (CS2Assets 의 FBX · 텍스처에서).

    blender -b --python make_blends.py -- [--only IlsanGS25,IlsanCU] [--out Blender]

Blender/<이름>.blend 하나에 에셋 하나:
  - 오브젝트 `<이름>`, `<이름>_LOD1`, `<이름>_LOD2` (Z 위, 원점 = 부지 중심 지면, 정면 = -Y)
    → cs2_asset_tools 애드온의 검사 · FBX 내보내기가 그대로 찾는다 (LOD 는 CS2_LODs 컬렉션)
  - 재질 하나: 구운 텍스처 5장 (BaseColor · Normal · MaskMap · Emissive, ControlMask 는 이미지만)을
    ../CS2Assets/<이름>/ 에서 상대 경로로 읽는다 (파일에 넣지 않으므로 Blender 와 CS2Assets 폴더를 같이 둔다)
  - 애드온 설정: 에셋 이름 = <이름>, 프로젝트 루트 = //../CS2Assets/
  - 오브젝트 사용자 속성: 부지 셀 · 종류 · 높이 · 삼각형 수 (<이름>.json)
"""

import argparse
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

import bake  # noqa: E402
import cs2_asset_tools  # noqa: E402

TEXTURES = ("_BaseColor", "_Normal", "_MaskMap", "_ControlMask", "_Emissive")


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--assets", default=os.path.join(HERE, "CS2Assets"))
    p.add_argument("--out", default=os.path.join(HERE, "Blender"))
    p.add_argument("--only")
    return p.parse_args(argv)


def import_mesh(path, name):
    """FBX 하나를 가져와 축 변환을 메시에 구운 오브젝트 (변환 = 단위 행렬)"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    obj = next(o for o in new if o.type == 'MESH')
    for o in new:
        if o is not obj:
            bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    obj.data.transform(obj.matrix_world)
    obj.matrix_world.identity()
    obj.name = obj.data.name = name
    return obj


def make_blend(name, assets, out):
    folder = os.path.join(assets, name)
    with open(os.path.join(folder, name + ".json"), encoding="utf-8") as f:
        info = json.load(f)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cs2_asset_tools.register()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.cs2.asset_name = name
    sc.cs2.export_dir = "//../CS2Assets/"
    sc.cs2.lod_count = 2

    paths = {s: os.path.join(folder, name + s + ".png") for s in TEXTURES}
    mat = bake.baked_material(name, paths)
    ctrl = mat.node_tree.nodes.new("ShaderNodeTexImage")      # ControlMask: 연결하지 않고 함께 둔다
    ctrl.image = bpy.data.images.load(paths["_ControlMask"], check_existing=True)
    ctrl.image.colorspace_settings.name = 'Non-Color'
    ctrl.label = "ControlMask (CS2 색상 변형)"

    lods = bpy.data.collections.new("CS2_LODs")
    sc.collection.children.link(lods)
    for level, suffix in enumerate(("", "_LOD1", "_LOD2")):
        obj = import_mesh(os.path.join(folder, name + suffix + ".fbx"), name + suffix)
        bake.replace_materials(obj, mat)
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        (sc.collection if level == 0 else lods).objects.link(obj)
        if level == 0:
            for k in ("title", "type", "kind", "lot_cells", "lot_m", "footprint_m", "height_m", "lod0_tris",
                      "lod_tris", "texture"):
                if k in info:
                    obj["cs2_" + k] = info[k]
    for m in [m for m in bpy.data.materials if m is not mat]:    # FBX 가 만든 재질 · 이미지는 버린다
        bpy.data.materials.remove(m)
    keep = {n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE'}
    for img in [i for i in bpy.data.images if i not in keep]:
        bpy.data.images.remove(img)
    for img in bpy.data.images:
        img.filepath = bpy.path.relpath(bpy.path.abspath(img.filepath), start=out)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, name + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, relative_remap=False)
    cs2_asset_tools.unregister()
    return path


def main():
    a = args()
    with open(os.path.join(a.assets, "catalog.json"), encoding="utf-8") as f:
        names = [x["name"] for x in json.load(f)]
    if a.only:
        names = [n for n in names if n in a.only.split(",")]
    for n in names:
        p = make_blend(n, os.path.abspath(a.assets), os.path.abspath(a.out))
        print("blend:", p, f"{os.path.getsize(p) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
