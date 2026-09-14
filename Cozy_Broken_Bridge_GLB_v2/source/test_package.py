"""Offline package tests; does NOT import bpy or claim Blender runtime validation."""
from pathlib import Path
import sys,json,ast,collections
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from generate_bridge_v2 import generate_bridge_meshes
from scene_geometry import make_environment,make_decoration_prototypes,decoration_instances

def main():
    tests=[]
    def check(label,condition):
        assert bool(condition),label
        tests.append({'check':label,'status':'PASS'})
    for p in ROOT.rglob('*.py'):
        ast.parse(p.read_text(encoding='utf8'),filename=str(p));tests.append({'check':'Python syntax: '+str(p.relative_to(ROOT)),'status':'PASS'})
    parts,counts=generate_bridge_meshes();again,_=generate_bridge_meshes()
    check('Exactly 6732 bridge triangles',sum(len(p.faces) for p in parts)==6732)
    check('Approximately one quarter of 27016 triangles',.245<6732/27016<=.25)
    check('Deterministic geometry',all(np.array_equal(a.vertices,b.vertices) and np.array_equal(a.faces,b.faces) for a,b in zip(parts,again)))
    for m in parts:
        v=np.asarray(m.vertices);f=np.asarray(m.faces);n=np.asarray(m.normals);uv=np.asarray(m.uvs)
        check(m.name+' finite data',all(np.isfinite(a).all() for a in [v,n,uv]))
        check(m.name+' nonempty faces, valid indices',len(f)>0 and f.min()>=0 and f.max()<len(v))
        fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
        check(m.name+' positive triangle area',np.linalg.norm(fn,axis=1).min()>1e-10)
        check(m.name+' consistent normals',np.allclose(np.linalg.norm(n,axis=1),1,atol=1e-6) and np.all((fn*n[f].mean(axis=1)).sum(axis=1)>=-1e-10))
        check(m.name+' inset UV bounds',uv.min()>0 and uv.max()<1)
    check('Clear gap preserved',abs((np.asarray(parts[1].vertices)[:,0].min()-np.asarray(parts[0].vertices)[:,0].max())-2.338804886)<1e-6)
    check('Debris remains below walking height',np.asarray(parts[2].vertices)[:,2].max()<-.85)
    for name in ['T_BrokenBridge_BaseColor.png','T_BrokenBridge_Normal_GL.png','T_BrokenBridge_Normal_DX.png','T_BrokenBridge_ORM.png']:
        im=Image.open(ROOT/'textures'/name);check('2K texture: '+name,im.size==(2048,2048));im.verify()
    cfg=json.loads((ROOT/'scene_config.json').read_text());env=make_environment(cfg);water=next(s for s in env if s['material']=='water')
    edges=collections.Counter(tuple(sorted((f[i],f[(i+1)%3]))) for f in water['faces'] for i in range(3))
    check('Water is a closed manifold volume',all(v==2 for v in edges.values()))
    check('Water has physical thickness',cfg['water_bottom_m']<cfg['water_level_m'])
    check('Riverbed inside water volume',min(np.asarray(s['vertices'])[:,2].min() for s in env if s['material']=='bed')>cfg['water_bottom_m'])
    check('Geometry and material names align',all(s['material'] in ['bank','bed','water'] for s in env))
    protos={s['name'] for s in make_decoration_prototypes()}
    check('Display decorations reuse three prototypes',len(protos)==3 and all(t[0] in protos for t in decoration_instances(cfg)))
    check('Defaults keep bridge one mesh',cfg['build_modular_parts'] is False)
    check('Textures are packed by Blender builder',cfg['pack_textures'] is True)
    report={'status':'PASS','checks':tests,'count':len(tests),'Blender_runtime_tested':False,'Unreal_runtime_tested':False,'Blender_render_tested':False,'scope':'Python syntax + actual geometry/material-file inputs. Does not execute Blender APIs.','environment_triangles_unique':sum(len(s['faces']) for s in env)+sum(len(s['faces']) for s in make_decoration_prototypes()),'environment_instances':len(decoration_instances(cfg))}
    (ROOT/'validation/source_and_geometry_tests.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('PASS',len(tests),'offline checks. Blender runtime NOT tested.')
if __name__=='__main__':main()
