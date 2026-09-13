import unittest,sys,random,itertools,json
from pathlib import Path
from math import pi,sqrt
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cozy_forest_core as core
import cozy_transforms as tr
import cozy_manifest as manifest
from cozy_landmarks import all_new_assets
matrix_for=core.matrix_for

def quat_rotate(q,v):
    xyz=q[:3];uv=core.cross(xyz,v);uuv=core.cross(xyz,uv)
    return core.add(v,core.add(core.mul(uv,2*q[3]),core.mul(uuv,2)))

TEST_CONFIG=dict(terrain_resolution=60,tree_count=150,ground_detail_count=250,
    meadow_flower_count=40,shore_rock_count=30,shore_plant_count=25,lily_count=25)

class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world=core.build_world(TEST_CONFIG)
        cls.layout=core.Layout(cls.world.config)
    def test_geometry_valid(self):self.assertEqual(core.validate_world(self.world),[])
    def test_new_assets_are_valid(self):
        w=core.World(core.validate_config(TEST_CONFIG))
        for mesh in all_new_assets():w.register(mesh)
        self.assertEqual(core.validate_world(w),[])
    def test_map_extent_300(self):
        points=[]
        for i in self.world.instances:
            m=self.world.assets[i['asset_id']]
            if m.category=='Terrain':points.extend(core.add(v,i['location']) for v in m.vertices)
        self.assertEqual([min(p[k] for p in points) for k in (0,1)],[-150,-150])
        self.assertEqual([max(p[k] for p in points) for k in (0,1)],[150,150])
    def test_36_terrain_cells(self):
        self.assertEqual(sum(m.category=='Terrain' for m in self.world.assets.values()),36)
    def test_terrain_triangle_count(self):
        self.assertEqual(sum(len(m.faces) for m in self.world.assets.values() if m.category=='Terrain'),2*60**2)
    def test_12_landmark_regions(self):self.assertEqual(len(self.world.points_of_interest),12)
    def test_lakes_have_water(self):
        self.assertEqual(len(self.layout.lakes),3)
        for lake in self.layout.lakes:self.assertLess(self.layout.water_distance(*lake['center']),-4)
    def test_landmark_centres_are_dry(self):
        for p in self.world.points_of_interest:self.assertGreater(self.layout.water_distance(p['x'],p['y']),0,p['id'])
    def test_landmarks_connected_to_trails(self):
        for p in self.world.points_of_interest:self.assertLess(self.layout.path_distance(p['x'],p['y']),2,p['id'])
    def test_seed_determinism(self):
        second=core.build_world(TEST_CONFIG)
        self.assertEqual(core.geometry_digest(self.world),core.geometry_digest(second))
    def test_different_seed_changes_placements(self):
        self.assertNotEqual(self.world.instances,core.build_world(dict(TEST_CONFIG,seed=99)).instances)
    def test_reusable_props_no_per_instance_vertices(self):
        for i in self.world.instances:
            self.assertNotIn('vertices',i);self.assertNotIn('faces',i)
            self.assertIn(i['asset_id'],self.world.assets)
        self.assertGreater(self.world.stats()['instance_counts']['CF_LanternPost'],20)
    def test_forest_tree_count(self):self.assertEqual(self.world.stats()['forest_trees'],150)
    def test_forest_avoids_water_paths_clearings(self):
        for i in self.world.instances:
            if i['source']!='forest_tree':continue
            x,y,z=i['location']
            self.assertGreaterEqual(self.layout.water_distance(x,y),3.5)
            self.assertGreaterEqual(self.layout.path_distance(x,y),self.layout.path_half_width(x,y)+2)
            self.assertFalse(self.layout.reserved(x,y,1.9))
    def test_tree_min_spacing(self):
        g=core.SpatialHash(3.15)
        for i in self.world.instances:
            if i['source']!='forest_tree':continue
            x,y=i['location'][:2];self.assertTrue(g.clear(x,y,3.15));g.add(x,y)
    def test_orchard_trees_avoid_paths(self):
        for i in self.world.instances:
            if i['asset_id']=='CF_Tree_Apple':self.assertGreaterEqual(self.layout.path_distance(*i['location'][:2]),3)
    def test_terrain_tile_seams_exact(self):
        seen={}
        for i in self.world.instances:
            mesh=self.world.assets[i['asset_id']]
            if mesh.category!='Terrain':continue
            for v in mesh.vertices:
                p=core.add(v,i['location']);key=(round(p[0],7),round(p[1],7))
                if key in seen:self.assertAlmostEqual(seen[key],p[2],places=9)
                else:seen[key]=p[2]
    def test_water_level_and_no_duplicate_faces(self):
        seen=set()
        for i in self.world.instances:
            mesh=self.world.assets[i['asset_id']]
            if mesh.category!='Water':continue
            for tri in mesh.faces:
                pts=[core.add(mesh.vertices[j],i['location']) for j in tri]
                for p in pts:self.assertAlmostEqual(p[2],.004)
                key=tuple(sorted(tuple(round(v,7) for v in p) for p in pts))
                self.assertNotIn(key,seen);seen.add(key)
    def test_all_cell_assignments(self):
        for i in self.world.instances:self.assertEqual(i['cell_id'],manifest.cell_id_for_position(*i['location'][:2],300,6))
    def test_cell_bounds_and_counts(self):
        cells=manifest.make_cell_records(self.world.instances,300,6)
        self.assertEqual(len(cells),36)
        self.assertEqual(sum(c['instance_count'] for c in cells),len(self.world.instances))
        for c in cells:
            x0,y0,x1,y1=c['bounds_xy_m'];self.assertEqual((x1-x0,y1-y0),(50,50))
    def test_hism_grouping_cell_plus_asset(self):
        groups=manifest.group_instances(self.world.instances)
        self.assertEqual(sum(len(x) for x in groups.values()),len(self.world.instances))
        for (cell,asset),rows in groups.items():
            self.assertTrue(all(r['cell_id']==cell and r['asset_id']==asset for r in rows))
    def test_manifest_rejects_outside_pivots(self):
        for x,y in [(151,0),(0,-151),(float('nan'),0)]:
            with self.assertRaises(ValueError):manifest.cell_id_for_position(x,y,300,6)
    def test_no_structures_when_disabled(self):
        cfg=dict(TEST_CONFIG,include_cabin=False,include_well=False,include_bridge=False,include_dock=False,include_landmarks=False)
        w=core.build_world(cfg)
        self.assertFalse(any(m.category in ('Structures','Landmarks','Camping','Village','Garden','Ruins') for m in w.assets.values()))
    def test_config_validation(self):
        for cfg in ({'map_size_m':30},{'terrain_resolution':481},{'tree_count':-1},{'tree_min_spacing_m':1},{'bad':1}):
            with self.assertRaises(ValueError):core.validate_config(cfg)
    def test_light_preset_valid(self):
        cfg=json.loads((Path(__file__).resolve().parents[1]/'presets'/'cozy_config_light.json').read_text())
        self.assertEqual(core.validate_config(cfg)['map_size_m'],300)
    def test_positive_scale_and_finite_matrices(self):
        for i in self.world.instances:
            out=tr.convert_transform(matrix_for(i['location'],i['rotation_euler_xyz'],i['scale']),tr.IDENTITY3)
            self.assertGreater(min(out['scale']),0)

