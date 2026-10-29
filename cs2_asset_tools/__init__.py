"""Cities: Skylines II 에셋 제작 도우미 (Blender 애드온).

3D 뷰포트 사이드바(N) > CS2 탭에서 사용한다.
"""

bl_info = {
    "name": "CS2 Asset Tools",
    "author": "anchovy8781",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > CS2",
    "description": "Cities: Skylines II 용 메시 정리, LOD 생성, 텍스처 패킹, FBX 내보내기",
    "category": "Import-Export",
}

import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import core


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def asset_dir(props):
    return os.path.join(bpy.path.abspath(props.export_dir), props.asset_name)


def lod_objects(props):
    """씬에서 `<이름>`, `<이름>_LOD1` ... 순서로 존재하는 메시 오브젝트."""
    found = []
    for level in range(0, 10):
        obj = bpy.data.objects.get(core.lod_name(props.asset_name, level))
        if obj is None or obj.type != 'MESH':
            break
        found.append(obj)
    return found


def load_gray(path):
    """이미지를 Non-Color 로 불러와 (H, W) float 배열로 돌려준다."""
    if not path:
        return None
    img = bpy.data.images.load(bpy.path.abspath(path), check_existing=False)
    try:
        img.colorspace_settings.name = 'Non-Color'
        w, h = img.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        return buf.reshape(h, w, 4)[..., 0].copy()
    finally:
        bpy.data.images.remove(img)


def save_png(path, packed):
    """(H, W, C) float 배열을 PNG 로 저장. Blender 픽셀은 아래쪽 행부터지만 읽을 때도 같은 순서라 그대로 쓴다."""
    h, w, c = packed.shape
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :c] = packed
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=(c == 4))
    try:
        img.colorspace_settings.name = 'Non-Color'
        img.pixels.foreach_set(rgba.ravel())
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
    finally:
        bpy.data.images.remove(img)


def first_size(*arrays):
    for a in arrays:
        if a is not None:
            return a.shape[:2]
    return None


# ---------------------------------------------------------------------------
# 속성
# ---------------------------------------------------------------------------

class CS2Props(bpy.types.PropertyGroup):
    asset_name: bpy.props.StringProperty(name="에셋 이름", default="MyBuilding")
    export_dir: bpy.props.StringProperty(name="프로젝트 루트", subtype='DIR_PATH', default="//CS2Assets/")

    lod_count: bpy.props.IntProperty(name="LOD 개수", default=2, min=1, max=5)
    lod_ratio: bpy.props.FloatProperty(name="단계별 비율", default=0.5, min=0.05, max=0.95)

    metallic_path: bpy.props.StringProperty(name="Metallic", subtype='FILE_PATH')
    coat_path: bpy.props.StringProperty(name="Coat", subtype='FILE_PATH')
    gloss_path: bpy.props.StringProperty(name="Gloss/Rough", subtype='FILE_PATH')
    gloss_is_roughness: bpy.props.BoolProperty(
        name="Roughness 맵임 (반전)", default=True,
        description="Substance/Blender 의 Roughness 맵이면 켜기. 1-Roughness 를 Glossiness 로 쓴다")

    mask1_path: bpy.props.StringProperty(name="색상 마스크 1 (R)", subtype='FILE_PATH')
    mask2_path: bpy.props.StringProperty(name="색상 마스크 2 (G)", subtype='FILE_PATH')
    mask3_path: bpy.props.StringProperty(name="색상 마스크 3 (B)", subtype='FILE_PATH')

    bake_space_transform: bpy.props.BoolProperty(
        name="Apply Transform (축 변환 굽기)", default=True,
        description="FBX 에 Z-up -> Y-up 회전을 메시에 직접 굽는다. 게임에서 에셋이 누워 보이면 끄고 비교")

    report: bpy.props.StringProperty(default="")


# ---------------------------------------------------------------------------
# 오퍼레이터
# ---------------------------------------------------------------------------

