"""Open this file in Blender's Text Editor, then Run Script (Alt+P).

Builds a NEW generated scene, without deleting objects from your working scene.
Run from the extracted ZIP directory, not from inside the ZIP.
Target API: Blender 4.2+. Runtime integration has not been tested here; see TEST_REPORT.md.
"""
from __future__ import annotations
import bpy
from mathutils import Vector
from pathlib import Path
from array import array
import sys
import json
import time
import traceback

SCENE_NAME = "CF_CozyLake_300m"
OWNER = "CozyLakeForest300_v2"


def package_directory():
    candidates=[]
    if globals().get('__file__'): candidates.append(Path(__file__).expanduser().resolve().parent)
    space=getattr(bpy.context,'space_data',None)
    text=getattr(space,'text',None)
    if text and text.filepath: candidates.append(Path(bpy.path.abspath(text.filepath)).resolve().parent)
    for p in candidates:
        if (p/'cozy_forest_core.py').is_file(): return p
    raise RuntimeError('Extract the complete ZIP, then Text Editor > Open > 01_build_scene.py. Do not paste only this file into an unnamed Text block.')


def linear(v):
    return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4


def material(kind):
    name={'opaque':'CF_M_VertexColor','foliage':'CF_M_VertexColor_TwoSided','water':'CF_M_StylizedWater'}[kind]
    mat=bpy.data.materials.get(name)
    if mat and mat.get('cf_owner')!=OWNER:
        mat=None  # Never change somebody else's material with a matching name.
    if mat is None:
        mat=bpy.data.materials.new(name); mat['cf_owner']=OWNER
        mat.use_nodes=True; nodes=mat.node_tree.nodes; nodes.clear()
        out=nodes.new('ShaderNodeOutputMaterial'); out.location=(360,40)
        bs=nodes.new('ShaderNodeBsdfPrincipled'); bs.location=(20,40)
        color=nodes.new('ShaderNodeVertexColor'); color.layer_name='Color'; color.location=(-240,120)
        mat.node_tree.links.new(color.outputs['Color'],bs.inputs['Base Color'])
        mat.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
        bs.inputs['Roughness'].default_value=.23 if kind=='water' else .89
        bs.inputs['Metallic'].default_value=0
        if 'Specular IOR Level' in bs.inputs: bs.inputs['Specular IOR Level'].default_value=.32 if kind=='water' else .24
        mat.diffuse_color=(.25,.58,.60,1) if kind=='water' else (.52,.66,.25,1)
        mat.use_backface_culling=False if kind in ('foliage','water') else True
        mat['cf_material_kind']=kind
    return mat


def create_mesh(recipe,mat):
    # NumPy is bundled with supported Blender releases. Bulk attribute writes avoid
    # millions of slow Python-to-RNA property lookups on a 300 m terrain.
    import numpy as np
    mesh=bpy.data.meshes.new(recipe.name+'_Mesh')
    mesh['cf_owner']=OWNER; mesh['cf_asset_id']=recipe.name
    mesh['cf_category']=recipe.category; mesh['cf_material_kind']=recipe.material
    mesh['cf_collision']=recipe.collision
    mesh.from_pydata(recipe.vertices,[],recipe.faces)
    mesh.update(); mesh.materials.append(mat)
    attr=mesh.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER')
    colors=np.asarray(recipe.colors,dtype=np.float32).reshape(-1,4).copy()
    srgb=colors[:,:3]
    colors[:,:3]=np.where(srgb<=.04045,srgb/12.92,((srgb+.055)/1.055)**2.4)
    attr.data.foreach_set('color',colors.ravel())
    mesh.color_attributes.active_color_index=0
    try: mesh.color_attributes.render_color_index=0
    except (AttributeError,TypeError): pass
    if recipe.smooth_shading:
        mesh.polygons.foreach_set('use_smooth',np.ones(len(mesh.polygons),dtype=np.bool_))
    # UV0 is box projection for optional later texturing, not a lightmap atlas.
    verts=np.asarray(recipe.vertices,dtype=np.float32)
    faces=np.asarray(recipe.faces,dtype=np.int32)
    xyz=verts[faces]
    axes=np.argmax(np.abs(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])),axis=1)
    uv_coords=np.empty((len(faces),3,2),dtype=np.float32)
    for ax in range(3):
        mask=axes==ax; us=[i for i in range(3) if i!=ax]
        uv_coords[mask]=xyz[mask][:,:,us]*.25
    uv=mesh.uv_layers.new(name='UV0')
    uv.data.foreach_set('uv',uv_coords.ravel())
    mesh.update()
    return mesh


def camera(collection,name,location,target,ortho=None,lens=45):
    data=bpy.data.cameras.new(name); data['cf_owner']=OWNER
    obj=bpy.data.objects.new(name,data); collection.objects.link(obj)
    obj['cf_owner']=OWNER; obj['cf_role']='preview'
    obj.location=location
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    data.clip_end=1000; data.lens=lens
    if ortho: data.type='ORTHO'; data.ortho_scale=ortho
    return obj


