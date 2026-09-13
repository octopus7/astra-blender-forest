[English](README.md) · [한국어](README_KO.md) · [日本語](README_JA.md)

<p align="center">
  <img src="../images/forest300_1.jpeg" alt="Overview of the Cozy Lake Forest scene" width="32%" />
  <img src="../images/forest300_2.jpeg" alt="Lakeside village view" width="32%" />
  <img src="../images/forest300_3.jpeg" alt="Orchard and garden view" width="32%" />
</p>

# Cozy Lake Forest — 300 × 300 m

`Cozy_Lake_Forest_300m` is a Blender Python source package for generating a stylized forest scene on a **300 × 300 m** site. The generator creates a large lake, two small ponds, a stream, connected walking trails, dense forest, low-poly props, and 12 landmark areas.

This is a source package rather than a finished scene. It generates the models and placement in Blender; it does not ship a completed `.blend` or FBX file. Keep the complete folder together when running the scripts.

## Requirements

- Blender 4.2 or newer
- No external Python package installation
- A writable package directory

The scripts use Blender's bundled Python and built-in `bpy` APIs. The generated scene uses metric units with `Unit Scale = 1.0`.

## Build the Blender scene

1. Open the complete `Cozy_Lake_Forest_300m` folder in a writable location.
2. In Blender, open **Scripting → Text Editor → Open** and select `01_build_scene.py`.
3. Move the mouse over the Text Editor and press **Alt+P**, or choose **Run Script**.
4. Inspect the generated `CF_CozyLake_300m` scene.
5. Save the `.blend` file manually.

The default configuration is `cozy_config.json` with seed `42`. The script does not automatically save a `.blend` or render a preview. Running the generator again replaces the previous generated scene owned by this package, so save manual edits before rebuilding. If another scene already uses the name `CF_CozyLake_300m`, the script stops without deleting it.

## Default generation

| Item | Default or generated result |
| --- | ---: |
| Site | 300 × 300 m, 90,000 m² |
| Coordinate range | X and Y from -150 to +150 m |
| Spatial layout | 36 cells, each 50 × 50 m |
| Landmark areas | 12 |
| Water | 1 lake, 2 ponds, and a stream |
| Placed instances | 16,573 |
| Trees | 3,839 including the guardian tree |
| Reusable mesh assets | 127 |
| Unique mesh triangles | 521,197 |
| Triangles if every placement is counted separately | 4,807,521 |

The last triangle count describes total placed geometry and is not a frame-time or performance measurement. See `default_generation_stats.json` for per-asset and per-cell counts. The terrain is split into 36 regular Static Mesh tiles with a 480 × 480 base grid; it is not an Unreal Landscape.

## Landmark areas

| ID | Area |
| --- | --- |
| `village` | Lakeside village with cottages, a well, market stalls, flowers, and benches |
| `meadow` | Flower garden with a gazebo, swing, beehives, and blossom trees |
| `camp` | Lantern campground with three tents, a campfire ring, hammock, picnic table, and festoons |
| `orchard` | Apple orchard with garden beds, beehives, crates, and a produce stall |
| `lookout` | Windmill lookout hill with a timber deck and telescope |
| `guardian` | Wishing-tree grove with a large oak, ribbons, and a fox statue |
| `ruins` | Mossy ruins with a stone arch, broken pillars, and moss rocks |
| `fishing` | Quiet fishing pond with docks, rowboats, benches, and lily pads |
| `reading` | Forest reading shelter with a book kiosk, gazebo, and blossom trees |
| `mushroom` | Mushroom tea garden with giant mushrooms and picnic seating |
| `arrival` | Forest entrance with a welcome gate, signposts, and a rest area |
| `boathouse` | Waterside picnic area with tables, benches, and a lakeside trail |

The landmarks are scene-design locations. Fishing, gathering, building, reading, and other gameplay systems are not implemented.

## Blender scene structure

- `CF_00_ASSET_LIBRARY`: hidden source meshes. Repeated objects reference the same Mesh datablock.
- `CF_10_CELLS_50m`: 36 cell collections, with category collections inside each cell.
- `CF_20_LANDMARK_MARKERS`: hidden Empty objects for landmark locations and clearing radii.

Use **Alt+D** when manually duplicating a repeated asset so the new object keeps the shared mesh. If one object needs a unique model, make its mesh single-user and give it a unique `cf_asset_id`; duplicate asset IDs across separate mesh datablocks will stop the exporter.

The exporter rejects negative scale, shear, non-finite transforms, shape keys, active unapplied modifiers, and object-level material overrides. Apply changes to the shared source mesh instead.

## Export for Unreal

### Blender export

Select or activate the generated `CF_CozyLake_300m` scene and run `02_export_unreal.py`. The default output is:

