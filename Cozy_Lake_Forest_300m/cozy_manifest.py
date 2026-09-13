"""Pure-Python spatial export helpers, shared with the Blender exporter and tests."""
from collections import defaultdict
from math import floor,isfinite
import re


def cell_id_for_position(x,y,map_size_m,tiles):
    half=map_size_m/2
    if not isfinite(x) or not isfinite(y):raise ValueError('Non-finite instance position.')
    if abs(x)>half+.01 or abs(y)>half+.01:
        raise ValueError(f'Instance pivot ({x:.3f}, {y:.3f}) is outside the {map_size_m:g} m map.')
    size=map_size_m/tiles
    ix=max(0,min(tiles-1,floor((x+half)/size)))
    iy=max(0,min(tiles-1,floor((y+half)/size)))
    return f'C{ix:02d}_{iy:02d}'


def make_cell_records(instances,map_size_m,tiles):
    counts=defaultdict(int)
    for record in instances:counts[record['cell_id']]+=1
    half=map_size_m/2;size=map_size_m/tiles;cells=[]
    for iy in range(tiles):
        for ix in range(tiles):
            key=f'C{ix:02d}_{iy:02d}'
            cells.append({'cell_id':key,'ix':ix,'iy':iy,
                'origin_blender_m':[-half+(ix+.5)*size,-half+(iy+.5)*size,0.0],
                'bounds_xy_m':[-half+ix*size,-half+iy*size,-half+(ix+1)*size,-half+(iy+1)*size],
                'instance_count':counts.get(key,0),'file':f'cells/{key}.json'})
    extra=set(counts)-{c['cell_id'] for c in cells}
    if extra:raise ValueError('Unknown cells: '+str(extra))
    return cells


def group_instances(instances):
    groups=defaultdict(list)
    for row in instances:groups[(row['cell_id'],row['asset_id'])].append(row)
    return dict(groups)