def setup_preview(scene,col,cfg):
    k=cfg['map_size_m']/300; aspect=cfg['render_resolution_x']/cfg['render_resolution_y']
    def cam(name,loc,target,ortho):
        return camera(col,name,tuple(v*k for v in loc),tuple(v*k for v in target),ortho*k)
    scene.camera=cam('CF_Camera_Overview',(270,-350,300),(0,0,0),438)
    cam('CF_Camera_Village',(98,-2,32),(64,37,2.3),68)
    cam('CF_Camera_Camp',(-25,-77,29),(-58,-43,2.1),60)
    cam('CF_Camera_Meadow',(-44,-10,35),(-79,28,2),68)
    cam('CF_Camera_Windmill',(130,62,35),(98,96,8),68)
    cam('CF_Camera_Guardian',(-64,61,38),(-98,95,7),66)
    camera(col,'CF_Camera_Top',(0,-.001,440*k),(0,0,0),(cfg['map_size_m']+14)*max(1,aspect))
    sun_data=bpy.data.lights.new('CF_Sun','SUN'); sun_data['cf_owner']=OWNER
    sun_data.energy=2.3; sun_data.angle=.13; sun_data.color=(1,.93,.80)
    sun=bpy.data.objects.new('CF_Sun',sun_data); col.objects.link(sun)
    sun['cf_owner']=OWNER; sun['cf_role']='preview'; sun.location=(-180,-220,310)
    sun.rotation_euler=(Vector((0,0,0))-sun.location).to_track_quat('-Z','Y').to_euler()
    world=bpy.data.worlds.new('CF_World_300m'); world['cf_owner']=OWNER; world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.60,.76,.83,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.53; scene.world=world
    try: scene.render.engine='CYCLES'
    except (TypeError,ValueError): scene.render.engine='BLENDER_EEVEE_NEXT'
    if scene.render.engine=='CYCLES':
        scene.cycles.samples=cfg['render_samples']; scene.cycles.use_denoising=True
        scene.cycles.max_bounces=6
    scene.render.resolution_x=cfg['render_resolution_x']; scene.render.resolution_y=cfg['render_resolution_y']
    scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
    try:
        scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
    except (TypeError,ValueError): pass
    scene.view_settings.exposure=.15; scene.render.film_transparent=False


def remove_owned_scene(scene):
    """Remove ONLY this generator's scene and objects not used by another scene."""
    if scene is None or scene.get('cf_owner')!=OWNER: return
    objects=list(scene.objects)
    collections=list(scene.collection.children)
    bpy.data.scenes.remove(scene)
    for obj in objects:
        if obj.get('cf_owner')==OWNER and len(obj.users_scene)==0:
            bpy.data.objects.remove(obj,do_unlink=True)
    # Removing a parent can orphan its children; repeat instead of leaving hidden
    # cell collections behind on each rebuild. Never remove another owner's data.
    changed=True
    while changed:
        changed=False
        for col in list(bpy.data.collections):
            if col.get('cf_owner')==OWNER and col.users==0:
                bpy.data.collections.remove(col); changed=True
    for mesh in list(bpy.data.meshes):
        if mesh.get('cf_owner')==OWNER and mesh.users==0: bpy.data.meshes.remove(mesh)
    for data_collection in (bpy.data.cameras,bpy.data.lights,bpy.data.worlds):
        for item in list(data_collection):
            if item.get('cf_owner')==OWNER and item.users==0: data_collection.remove(item)