```text
output/unreal_export/
  meshes/                     One FBX per unique asset
  calibration/                Three axis and unit probe FBX files
  scene_instances.json        Asset manifest and all placement transforms
  geometry_cache.json         Source mesh hashes
  cell_index.json             Cell bounds and counts
  cells/C00_00.json           Placement rows for one cell
  ...
```

The exporter writes each unique mesh once and stores placement matrices in JSON. `TRANSFORMS_ONLY = True` can be used when only placement changed and all source mesh hashes still match. Set it back to `False` when a source mesh or a new asset is introduced.

Keep Blender at `Unit Scale = 1.0`. The manifest records Blender metres as the source and Unreal centimetres as the target. The calibration FBX files are diagnostic probes and should not be placed as scene props.

### Unreal import

1. Save the working Unreal level.
2. Enable **Python Editor Script Plugin** and **Editor Scripting Utilities**.
3. In **Tools → Execute Python Script**, run `03_import_unreal.py`.

The default content root is `/Game/CozyLakeForest300m`. The importer reuses Static Mesh assets and groups repeated assets by cell and asset ID as HISM components. Assets used only once in a cell are placed as regular Static Mesh Actors.

If the HISM SubobjectData path is unavailable in the target engine version, set the importer option below and try the regular actor path:

```python
PLACEMENT_MODE = 'ACTORS'
```

For a partial reload, set `ONLY_CELL_IDS` in the importer:

```python
ONLY_CELL_IDS = ['C03_03', 'C04_03']
```

An empty list imports all cells. When an object moves between cells, update both the source and destination cells or perform a full update so the old placement is removed. Existing user-created level actors are not importer targets. Level saving remains manual.

## Focus a region in Blender

Run `05_focus_region.py` to show selected cells or a landmark region:

```python
MODE = 'ZONE'
ZONE_ID = 'camp'
```

Use `MODE = 'ALL'` to show the complete map, or `MODE = 'CELLS'` with `CELL_IDS` to choose cell IDs. This changes viewport visibility by default. Hidden cells remain eligible for export; set `APPLY_TO_RENDER = True` when they should also be excluded from rendering.

For a lighter build, copy `presets/cozy_config_light.json` over `cozy_config.json` and rebuild. The light preset keeps the 300 m site and landmarks while reducing the forest, terrain resolution, and small details.

The most useful configuration values are `seed`, `tree_count`, `ground_detail_count`, `meadow_flower_count`, and `terrain_resolution`. Terrain resolution must divide evenly across the six cells on each axis. Tree spacing can prevent the requested count from being reached; the generator reports this in its notes.

## Scope and post-processing

The package uses vertex colors and simple opaque, foliage, and water materials. It does not download external textures or call image-generation services.

The following require project-specific post-processing:

- Production LODs, collision, navigation, and gameplay systems
- Unreal Landscape, World Partition, sublevels, or runtime streaming
- Animated water, leaves, windmill blades, campfire, or lantern lighting
- Production UV unwraps, lightmaps, texture baking, and final materials

Unreal component collision is disabled by default. Configure collision for terrain, buildings, bridges, and other walkable objects before first-person gameplay. Water, fire, ducks, festoons, windmill blades, and wishing ribbons are static visual models.

## Files

| File | Purpose |
| --- | --- |
| `01_build_scene.py` | Build the Blender scene, shared meshes, placement, and preview cameras |
| `02_export_unreal.py` | Export unique FBX meshes and placement manifests |
| `03_import_unreal.py` | Import assets and place HISM components or actors in Unreal |
| `04_validate_blender_scene.py` | Validate generated Blender mesh sharing and scene metadata |
| `05_focus_region.py` | Show selected cells or landmarks in Blender |
| `cozy_forest_core.py` | Generate terrain, water, trails, and forest distribution |
| `cozy_mesh_library.py` | Define reusable trees, nature assets, structures, and props |
| `cozy_landmarks.py` | Define landmark assets and placements |
| `cozy_manifest.py`, `cozy_transforms.py` | Cell manifests and coordinate conversion utilities |
| `tests/` | Pure-Python unit tests and full generation validation |
| `OPEN_PREVIEWS.html` | Offline preview gallery |
| `previews/` | World map and landmark preview images |

## Validation

The recorded pure-Python validation passes 30 tests covering configuration, geometry, water, terrain seams, spacing, cell assignment, shared meshes, deterministic seeds, and transform conversion. Blender and Unreal Editor runtime execution has not been included in that report.

```text
python -m unittest discover -s tests -v
python tests/validate_full_scene.py
```

Reports are stored in `tests/reports/unit_tests.txt` and `tests/reports/full_python_validation.json`.