class CS2_OT_setup_scene(bpy.types.Operator):
    """단위를 미터(1 BU = 1 m)로 맞춘다"""
    bl_idname = "cs2.setup_scene"
    bl_label = "씬 단위 설정 (미터)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        us = context.scene.unit_settings
        us.system = 'METRIC'
        us.scale_length = 1.0
        us.length_unit = 'METERS'
        self.report({'INFO'}, "단위: Metric, 스케일 1.0, 미터")
        return {'FINISHED'}


class CS2_OT_prepare_mesh(bpy.types.Operator):
    """선택한 메시의 변환을 적용하고, 원점을 바닥 중앙으로 옮긴 뒤 월드 원점에 놓고 에셋 이름으로 바꾼다"""
    bl_idname = "cs2.prepare_mesh"
    bl_label = "메인 메시 준비"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        props = context.scene.cs2
        obj = context.active_object
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        if obj.parent is not None:
            mw = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = mw

        me = obj.data
        me.transform(obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)

        coords = [v.co for v in me.vertices]
        if not coords:
            self.report({'ERROR'}, "버텍스가 없습니다")
            return {'CANCELLED'}
        lo = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
        hi = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
        pivot = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
        me.transform(Matrix.Translation(-pivot))
        me.update()

        obj.name = props.asset_name
        me.name = props.asset_name
        size = hi - lo
        self.report({'INFO'}, f"{obj.name}: 크기 {size.x:.2f} x {size.y:.2f} x {size.z:.2f} m")
        return {'FINISHED'}


class CS2_OT_generate_lods(bpy.types.Operator):
    """메인 메시를 복제하고 Decimate 를 적용해 <이름>_LOD1.. 을 만든다 (기존 LOD 는 교체)"""
    bl_idname = "cs2.generate_lods"
    bl_label = "LOD 생성"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.cs2
        base = bpy.data.objects.get(props.asset_name)
        if base is None or base.type != 'MESH':
            self.report({'ERROR'}, f"'{props.asset_name}' 메시가 없습니다. 먼저 '메인 메시 준비'를 실행하세요")
            return {'CANCELLED'}

        coll = bpy.data.collections.get("CS2_LODs")
        if coll is None:
            coll = bpy.data.collections.new("CS2_LODs")
            context.scene.collection.children.link(coll)

        for level in range(1, 10):
            old = bpy.data.objects.get(core.lod_name(props.asset_name, level))
            if old is not None:
                bpy.data.objects.remove(old)

        depsgraph = context.evaluated_depsgraph_get()
        for level, ratio in enumerate(core.lod_ratios(props.lod_count, props.lod_ratio), start=1):
            name = core.lod_name(props.asset_name, level)
            tmp = base.copy()
            tmp.data = base.data.copy()
            context.scene.collection.objects.link(tmp)
            mod = tmp.modifiers.new("CS2_Decimate", 'DECIMATE')
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            depsgraph.update()
            mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(depsgraph))
            old_data = tmp.data
            bpy.data.objects.remove(tmp)
            bpy.data.meshes.remove(old_data)

            mesh.name = name
            lod = bpy.data.objects.new(name, mesh)
            lod.matrix_world = base.matrix_world
            coll.objects.link(lod)

        self.report({'INFO'}, f"LOD {props.lod_count}개 생성 (CS2_LODs 컬렉션)")
        return {'FINISHED'}


class CS2_OT_pack_maskmap(bpy.types.Operator):
    """Metallic / Coat / Glossiness(또는 Roughness) 맵을 <이름>_MaskMap.png 로 패킹한다"""
    bl_idname = "cs2.pack_maskmap"
    bl_label = "MaskMap 패킹"

    def execute(self, context):
        props = context.scene.cs2
        metallic = load_gray(props.metallic_path)
        coat = load_gray(props.coat_path)
        gloss = load_gray(props.gloss_path)
        size = first_size(metallic, coat, gloss)
        if size is None:
            self.report({'ERROR'}, "입력 이미지가 하나도 없습니다")
            return {'CANCELLED'}
        try:
            if props.gloss_is_roughness:
                packed = core.pack_maskmap(size, metallic, coat, roughness=gloss)
            else:
                packed = core.pack_maskmap(size, metallic, coat, glossiness=gloss)
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        out_dir = asset_dir(props)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, core.texture_name(props.asset_name, "_MaskMap"))
        save_png(path, packed)
        self.report({'INFO'}, f"저장: {path}")
        return {'FINISHED'}


