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


def timber(m,a,b,w=.25,t=.18,key='wood_old',broken_start=False,broken_end=False,twist=0):
    """Solid chamfered timber. Broken ring has a jagged, non-planar fracture cap."""
    a=np.asarray(a,dtype=float); b=np.asarray(b,dtype=float)
    length=np.linalg.norm(b-a); f=frame(a,b)
    if twist:
        c,s=math.cos(twist),math.sin(twist)
        f=f@np.array([[1,0,0],[0,c,-s],[0,s,c]])
    bevel=min(w,t)*.16
    profile=np.array([(w/2-bevel,t/2),(-w/2+bevel,t/2),(-w/2,t/2-bevel),(-w/2,-t/2+bevel),(-w/2+bevel,-t/2),(w/2-bevel,-t/2),(w/2,-t/2+bevel),(w/2,t/2-bevel)])
    rings=[]; local=[]
    for j,q in enumerate((0,.26,.75,1)):
        ring=[]; loc=[]
        for i,(y,z) in enumerate(profile):
            x=q*length
            if j==0 and broken_start:x+=R.uniform(0,min(.43,length*.24))
            if j==3 and broken_end:x-=R.uniform(0,min(.56,length*.27))
            zz=z+math.sin(q*PI)*R.uniform(-.022,.022)
            yy=y*(1+R.uniform(-.045,.045))
            pp=np.array([x,yy,zz]); ring.append(a+f@pp);loc.append(pp)
        rings.append(np.asarray(ring));local.append(np.asarray(loc))
    tex_start=R.uniform(.01,.38); tex_span=R.uniform(.48,.60)
    for j in range(3):
        for i in range(8):
            k=(i+1)%8
            points=[rings[j][i],rings[j][k],rings[j+1][k],rings[j+1][i]]
            # U follows the cross section; V follows the timber's long grain.
            u0=tex_start;u1=min(.99,tex_start+tex_span)
            v0=.03+local[j][i][0]/length*.94;v1=.03+local[j+1][i][0]/length*.94
            use_key=key
            if j==2 and broken_end:use_key='wood_rot'
            if j==0 and broken_start:use_key='wood_rot'
            m.face(points,use_key,[(u0,v0),(u1,v0),(u1,v1),(u0,v1)])
    for j,rev,broken in [(0,True,broken_start),(3,False,broken_end)]:
        inds=list(range(8));
        if rev:inds.reverse()
        center=rings[j].mean(axis=0)
        if broken:
            center+=f[:,0]*(.095 if j==0 else -.095)
        for i in range(8):
            i0=inds[i];i1=inds[(i+1)%8]
            uv0=(profile[i0][0]/w+.5,profile[i0][1]/t+.5)
            uv1=(profile[i1][0]/w+.5,profile[i1][1]/t+.5)
            m.tri([center,rings[j][i0],rings[j][i1]],'rot_end' if broken else 'endgrain',[(.5,.5),uv0,uv1])
    m.record('timber')
    return f


