"""Run in the Unreal Editor, NOT in Blender.
Enable Python Editor Script Plugin and Editor Scripting Utilities.
Tools > Execute Python Script > this file. See README_KO.md.
Uses the explicit legacy FBX factory; engine integration is not runtime-tested here.
"""
from __future__ import annotations
import unreal
from pathlib import Path
from collections import defaultdict
import json
import sys
import hashlib

# ---------------- User settings ----------------
# Empty uses this package's cozy_config.json -> output_directory -> unreal_export.
EXPORT_DIRECTORY_OVERRIDE = r""
CONTENT_ROOT = '/Game/CozyLakeForest300m'
PLACEMENT_MODE = 'HISM'              # 'HISM' or 'ACTORS' (shared StaticMeshes)
UPDATE_EXISTING_MESHES = False        # set True after editing a source mesh
REPLACE_PREVIOUS_GENERATED_ACTORS = True
ONLY_CELL_IDS = []                  # [] = all; e.g. ['C02_02','C03_02']
ENABLE_DETAIL_CULLING = False       # opt-in hard distance culling, no fade shader
DETAIL_CULL_METRES = {'GroundCover':90,'Flowers':120,'Understory':140,'ShorePlants':140} 
# No level autosave. Collision/LOD/Nanite/animated water are intentionally left to you.
# ------------------------------------------------


def set_optional(obj,name,value):
    try:obj.set_editor_property(name,value)
    except Exception as e:unreal.log_warning(f'[Cozy] Optional property {name}: {e}')


def import_mesh(file,dest,name,force=False):
    if not file.is_file():raise RuntimeError('FBX file is missing: '+str(file))
    existing=unreal.EditorAssetLibrary.load_asset(dest+'/'+name)
    if existing and not isinstance(existing,unreal.StaticMesh):raise RuntimeError('Asset name collision with a non-StaticMesh: '+dest+'/'+name)
    if existing and not (UPDATE_EXISTING_MESHES or force):return existing
    opts=unreal.FbxImportUI()
    opts.set_editor_property('import_mesh',True)
    opts.set_editor_property('import_as_skeletal',False)
    opts.set_editor_property('import_materials',False)
    opts.set_editor_property('import_textures',False)
    opts.set_editor_property('import_animations',False)
    opts.set_editor_property('automated_import_should_detect_type',False)
    opts.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
    data=opts.get_editor_property('static_mesh_import_data')
    for key,value in {
        'combine_meshes':False,'auto_generate_collision':False,
        'convert_scene':True,'convert_scene_unit':True,'force_front_x_axis':False,
        'transform_vertex_to_absolute':True,'bake_pivot_in_vertex':False,
        'generate_lightmap_u_vs':False,'import_uniform_scale':1.,
        'vertex_color_import_option':unreal.VertexColorImportOption.REPLACE,
        'normal_import_method':unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
        'remove_degenerates':True
    }.items():data.set_editor_property(key,value)
    set_optional(data,'build_nanite',False)
    task=unreal.AssetImportTask()
    for key,value in {'filename':str(file),'destination_path':dest,'destination_name':name,
                       'automated':True,'replace_existing':bool(existing),
                       'replace_existing_settings':True,'save':True,'options':opts,
                       'factory':unreal.FbxFactory()}.items():task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths=task.get_editor_property('imported_object_paths')
    meshes=[unreal.EditorAssetLibrary.load_asset(p) for p in paths]
    meshes=[m for m in meshes if isinstance(m,unreal.StaticMesh)]
    if len(meshes)!=1:raise RuntimeError(f'{name}: expected one imported StaticMesh; got {paths}. Verify the legacy FBX factory is enabled in this UE version.')
    return meshes[0]


