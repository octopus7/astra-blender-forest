"""Rebuild the low-poly bridge from component outlines, NOT by importing a GLB.
Runs in Blender's bundled Python (NumPy) or ordinary Python 3.10+ with NumPy.
The recipe fixes major silhouettes, UV domains and the original broken span.
"""
from __future__ import annotations
from pathlib import Path
import json, math, sys
import numpy as np
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from mesh_core import Mesh, normalize, frame, export_glb, ROOT
PI=math.pi

def get(c,index,name,default=None):
    return c['args'][index] if index<len(c['args']) else c['kwargs'].get(name,default)

def tube_low(m,points,radius=.03,key='rope',sides=4,segments=6,taper=1,cap=False):
    p=np.asarray(points,float)
    lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    if lengths[-1]<1e-8:return
    t=np.linspace(0,lengths[-1],segments+1)
    p=np.column_stack([np.interp(t,lengths,p[:,j]) for j in range(3)])
    rings=[]; normals=[];prev=None
    for j,point in enumerate(p):
        d=normalize(p[min(j+1,segments)]-p[max(j-1,0)])
        ref=[0,0,1] if abs(d[2])<.92 else [0,1,0]
        y=normalize(np.cross(d,ref)) if prev is None else normalize(prev-d*np.dot(prev,d))
        z=np.cross(d,y);prev=y
        ns=[math.cos(2*PI*k/sides)*y+math.sin(2*PI*k/sides)*z for k in range(sides)]
        rr=radius*(1+(taper-1)*j/segments)
        rings.append([point+rr*n for n in ns]);normals.append(ns)
    for j in range(segments):
        for k in range(sides):
            kk=(k+1)%sides
            u0=.05+.9*k/sides;u1=.05+.9*(k+1)/sides
            v0=.03+.94*j/segments;v1=.03+.94*(j+1)/segments
            m.face([rings[j][k],rings[j][kk],rings[j+1][kk],rings[j+1][k]],key,
                   [(u0,v0),(u1,v0),(u1,v1),(u0,v1)],
                   [normals[j][k],normals[j][kk],normals[j+1][kk],normals[j+1][k]])
    if cap:
        m.face(rings[0][::-1],key);m.face(rings[-1],key)

def timber_low(m,c,idx):
    rings=np.asarray(c['rings']);a=rings[0];b=rings[-1]
    bs=get(c,5,'broken_start',False);be=get(c,6,'broken_end',False)
    key=get(c,4,'key','wood_old')
    # Keep original eight-point fracture rings. Remove interior lengthwise loops.
    u0=.015+(idx*.137)% .34;u1=u0+.58
    for i in range(8):
        k=(i+1)%8
        m.face([a[i],a[k],b[k],b[i]],key,[(u0,.02),(u1,.02),(u1,.98),(u0,.98)])
    # Preserve the original recessed fracture center, rather than sealing with a flat face.
    for j,ring,broken,rev in [(0,a,bs,True),(1,b,be,False)]:
        order=list(range(8))
        if rev:order.reverse()
        verts=ring[order]
        uv=[(.5+.47*math.cos(2*PI*i/8),.5+.47*math.sin(2*PI*i/8)) for i in order]
        if broken:
            for k in range(8):m.face([c['centers'][j],verts[k],verts[(k+1)%8]],'rot_end',[(.5,.5),uv[k],uv[(k+1)%8]])
        else:m.face(verts,'endgrain',uv)
    m.record('timber')

def splinter_low(m,c):
    base=np.asarray(c['base']);tip=np.asarray(c['tip']);key=get(c,4,'key','wood_rot')
    m.face(base[::-1],'rot_end',[(0,0),(1,0),(1,1),(0,1)])
    for i in range(4):m.face([base[i],base[(i+1)%4],tip],key,[(.08,0),(.8,0),(.45,1)])
    m.record('splinter')

def moss_low(m,c):
    edge=np.asarray(c['edge']);inds=[0,2,4,5];top=np.asarray(c['top'])
    # Only a shallow silhouette cap remains; surface microdetail comes from the atlas.
    top=edge.mean(axis=0)+(top-edge.mean(axis=0))*.45
    for j,i in enumerate(inds):
        k=inds[(j+1)%len(inds)]
        m.face([edge[i],edge[k],top],'moss',[(.5+.46*math.cos(2*PI*i/7),.5+.46*math.sin(2*PI*i/7)),(.5+.46*math.cos(2*PI*k/7),.5+.46*math.sin(2*PI*k/7)),(.5,.5)])
    m.record('moss_patch')

