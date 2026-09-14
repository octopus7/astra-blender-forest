"""Create real textured bridge geometry and self-contained GLB 2.0 files.
All construction coordinates are right-handed, Z-up, in metres. GLB is Y-up.
Requires numpy. Textures are generated separately by compose_textures.py.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field
import json, math, random, struct
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
R=random.Random(640219)
PI=math.pi
TILES=json.loads((ROOT/'textures/atlas_layout.json').read_text())['tiles_top_left_pixel_coordinates']

def normalize(a):
    a=np.asarray(a,dtype=float); n=np.linalg.norm(a)
    return a/max(n,1e-12)

def frame(a,b):
    x=normalize(np.asarray(b)-a)
    ref=np.array([0.,0.,1.]) if abs(x[2])<.92 else np.array([0.,1.,0.])
    y=normalize(np.cross(ref,x)); z=np.cross(x,y)
    return np.column_stack((x,y,z))

def uv_atlas(key,uv):
    x0,y0,x1,y1=TILES[key]; p=12
    uv=np.asarray(uv,dtype=float)
    # glTF texture coordinates: (0,0) is the image upper-left.
    return np.array([(x0+p+uv[0]*(x1-x0-2*p))/2048,
                     (y1-p-uv[1]*(y1-y0-2*p))/2048])

@dataclass
class Mesh:
    name:str
    vertices:list=field(default_factory=list)
    normals:list=field(default_factory=list)
    uvs:list=field(default_factory=list)
    faces:list=field(default_factory=list)
    components:dict=field(default_factory=dict)

    def face(self,points,key='wood_old',uv=None,normals=None):
        pts=np.asarray(points,dtype=float)
        if len(pts)<3: return
        if uv is None:
            uv=[(.5+.46*math.cos(2*PI*i/len(pts)),.5+.46*math.sin(2*PI*i/len(pts))) for i in range(len(pts))]
        # Fan triangulation is only used on convex faces or star-shaped rings.
        indices=[]
        n=normalize(np.cross(pts[1]-pts[0],pts[2]-pts[0]))
        for i,p in enumerate(pts):
            indices.append(len(self.vertices)); self.vertices.append(p.tolist())
            self.normals.append(n.tolist() if normals is None else normalize(normals[i]).tolist())
            self.uvs.append(uv_atlas(key,uv[i]).tolist())
        for i in range(1,len(indices)-1):
            ids=(indices[0],indices[i],indices[i+1])
            p=pts[[0,i,i+1]]
            if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-10:
                self.faces.append(ids)

    def tri(self,points,key,uv=None,normals=None):self.face(points,key,uv,normals)

    def record(self,kind):self.components[kind]=self.components.get(kind,0)+1

    def append(self,other,offset=(0,0,0)):
        start=len(self.vertices); off=np.asarray(offset)
        self.vertices.extend((np.asarray(other.vertices)+off).tolist())
        self.normals.extend(other.normals); self.uvs.extend(other.uvs)
        self.faces.extend((np.asarray(other.faces)+start).tolist())
        for k,v in other.components.items():self.components[k]=self.components.get(k,0)+v

    def arrays(self,center=(0,0,0)):
        v=np.asarray(self.vertices,dtype=np.float32)-np.asarray(center,dtype=np.float32)
        n=np.asarray(self.normals,dtype=np.float32)
        # RH Z-up -> RH Y-up; determinant +1.
        v=v[:,[0,2,1]]; v[:,2]*=-1
        n=n[:,[0,2,1]]; n[:,2]*=-1
        return v,n,np.asarray(self.uvs,dtype=np.float32),np.asarray(self.faces,dtype=np.uint32)


def tangents(v,n,uv,faces):
    t=np.zeros_like(v);bt=np.zeros_like(v)
    for f in faces:
        a,b,c=v[f];ta,tb,tc=uv[f];e1=b-a;e2=c-a;d1=tb-ta;d2=tc-ta
        det=d1[0]*d2[1]-d1[1]*d2[0]
        if abs(det)<1e-12:continue
        s=(e1*d2[1]-e2*d1[1])/det;z=(e2*d1[0]-e1*d2[0])/det
        for j in f:t[j]+=s;bt[j]+=z
    t-=n*np.sum(n*t,axis=1)[:,None]
    length=np.linalg.norm(t,axis=1)
    bad=length<1e-8
    if bad.any():
        candidates=np.cross(n[bad],np.array([1,0,0]))
        b2=np.linalg.norm(candidates,axis=1)<1e-7
        candidates[b2]=np.cross(n[bad][b2],np.array([0,1,0]))
        t[bad]=candidates
    t/=np.maximum(np.linalg.norm(t,axis=1)[:,None],1e-10)
    w=np.where(np.sum(np.cross(n,t)*bt,axis=1)<0,-1.,1.)
    return np.column_stack([t,w]).astype(np.float32)


def export_glb(path,meshes,centers=None,translations=None,with_textures=True,metadata=None,instances=None):
    """No external URIs: positions, normals, tangents, UVs and all PNGs embedded."""
    centers=centers or [(0,0,0)]*len(meshes)
    translations=translations or [(0,0,0)]*len(meshes)
    tree={'asset':{'version':'2.0','generator':'Cozy Broken Bridge v2 / silhouette-aware component retopology','extras':{'units':'metres','up_axis':'Y','source_up_axis':'Z'}},
          'scene':0,'scenes':[{'name':'Cozy_Broken_Bridge_v2','nodes':[]}],
          'nodes':[],'meshes':[],'materials':[],'accessors':[],'bufferViews':[],'buffers':[]}
    if metadata:tree['asset']['extras'].update(metadata)
    binary=bytearray()
    def view(data,target=None):
        binary.extend(b'\0'*((-len(binary))%4));offset=len(binary);binary.extend(data)
        out={'buffer':0,'byteOffset':offset,'byteLength':len(data)}
        if target:out['target']=target
        tree['bufferViews'].append(out);return len(tree['bufferViews'])-1
    def accessor(a,typ,component,target):
        a=np.ascontiguousarray(a)
        vv=view(a.tobytes(),target)
        d={'bufferView':vv,'componentType':component,'count':len(a),'type':typ}
        if typ=='VEC3':d.update(min=a.min(axis=0).astype(float).tolist(),max=a.max(axis=0).astype(float).tolist())
        if typ=='SCALAR':d.update(min=[int(a.min())],max=[int(a.max())])
        tree['accessors'].append(d);return len(tree['accessors'])-1
    if with_textures:
        tree['samplers']=[{'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071}]
        tree['images']=[];tree['textures']=[]
        for name in ['T_BrokenBridge_BaseColor.png','T_BrokenBridge_Normal_GL.png','T_BrokenBridge_ORM.png']:
            i=len(tree['images']);tree['images'].append({'name':name,'mimeType':'image/png','bufferView':view((ROOT/'textures'/name).read_bytes())})
            tree['textures'].append({'source':i,'sampler':0})
        tree['materials']=[{'name':'M_BrokenBridge_Atlas_PBR','pbrMetallicRoughness':{'baseColorTexture':{'index':0},'baseColorFactor':[1,1,1,1],
            'metallicRoughnessTexture':{'index':2},'metallicFactor':1,'roughnessFactor':1},'normalTexture':{'index':1,'scale':.70},
            'occlusionTexture':{'index':2,'strength':.6},'alphaMode':'OPAQUE','doubleSided':True}]
    else:
        tree['materials']=[{'name':'Collision_Proxy','pbrMetallicRoughness':{'baseColorFactor':[.25,.6,.3,1],'metallicFactor':0,'roughnessFactor':1}}]
    for i,(m,center,translation) in enumerate(zip(meshes,centers,translations)):
        v,n,uv,f=m.arrays(center);t=tangents(v,n,uv,f)
        attr={'POSITION':accessor(v.astype('<f4'),'VEC3',5126,34962),'NORMAL':accessor(n.astype('<f4'),'VEC3',5126,34962),
              'TEXCOORD_0':accessor(uv.astype('<f4'),'VEC2',5126,34962),'TANGENT':accessor(t.astype('<f4'),'VEC4',5126,34962)}
        if len(v)<65536:idx=f.flatten().astype('<u2');ct=5123
        else:idx=f.flatten().astype('<u4');ct=5125
        ia=accessor(idx,'SCALAR',ct,34963)
        tree['meshes'].append({'name':m.name,'primitives':[{'attributes':attr,'indices':ia,'material':0,'mode':4}],
                               'extras':{'triangles':len(f),'components':m.components}})
        x,y,z=translation
        tree['nodes'].append({'name':m.name,'mesh':i,'translation':[x,z,-y]})
        tree['scenes'][0]['nodes'].append(i)
    if instances:
        for name,meshindex,translation in instances:
            x,y,z=translation
            tree['nodes'].append({'name':name,'mesh':meshindex,'translation':[x,z,-y]})
            tree['scenes'][0]['nodes'].append(len(tree['nodes'])-1)
    tree['buffers']=[{'byteLength':len(binary)}]
    jb=json.dumps(tree,separators=(',',':'),ensure_ascii=True).encode('utf8');jb+=b' '*((-len(jb))%4)
    binary.extend(b'\0'*((-len(binary))%4))
    total=12+8+len(jb)+8+len(binary)
    glb=struct.pack('<4sII',b'glTF',2,total)+struct.pack('<I4s',len(jb),b'JSON')+jb+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(glb)
    return {'file':str(path.relative_to(ROOT)),'bytes':len(glb),'triangles_unique':sum(len(m.faces) for m in meshes),'meshes':len(meshes),'nodes':len(tree['nodes']),'embedded_images':len(tree.get('images',[]))}

