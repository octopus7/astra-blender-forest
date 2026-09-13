"""Optional: run in Blender to inspect actual datablock sharing before exporting."""
import bpy
import json
from collections import defaultdict
from pathlib import Path
import sys


def main():
    scene=bpy.context.scene
    if scene.get('cf_owner')!='CozyLakeForest300_v2':raise RuntimeError('Select CF_CozyLake_300m first.')
    package=Path(scene['cf_package_dir'])
    if str(package) not in sys.path:sys.path.insert(0,str(package))
    from cozy_transforms import convert_transform,IDENTITY3
    bpy.context.view_layer.update()
    groups=defaultdict(list);errors=[]
    for obj in scene.objects:
        if obj.type!='MESH' or obj.get('cf_role')!='instance':continue
        key=obj.data.get('cf_asset_id')
        if not key:errors.append(obj.name+': missing asset ID');continue
        groups[key].append(obj)
        try:convert_transform([float(obj.matrix_world[i][j]) for i in range(4) for j in range(4)],IDENTITY3)
        except ValueError as e:errors.append(obj.name+': '+str(e))
        if any(m.show_viewport or m.show_render for m in obj.modifiers):errors.append(obj.name+': unbaked modifier')
    rows=[]
    for key,objects in sorted(groups.items()):
        pointers={o.data.as_pointer() for o in objects}
        if len(pointers)!=1:errors.append(key+': more than one mesh datablock for this asset ID')
        mesh=objects[0].data
        if not mesh.color_attributes.get('Color'):errors.append(key+': missing Color attribute')
        mesh.calc_loop_triangles()
        rows.append({'asset_id':key,'instances':len(objects),'mesh_datablocks':len(pointers),'triangles':len(mesh.loop_triangles)})
    report={'unique_assets':len(groups),'placed_instances':sum(len(g) for g in groups.values()),'errors':errors,'assets':rows}
    dest=Path(scene['cf_output_dir'])/'blender_validation_report.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,indent=2))
    if errors:raise RuntimeError('Validation failed. See '+str(dest))
    print('[Cozy] PASS: each asset ID resolves to one shared mesh datablock. '+str(dest))


if __name__=='__main__':main()
