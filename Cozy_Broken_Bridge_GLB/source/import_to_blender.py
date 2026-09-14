"""Optional convenience importer. The delivered GLB works without this script.
Open this file in Blender's Text Editor and Run Script.
"""
from pathlib import Path
import bpy

# Leave blank when this script is opened from the extracted package.
PACKAGE_DIR = ''
CREATE_LINKED_EXAMPLE = False

if PACKAGE_DIR:
    root = Path(PACKAGE_DIR).expanduser().resolve()
else:
    file_path = globals().get('__file__')
    if not file_path and getattr(bpy.context.space_data, 'text', None):
        file_path = bpy.context.space_data.text.filepath
    if not file_path:
        raise RuntimeError('Open this script from disk, or set PACKAGE_DIR to the extracted folder.')
    root = Path(bpy.path.abspath(file_path)).resolve().parents[1]

asset_path = root / 'models' / 'SM_BrokenBridge.glb'
if not asset_path.is_file():
    raise FileNotFoundError(str(asset_path))

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(asset_path))
new_objects = [obj for obj in bpy.data.objects if obj not in before]
collection = bpy.data.collections.new('CB_BrokenBridge')
bpy.context.scene.collection.children.link(collection)
for obj in new_objects:
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    collection.objects.link(obj)

meshes = [obj for obj in new_objects if obj.type == 'MESH']
if not meshes:
    raise RuntimeError('GLB importer returned no mesh objects.')
if CREATE_LINKED_EXAMPLE:
    for i in (1, 2):
        for source in meshes:
            duplicate = source.copy()
            duplicate.data = source.data  # Linked mesh; never copy mesh data.
            duplicate.name = f'{source.name}_Shared_{i:02d}'
            collection.objects.link(duplicate)
            duplicate.location.y += i * 7.5

bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
print('Imported actual GLB:', asset_path)
print('New mesh objects:', len(meshes), '| Linked example:', CREATE_LINKED_EXAMPLE)
