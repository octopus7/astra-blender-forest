"""Run in Blender AFTER 01_build_scene.py, with CF_CozyLake_300m as the active scene.
One FBX per unique mesh; placement-only JSON; unchanged FBX files are reused.
"""
from __future__ import annotations
import bpy
from pathlib import Path
from array import array
import hashlib
import json
import re
import sys
from datetime import datetime,timezone
from collections import defaultdict

# ---------------- User settings ----------------
EXPORT_DIRECTORY_OVERRIDE = r""  # empty -> output/unreal_export in this package
TRANSFORMS_ONLY = False           # True: refuse any geometry export/change
SKIP_UNCHANGED_MESHES = True
# ------------------------------------------------
OWNER='CozyLakeForest300_v2'
FBX_SETTINGS=dict(use_selection=True,object_types={'MESH'},global_scale=1.,
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    use_mesh_modifiers=False,mesh_smooth_type='FACE',use_triangles=True,
    use_custom_props=False,add_leaf_bones=False,bake_anim=False,
    axis_forward='-Y',axis_up='Z',use_space_transform=True,
    bake_space_transform=False,path_mode='AUTO',colors_type='LINEAR')


def atomic_json(path,data):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    temp.replace(path)


def signature(mesh):
    h=hashlib.sha256()
    for seq,prop,width,typecode in [(mesh.vertices,'co',3,'f'),(mesh.loops,'vertex_index',1,'i'),
                                   (mesh.polygons,'loop_total',1,'i'),(mesh.polygons,'use_smooth',1,'b')]:
        a=array(typecode,[0])*(len(seq)*width); seq.foreach_get(prop,a);h.update(a.tobytes())
    attr=mesh.color_attributes.get('Color')
    if not attr: raise RuntimeError(f'{mesh.name}: missing Color attribute.')
    a=array('f',[0])*(len(attr.data)*4);attr.data.foreach_get('color',a);h.update(a.tobytes())
    for uv in mesh.uv_layers:
        a=array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',a);h.update(a.tobytes())
    h.update(str(mesh.get('cf_material_kind','opaque')).encode())
    h.update(str(bpy.app.version).encode())
    h.update(json.dumps(FBX_SETTINGS,sort_keys=True,default=lambda value:sorted(value)).encode())
    return h.hexdigest()