class CS2_OT_pack_controlmask(bpy.types.Operator):
    """색상 변형 마스크 3장을 <이름>_ControlMask.png 의 R/G/B 로 패킹한다"""
    bl_idname = "cs2.pack_controlmask"
    bl_label = "ControlMask 패킹"

    def execute(self, context):
        props = context.scene.cs2
        masks = [load_gray(p) for p in (props.mask1_path, props.mask2_path, props.mask3_path)]
        size = first_size(*masks)
        if size is None:
            self.report({'ERROR'}, "입력 마스크가 하나도 없습니다")
            return {'CANCELLED'}
        try:
            packed = core.pack_controlmask(size, *masks)
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        out_dir = asset_dir(props)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, core.texture_name(props.asset_name, "_ControlMask"))
        save_png(path, packed)
        overlap = core.controlmask_overlap(packed)
        level = 'WARNING' if overlap > 0 else 'INFO'
        self.report({level}, f"저장: {path} (채널 겹침 {overlap:.1%})")
        return {'FINISHED'}


class CS2_OT_validate(bpy.types.Operator):
    """메시와 텍스처가 CS2 임포터 규칙에 맞는지 검사한다"""
    bl_idname = "cs2.validate"
    bl_label = "검사"

    def execute(self, context):
        props = context.scene.cs2
        lines = []
        objs = lod_objects(props)
        if not objs:
            lines.append(f"✗ '{props.asset_name}' 메시가 없습니다")

        prev_tris = None
        for obj in objs:
            me = obj.data
            tris = sum(len(p.vertices) - 2 for p in me.polygons)
            ngons = sum(1 for p in me.polygons if len(p.vertices) > 4)
            lines.append(f"• {obj.name}: 삼각형 {tris:,}, 머티리얼 {len(me.materials)}")
            if any(abs(s - 1.0) > 1e-4 for s in obj.scale) or any(abs(r) > 1e-4 for r in obj.rotation_euler):
                lines.append(f"  ✗ 회전/스케일이 적용되지 않았습니다 (Ctrl+A)")
            if not me.uv_layers:
                lines.append(f"  ✗ UV 맵이 없습니다")
            if ngons:
                lines.append(f"  ! N-gon {ngons}개 (삼각화 권장)")
            if me.vertices:
                min_z = min(v.co.z for v in me.vertices)
                if abs(min_z) > 0.01:
                    lines.append(f"  ! 바닥(min Z={min_z:.3f})이 원점 높이가 아닙니다")
            if prev_tris is not None and tris >= prev_tris:
                lines.append(f"  ✗ 이전 LOD 보다 삼각형이 적지 않습니다")
            prev_tris = tris

        out_dir = asset_dir(props)
        sizes = {}
        if os.path.isdir(out_dir):
            for fn in sorted(os.listdir(out_dir)):
                if not fn.lower().endswith(".png"):
                    continue
                stem = fn[:-4]
                if not any(stem == props.asset_name + s for s in core.TEXTURE_SUFFIXES):
                    lines.append(f"! {fn}: 이름이 <에셋이름><접미사>.png 규칙과 다릅니다")
                try:
                    w, h, bits = core.png_size(os.path.join(out_dir, fn))
                except ValueError as e:
                    lines.append(f"✗ {e}")
                    continue
                if bits != 8:
                    lines.append(f"✗ {fn}: 채널당 {bits}비트 (8비트만 가능)")
                sizes[fn] = (w, h)
            lines += ["✗ " + w for w in core.check_textures(sizes)]
            if not any(fn.endswith("_BaseColor.png") for fn in sizes):
                lines.append("! _BaseColor 텍스처가 없습니다")
        else:
            lines.append(f"! 출력 폴더 없음: {out_dir}")

        errors = sum(1 for l in lines if "✗" in l)
        lines.append(f"결과: 오류 {errors}개")
        props.report = "\n".join(lines)
        self.report({'WARNING'} if errors else {'INFO'}, f"검사 완료: 오류 {errors}개")
        return {'FINISHED'}


