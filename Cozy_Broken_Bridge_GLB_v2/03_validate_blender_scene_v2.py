"""Run inside the generated Blender scene; writes an actual runtime report.
Does not pretend that a standalone Python syntax check is a Blender runtime test.
"""
import bpy,json,math
from pathlib import Path

def main():
    scene=bpy.context.scene;root=scene.get('package_root')
    if not root:raise RuntimeError('CF_BrokenBridge_v2 씬에서 실행하세요.')
    collection=next((c for c in scene.collection.children if c.name.startswith('01_BRIDGE_')),None)
    if collection is None:raise RuntimeError('다리 컬렉션을 찾지 못했습니다.')
    obs=[o for o in collection.objects if o.type=='MESH' and o.get('cb_bridge_asset')]
    seen=set();unique_tris=0
    for ob in obs:
        if ob.data.as_pointer() in seen:continue
        seen.add(ob.data.as_pointer());ob.data.calc_loop_triangles();unique_tris+=len(ob.data.loop_triangles)
        assert ob.data.uv_layers.get('UV0') is not None
        assert len(ob.data.materials)==1
        assert all(math.isfinite(x) for v in ob.data.vertices for x in v.co)
    assert unique_tris==6732,unique_tris
    env=next((c for c in scene.collection.children if c.name.startswith('02_RIVER_')),None)
    water=next((o for o in env.objects if o.name.startswith('River_Water_Volume')),None) if env else None
    report={'Blender_runtime_tested':True,'Blender_version':bpy.app.version_string,'scene':scene.name,'bridge_triangles_unique':unique_tris,'bridge_mesh_datablocks':len(seen),'has_camera':scene.camera is not None,'lights':sum(o.type=='LIGHT' for o in scene.objects),'has_river_water':water is not None,'render_engine':scene.render.engine,'render_performed_by_this_validator':False}
    if water:
        types={n.bl_idname for n in water.data.materials[0].node_tree.nodes}
        assert {'ShaderNodeBsdfPrincipled','ShaderNodeVolumeAbsorption','ShaderNodeBump'}<=types
        report['water_shader_nodes_pass']=True
    p=Path(root)/'validation/BLENDER_RUNTIME_USER_RESULT.json';p.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps(report,indent=2,ensure_ascii=False));print('기록:',p)
if __name__=='__main__':main()