def calibration_mesh(axis):
    index='XYZ'.index(axis)
    vs=[]
    for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:
        v=[x*.05,y*.05,z*.05];v[index]+=1.;vs.append(v)
    mesh=bpy.data.meshes.new('CF_Calibration_'+axis)
    mesh.from_pydata(vs,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    mesh.update();return mesh


def main():
    scene=bpy.context.scene
    if scene.get('cf_owner')!=OWNER:
        raise RuntimeError('Select scene CF_CozyLake_300m before running this exporter.')
    if abs(scene.unit_settings.scale_length-1.)>1e-6:
        raise RuntimeError('The generated scene must remain at Unit Scale = 1.0 (metres).')
    package=Path(scene['cf_package_dir'])
    if str(package) not in sys.path:sys.path.insert(0,str(package))
    from cozy_transforms import convert_transform,IDENTITY3
    from cozy_manifest import cell_id_for_position,make_cell_records
    cfg=json.loads(scene['cf_config_json'])
    export_root=Path(EXPORT_DIRECTORY_OVERRIDE).expanduser() if EXPORT_DIRECTORY_OVERRIDE else Path(scene['cf_output_dir'])/'unreal_export'
    mesh_dir=export_root/'meshes';cal_dir=export_root/'calibration'
    export_root.mkdir(parents=True,exist_ok=True);mesh_dir.mkdir(exist_ok=True);cal_dir.mkdir(exist_ok=True)
    bpy.context.view_layer.update()
    objects=[o for o in scene.objects if o.type=='MESH' and o.get('cf_owner')==OWNER and o.get('cf_role')=='instance']
    if not objects:raise RuntimeError('No generated instances found.')
    assets={};instances=[]
    for obj in sorted(objects,key=lambda x:x.name):
        if any(m.show_viewport or m.show_render for m in obj.modifiers):
            raise RuntimeError(f'{obj.name}: modifiers must be baked into its shared source mesh first.')
        if obj.data.shape_keys:raise RuntimeError(f'{obj.name}: shape keys are not supported in this static-mesh exporter.')
        if any(slot.link=='OBJECT' for slot in obj.material_slots):
            raise RuntimeError(f'{obj.name}: object material overrides would break transform-only instancing. Use shared mesh materials.')
        key=str(obj.data.get('cf_asset_id',''))
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',key):raise RuntimeError(f'{obj.name}: invalid/missing mesh cf_asset_id.')
        if key in assets and assets[key].as_pointer()!=obj.data.as_pointer():
            raise RuntimeError(f'Two separate mesh datablocks share asset_id {key}. Use Alt+D, or give the new mesh a new cf_asset_id.')
        assets[key]=obj.data
        matrix=[float(obj.matrix_world[i][j]) for i in range(4) for j in range(4)]
        convert_transform(matrix,IDENTITY3)  # rejects shear, negative scale and NaN
        cell=cell_id_for_position(matrix[3],matrix[7],cfg['map_size_m'],cfg['terrain_tiles_per_axis'])
        instances.append({'name':obj.name,'asset_id':key,'matrix_blender_row_major':matrix,
                          'cell_id':cell,'zone':str(obj.get('cf_zone','forest'))})
    cache_path=export_root/'geometry_cache.json'
    old=json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    old_hashes=old.get('source_hashes',{})
    hashes={key:signature(mesh) for key,mesh in assets.items()}
    changed=[key for key in assets if old_hashes.get(key)!=hashes[key] or not (mesh_dir/(key+'.fbx')).is_file()]
    calibration=[{'axis':a,'file':f'calibration/CF_Calibration_{a}.fbx','source_center_m':[1. if j=='XYZ'.index(a) else 0. for j in range(3)]} for a in 'XYZ']
    if TRANSFORMS_ONLY:
        if changed:raise RuntimeError('TRANSFORMS_ONLY: new/changed mesh data needs a geometry export: '+', '.join(changed))
        if any(not (export_root/p['file']).is_file() for p in calibration):raise RuntimeError('Calibration FBX files are missing. Run a full export first.')
    written=[];temp_scene=None;before=bpy.context.window.scene if bpy.context.window else scene
    try:
        if not TRANSFORMS_ONLY:
            try:bpy.ops.export_scene.fbx.get_rna_type()
            except Exception:
                try:bpy.ops.preferences.addon_enable(module='io_scene_fbx')
                except Exception as exc:raise RuntimeError('Blender FBX exporter is unavailable. Enable/install the built-in FBX import/export module.') from exc
            temp_scene=bpy.data.scenes.new('CF_TEMP_EXPORT')
            temp_scene.unit_settings.system='METRIC';temp_scene.unit_settings.scale_length=1.
            if bpy.context.window:bpy.context.window.scene=temp_scene
            supported=bpy.ops.export_scene.fbx.get_rna_type().properties.keys()
            options={k:v for k,v in FBX_SETTINGS.items() if k in supported}
            if 'colors_type' not in supported:raise RuntimeError('This FBX exporter cannot specify linear vertex colors. Use Blender 4.2 or newer.')
            def export_one(mesh,key,path):
                proxy=bpy.data.objects.new(key,mesh);temp_scene.collection.objects.link(proxy)
                layer=temp_scene.view_layers[0];layer.update()
                proxy.select_set(True,view_layer=layer);layer.objects.active=proxy
                tmp=path.with_name(path.stem+'.part.fbx')
                try:
                    with bpy.context.temp_override(scene=temp_scene,view_layer=layer):
                        result=bpy.ops.export_scene.fbx(filepath=str(tmp),check_existing=False,**options)
                    if 'FINISHED' not in result or not tmp.exists():raise RuntimeError('FBX export failed: '+key)
                    tmp.replace(path)
                finally:
                    bpy.data.objects.remove(proxy,do_unlink=True)
            for key in sorted(assets):
                if SKIP_UNCHANGED_MESHES and key not in changed:continue
                print('[Cozy export]',key)
                export_one(assets[key],key,mesh_dir/(key+'.fbx'));written.append(key)
            for item in calibration:
                mesh=calibration_mesh(item['axis'])
                try:export_one(mesh,'CF_Calibration_'+item['axis'],export_root/item['file'])
                finally:bpy.data.meshes.remove(mesh)
    finally:
        if bpy.context.window:bpy.context.window.scene=before
        if temp_scene:bpy.data.scenes.remove(temp_scene)
    records=[]
    for key,mesh in sorted(assets.items()):
        mesh.calc_loop_triangles()
        records.append({'asset_id':key,'file':f'meshes/{key}.fbx','source_hash':hashes[key],
                        'category':mesh.get('cf_category','Props'),'material':mesh.get('cf_material_kind','opaque'),
                        'collision_hint':mesh.get('cf_collision','none'),'triangles':len(mesh.loop_triangles)})
    cells=make_cell_records(instances,cfg['map_size_m'],cfg['terrain_tiles_per_axis'])
    manifest={'format':'cozy-lake-instances','schema_version':2,'generated_at_utc':datetime.now(timezone.utc).isoformat(),
              'blender_version':bpy.app.version_string,'source_units':'metres','target_units':'centimetres',
              'transform_layout':'row-major 4x4, column-vector convention, translation at indices 3/7/11',
              'coordinate_conversion':'Calibrate B from the three imported probe bounding-box centers; M_UE = B M_Blender inverse(B).',
              'vertex_colors':'Color attribute; linear RGB in FBX; use UE VertexColor -> BaseColor',
              'map_size_m':cfg['map_size_m'],'cell_size_m':cfg['map_size_m']/cfg['terrain_tiles_per_axis'],
              'cells':cells,'landmarks':json.loads(scene.get('cf_pois_json','[]')),
              'assets':records,'instances':instances,'calibration':calibration,
              'stats':{'unique_assets':len(records),'placed_instances':len(instances),'geometry_files_written_this_run':len(written)}}
    # Geometry is exported globally once. These small files contain only the
    # per-cell placement rows, for selective reloads or a custom streaming tool.
    cell_dir=export_root/'cells';cell_dir.mkdir(exist_ok=True)
    by_cell=defaultdict(list)
    for row in instances:by_cell[row['cell_id']].append(row)
    for cell in cells:
        atomic_json(export_root/cell['file'],{'schema_version':2,'cell':cell,
                    'shared_asset_manifest':'../scene_instances.json','instances':by_cell[cell['cell_id']]})
    atomic_json(export_root/'cell_index.json',{'map_size_m':cfg['map_size_m'],
                'cell_size_m':manifest['cell_size_m'],'cells':cells})
    atomic_json(export_root/'scene_instances.json',manifest)
    atomic_json(cache_path,{'source_hashes':hashes,'blender_version':bpy.app.version_string})
    print(f'\n[Cozy export] {len(records)} unique assets / {len(instances)} transforms / {len(written)} mesh FBX files written.')
    print('Manifest:',export_root/'scene_instances.json')
    print('Cell index:',export_root/'cell_index.json')
    print('Run 03_import_unreal.py in the Unreal Editor. Calibration files are diagnostics, not visible scene props.')


if __name__=='__main__':main()