class TransformTests(unittest.TestCase):
    def test_basis_calibration_rejects_wrong_scale(self):
        with self.assertRaises(ValueError):tr.basis_from_probe_centers([[1,0,0],[0,-1,0],[0,0,1]])
    def test_all_48_axis_conversions_with_nonuniform_scale(self):
        rng=random.Random(9283)
        for perm in itertools.permutations(range(3)):
            for signs in itertools.product((-1,1),repeat=3):
                centers=[]
                for i in range(3):
                    c=[0.,0.,0.];c[perm[i]]=signs[i]*100.;centers.append(c)
                B=tr.basis_from_probe_centers(centers)
                for _ in range(5):
                    loc=[rng.uniform(-30,30) for _ in range(3)]
                    rot=[rng.uniform(-pi,pi) for _ in range(3)]
                    scale=[rng.uniform(.3,2) for _ in range(3)]
                    flat=matrix_for(loc,rot,scale); out=tr.convert_transform(flat,B)
                    p=[rng.uniform(-3,3) for _ in range(3)]
                    expected=tr.mv(B,core.transformed(p,loc,rot,scale))
                    imported=tr.mv(B,p)
                    scaled=[imported[i]*out['scale'][i] for i in range(3)]
                    actual=core.add(quat_rotate(out['rotation_xyzw'],scaled),out['translation'])
                    for a,b in zip(expected,actual):self.assertAlmostEqual(a,b,places=7)
    def test_reject_shear_negative_scale_and_nonfinite(self):
        neg=matrix_for((0,0,0),(0,0,0),(-1,1,1))
        shear=matrix_for((0,0,0),(0,0,0),(1,1,1));shear[1]=.3
        bad=matrix_for((0,0,0),(0,0,0),(1,1,1));bad[3]=float('nan')
        for matrix in (neg,shear,bad):
            with self.assertRaises(ValueError):tr.convert_transform(matrix,tr.IDENTITY3)
    def test_all_default_scene_transforms(self):
        B=[[100,0,0],[0,-100,0],[0,0,100]]
        for instance in GeometryTests.world.instances:
            flat=matrix_for(instance['location'],instance['rotation_euler_xyz'],instance['scale'])
            out=tr.convert_transform(flat,B)
            self.assertTrue(all(x>0 for x in out['scale']))


if __name__=='__main__':unittest.main()
