"""Blender: Scripting > Open this file > Run Script.
Reconstructs the bridge from the included editable recipe and low-poly builder.
Creates a NEW scene; does not clear or replace the user's existing scene.
Target: Blender 4.2+ / 4.5 LTS / 5.x. No pip packages required in Blender.
"""
from __future__ import annotations
import sys,json,math
from pathlib import Path
import bpy
from mathutils import Vector

# Only needed when the text was pasted instead of opened from the extracted ZIP.
PACKAGE_DIR = r""


def find_root():
    candidates=[]
    if PACKAGE_DIR:candidates.append(Path(PACKAGE_DIR).expanduser())
    if '__file__' in globals():candidates.append(Path(__file__).resolve().parent)
    space=getattr(bpy.context,'space_data',None)
    text=getattr(space,'text',None)
    if text and text.filepath:candidates.append(Path(bpy.path.abspath(text.filepath)).parent)
    if bpy.data.filepath:candidates.extend([Path(bpy.data.filepath).parent,Path(bpy.data.filepath).parent.parent])
    for p in candidates:
        if (p/'data/bridge_recipe.json').is_file() and (p/'source/generate_bridge_v2.py').is_file():return p
    raise RuntimeError('ZIP 전체를 압축 해제한 뒤 01_build_blender_scene_v2.py를 Open으로 여세요. 경로 탐지 실패 시 PACKAGE_DIR에 폴더 경로를 지정하세요.')

ROOT=find_root();SRC=ROOT/'source'
if str(SRC) in sys.path:sys.path.remove(str(SRC))
sys.path.insert(0,str(SRC))
# Reload only this package's helper modules when running the script a second time.
for name in ('generate_bridge_v2','scene_geometry','mesh_core'):
    old=sys.modules.get(name)
    if old:del sys.modules[name]
from generate_bridge_v2 import generate_bridge_meshes
from mesh_core import Mesh
from scene_geometry import make_environment,make_decoration_prototypes,decoration_instances
import numpy as np
CFG=json.loads((ROOT/'scene_config.json').read_text(encoding='utf8'))


def node(nt,kind,name,x,y):
    n=nt.nodes.new(kind);n.name=name;n.label=name;n.location=(x,y);return n

def set_input(n,name,value):
    s=n.inputs.get(name)
    if s is not None:s.default_value=value

def material_base(name):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
    out=node(nt,'ShaderNodeOutputMaterial','Material Output',850,180)
    bs=node(nt,'ShaderNodeBsdfPrincipled','Principled BSDF',550,180)
    nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    return m,nt,bs,out

def load_image(filename,noncolor=False):
    path=ROOT/'textures'/filename
    if not path.is_file():raise FileNotFoundError(f'텍스처 누락: {path}')
    im=bpy.data.images.load(str(path),check_existing=True)
    im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
    if CFG.get('pack_textures',True):im.pack()
    return im