def splinter(m,a,b,w=.07,t=.065,key='wood_rot'):
    a=np.asarray(a);b=np.asarray(b);f=frame(a,b);L=np.linalg.norm(b-a)
    base=[a+f@np.array([0,y*w/2,z*t/2]) for y,z in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    shoulder=[a+f@np.array([L*.68,y*w*.30,z*t*.30]) for y,z in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    tip=b+f[:,1]*R.uniform(-w*.3,w*.3)
    m.face(base[::-1],'rot_end',[(0,0),(1,0),(1,1),(0,1)])
    for i in range(4):
        j=(i+1)%4
        m.face([base[i],base[j],shoulder[j],shoulder[i]],key,[(.1,0),(.65,0),(.65,.7),(.1,.7)])
        m.tri([shoulder[i],shoulder[j],tip],key,[(.1,.7),(.65,.7),(.4,1)])
    m.record('splinter')


def tube(m,points,radius=.035,key='rope',sides=6,taper=1,smooth=True,cap=True):
    p=np.asarray(points,dtype=float)
    if len(p)<2:return
    rings=[];nrings=[]
    ref=np.array([0.,0.,1.])
    cumulative=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    prev_y=None
    for j,pos in enumerate(p):
        v=normalize(p[min(j+1,len(p)-1)]-p[max(0,j-1)])
        if prev_y is None:
            y=normalize(np.cross(v,ref if abs(v[2])<.92 else np.array([0.,1.,0.])))
        else:
            y=normalize(prev_y-v*np.dot(prev_y,v))
        z=np.cross(v,y);prev_y=y
        rr=radius*(1+(taper-1)*j/(len(p)-1))
        normals=[math.cos(2*PI*k/sides)*y+math.sin(2*PI*k/sides)*z for k in range(sides)]
        rings.append([pos+rr*n for n in normals]);nrings.append(normals)
    for j in range(len(p)-1):
        for k in range(sides):
            kk=(k+1)%sides
            u0=.08+.84*k/sides;u1=.08+.84*(k+1)/sides
            v0=.03+.94*cumulative[j]/max(cumulative[-1],1e-8);v1=.03+.94*cumulative[j+1]/max(cumulative[-1],1e-8)
            normals=[nrings[j][k],nrings[j][kk],nrings[j+1][kk],nrings[j+1][k]] if smooth else None
            m.face([rings[j][k],rings[j][kk],rings[j+1][kk],rings[j+1][k]],key,[(u0,v0),(u1,v0),(u1,v1),(u0,v1)],normals)
    if cap:
        m.face(rings[0][::-1],key);m.face(rings[-1],key)


def rope(m,a,b,sag=.22,fray=False):
    a=np.asarray(a);b=np.asarray(b)
    n=max(12,int(np.linalg.norm(b-a)/.095));points=[]
    for i in range(n+1):
        t=i/n;p=a*(1-t)+b*t;p[2]-=4*sag*t*(1-t);points.append(p)
    tube(m,points,.039,'rope',6)
    # One narrow raised strand makes the silhouette read as a twisted rope.
    pts=[]
    for i,p in enumerate(points):
        d=normalize(np.asarray(points[min(i+1,n)])-np.asarray(points[max(0,i-1)]))
        y=normalize(np.cross(d,[0,0,1]));z=np.cross(d,y)
        ang=i*1.15
        pts.append(p+.038*(math.cos(ang)*y+math.sin(ang)*z))
    tube(m,pts,.009,'rope',4)
    if fray:
        for j in range(4):
            end=np.asarray(points[-1]);p2=end+np.array([R.uniform(-.13,.13),R.uniform(-.1,.1),-.20-R.random()*.11])
            tube(m,[end,(end+p2)*.5+np.array([.01,.015,.02]),p2],.009,'rope',4,taper=.12)
    m.record('rope_span')


def binding(m,x,y,z,r=.205,turns=2.35):
    pts=[];n=42
    for j in range(n+1):
        t=j/n;a=t*2*PI*turns
        rr=r*(1+.025*math.sin(a*4))
        pts.append((x+rr*math.cos(a),y+rr*math.sin(a),z+.155*t))
    tube(m,pts,.032,'rope',6)
    # Hanging knot tail.
    tube(m,[(x+r,y,z+.035),(x+r+.075,y-.02,z-.04),(x+r+.04,y-.07,z-.22)],.025,'rope',6,taper=.4)
    m.record('rope_binding')


def moss_blob(m,center,rx=.18,ry=.12,height=.045,normal=(0,0,1)):
    c=np.asarray(center);n=normalize(normal)
    x=normalize(np.cross([0,1,0],n)) if abs(n[1])<.92 else normalize(np.cross([1,0,0],n))
    y=np.cross(n,x);num=7
    edge=[]
    for j in range(num):
        a=2*PI*j/num;rr=R.uniform(.77,1.1)
        edge.append(c+rr*rx*math.cos(a)*x+rr*ry*math.sin(a)*y)
    top=c+n*height
    for j in range(num):
        k=(j+1)%num
        m.tri([edge[j],edge[k],top],'moss',[(.5+.45*math.cos(2*PI*j/num),.5+.45*math.sin(2*PI*j/num)),(.5+.45*math.cos(2*PI*k/num),.5+.45*math.sin(2*PI*k/num)),(.5,.5)])
        m.face([edge[k],edge[j],edge[j]-n*.014,edge[k]-n*.014],'moss',[(.1,.3),(.8,.3),(.8,.1),(.1,.1)])
    m.face([v-n*.014 for v in edge][::-1],'moss')
    m.record('moss_patch')


def drape(m,start,length=.48,width=.1):
    s=np.asarray(start);n=5;left=[];right=[]
    for i in range(n+1):
        t=i/n;z=-length*t;x=.02*math.sin(t*PI*1.5)
        p=s+np.array([x,.025*math.sin(t*3*PI),z])
        w=width*(1-t*.65)*(1+.18*math.sin(t*5*PI))
        left.append(p+np.array([-w/2,0,0]));right.append(p+np.array([w/2,0,0]))
    for j in range(n):
        p=[left[j],right[j],right[j+1],left[j+1]]
        uv=[(.15,1-j/n),(.8,1-j/n),(.8,1-(j+1)/n),(.15,1-(j+1)/n)]
        m.face(p,'moss',uv);m.face(p[::-1],'moss',uv[::-1])
    m.record('hanging_moss')


def leaf(m,start,end,width=.10,bulge=.025):
    a=np.asarray(start);b=np.asarray(end);d=b-a
    side=normalize(np.cross(d,[0,1,.3]))*width
    if np.linalg.norm(side)<1e-6:return
    mid=a+d*.47;top=mid+np.array([0,-bulge,bulge*.4])
    v=[a,mid-side*.52,b,mid+side*.52]
    uv=[(.5,.04),(.07,.5),(.5,.96),(.93,.5)]
    for j in range(4):
        k=(j+1)%4
        m.tri([v[j],v[k],top],'leaf',[uv[j],uv[k],(.5,.52)])
        m.tri([v[k],v[j],mid-np.array([0,.005,0])],'leaf',[uv[k],uv[j],(.5,.5)])
    m.record('ivy_leaf')


def vine(m,start,length=.85,drift=(.13,0,0)):
    s=np.asarray(start);n=7;points=[]
    for j in range(n+1):
        t=j/n;p=s+np.array(drift)*t+np.array([.08*math.sin(t*8),-.05*math.sin(t*5),-length*t]);points.append(p)
    tube(m,points,.012,'leaf',5,taper=.45)
    for i,p in enumerate(points[1:-1]):
        side=1 if i%2 else -1
        dest=p+np.array([side*R.uniform(.13,.21),-.07,-R.uniform(.08,.16)])
        leaf(m,p,dest,width=R.uniform(.12,.20),bulge=.027)
        if i%2==0:leaf(m,p+np.array([0,0,-.06]),p+np.array([-side*.15,-.04,-.19]),.13)
    m.record('ivy_vine')


def mushroom(m,base,r=.20,h=.28,shelf=False,heading=-PI/2):
    base=np.asarray(base,dtype=float);seg=16 if r>.15 else 12
    if shelf:
        # A half-disk bracket fungus grows away from timber; no free-floating cap.
        f=np.array([math.cos(heading),math.sin(heading),0])
        s=np.array([-math.sin(heading),math.cos(heading),0])
        center=base;angs=np.linspace(-PI*.51,PI*.51,seg+1)
        def pnt(rr,a,z):return center+f*(rr*math.cos(a))+s*(rr*math.sin(a))+[0,0,z]
    else:
        stem_top=base+np.array([r*.08,-r*.06,h])
        tube(m,[base,base+np.array([.01,-.01,h*.6]),stem_top],max(.022,r*.18),'gills',8,taper=.76)
        center=stem_top;angs=np.linspace(0,2*PI,seg+1)
        def pnt(rr,a,z):return center+np.array([rr*math.cos(a),rr*math.sin(a),z])
    profiles=[(.0,r*.34),(.28,r*.32),(.66,r*.24),(.91,r*.095),(1.0,0),(.94,-r*.075),(.55,-r*.12),(0,-r*.10)]
    for k in range(len(profiles)-1):
        rr0,z0=profiles[k];rr1,z1=profiles[k+1]
        tile='cap' if k<4 else 'gills'
        for j in range(seg):
            a0=angs[j];a1=angs[j+1]
            def pp(rr,a,z):return pnt(rr*r*(1+.018*math.sin(a*5+heading)),a,z)
            def uv(rr,a):return (.5+.475*rr*math.cos(a),.5+.475*rr*math.sin(a))
            points=[pp(rr0,a0,z0),pp(rr1,a0,z1),pp(rr1,a1,z1),pp(rr0,a1,z0)]
            uvs=[uv(rr0,a0),uv(rr1,a0),uv(rr1,a1),uv(rr0,a1)]
            if rr0==0:points=points[:3];uvs=uvs[:3]
            elif rr1==0:points=[points[0],points[1],points[3]];uvs=[uvs[0],uvs[1],uvs[3]]
            m.face(points,tile,uvs)
    if shelf:
        for a,reverse in [(angs[0],False),(angs[-1],True)]:
            pts=[pnt(rr*r,a,z) for rr,z in profiles]
            if reverse:pts.reverse()
            m.face(pts,'gills')
    m.record('shelf_fungus' if shelf else 'mushroom')


def rock(m,center,size=(.65,.60,.50),seed=0):
    """Solid chamfered stone with off-axis bevels, not a decimated sphere."""
    r=random.Random(seed);c=np.asarray(center);sx,sy,sz=np.asarray(size)/2
    bevel=min(sx,sy,sz)*.37
    xy=[(sx-bevel,sy),(-sx+bevel,sy),(-sx,sy-bevel),(-sx,-sy+bevel),(-sx+bevel,-sy),(sx-bevel,-sy),(sx,-sy+bevel),(sx,sy-bevel)]
    rings=[]
    for z,scale in [(-sz,.78),(-sz+bevel,1),(sz-bevel,1),(sz,.80)]:
        rings.append([c+np.array([x*scale+r.uniform(-.035,.035),y*scale+r.uniform(-.035,.035),z+r.uniform(-.025,.025)]) for x,y in xy])
    for j in range(3):
        for i in range(8):
            k=(i+1)%8
            m.face([rings[j][i],rings[j][k],rings[j+1][k],rings[j+1][i]],'stone',[(.06,.05),(.94,.05),(.94,.95),(.06,.95)])
    m.face(rings[0][::-1],'stone');m.face(rings[-1],'stone')
    m.record('foundation_stone')


def nail(m,p,axis=(0,0,1),r=.025):
    p=np.asarray(p);axis=normalize(axis)
    tube(m,[p,p+axis*.018],r,'metal',6,smooth=False)
    m.record('rusted_nail')


def build_half(side):
    """side -1 = west bank, +1 = east bank. Deliberately asymmetric damage."""
    m=Mesh('SM_BrokenBridge_Left' if side<0 else 'SM_BrokenBridge_Right')
    deck=1.67 if side<0 else 1.82
    # Main stringers remain at their own bank and stop before the clear gap.
    for y in [-1.34,1.34]:
        outer=np.array([side*5.35,y,deck-.32]);inner=np.array([side*1.62,y+.035*side,deck-.49])
        timber(m,outer,inner,.29,.35,'wood_moss',broken_end=True)
        for j in range(7):
            a=inner+np.array([side*R.uniform(.16,.42),R.uniform(-.10,.10),R.uniform(-.11,.09)])
            b=inner+np.array([-side*R.uniform(.05,.47),R.uniform(-.11,.11),-R.uniform(.05,.39)])
            splinter(m,a,b,R.uniform(.035,.075),R.uniform(.026,.062))
    # Uneven transverse planks. Long grain runs across the actual plank width.
    for j in range(11):
        x=side*(5.13-j*.285)
        z=deck+.065*math.sin(j*.4)-(j/10)**3*(.10 if side<0 else .19)
        twist=R.uniform(-.03,.03)
        if j==8 and side>0:continue # an extra small hole on the east deck
        if j>=9:
            # Two irregular halves, snapped in the crosswise direction as well.
            for sign in (-1,1):
                yend=sign*R.uniform(.06,.49)
                a=[x,sign*1.69,z+R.uniform(-.025,.025)]
                b=[x+R.uniform(-.08,.08),yend,z-R.uniform(.025,.14)]
                timber(m,a,b,.257,.18,'wood_rot' if j==10 else 'wood_moss',broken_end=True,twist=twist)
        else:
            timber(m,[x,-1.72,z],[x+R.uniform(-.03,.03),1.72,z+R.uniform(-.035,.035)],.259,.18,
                   ['wood_old','wood_clean','wood_moss','wood_old'][j%4],twist=twist)
        for y in (-1.28,1.28):nail(m,(x,y,z+.096))
        # Broad contiguous patches, with bare weathered timber between them.
        if j in (0,1,3,4,7,9,10):
            for q in range(3 if j<9 else 2):
                y=R.uniform(-1.5,1.5)
                moss_blob(m,(x,y,z+.10),R.uniform(.08,.14),R.uniform(.15,.28),R.uniform(.022,.052))
    # Underside cross members and sloping braces.
    for xx in [4.92,3.46]:
        timber(m,[side*xx,-1.6,deck-.55],[side*xx,1.6,deck-.55],.24,.25,'wood_rot')
    for y in [-1.49,1.49]:
        timber(m,[side*4.96,y,.55],[side*3.34,y,deck-.26],.18,.21,'wood_old')
    posts=[]
    for xx in [5.0,2.69]:
        for y in [-1.64,1.64]:
            x=side*xx
            broken=(xx<3 and ((y>0 and side<0) or (y<0 and side>0)))
            top=deck+(1.14 if not broken else .74)+R.uniform(-.1,.09)
            lean=np.array([-side*.055,R.uniform(-.065,.065),0])
            timber(m,[x,y,.23],[x+lean[0],y+lean[1],top],.32,.33,'wood_moss',broken_end=broken,twist=R.uniform(-.045,.045))
            posts.append((x,y,top,broken))
            binding(m,x+lean[0]*.9,y+lean[1]*.9,top-.27,r=.206,turns=2.35)
            moss_blob(m,[x+lean[0],y+lean[1],top+.008],.13,.14,.048)
            if broken:
                for j in range(3):
                    a=[x+R.uniform(-.10,.10),y+R.uniform(-.1,.1),top-.21]
                    b=[a[0]+R.uniform(-.05,.05),a[1]+R.uniform(-.05,.05),top+R.uniform(.05,.22)]
                    splinter(m,a,b,.055,.053)
            for j in range(3):
                moss_blob(m,(x+.04,y-.175,.72+j*.34),.15,.20,.027,(0,-1,0))
            vine(m,(x+.15,y-.20,top-.35),R.uniform(.92,1.35),(-side*.20,-.025,0))
            if xx<3 or y<0:
                for k in range(3):
                    mushroom(m,(x+.025*(k%2),y-.165,deck-.38+k*.24),r=[.22,.15,.11][k],shelf=True,heading=-PI/2)
            nail(m,(x,y-.178,top-.48),(0,-1,0),.03)
    # Rail on one side, rope on the other. Nothing crosses the missing span.
    for y in [-1.64,1.64]:
        p0=[side*4.99,y,deck+.85]
        p1=[side*2.73,y,deck+(.51 if (y<0 and side>0) or (y>0 and side<0) else .80)]
        if (y>0 and side>0) or (y<0 and side<0):
            timber(m,p0,p1,.12,.16,'wood_old',broken_end=False)
            for j in range(6):
                p=np.array(p0)*(1-j/7)+np.array(p1)*(j/7)
                moss_blob(m,p+[0,0,.09],.15,.073,.025)
        else:rope(m,p0,p1,.30)
        # Lower broken rail fragment attached to the inner post, falling outward.
        a=np.array([side*2.69,y,deck+.25]);b=a+np.array([-side*.79,side*.11,-.48])
        timber(m,a,b,.105,.13,'wood_rot',broken_end=True)
        rope(m,np.array(p1)+[0,0,-.08],np.array(p1)+[-side*.19,-.08,-.59],.075,fray=True)
    # Fallen planks still caught on their own bank, not bridging to the other side.
    for j,y in enumerate([-.94,.67]):
        outer=np.array([side*(2.87+j*.12),y,deck-.25])
        inner=np.array([side*(1.59+j*.21),y+.22,deck-.92-j*.21])
        timber(m,outer,inner,.24,.16,'wood_rot',broken_end=True,twist=side*.18)
        for k in range(4):
            a=inner+[side*.16,R.uniform(-.07,.07),R.uniform(-.04,.04)]
            b=inner+[-side*R.uniform(.1,.4),R.uniform(-.10,.10),-R.uniform(.12,.32)]
            splinter(m,a,b,.036,.033)
    # Foundation stones form four independent little piers.
    for y in [-1.52,1.52]:
        for layer in range(3):
            z=.18+layer*.37
            for off in [-.24,.24]:
                rock(m,(side*4.98+off+(.08 if layer%2 else 0),y,z),(.48,.76,.35),1000+len(m.faces))
        rock(m,(side*4.98,y,1.27),(.99,.86,.22),1000+len(m.faces))
        for j in range(5):
            moss_blob(m,(side*5.05+R.uniform(-.43,.43),y+R.uniform(-.31,.31),1.40),.18,.17,.035)
        for j in range(3):
            rock(m,(side*5.33+R.uniform(-.5,.3),y+R.uniform(-.39,.39),.15),(.60,.59,.44),1000+len(m.faces))
    # Clusters of small mushrooms on damp planks near the break.
    for x,y in [(side*3.05,-1.18),(side*3.35,1.22),(side*4.71,.74)]:
        z=deck+.11
        for j in range(3):
            mushroom(m,(x+R.uniform(-.15,.15),y+R.uniform(-.16,.16),z),r=[.19,.12,.08][j],h=[.28,.21,.14][j])
    for xx in [2.50,3.38,4.65]:
        for y in [-1.75,1.74]:
            for j in range(2):
                drape(m,(side*xx+j*.09,y,deck-.03),R.uniform(.24,.62),R.uniform(.055,.11))
            if xx<3.5:vine(m,(side*xx,y,deck-.02),R.uniform(.58,.96),(-side*.2,0,0))
    return m


def build_debris():
    m=Mesh('SM_BrokenBridge_Debris')
    # All debris stays below the walking deck. No high central stepping platform.
    for a,b,w,t in [([-.72,.52,.12],[.21,.87,.36],.21,.13),([.61,-.42,.12],[1.02,-.12,.53],.19,.12),([-.52,-.90,.12],[-.17,-.45,.20],.18,.12)]:
        timber(m,a,b,w,t,'wood_rot',broken_start=True,broken_end=True,twist=R.uniform(-.4,.4))
        for j in range(3):
            aa=np.array(b)+[R.uniform(-.04,.04),R.uniform(-.05,.05),0]
            splinter(m,aa,aa+[R.uniform(-.2,.2),R.uniform(.12,.32),R.uniform(-.12,.04)],.035,.025)
    # Splintered support stump protruding from the stream bed, not a usable step.
    timber(m,[.28,1.34,-.13],[.25,1.30,.61],.24,.24,'wood_rot',broken_end=True)
    for j in range(4):
        splinter(m,[.25+R.uniform(-.09,.09),1.3+R.uniform(-.09,.09),.47],[.25+R.uniform(-.09,.09),1.3+R.uniform(-.09,.09),.72+R.uniform(0,.11)],.04,.036)
    moss_blob(m,[.22,1.29,.6],.1,.10,.03)
    m.record('debris_cluster')
    return m


def box(m,lo,hi):
    x0,y0,z0=lo;x1,y1,z1=hi
    v=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    for inds in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
        m.face([v[i] for i in inds],'wood_clean',[(0,0),(1,0),(1,1),(0,1)])


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
    tree={'asset':{'version':'2.0','generator':'Cozy Broken Bridge / explicit textured mesh generator','extras':{'units':'metres','up_axis':'Y','source_up_axis':'Z'}},
          'scene':0,'scenes':[{'name':'Cozy_Broken_Bridge','nodes':[]}],
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
            'occlusionTexture':{'index':2,'strength':.6},'alphaMode':'OPAQUE','doubleSided':False}]
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


def build():
    R.seed(640219)
    left=build_half(-1);right=build_half(1);debris=build_debris()
    allmesh=Mesh('SM_BrokenBridge')
    for m in [left,right,debris]:allmesh.append(m)
    # Placement origin is the centre of the bridge, at bank walking-deck level.
    # This allows all foundations to extend downward into banks/water.
    pivot=np.array([0.,0.,1.76])
    for m in [left,right,debris,allmesh]:
        m.vertices=(np.array(m.vertices)-pivot).tolist()
    meta={'purpose':'collapsed cozy forest bridge','continuous_walkable_span':False,
          'origin':'centre of missing span at bank deck level','collision':'separate proxies; do not generate one convex hull across the gap'}
    files=[]
    files.append(export_glb(ROOT/'models/SM_BrokenBridge.glb',[allmesh],metadata=meta))
    centers=[(-4,0,0),(4,0,0),(0,0,0)]
    files.append(export_glb(ROOT/'modular/BrokenBridge_Modular.glb',[left,right,debris],centers=centers,translations=centers,metadata=meta))
    for m,cen in zip([left,right,debris],centers):
        files.append(export_glb(ROOT/f'modular/{m.name}.glb',[m],centers=[cen],metadata=meta))
    # Three placements reference the exact same mesh index and embedded material.
    files.append(export_glb(ROOT/'modular/Reuse_3_Instances.glb',[allmesh],metadata=meta,
                  instances=[('BrokenBridge_Instance_02',0,(0,7.5,0)),('BrokenBridge_Instance_03',0,(0,15,0))]))
    collision=[]
    for s in (-1,1):
        cm=Mesh('UCX_BrokenBridge_Left' if s<0 else 'UCX_BrokenBridge_Right')
        if s<0:lo=(-5.28,-1.60,-.29);hi=(-2.65,1.60,.035)
        else:lo=(2.65,-1.60,-.20);hi=(5.28,1.60,.13)
        box(cm,lo,hi);collision.append(cm)
    files.append(export_glb(ROOT/'collision/Deck_Proxies.glb',collision,with_textures=False,
                            metadata={'automatic_collision_import':False,'warning':'assign separate hulls to each bank. Never one combined convex hull.'}))
    vs=np.asarray(allmesh.vertices);bounds=[vs.min(axis=0).tolist(),vs.max(axis=0).tolist()]
    stats={'asset':'SM_BrokenBridge','seed':640219,'coordinates':{'construction':'X length, Y width, Z up; metres','glb':'X length, Y up, Z width; metres'},
           'bounds_z_up_m':bounds,'dimensions_length_width_height_m':(vs.max(axis=0)-vs.min(axis=0)).tolist(),
           'triangles':len(allmesh.faces),'vertices_with_uv_normal_splits':len(allmesh.vertices),'material_count':1,'texture_resolution':[2048,2048],
           'components':allmesh.components,'files':files,'clear_gap_x_m':[float(np.asarray(left.vertices)[:,0].max()),float(np.asarray(right.vertices)[:,0].min())],
           'clear_gap_width_m':float(np.asarray(right.vertices)[:,0].min()-np.asarray(left.vertices)[:,0].max()),
           'gameplay_note':'No intact deck, rail, rope or beam connects the banks. Character jumping, invisible blockers and navigation must be configured in the game engine.',
           'texture_provenance':'Reuses the previously supplied atlas; source crops and re-composition script included. No new AI image generation was performed for this correction.',
           'testing':{'Blender':False,'Unreal':False}}
    (ROOT/'validation/model_stats.json').write_text(json.dumps(stats,indent=2,ensure_ascii=False),encoding='utf8')
    layout={'units':'metres','axis':'Z_UP_RIGHT_HANDED','scene_origin':'centre of bridge at bank deck height',
            'assets':[{'id':m.name,'file':f'modular/{m.name}.glb'} for m in [left,right,debris]],
            'instances':[{'asset':m.name,'translation':list(c),'rotation_quaternion_xyzw':[0,0,0,1],'scale':[1,1,1]} for m,c in zip([left,right,debris],centers)],
            'unreal_cm_hint':'Multiply translations by 100. Import the glTF asset with correct axis conversion before applying transforms.'}
    (ROOT/'modular/placement_transforms.json').write_text(json.dumps(layout,indent=2),encoding='utf8')
    np.savez_compressed(ROOT/'source/mesh_construction_zup.npz',vertices=np.asarray(allmesh.vertices,np.float32),normals=np.asarray(allmesh.normals,np.float32),uv_gltf=np.asarray(allmesh.uvs,np.float32),faces=np.asarray(allmesh.faces,np.uint32))
    print(json.dumps({'triangles':len(allmesh.faces),'vertices':len(allmesh.vertices),'dimensions':stats['dimensions_length_width_height_m'],'components':allmesh.components,'files':files},indent=2))

if __name__=='__main__':build()