class CS2_OT_export(bpy.types.Operator):
    """메인 메시와 LOD 를 각각 <프로젝트 루트>/<이름>/<이름>[_LODn].fbx 로 내보낸다"""
    bl_idname = "cs2.export"
    bl_label = "FBX 내보내기"

    def execute(self, context):
        props = context.scene.cs2
        objs = lod_objects(props)
        if not objs:
            self.report({'ERROR'}, f"'{props.asset_name}' 메시가 없습니다")
            return {'CANCELLED'}
        out_dir = asset_dir(props)
        os.makedirs(out_dir, exist_ok=True)

        view_layer = context.view_layer
        prev_active = view_layer.objects.active
        prev_selected = list(context.selected_objects)
        try:
            for obj in objs:
                for o in context.selected_objects:
                    o.select_set(False)
                obj.select_set(True)
                view_layer.objects.active = obj
                bpy.ops.export_scene.fbx(
                    filepath=os.path.join(out_dir, obj.name + ".fbx"),
                    use_selection=True,
                    object_types={'MESH'},
                    apply_unit_scale=True,
                    apply_scale_options='FBX_SCALE_ALL',
                    axis_forward='-Z',
                    axis_up='Y',
                    bake_space_transform=props.bake_space_transform,
                    use_mesh_modifiers=True,
                    mesh_smooth_type='FACE',
                    use_tspace=True,
                    add_leaf_bones=False,
                    bake_anim=False,
                    path_mode='AUTO',
                    embed_textures=False,
                )
        finally:
            for o in context.selected_objects:
                o.select_set(False)
            for o in prev_selected:
                o.select_set(True)
            view_layer.objects.active = prev_active

        self.report({'INFO'}, f"FBX {len(objs)}개 내보냄: {out_dir}")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class CS2_PT_panel(bpy.types.Panel):
    bl_label = "Cities: Skylines II"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CS2"

    def draw(self, context):
        props = context.scene.cs2
        layout = self.layout

        box = layout.box()
        box.label(text="1. 기본", icon='SETTINGS')
        box.prop(props, "asset_name")
        box.prop(props, "export_dir")
        box.operator("cs2.setup_scene", icon='DRIVER_DISTANCE')
        box.operator("cs2.prepare_mesh", icon='PIVOT_BOUNDBOX')

        box = layout.box()
        box.label(text="2. LOD", icon='MOD_DECIM')
        row = box.row()
        row.prop(props, "lod_count")
        row.prop(props, "lod_ratio")
        box.operator("cs2.generate_lods")

        box = layout.box()
        box.label(text="3. 텍스처 패킹", icon='TEXTURE')
        box.prop(props, "metallic_path")
        box.prop(props, "coat_path")
        box.prop(props, "gloss_path")
        box.prop(props, "gloss_is_roughness")
        box.operator("cs2.pack_maskmap")
        box.separator()
        box.prop(props, "mask1_path")
        box.prop(props, "mask2_path")
        box.prop(props, "mask3_path")
        box.operator("cs2.pack_controlmask")

        box = layout.box()
        box.label(text="4. 검사 / 내보내기", icon='EXPORT')
        box.prop(props, "bake_space_transform")
        row = box.row()
        row.operator("cs2.validate", icon='CHECKMARK')
        row.operator("cs2.export", icon='EXPORT')
        if props.report:
            col = box.column(align=True)
            for line in props.report.splitlines():
                col.label(text=line)


classes = (
    CS2Props,
    CS2_OT_setup_scene,
    CS2_OT_prepare_mesh,
    CS2_OT_generate_lods,
    CS2_OT_pack_maskmap,
    CS2_OT_pack_controlmask,
    CS2_OT_validate,
    CS2_OT_export,
    CS2_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cs2 = bpy.props.PointerProperty(type=CS2Props)


def unregister():
    del bpy.types.Scene.cs2
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
