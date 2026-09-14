"""Structural / numeric GLB validation and independent Trimesh re-import.
This is a project-specific validator, not the Khronos glTF Validator.
"""
from pathlib import Path
import struct,json,io,hashlib
import numpy as np
from PIL import Image
import trimesh
ROOT=Path(__file__).resolve().parents[1]
TYPE={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
DTYPE={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}

def parse(p):
    data=p.read_bytes();magic,ver,total=struct.unpack_from('<4sII',data)
    assert magic==b'glTF' and ver==2 and total==len(data)
    n,typ=struct.unpack_from('<I4s',data,12);assert typ==b'JSON' and n%4==0
    tree=json.loads(data[20:20+n]);off=20+n
    size,typ=struct.unpack_from('<I4s',data,off);assert typ==b'BIN\0'
    binary=data[off+8:];assert size==len(binary) and size%4==0
    assert tree['asset']['version']=='2.0'
    assert 'uri' not in tree['buffers'][0]
    return tree,binary

def accessor(tree,binbuf,index):
    a=tree['accessors'][index];bv=tree['bufferViews'][a['bufferView']]
    dt=np.dtype(DTYPE[a['componentType']]);num=TYPE[a['type']]
    off=bv.get('byteOffset',0)+a.get('byteOffset',0)
    assert off%dt.itemsize==0
    assert a['count']*num*dt.itemsize+a.get('byteOffset',0)<=bv['byteLength']
    arr=np.frombuffer(binbuf,dtype=dt,count=a['count']*num,offset=off).reshape(a['count'],num)
    assert np.isfinite(arr).all()
    if 'min' in a:assert np.allclose(arr.min(axis=0),a['min'],atol=1e-6)
    if 'max' in a:assert np.allclose(arr.max(axis=0),a['max'],atol=1e-6)
    return arr

def validate(p):
    tree,binary=parse(p)
    checks=['GLB header and chunk lengths','Embedded buffer, no external URI']
    for bv in tree['bufferViews']:
        assert bv.get('byteOffset',0)%4==0
        assert bv.get('byteOffset',0)+bv['byteLength']<=tree['buffers'][0]['byteLength']<=len(binary)
    checks.append('Buffer bounds and four-byte alignment')
    triangles=0;verts=0
    for mesh in tree['meshes']:
        for prim in mesh['primitives']:
            assert prim.get('mode',4)==4
            attr=prim['attributes'];v=accessor(tree,binary,attr['POSITION']);n=accessor(tree,binary,attr['NORMAL'])
            uv=accessor(tree,binary,attr['TEXCOORD_0']);t=accessor(tree,binary,attr['TANGENT'])
            f=accessor(tree,binary,prim['indices']).flatten().reshape(-1,3)
            assert len(v)==len(n)==len(uv)==len(t)
            assert len(f)>0 and f.min()>=0 and f.max()<len(v)
            assert np.max(np.abs(np.linalg.norm(n,axis=1)-1))<2e-5
            assert np.max(np.abs(np.linalg.norm(t[:,:3],axis=1)-1))<2e-5
            assert np.max(np.abs(np.sum(n*t[:,:3],axis=1)))<2e-5
            assert np.all(np.isin(t[:,3],[-1,1]))
            area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)/2
            assert area.min()>1e-11,(p,area.min())
            assert uv.min()>=0 and uv.max()<=1
            triangles+=len(f);verts+=len(v)
    checks.extend(['Finite positions and accessor min/max','Index and attribute counts','Non-degenerate triangles',
                   'Unit normals','Unit orthogonal tangents and valid handedness','UV bounds'])
    images=[]
    for im in tree.get('images',[]):
        assert 'uri' not in im
        bv=tree['bufferViews'][im['bufferView']];off=bv.get('byteOffset',0);raw=binary[off:off+bv['byteLength']]
        img=Image.open(io.BytesIO(raw));assert img.size==(2048,2048);img.verify()
        images.append({'name':im['name'],'resolution':[2048,2048],'sha256':hashlib.sha256(raw).hexdigest()})
    checks.append('Embedded PNG decoding and 2K image size')
    scene=trimesh.load_scene(p,process=False)
    assert len(scene.geometry)==len(tree['meshes']),(p,len(scene.geometry),len(tree['meshes']))
    assert np.isfinite(scene.bounds).all()
    checks.append('Independent Trimesh GLB re-import')
    return {'file':str(p.relative_to(ROOT)),'status':'PASS','checks':checks,'triangles_unique':triangles,'vertices':verts,
            'mesh_count':len(tree['meshes']),'node_count':len(tree['nodes']),'images':images,'bounds_y_up_m':scene.bounds.tolist()}

def main():
    reports=[validate(p) for p in sorted(ROOT.rglob('*.glb'))]
    byname={Path(r['file']).name:r for r in reports}
    assert np.allclose(byname['SM_BrokenBridge_v2.glb']['bounds_y_up_m'],byname['BrokenBridge_Modular_v2.glb']['bounds_y_up_m'],atol=1e-5)
    assert byname['Reuse_3_Instances_v2.glb']['mesh_count']==1
    assert byname['Reuse_3_Instances_v2.glb']['node_count']==3
    tree,binary=parse(ROOT/'collision/Deck_Proxies.glb')
    for m in tree['meshes']:
        p=accessor(tree,binary,m['primitives'][0]['attributes']['POSITION'])
        assert np.all(p[:,0]<-2.6) or np.all(p[:,0]>2.6)
    data={'status':'PASS','validator':'Project-specific structural/numeric tests + Trimesh '+trimesh.__version__,
          'not_khronos_validator':True,'files_checked':len(reports),'per_file_check_count':len(reports[0]['checks']),
          'assembly_checks':['Modular assembly bounds equal complete asset','Instance example has 1 mesh referenced by 3 nodes','Left/right collision proxies leave the centre open'],
          'files':reports,'Blender_runtime_tested':False,'Unreal_runtime_tested':False}
    (ROOT/'validation/validation_report_v2.json').write_text(json.dumps(data,indent=2),encoding='utf8')
    print('PASS:',len(reports),'GLBs,',len(reports[0]['checks']),'checks per file, 3 assembly checks.');
    print('Trimesh re-import succeeded for every GLB.')
if __name__=='__main__':main()
