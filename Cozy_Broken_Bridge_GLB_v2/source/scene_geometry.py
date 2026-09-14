"""Small river display geometry, separate from the 6,732-triangle bridge asset.
Pure Python/NumPy, shared by the Blender builder and independent VTK preview.
"""
from __future__ import annotations
import math,random
import numpy as np

def mesh(name,vertices,faces,material,shore=None):
    return {'name':name,'vertices':np.asarray(vertices,float),'faces':faces,'material':material,'shore':shore}

def bank_edge(y):return 4.25+.20*math.sin(y*.48)+.12*math.sin(y*1.32)

def make_environment(config):
    out=[];half=config['river_length_m']/2;nx=10;ny=28
    for side in (-1,1):
        vs=[];faces=[];shore=[]
        for j in range(ny+1):
            y=-half+2*half*j/ny
            for i in range(nx+1):
                u=i/nx;x=side*(bank_edge(y)+u*6.5);s=min(1,u/.2);s=s*s*(3-2*s)
                z=-.98+.84*s+.10*math.sin(y*.52+x*.32)*min(1,u*2)
                vs.append((x,y,z));shore.append(u)
        for j in range(ny):
            for i in range(nx):
                a=j*(nx+1)+i;b=a+1;c=b+nx+1;d=a+nx+1
                if side>0:faces.extend([(a,b,c),(a,c,d)])
                else:faces.extend([(a,c,b),(a,d,c)])
        out.append(mesh('Riverbank_West' if side<0 else 'Riverbank_East',vs,faces,'bank',shore))
    vs=[];faces=[];nx=12;ny=24
    for j in range(ny+1):
        y=-half+2*half*j/ny
        for i in range(nx+1):
            x=-6+12*i/nx;z=-2.03+.095*math.sin(x*1.5+y*.72)+.055*math.sin(y*2.4-x*.42)
            vs.append((x,y,z))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=b+nx+1;d=a+nx+1;faces.extend([(a,b,c),(a,c,d)])
    out.append(mesh('Riverbed',vs,faces,'bed'))
    x=config['river_half_width_m'];y=half;z0=config['water_bottom_m'];z1=config['water_level_m']
    v=[(-x,-y,z0),(x,-y,z0),(x,y,z0),(-x,y,z0),(-x,-y,z1),(x,-y,z1),(x,y,z1),(-x,y,z1)]
    faces=[]
    for a,b,c,d in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:faces.extend([(a,b,c),(a,c,d)])
    out.append(mesh('River_Water_Volume',v,faces,'water'))
    return out

def make_decoration_prototypes():
    out=[]
    # A single low-poly bank stone, shared by every instance.
    vs=[];n=7
    for z,r in [(-.18,.64),(.02,1),(.29,.69)]:
        for j in range(n):
            a=2*math.pi*j/n;vs.append((math.cos(a)*r*.52,math.sin(a)*r*.43,z+.025*math.sin(j*3)))
    fs=[]
    for k in range(2):
        for i in range(n):
            a=k*n+i;b=k*n+(i+1)%n;c=b+n;d=a+n;fs.extend([(a,b,c),(a,c,d)])
    for i in range(1,n-1):fs.extend([(0,i+1,i),(2*n,2*n+i,2*n+i+1)])
    out.append(mesh('Stone_Prototype',vs,fs,'shore_stone'))
    # Notched leaf; no fully modeled veins or underside.
    vs=[(0,0,.003)]
    for i in range(10):
        a=.22+(2*math.pi-.44)*i/9;vs.append((.30*math.cos(a),.25*math.sin(a),0))
    fs=[(0,i,i+1) for i in range(1,10)]
    out.append(mesh('LilyPad_Prototype',vs,fs,'lily'))
    # Curved triangular reed blades; all clusters share one mesh.
    vs=[];fs=[];r=random.Random(733)
    for i in range(9):
        a=r.random()*math.tau;h=r.uniform(.28,.69);rad=r.uniform(.01,.19);x=math.cos(a)*rad;y=math.sin(a)*rad;s=len(vs)
        p=np.array([x,y,0]);d=np.array([math.cos(a),math.sin(a),0]);w=np.array([-math.sin(a),math.cos(a),0])*.022
        vs.extend([p-w,p+w,p+d*.06+[0,0,h*.63]-w*.55,p+d*.06+[0,0,h*.63]+w*.55,p+d*.2+[0,0,h]])
        fs.extend([(s,s+1,s+3),(s,s+3,s+2),(s+2,s+3,s+4)])
    out.append(mesh('Reeds_Prototype',vs,fs,'reed'))
    return out

def decoration_instances(config):
    r=random.Random(config['seed']);instances=[];half=config['river_length_m']/2
    for side in (-1,1):
        for j in range(12):
            y=-half+1+j*(2*half-2)/11+r.uniform(-.2,.2)
            if abs(y)<2.2:continue
            x=side*(bank_edge(y)+r.uniform(.15,.46))
            instances.append(('Stone_Prototype',(x,y,-.60),(0,0,r.random()*math.tau),(r.uniform(.8,1.3),r.uniform(.8,1.3),r.uniform(.7,1.3))))
        for j in range(6):
            y=r.uniform(-half+1,half-1)
            if abs(y)<2.3:y+=3.1
            instances.append(('Reeds_Prototype',(side*(bank_edge(y)-.08),y,config['water_level_m']-.015),(0,0,r.random()*math.tau),(1,1,r.uniform(.8,1.25))))
    for j in range(14):
        x=r.choice((-1,1))*r.uniform(2.9,4.1);y=r.uniform(-half+1,half-1)
        if abs(y)<2.4:y+=3.3
        s=r.uniform(.62,1.2)
        instances.append(('LilyPad_Prototype',(x,y,config['water_level_m']+.014),(0,0,r.random()*math.tau),(s,s,1)))
    return instances