def leaf_low(m,c):
    a=np.asarray(get(c,0,'start'));b=np.asarray(get(c,1,'end'));w=get(c,2,'width',.10)
    side=normalize(np.cross(b-a,[0,1,.3]))*w;mid=a+(b-a)*.47
    m.face([a,mid-side*.52,b,mid+side*.52],'leaf',[(.5,.04),(.07,.5),(.5,.96),(.93,.5)])
    m.record('ivy_leaf')

def rope_low(m,c):
    primary=c['children'][0];points=get(primary,0,'points');length=np.linalg.norm(np.asarray(points[-1])-points[0])
    tube_low(m,points,get(primary,1,'radius',.039),'rope',4,8 if length>1 else 4)
    # Frayed fibers are represented by the rope map and one short silhouette ribbon.
    if get(c,3,'fray',False):
        a=np.asarray(points[-1]);b=a+[.04,-.025,-.14]
        m.face([a+[-.015,0,0],a+[.015,0,0],b],'rope',[(.1,.05),(.85,.05),(.47,.95)])
    m.record('rope_span')

def binding_low(m,c):
    for i,t in enumerate(c['children'][:2]):
        tube_low(m,get(t,0,'points'),get(t,1,'radius',.032),'rope',4 if i==0 else 3,12 if i==0 else 2,get(t,4,'taper',1))
    m.record('rope_binding')

def vine_low(m,c):
    for child in c['children']:
        if child['kind']=='tube':tube_low(m,get(child,0,'points'),get(child,1,'radius',.012),'leaf',3,4,.45)
        elif child['kind']=='leaf':leaf_low(m,child)
    m.record('ivy_vine')

def drape_low(m,c):
    s=np.asarray(get(c,0,'start'));length=get(c,1,'length',.48);width=get(c,2,'width',.1)
    left=[];right=[];n=2
    for i in range(n+1):
        t=i/n;p=s+[.02*math.sin(t*PI*1.5),.025*math.sin(t*3*PI),-length*t];w=width*(1-t*.65)
        left.append(p+[-w/2,0,0]);right.append(p+[w/2,0,0])
    for i in range(n):m.face([left[i],right[i],right[i+1],left[i+1]],'moss',[(.15,1-i/n),(.8,1-i/n),(.8,1-(i+1)/n),(.15,1-(i+1)/n)])
    m.record('hanging_moss')

def mushroom_low(m,c):
    base=np.asarray(get(c,0,'base'));r=get(c,1,'r',.2);h=get(c,2,'h',.28);shelf=get(c,3,'shelf',False);heading=get(c,4,'heading',-PI/2)
    if shelf:
        seg=6;center=base;f=np.array([math.cos(heading),math.sin(heading),0]);s=np.array([-math.sin(heading),math.cos(heading),0])
        angs=np.linspace(-PI*.51,PI*.51,seg+1)
        def pt(rr,a,z):return center+f*(rr*r*math.cos(a))+s*(rr*r*math.sin(a))+[0,0,z*r]
    else:
        seg=9;center=base+[r*.08,-r*.06,h];angs=np.linspace(0,2*PI,seg+1)
        tube_low(m,[base,center],max(.022,r*.18),'gills',5,1,.76,True)
        def pt(rr,a,z):return center+np.array([rr*r*math.cos(a),rr*r*math.sin(a),z*r])
    def uv(rr,a):return (.5+.475*rr*math.cos(a),.5+.475*rr*math.sin(a))
    rings=[(0,.34),(.66,.24),(1,0),(0,-.10)]
    for k in range(3):
        rr0,z0=rings[k];rr1,z1=rings[k+1]
        for j in range(seg):
            a0,a1=angs[j:j+2];p=[pt(rr0,a0,z0),pt(rr1,a0,z1),pt(rr1,a1,z1),pt(rr0,a1,z0)];u=[uv(rr0,a0),uv(rr1,a0),uv(rr1,a1),uv(rr0,a1)]
            if rr0==0:p=p[:3];u=u[:3]
            elif rr1==0:p=[p[0],p[1],p[3]];u=[u[0],u[1],u[3]]
            m.face(p,'cap' if k<2 else 'gills',u)
    if shelf:
        for a,rev in [(angs[0],False),(angs[-1],True)]:
            p=[pt(rr,a,z) for rr,z in rings]
            if rev:p.reverse()
            m.face(p,'gills')
    m.record('shelf_fungus' if shelf else 'mushroom')