def main():
    if bpy.app.version<(4,2,0): raise RuntimeError('Blender 4.2 or newer is required.')
    root=package_directory()
    if str(root) not in sys.path: sys.path.insert(0,str(root))
    import importlib
    # Another generated package may previously have used the same module name.
    for name in ('cozy_forest_core','cozy_landmarks','cozy_mesh_library','cozy_transforms','cozy_manifest'):
        sys.modules.pop(name,None)
    core=importlib.import_module('cozy_forest_core')
    config_path=root/'cozy_config.json'
    config=json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
    start=time.perf_counter(); world=core.build_world(config)
    errors=core.validate_world(world)
    if errors: raise RuntimeError('Geometry validation failed:\n'+'\n'.join(errors[:20]))
    previous=bpy.data.scenes.get(SCENE_NAME)
    if previous and previous.get('cf_owner')!=OWNER:
        raise RuntimeError(f'A user scene named {SCENE_NAME} exists. Rename it first; nothing was deleted.')
    before=bpy.context.window.scene if bpy.context.window else bpy.context.scene
    scene=bpy.data.scenes.new(SCENE_NAME+'__BUILDING'); scene['cf_owner']=OWNER
    scene['cf_package_dir']=str(root); scene['cf_version']=core.VERSION
    scene['cf_config_json']=json.dumps(world.config)
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1.0
    try:
        if bpy.context.window: bpy.context.window.scene=scene
        def collection(name,parent=None):
            c=bpy.data.collections.new(name); c['cf_owner']=OWNER
            (parent or scene.collection).children.link(c); return c
        library=collection('CF_00_ASSET_LIBRARY')
        library.hide_render=True; library.hide_viewport=True
        cells_root=collection('CF_10_CELLS_50m')
        cells={}; cats={}
        for record in world.instances:
            cell=record['cell_id']; category=world.assets[record['asset_id']].category
            if cell not in cells:
                cells[cell]=collection('CF_'+cell,cells_root); cells[cell]['cf_cell_id']=cell
            key=(cell,category)
            if key not in cats: cats[key]=collection('CF_'+cell+'_'+category,cells[cell])
        preview=collection('CF_Preview_CamerasLights')
        materials={kind:material(kind) for kind in ('opaque','foliage','water')}
        meshes={}
        for asset_id,recipe in world.assets.items():
            meshes[asset_id]=create_mesh(recipe,materials[recipe.material])
            master=bpy.data.objects.new(asset_id+'__SOURCE',meshes[asset_id])
            library.objects.link(master); master['cf_owner']=OWNER; master['cf_role']='prototype'
            master['cf_asset_id']=asset_id
        for record in world.instances:
            asset_id=record['asset_id']; mesh=meshes[asset_id]
            # Linked data, NOT mesh.copy(): every repeated model uses this one datablock.
            obj=bpy.data.objects.new(record['name'],mesh)
            cats[(record['cell_id'],world.assets[asset_id].category)].objects.link(obj)
            obj.location=record['location']; obj.rotation_mode='XYZ'
            obj.rotation_euler=record['rotation_euler_xyz']; obj.scale=record['scale']
            obj['cf_owner']=OWNER; obj['cf_role']='instance'; obj['cf_asset_id']=asset_id
            obj['cf_cell_id']=record['cell_id']; obj['cf_zone']=record['zone']; obj['cf_source']=record['source']
        markers=collection('CF_20_LANDMARK_MARKERS'); markers.hide_render=True
        for poi in world.points_of_interest:
            if not poi['enabled']: continue
            obj=bpy.data.objects.new('POI_'+poi['id'],None); markers.objects.link(obj)
            obj.location=(poi['x'],poi['y'],poi['z']+1)
            obj.empty_display_type='CIRCLE'; obj.empty_display_size=1.2
            obj['cf_owner']=OWNER; obj['cf_role']='poi'; obj['cf_zone']=poi['id']
            obj['title']=poi['title_ko']; obj['clearing_radius_m']=poi['radius']
        markers.hide_viewport=True
        scene['cf_pois_json']=json.dumps(world.points_of_interest,ensure_ascii=False)
        scene['cf_routes_json']=json.dumps(world.routes)
        setup_preview(scene,preview,world.config)
        stats=world.stats(); scene['cf_stats_json']=json.dumps(stats)
        out=Path(world.config['output_directory']).expanduser()
        if not out.is_absolute(): out=root/out
        out.mkdir(parents=True,exist_ok=True)
        scene['cf_output_dir']=str(out.resolve())
        (out/'generation_stats.json').write_text(json.dumps(stats,indent=2,ensure_ascii=False),encoding='utf-8')
        # Switch only once construction succeeds; preserve the former generated scene on failure.
        if previous: remove_owned_scene(previous)
        scene.name=SCENE_NAME
        if bpy.context.window: bpy.context.window.scene=scene
        bpy.context.view_layer.update()
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type=='VIEW_3D':
                    space=area.spaces.active
                    space.clip_end=1000
                    space.shading.type='MATERIAL' if world.config['viewport_material_preview'] else 'SOLID'
                    if space.shading.type=='SOLID': space.shading.color_type='VERTEX'
                    space.shading.use_scene_world=True; space.shading.use_scene_lights=True
                    if space.region_3d: space.region_3d.view_perspective='CAMERA'
        if world.config['save_blend_on_build']:
            dest=out/'cozy_lake_forest_300m.blend'
            if dest.exists(): raise RuntimeError(f'Refusing to overwrite {dest}. Save As manually or rename the existing file.')
            bpy.ops.wm.save_as_mainfile(filepath=str(dest))
        if world.config['render_preview_on_build']:
            scene.render.filepath=str(out/'cozy_lake_300m_preview.png')
            bpy.ops.render.render(write_still=True,scene=scene.name)
        print('\n[Cozy Lake Forest 300m] Generation complete')
        print(json.dumps(stats,indent=2)); print(f'Elapsed: {time.perf_counter()-start:.2f}s')
        for note in world.notes: print('[NOTE]',note)
        print('Save the .blend manually. Run 02_export_unreal.py when ready.')
    except Exception:
        # Do not delete the successfully-built scene because optional saving/rendering failed.
        if scene.name.endswith('__BUILDING'):
            if bpy.context.window and before.name in bpy.data.scenes: bpy.context.window.scene=before
            remove_owned_scene(scene)
        traceback.print_exc(); raise


if __name__=='__main__': main()