def bridge_material():
    m,nt,bs,out=material_base('M_BrokenBridge_Atlas_PBR_v2');m.use_backface_culling=False
    uv=node(nt,'ShaderNodeUVMap','UV0',-880,180);uv.uv_map='UV0'
    color=node(nt,'ShaderNodeTexImage','2K Base Color',-630,460);color.image=load_image('T_BrokenBridge_BaseColor.png')
    normal=node(nt,'ShaderNodeTexImage','2K Normal (OpenGL)',-630,100);normal.image=load_image('T_BrokenBridge_Normal_GL.png',True)
    orm=node(nt,'ShaderNodeTexImage','2K ORM: R=AO, G=Roughness, B=Metallic',-630,-250);orm.image=load_image('T_BrokenBridge_ORM.png',True)
    for n in (color,normal,orm):n.extension='EXTEND';nt.links.new(uv.outputs['UV'],n.inputs['Vector'])
    nt.links.new(color.outputs['Color'],bs.inputs['Base Color'])
    sep=node(nt,'ShaderNodeSeparateColor','Unpack ORM',-240,-240);sep.mode='RGB';nt.links.new(orm.outputs['Color'],sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    nm=node(nt,'ShaderNodeNormalMap','Fine grain / moss detail',-170,100);nm.space='TANGENT';nm.uv_map='UV0';nm.inputs['Strength'].default_value=.7
    nt.links.new(normal.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    set_input(bs,'Specular IOR Level',.32)
    # glTF exporter reads AO from this conventionally named group input.
    group=bpy.data.node_groups.get('glTF Material Output')
    if group is None:
        group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
        if hasattr(group,'interface'):group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
        else:group.inputs.new('NodeSocketFloat','Occlusion')
        group.nodes.new('NodeGroupInput')
    gn=node(nt,'ShaderNodeGroup','glTF Material Output',160,-270);gn.node_tree=group
    if gn.inputs.get('Occlusion'):nt.links.new(sep.outputs['Red'],gn.inputs['Occlusion'])
    m['texture_note']='OpenGL normal; packed ORM. Height/AO are texture-derived, not high-poly baked.'
    return m

def color_ramp(nt,name,stops,x,y):
    n=node(nt,'ShaderNodeValToRGB',name,x,y);r=n.color_ramp
    while len(r.elements)>2:r.elements.remove(r.elements[-1])
    r.elements[0].position=stops[0][0];r.elements[0].color=stops[0][1]
    r.elements[1].position=stops[-1][0];r.elements[1].color=stops[-1][1]
    for pos,col in stops[1:-1]:e=r.elements.new(pos);e.color=col
    r.interpolation='EASE';return n

def ground_material(kind):
    m,nt,bs,out=material_base('M_River_'+kind+'_v2')
    geom=node(nt,'ShaderNodeNewGeometry','World Position',-1000,0)
    noise=node(nt,'ShaderNodeTexNoise','Ground variation',-800,230);noise.inputs['Scale'].default_value=2.8;noise.inputs['Detail'].default_value=3.2
    nt.links.new(geom.outputs['Position'],noise.inputs['Vector'])
    if kind=='bank':
        shore=node(nt,'ShaderNodeAttribute','Distance from bank edge',-1000,520);shore.attribute_name='shore_factor'
        ramp=color_ramp(nt,'Wet sand to grass',[(0,(.075,.085,.039,1)),(.07,(.25,.22,.095,1)),(.19,(.42,.37,.14,1)),(.25,(.19,.29,.045,1)),(1,(.22,.34,.065,1))],-670,570)
        nt.links.new(shore.outputs['Fac'],ramp.inputs['Fac'])
        noise_ramp=color_ramp(nt,'Grass texture variation',[(0,(.35,.44,.11,1)),(1,(.91,.90,.55,1))],-490,230);nt.links.new(noise.outputs['Fac'],noise_ramp.inputs['Fac'])
        mix=node(nt,'ShaderNodeMixRGB','Mottled ground',-220,470);mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.45
        nt.links.new(ramp.outputs['Color'],mix.inputs[1]);nt.links.new(noise_ramp.outputs['Color'],mix.inputs[2])
        # A sand path approaches both ends of the bridge, without crossing the gap.
        sep=node(nt,'ShaderNodeSeparateXYZ','Path coordinates',-790,-150);nt.links.new(geom.outputs['Position'],sep.inputs['Vector'])
        ab=node(nt,'ShaderNodeMath','Path distance',-570,-130);ab.operation='ABSOLUTE';nt.links.new(sep.outputs['Y'],ab.inputs[0])
        path=color_ramp(nt,'Soft path boundary',[(0,(1,1,1,1)),(1,(0,0,0,1))],-350,-120)
        scale=node(nt,'ShaderNodeMath','Path half-width 1.55m',-550,-310);scale.operation='DIVIDE';scale.inputs[1].default_value=1.55;nt.links.new(ab.outputs[0],scale.inputs[0]);nt.links.new(scale.outputs[0],path.inputs['Fac'])
        final=node(nt,'ShaderNodeMixRGB','Sandy approach path',70,420);nt.links.new(path.outputs['Color'],final.inputs[0]);nt.links.new(mix.outputs[0],final.inputs[1]);final.inputs[2].default_value=(.43,.35,.16,1)
        nt.links.new(final.outputs[0],bs.inputs['Base Color'])
    else:
        ramp=color_ramp(nt,'Sand / silt / pebbles',[(0,(.065,.072,.030,1)),(.48,(.20,.22,.11,1)),(1,(.42,.39,.22,1))],-440,240);nt.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);nt.links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
        vor=node(nt,'ShaderNodeTexVoronoi','Riverbed pebble grain',-800,-170);vor.inputs['Scale'].default_value=15
        nt.links.new(geom.outputs['Position'],vor.inputs['Vector']);noise=vor
    bump=node(nt,'ShaderNodeBump','Fine ground relief',180,-150);bump.inputs['Strength'].default_value=.24;bump.inputs['Distance'].default_value=.025
    nt.links.new(noise.outputs[0],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal']);set_input(bs,'Roughness',.92)
    return m

def water_material(scene):
    m,nt,bs,out=material_base('M_River_Water_v2')
    set_input(bs,'Base Color',(.53,.88,.78,1));set_input(bs,'Metallic',0);set_input(bs,'Roughness',CFG['water_roughness']);set_input(bs,'IOR',CFG['water_ior'])
    set_input(bs,'Transmission Weight',CFG['water_transmission']);set_input(bs,'Coat Weight',.18);set_input(bs,'Coat Roughness',.075)
    coord=node(nt,'ShaderNodeTexCoord','Object-space ripples',-1100,100)
    mapping=node(nt,'ShaderNodeMapping','River flow (animated Y offset)',-880,100);mapping.vector_type='POINT'
    nt.links.new(coord.outputs['Object'],mapping.inputs['Vector']);mapping.inputs['Scale'].default_value=(1.65,5.8,.8)
    speed=CFG['water_flow_metres_per_second'];fps=scene.render.fps/scene.render.fps_base
    # Keyframes, not drivers: the saved .blend does not require auto-run Python.
    loc=mapping.inputs['Location'];loc.default_value=(0,0,0);loc.keyframe_insert('default_value',frame=1,index=1)
    loc.default_value=(0,-speed*240/fps,0);loc.keyframe_insert('default_value',frame=241,index=1)
    try:
        for fc in nt.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
    except (AttributeError,RuntimeError):pass
    noise=node(nt,'ShaderNodeTexNoise','Broad water ripples',-570,230);noise.noise_dimensions='3D';noise.inputs['Scale'].default_value=1.35;noise.inputs['Detail'].default_value=2.4;noise.inputs['Roughness'].default_value=.55
    nt.links.new(mapping.outputs['Vector'],noise.inputs['Vector'])
    fine=node(nt,'ShaderNodeTexNoise','Small overlapping ripples',-570,-65);fine.inputs['Scale'].default_value=6.0;fine.inputs['Detail'].default_value=2;nt.links.new(mapping.outputs['Vector'],fine.inputs['Vector'])
    mix=node(nt,'ShaderNodeMixRGB','Two ripple scales',-280,140);mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.23;nt.links.new(noise.outputs['Fac'],mix.inputs[1]);nt.links.new(fine.outputs['Fac'],mix.inputs[2])
    bump=node(nt,'ShaderNodeBump','Ripple normal (no tessellation)',10,140);bump.inputs['Strength'].default_value=CFG['water_ripple_strength'];bump.inputs['Distance'].default_value=CFG['water_ripple_distance_m']
    nt.links.new(mix.outputs[0],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    absorption=node(nt,'ShaderNodeVolumeAbsorption','Teal depth / absorption',530,-170);absorption.inputs['Color'].default_value=(.20,.72,.56,1);absorption.inputs['Density'].default_value=CFG['water_absorption_density']
    nt.links.new(absorption.outputs['Volume'],out.inputs['Volume'])
    m['render_note']='Closed water volume. Cycles is the reference shader path; Eevee refraction depends on its ray-tracing settings.'
    m['export_note']='Blender procedural water and volume do not accompany the standalone bridge GLB; rebuild them in the destination engine.'
    return m

def simple_material(name,color,roughness=.8):
    m,nt,bs,out=material_base(name);set_input(bs,'Base Color',color);set_input(bs,'Roughness',roughness);return m

def make_collection(scene,name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c

def object_from_bridge(spec,collection,material):
    data=bpy.data.meshes.new(spec.name);data.from_pydata(spec.vertices,[],spec.faces);data.update()
    uv=np.asarray(spec.uvs,float).copy();uv[:,1]=1-uv[:,1]
    layer=data.uv_layers.new(name='UV0');indices=np.array([l.vertex_index for l in data.loops],int);layer.data.foreach_set('uv',uv[indices].ravel())
    # Split normals preserve hard timber edges and smooth low-sided rope cylinders.
    for p in data.polygons:p.use_smooth=True
    try:data.normals_split_custom_set_from_vertices(spec.normals)
    except (AttributeError,RuntimeError):
        for p in data.polygons:p.use_smooth=False
    data.materials.append(material);obj=bpy.data.objects.new(spec.name,data);collection.objects.link(obj)
    obj['cb_bridge_asset']=True;obj['triangles']=len(spec.faces);obj['version']=2
    return obj

def object_from_env(spec,collection,material):
    data=bpy.data.meshes.new(spec['name']);data.from_pydata(spec['vertices'].tolist(),[],spec['faces']);data.update()
    if spec.get('shore') is not None:
        a=data.attributes.new('shore_factor','FLOAT','POINT');a.data.foreach_set('value',spec['shore'])
    if spec['material'] in ('bank','bed'):
        for p in data.polygons:p.use_smooth=True
    data.materials.append(material);obj=bpy.data.objects.new(spec['name'],data);collection.objects.link(obj);return obj

def aim(obj,point):obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()

def add_light(collection,name,kind,location,energy,color,size=5,target=(0,0,-.2)):
    data=bpy.data.lights.new(name,kind);data.energy=energy;data.color=color
    if kind=='AREA':data.shape='DISK';data.size=size
    if kind=='SUN':data.angle=math.radians(size)
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.location=location;aim(obj,target);return obj

def build_lighting(scene,collection):
    world=bpy.data.worlds.new('World_CozyRiver_v2');world.use_nodes=True;scene.world=world;nt=world.node_tree;nt.nodes.clear()
    out=node(nt,'ShaderNodeOutputWorld','World Output',400,0);bg=node(nt,'ShaderNodeBackground','Cool sky fill',120,0)
    bg.inputs['Color'].default_value=(.68,.80,.96,1);bg.inputs['Strength'].default_value=CFG['world_strength'];nt.links.new(bg.outputs[0],out.inputs['Surface'])
    add_light(collection,'Sun_Warm_Afternoon','SUN',(-8,-6,13),CFG['sun_energy'],(1,.83,.59),9)
    add_light(collection,'Area_Soft_Sky','AREA',(4,-2,10),700,(.67,.85,1),9)
    add_light(collection,'Area_Warm_Rim','AREA',(-1,7,8),1100,(1,.86,.65),7)
    for name,loc,target,scale in [('Camera_Hero',(11,-16,11),(0,0,-.3),16.8),('Camera_Top',(0,0,20),(0,0,0),17.5),('Camera_Detail',(-1.2,-6,3.2),(-3.4,-1.1,-.08),5.2)]:
        data=bpy.data.cameras.new(name);obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.location=loc;data.type='ORTHO';data.ortho_scale=scale;data.clip_end=150;aim(obj,target)
        if name=='Camera_Hero':scene.camera=obj

def main():
    if bpy.app.version<(4,2,0):raise RuntimeError('이 스크립트의 대상 버전은 Blender 4.2 이상입니다.')
    scene=bpy.data.scenes.new(CFG['scene_name']);scene['cb_package_version']=2;scene['asset_triangle_count']=6732;scene['asset_triangles_exclude_environment']=True
    if bpy.context.window:bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
    scene.render.engine=CFG.get('render_engine','CYCLES');scene.render.resolution_x,scene.render.resolution_y=CFG['resolution'];scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'previews/Blender_Hero_v2.png');scene.render.fps=24;scene.frame_start=1;scene.frame_end=240
    if scene.render.engine=='CYCLES':
        scene.cycles.samples=CFG['render_samples'];scene.cycles.use_denoising=True;scene.cycles.max_bounces=10;scene.cycles.transmission_bounces=8;scene.cycles.volume_bounces=2
    elif hasattr(scene,'eevee') and hasattr(scene.eevee,'use_raytracing'):scene.eevee.use_raytracing=True
    try:scene.view_settings.view_transform='AgX'
    except TypeError:scene.view_settings.view_transform='Standard'
    scene.view_settings.exposure=.20;scene.view_settings.gamma=1
    asset=make_collection(scene,'01_BRIDGE_6732_TRIS');environment=make_collection(scene,'02_RIVER_AND_BANKS');lighting=make_collection(scene,'03_LIGHTS_AND_CAMERAS')
    mat=bridge_material();parts,_=generate_bridge_meshes()
    if CFG.get('build_modular_parts',False):
        bridge_objects=[object_from_bridge(p,asset,mat) for p in parts]
    else:
        combined=Mesh('SM_BrokenBridge_v2')
        for p in parts:combined.append(p)
        bridge_objects=[object_from_bridge(combined,asset,mat)]
    if CFG.get('show_instance_example',False):
        examples=make_collection(scene,'04_LINKED_INSTANCE_EXAMPLES')
        for n in (1,2):
            for original in bridge_objects:
                instance=original.copy();instance.data=original.data;examples.objects.link(instance);instance.location.y=n*27
    if CFG.get('build_environment',True):
        materials={'bank':ground_material('bank'),'bed':ground_material('bed'),'water':water_material(scene),'shore_stone':simple_material('M_ShoreStone_v2',(.28,.33,.18,1)), 'lily':simple_material('M_LilyPad_v2',(.19,.35,.08,1),.54),'reed':simple_material('M_Reed_v2',(.22,.34,.07,1))}
        for spec in make_environment(CFG):object_from_env(spec,environment,materials[spec['material']])
        if CFG.get('environment_decoration',True):
            proto={}
            for spec in make_decoration_prototypes():
                ob=object_from_env(spec,environment,materials[spec['material']]);proto[spec['name']]=ob.data
                bpy.data.objects.remove(ob,do_unlink=True)
            for i,(name,pos,rot,scale) in enumerate(decoration_instances(CFG)):
                ob=bpy.data.objects.new(name.replace('_Prototype','')+f'_{i:02d}',proto[name]);environment.objects.link(ob);ob.location=pos;ob.rotation_euler=rot;ob.scale=scale
    build_lighting(scene,lighting);scene.frame_set(1)
    for obj in scene.objects:obj.select_set(False,view_layer=scene.view_layers[0])
    for obj in bridge_objects:obj.select_set(True,view_layer=scene.view_layers[0])
    scene.view_layers[0].objects.active=bridge_objects[0]
    scene['package_root']=str(ROOT);scene['water_shader']='Transmission + IOR 1.333 + animated bump + volume absorption'
    # On opening Material Preview, use the scene lighting rather than the default studio HDRI.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.shading.use_scene_world=True;area.spaces.active.shading.use_scene_lights=True
                area.spaces.active.shading.type='MATERIAL'
                area.spaces.active.region_3d.view_perspective='CAMERA'
    print('완료: 새 씬',scene.name,'/ 다리 6,732 삼각형 / 강물·강바닥·조명 별도 컬렉션')
    print('F12: 렌더 | File > Save As: .blend 저장 | 수면 움직임: 프레임 1~240')
    if '--save-blend' in sys.argv:
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'BrokenBridge_River_v2.blend'))
    if '--render' in sys.argv:
        with bpy.context.temp_override(scene=scene,view_layer=scene.view_layers[0]):bpy.ops.render.render(write_still=True)
    return scene

if __name__=='__main__':main()