def rock_low(m,c):
    rings=np.asarray(c['rings']);inds=[0,1,3,4,5,7]
    vs=np.array([rings[0][inds],rings[-1][inds]])
    old=rings.reshape((-1,3));lo=old.min(axis=0);hi=old.max(axis=0)
    flat=vs.reshape((-1,3));mn=flat.min(axis=0);mx=flat.max(axis=0)
    vs=lo+(vs-mn)/np.maximum(mx-mn,1e-9)*(hi-lo)
    for i in range(6):
        j=(i+1)%6;m.face([vs[0][i],vs[0][j],vs[1][j],vs[1][i]],'stone',[(.06,.05),(.94,.05),(.94,.95),(.06,.95)])
    m.face(vs[0][::-1],'stone');m.face(vs[1],'stone');m.record('foundation_stone')

def nail_low(m,c):
    p=np.asarray(get(c,0,'p'));n=normalize(get(c,1,'axis',[0,0,1]));r=get(c,2,'r',.025)
    x=normalize(np.cross(n,[0,1,0] if abs(n[1])<.92 else [1,0,0]));y=np.cross(n,x);p=p+n*.012
    m.face([p-x*r-y*r,p+x*r-y*r,p+x*r+y*r,p-x*r+y*r],'metal',[(.1,.1),(.9,.1),(.9,.9),(.1,.9)]);m.record('rusted_nail')

DISPATCH={'timber':timber_low,'splinter':splinter_low,'moss_blob':moss_low,'rope':rope_low,'binding':binding_low,'vine':vine_low,'drape':drape_low,'mushroom':mushroom_low,'rock':rock_low,'nail':nail_low}

def generate_bridge_meshes():
    recipe=json.loads((ROOT/'data/bridge_recipe.json').read_text(encoding='utf8'))
    names=['SM_BrokenBridge_Left','SM_BrokenBridge_Right','SM_BrokenBridge_Debris'];parts={n:Mesh(n+'_v2') for n in names}
    counts={}
    for i,c in enumerate(recipe['components']):
        m=parts[c['part']];before=len(m.faces)
        if c['kind']=='timber':timber_low(m,c,i)
        else:DISPATCH[c['kind']](m,c)
        counts[c['kind']]=counts.get(c['kind'],0)+len(m.faces)-before
    for m in parts.values():
        # Keep explicit shading normals consistent with triangle winding at tight bends.
        v=np.asarray(m.vertices);f=np.asarray(m.faces);n=np.asarray(m.normals)
        face_n=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
        bad=np.sum(face_n*n[f].mean(axis=1),axis=1)<0
        f[bad]=f[bad][:,[0,2,1]];m.faces=f.tolist()
        m.vertices=(v-recipe['source_pivot']).tolist()
    return list(parts.values()),counts

def build_files():
    parts,counts=generate_bridge_meshes();combined=Mesh('SM_BrokenBridge_v2')
    for p in parts:combined.append(p)
    meta={'continuous_walkable_span':False,'source_triangles':27016,'target_fraction':.25,'water_in_asset':False,'version':2}
    files=[export_glb(ROOT/'models/SM_BrokenBridge_v2.glb',[combined],metadata=meta)]
    centers=[(-4,0,0),(4,0,0),(0,0,0)]
    files.append(export_glb(ROOT/'modular/BrokenBridge_Modular_v2.glb',parts,centers=centers,translations=centers,metadata=meta))
    files.append(export_glb(ROOT/'modular/Reuse_3_Instances_v2.glb',[combined],metadata=meta,instances=[('BrokenBridge_02',0,(0,7.5,0)),('BrokenBridge_03',0,(0,15,0))]))
    v=np.array(combined.vertices);f=np.array(combined.faces);stats={'version':2,'source_triangles':27016,'triangles':len(f),'fraction_of_v1':len(f)/27016,'reduction_percent':100*(1-len(f)/27016),'vertex_records':len(v),'bounds_z_up_m':[v.min(axis=0).tolist(),v.max(axis=0).tolist()],'dimensions_m':np.ptp(v,axis=0).tolist(),'triangles_by_component':counts,'material_count':1,'texture_resolution':[2048,2048],'part_triangles':{m.name:len(m.faces) for m in parts},'clear_gap_x_m':[float(np.array(parts[0].vertices)[:,0].max()),float(np.array(parts[1].vertices)[:,0].min())],'files':files}
    stats['clear_gap_width_m']=stats['clear_gap_x_m'][1]-stats['clear_gap_x_m'][0]
    (ROOT/'validation/model_stats_v2.json').write_text(json.dumps(stats,indent=2),encoding='utf8')
    print(json.dumps(stats,indent=2));return stats
if __name__=='__main__':build_files()