def get_material(kind):
    names={'opaque':'M_CF_VertexColor','foliage':'M_CF_VertexColor_TwoSided','water':'M_CF_StylizedWater'}
    name=names[kind];path=CONTENT_ROOT+'/Materials'
    existing=unreal.EditorAssetLibrary.load_asset(path+'/'+name)
    if existing:
        if not isinstance(existing,unreal.MaterialInterface):raise RuntimeError('Material name collision: '+path+'/'+name)
        return existing
    mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,path,unreal.Material,unreal.MaterialFactoryNew())
    if mat is None:raise RuntimeError('Material creation failed: '+name)
    mat.set_editor_property('two_sided',kind in ('foliage','water'))
    set_optional(mat,'used_with_instanced_static_meshes',True)
    lib=unreal.MaterialEditingLibrary
    color=lib.create_material_expression(mat,unreal.MaterialExpressionVertexColor,-420,0)
    lib.connect_material_property(color,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(mat,unreal.MaterialExpressionConstant,-420,180)
    rough.set_editor_property('r',.23 if kind=='water' else .89)
    lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    spec=lib.create_material_expression(mat,unreal.MaterialExpressionConstant,-420,280)
    spec.set_editor_property('r',.32 if kind=='water' else .24)
    lib.connect_material_property(spec,'',unreal.MaterialProperty.MP_SPECULAR)
    lib.recompile_material(mat);unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def as_transform(record,basis,convert):
    d=convert(record['matrix_blender_row_major'],basis)
    t=unreal.Transform()
    # The constructor accepts Rotator on some UE versions; set Quat properties explicitly.
    t.set_editor_property('translation',unreal.Vector(*d['translation']))
    t.set_editor_property('rotation',unreal.Quat(*d['rotation_xyzw']))
    t.set_editor_property('scale3d',unreal.Vector(*d['scale']))
    return t


def object_from_handle(handle):
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    data=lib.get_data(handle)
    getter=getattr(lib,'get_associated_object',None) or lib.get_object
    return getter(data)


def add_hism_component(actor):
    subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles=subsystem.k2_gather_subobject_data_for_instance(actor)
    root=actor.get_component_by_class(unreal.StaticMeshComponent)
    parent=next((h for h in handles if object_from_handle(h)==root),handles[0])
    params=unreal.AddNewSubobjectParams()
    params.set_editor_property('parent_handle',parent)
    params.set_editor_property('new_class',unreal.HierarchicalInstancedStaticMeshComponent)
    # No blueprint_context: create a persistent INSTANCE component in the current level.
    handle,reason=subsystem.add_new_subobject(params)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    if not lib.is_handle_valid(handle):raise RuntimeError('HISM creation failed: '+str(reason))
    component=object_from_handle(handle)
    if not isinstance(component,unreal.HierarchicalInstancedStaticMeshComponent):
        raise RuntimeError('Subobject API did not return a HISM component. Set PLACEMENT_MODE="ACTORS" for the compatibility path.')
    return component


def main():
    if PLACEMENT_MODE not in ('HISM','ACTORS'):raise ValueError('PLACEMENT_MODE must be HISM or ACTORS.')
    if not CONTENT_ROOT.startswith('/Game/'):raise ValueError('CONTENT_ROOT must be a dedicated /Game/... content folder.')
    package=Path(__file__).resolve().parent
    if str(package) not in sys.path:sys.path.insert(0,str(package))
    from cozy_transforms import basis_from_probe_centers,convert_transform,mv
    from cozy_manifest import group_instances
    if EXPORT_DIRECTORY_OVERRIDE:root=Path(EXPORT_DIRECTORY_OVERRIDE).expanduser()
    else:
        cfg=json.loads((package/'cozy_config.json').read_text(encoding='utf-8'))
        root=Path(cfg.get('output_directory','./output')).expanduser()
        if not root.is_absolute():root=package/root
        root=root/'unreal_export'
    manifest_file=root/'scene_instances.json'
    if not manifest_file.is_file():raise RuntimeError('Run 02_export_unreal.py in Blender first. Missing: '+str(manifest_file))
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
    if manifest.get('format')!='cozy-lake-instances' or manifest.get('schema_version')!=2:raise RuntimeError('Unsupported manifest format.')
    records={a['asset_id']:a for a in manifest['assets']}
    if len(records)!=len(manifest['assets']):raise RuntimeError('Duplicate asset IDs in manifest.')
    cell_records={c['cell_id']:c for c in manifest['cells']}
    requested=set(ONLY_CELL_IDS)
    if requested-set(cell_records): raise ValueError('Unknown requested cell IDs: '+str(requested-set(cell_records)))
    selected=[row for row in manifest['instances'] if not requested or row['cell_id'] in requested]
    for record in selected:
        if record['asset_id'] not in records:raise RuntimeError('Unknown instance asset '+record['asset_id'])
        if record['cell_id'] not in cell_records:raise RuntimeError('Unknown cell '+record['cell_id'])
    groups=group_instances(selected)
    used={row['asset_id'] for row in selected}
    records={key:value for key,value in records.items() if key in used}
    # Do not start a partial import when files are missing or traverse outside the package.
    for item in manifest['assets']+manifest['calibration']:
        file=(root/item['file']).resolve()
        if not file.is_relative_to(root.resolve()) or not file.is_file():raise RuntimeError('Invalid/missing FBX path: '+str(file))
    tools=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    tag='CozyLakeForest300m_'+hashlib.sha1(CONTENT_ROOT.encode()).hexdigest()[:12]
    previous=[]
    for actor in tools.get_all_level_actors():
        tags={str(t) for t in actor.tags}
        if tag in tags and (not requested or any('CFCell_'+key in tags for key in requested)):
            previous.append(actor)
    if previous and not REPLACE_PREVIOUS_GENERATED_ACTORS:
        raise RuntimeError('A generated forest already exists. Use a different CONTENT_ROOT or enable replacement.')
    centers=[]
    for axis in 'XYZ':
        item=next(p for p in manifest['calibration'] if p['axis']==axis)
        probe=import_mesh(root/item['file'],CONTENT_ROOT+'/Calibration','CF_Calibration_'+axis,force=True)
        origin=probe.get_bounds().origin
        centers.append([origin.x,origin.y,origin.z])
    basis=basis_from_probe_centers(centers)
    unreal.log('[Cozy] Measured Blender metres -> UE centimetres basis: '+str(basis))
    # Convert every transform before mutating the level.
    transforms={k:[as_transform(r,basis,convert_transform) for r in rows] for k,rows in groups.items()}
    materials={kind:get_material(kind) for kind in ('opaque','foliage','water')}
    meshes={}
    # Preflight every existing source hash before importing any of the scene assets.
    for key,item in records.items():
        old_mesh=unreal.EditorAssetLibrary.load_asset(CONTENT_ROOT+'/Meshes/'+key)
        if old_mesh and not UPDATE_EXISTING_MESHES:
            stored=unreal.EditorAssetLibrary.get_metadata_tag(old_mesh,'CF_SourceHash')
            if stored!=item['source_hash']:
                raise RuntimeError(f'{key}: the FBX/source hash changed (or this is an untagged existing asset). Set UPDATE_EXISTING_MESHES=True to reimport, or use a new CONTENT_ROOT.')
    for key,item in records.items():
        mesh=import_mesh(root/item['file'],CONTENT_ROOT+'/Meshes',key)
        unreal.EditorAssetLibrary.set_metadata_tag(mesh,'CF_SourceHash',item['source_hash'])
        mat=materials[item['material']]
        slots=mesh.get_editor_property('static_materials')
        if not slots:raise RuntimeError('Imported mesh has no material slot: '+key)
        for index in range(len(slots)):mesh.set_material(index,mat)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        meshes[key]=mesh
    created=[];created_cells=[];hism_counts={}
    try:
        with unreal.ScopedEditorTransaction('Import Cozy Lake Forest'):
            for group,rows in groups.items():
                cell,key=group
                mesh=meshes[key];item=records[key];trs=transforms[group]
                origin=mv(basis,cell_records[cell]['origin_blender_m'])
                folder='CozyLakeForest300m/'+cell+'/'+item['category']
                if PLACEMENT_MODE=='HISM' and len(rows)>1:
                    holder=tools.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*origin),unreal.Rotator(0,0,0))
                    if not holder:raise RuntimeError('Could not spawn a HISM holder.')
                    created.append(holder);created_cells.append(cell)
                    holder.set_actor_label('CF_HISM_'+cell+'_'+key)
                    holder.set_folder_path(folder)
                    blank=holder.get_component_by_class(unreal.StaticMeshComponent)
                    blank.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                    component=add_hism_component(holder)
                    component.modify()
                    component.set_mobility(unreal.ComponentMobility.STATIC)
                    if not component.set_static_mesh(mesh):raise RuntimeError('HISM mesh assignment failed: '+key)
                    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                    set_optional(component,'can_ever_affect_navigation',False)
                    # World-space input, cell-centred actor: instances stay spatially local.
                    component.add_instances(trs,False,True,False)
                    if ENABLE_DETAIL_CULLING and item['category'] in DETAIL_CULL_METRES:
                        end=int(DETAIL_CULL_METRES[item['category']]*100)
                        component.set_cull_distances(0,end)
                    count=component.get_instance_count()
                    if count!=len(rows):raise RuntimeError(f'{key}: HISM count {count} != {len(rows)}')
                    hism_counts[cell+'/'+key]=count
                    holder.modify()
                else:
                    for row,tr in zip(rows,trs):
                        actor=tools.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,0),unreal.Rotator(0,0,0))
                        if not actor:raise RuntimeError('Could not spawn StaticMeshActor.')
                        created.append(actor);created_cells.append(cell)
                        component=actor.get_component_by_class(unreal.StaticMeshComponent)
                        component.set_mobility(unreal.ComponentMobility.MOVABLE)
                        component.set_static_mesh(mesh)
                        actor.set_actor_transform(tr,False,True)
                        component.set_mobility(unreal.ComponentMobility.STATIC)
                        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                        actor.set_actor_label(row['name']);actor.set_folder_path(folder)
            # Tag only after all creation succeeds; older actors survive any creation error.
            for actor,cell in zip(created,created_cells):actor.set_editor_property('tags',[unreal.Name(tag),unreal.Name('CFCell_'+cell)])
            for actor in previous:
                if not tools.destroy_actor(actor):raise RuntimeError('Could not replace an older generated actor; inspect the level for duplicates.')
    except Exception:
        for actor in created:
            try:tools.destroy_actor(actor)
            except Exception:pass
        raise
    report={'basis_metres_to_centimetres':basis,'probe_centers_cm':centers,
            'placement_mode':PLACEMENT_MODE,'unique_mesh_assets':len(meshes),
            'placed_instances':len(selected),'cells_imported':sorted({r['cell_id'] for r in selected}),'level_actors_created':len(created),
            'hism_instance_counts':hism_counts}
    (root/'unreal_import_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('[Cozy] Import complete: '+json.dumps(report))
    unreal.log('[Cozy] Save the level manually. Existing non-Cozy actors were preserved. Add your own lighting, collision and gameplay water. Cell folders are not automatic World Partition streaming.')


if __name__=='__main__':main()
