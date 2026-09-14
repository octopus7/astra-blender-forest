"""Blender: export only the rebuilt bridge, not the river, lights or display props.
Run 01 first. This exports current Blender edits, unlike the standalone generator.
"""
from pathlib import Path
import bpy

def main():
    scene=bpy.context.scene
    root=scene.get('package_root')
    if not root:raise RuntimeError('먼저 01_build_blender_scene_v2.py를 실행하고 CF_BrokenBridge_v2 씬을 선택하세요.')
    objects=[o for o in scene.objects if o.type=='MESH' and o.get('cb_bridge_asset') and o.name.startswith('SM_BrokenBridge')]
    # Ignore linked demonstration copies unless the user deliberately selects them.
    original=[o for o in objects if any(c.name.startswith('01_BRIDGE_') for c in o.users_collection)]
    if original:objects=original
    if not objects:raise RuntimeError('내보낼 다리 메시가 없습니다.')
    previous_selected=list(bpy.context.selected_objects);previous_active=bpy.context.view_layer.objects.active
    try:
        for o in bpy.context.selected_objects:o.select_set(False)
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        path=Path(root)/'models/SM_BrokenBridge_v2_blender_export.glb'
        options=dict(filepath=str(path),export_format='GLB',use_selection=True,export_texcoords=True,export_normals=True,export_tangents=True,export_materials='EXPORT',export_yup=True,export_animations=False,export_cameras=False,export_lights=False,export_apply=False)
        supported=bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
        bpy.ops.export_scene.gltf(**{k:v for k,v in options.items() if k in supported})
        print('다리 GLB 저장:',path)
        print('강물 노드, 조명, 강바닥은 제외했습니다. Blender 씬은 Save As로 .blend에 보관하세요.')
    finally:
        for o in bpy.context.selected_objects:o.select_set(False)
        for o in previous_selected:
            if o.name in scene.objects:o.select_set(True)
        if previous_active and previous_active.name in scene.objects:bpy.context.view_layer.objects.active=previous_active
if __name__=='__main__':main()
