"""Generate and validate the full DEFAULT 300m layout without Blender.

Run from a terminal:
    python tests/validate_full_scene.py
Only writes a JSON report below this package's output/ directory.
This does not test bpy, FBX export, or Unreal Editor APIs.
"""
from pathlib import Path
import sys
import json
import time
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cozy_forest_core as core
import cozy_manifest as manifest
import cozy_transforms as tr


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    started = time.perf_counter()
    config = json.loads((ROOT / 'cozy_config.json').read_text(encoding='utf-8'))
    world = core.build_world(config)
    errors = core.validate_world(world)
    require(not errors, '\n'.join(errors[:20]))
    layout = core.Layout(world.config)
    spacing = world.config['tree_min_spacing_m']
    grid = core.SpatialHash(spacing)
    terrain_bounds = [float('inf'), float('inf'), -float('inf'), -float('inf')]
    checked = Counter()
    for item in world.instances:
        x, y = item['location'][:2]
        require(item['cell_id'] == manifest.cell_id_for_position(
            x, y, world.config['map_size_m'], world.config['terrain_tiles_per_axis']),
            'Wrong cell for ' + item['name'])
        matrix = core.matrix_for(item['location'], item['rotation_euler_xyz'], item['scale'])
        tr.convert_transform(matrix, [[100, 0, 0], [0, -100, 0], [0, 0, 100]])
        checked['transforms_and_cell_ids'] += 1
        if item['source'] == 'forest_tree':
            require(grid.clear(x, y, spacing), 'Tree spacing violation: ' + item['name'])
            grid.add(x, y)
            require(layout.water_distance(x, y) >= 3.5, 'Tree in water')
            require(layout.path_distance(x, y) >= layout.path_half_width(x, y) + 2, 'Tree on path')
            require(not layout.reserved(x, y, 1.9), 'Tree in reserved clearing')
            checked['forest_spacing_and_exclusion'] += 1
        asset = world.assets[item['asset_id']]
        if asset.category == 'Terrain':
            for vertex in asset.vertices:
                px, py, _ = core.add(vertex, item['location'])
                terrain_bounds = [min(terrain_bounds[0], px), min(terrain_bounds[1], py),
                                  max(terrain_bounds[2], px), max(terrain_bounds[3], py)]
    half = world.config['map_size_m'] / 2
    require(terrain_bounds == [-half, -half, half, half], 'Wrong terrain footprint')
    groups = manifest.group_instances(world.instances)
    require(sum(map(len, groups.values())) == len(world.instances), 'HISM grouping lost placements')
    cells = manifest.make_cell_records(world.instances, world.config['map_size_m'],
                                      world.config['terrain_tiles_per_axis'])
    require(sum(c['instance_count'] for c in cells) == len(world.instances), 'Cell count mismatch')
    require(world.stats()['forest_trees'] == world.config['tree_count'], 'Forest target not reached')
    result = {
        'status': 'PASS',
        'engine_runtime_tested': False,
        'scope': 'pure Python generated geometry, spatial layout, shared asset references and transforms',
        'errors': errors,
        'stats': world.stats(),
        'checks': dict(checked),
        'terrain_bounds_xy_m': terrain_bounds,
        'elapsed_seconds_in_this_environment': round(time.perf_counter() - started, 3),
        'notes': world.notes,
    }
    output = ROOT / 'output'
    output.mkdir(exist_ok=True)
    target = output / 'full_python_validation.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'stats'}, ensure_ascii=False, indent=2))
    print('Report:', target)


if __name__ == '__main__':
    main()
