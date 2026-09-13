"""Optional Blender viewport helper. It never deletes or duplicates scene geometry.
MODE='ALL' restores every cell. MODE='ZONE' selects cells intersecting a landmark.
Hidden cells are still included in 02_export_unreal.py.
"""
import bpy,json
from math import floor

MODE='ALL'                       # 'ALL', 'ZONE', or 'CELLS'
ZONE_ID='village'                 # village, camp, meadow, orchard, lookout, guardian,
                                 # ruins, fishing, reading, mushroom, arrival, boathouse
CELL_IDS=['C03_03','C04_03']
APPLY_TO_RENDER=False             # True also excludes other cells from render
SWITCH_CAMERA=True
OWNER='CozyLakeForest300_v2'


def main():
    scene=bpy.context.scene
    if scene.get('cf_owner')!=OWNER:raise RuntimeError('Select scene CF_CozyLake_300m first.')
    cfg=json.loads(scene['cf_config_json']);pois=json.loads(scene['cf_pois_json'])
    selected=set(CELL_IDS);nt=cfg['terrain_tiles_per_axis'];size=cfg['map_size_m']/nt;half=cfg['map_size_m']/2
    if MODE not in ('ALL','ZONE','CELLS'):raise ValueError('MODE must be ALL, ZONE or CELLS.')
    if MODE=='ZONE':
        poi=next((p for p in pois if p['id']==ZONE_ID),None)
        if poi is None:raise ValueError('Unknown ZONE_ID: '+ZONE_ID)
        selected=set();radius=poi['radius']+14
        for iy in range(nt):
            for ix in range(nt):
                x=-half+(ix+.5)*size;y=-half+(iy+.5)*size
                if abs(x-poi['x'])<radius+size/2 and abs(y-poi['y'])<radius+size/2:
                    selected.add(f'C{ix:02d}_{iy:02d}')
    def visit(col):
        if col.get('cf_owner')==OWNER and col.get('cf_cell_id'):
            visible=MODE=='ALL' or col['cf_cell_id'] in selected
            col.hide_viewport=not visible
            if APPLY_TO_RENDER:col.hide_render=not visible
            elif MODE=='ALL':col.hide_render=False
        for child in col.children:visit(child)
    visit(scene.collection)
    cameras={'village':'Village','camp':'Camp','meadow':'Meadow','lookout':'Windmill','guardian':'Guardian'}
    wanted='CF_Camera_'+('Overview' if MODE=='ALL' else cameras.get(ZONE_ID,'Overview'))
    if SWITCH_CAMERA:
        camera=next((o for o in scene.objects if o.type=='CAMERA' and o.name.startswith(wanted)),None)
        if camera:scene.camera=camera
    print('[Cozy 300m] Visible: '+('ALL' if MODE=='ALL' else ', '.join(sorted(selected))))
    print('Only generator cell visibility was changed. Hidden cells will still export.')


if __name__=='__main__':main()
