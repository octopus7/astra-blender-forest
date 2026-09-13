"""Cozy Lake Forest — deterministic, dependency-free mesh and placement recipes.

No bpy import here: geometry, shared-asset references and layouts are testable
with ordinary Python. Units are metres; +Z is up. Colours are authored in sRGB.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter
from math import sin, cos, sqrt, atan2, pi, floor, radians
import hashlib
import json
import random



def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def smooth(a, b, x):
    t = clamp((x-a)/(b-a))
    return t*t*(3-2*t)


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4)) + (1.0,)


def shade(c, f):
    return tuple(clamp(v*f) for v in c[:3]) + (c[3] if len(c)>3 else 1.0,)


def mix(a, b, f):
    return tuple(x+(y-x)*f for x,y in zip(a,b))


def add(a,b): return tuple(x+y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def mul(a,s): return tuple(x*s for x in a)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a): return mul(a,1/max(1e-15,sqrt(dot(a,a))))


def transformed(v, location=(0,0,0), rotation=(0,0,0), scale=(1,1,1)):
    """Rz @ Ry @ Rx, radians; compatible with Blender Euler XYZ."""
    x,y,z=(v[i]*scale[i] for i in range(3))
    a,b,c=rotation
    y,z=y*cos(a)-z*sin(a), y*sin(a)+z*cos(a)
    x,z=x*cos(b)+z*sin(b), -x*sin(b)+z*cos(b)
    x,y=x*cos(c)-y*sin(c), x*sin(c)+y*cos(c)
    return x+location[0], y+location[1], z+location[2]


@dataclass
class Mesh:
    name: str
    category: str = "Props"
    material: str = "opaque"
    collision: str = "none"
    vertices: list = field(default_factory=list)
    faces: list = field(default_factory=list)
    colors: list = field(default_factory=list)  # three RGBA values for each triangle
    smooth_shading: bool = False

    def patch(self, vertices, faces, color, rng=None, variation=0.0, corner_colors=None):
        offset=len(self.vertices)
        self.vertices.extend(tuple(v) for v in vertices)
        for i, face in enumerate(faces):
            # The core stores triangles only, including deterministic n-gon triangulation.
            for j in range(1,len(face)-1):
                tri=(face[0],face[j],face[j+1])
                self.faces.append(tuple(offset+k for k in tri))
                if corner_colors is not None:
                    self.colors.append(tuple(corner_colors[k] for k in tri))
                else:
                    c=shade(color, 1+(rng.uniform(-variation,variation) if rng else 0))
                    self.colors.append((c,c,c))
        return self

    def merge(self, other, location=(0,0,0), rotation=(0,0,0), scale=(1,1,1)):
        off=len(self.vertices)
        self.vertices.extend(transformed(v,location,rotation,scale) for v in other.vertices)
        self.faces.extend(tuple(off+i for i in face) for face in other.faces)
        self.colors.extend(other.colors)
        return self

    def box(self, center, size, color, rotation=(0,0,0), rng=None, variation=.025):
        vs=[transformed((x*size[0]/2,y*size[1]/2,z*size[2]/2),center,rotation)
            for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                          (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        return self.patch(vs,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],color,rng,variation)

    def beam(self,a,b,width,depth,color):
        axis=norm(sub(b,a)); helper=(0,0,1) if abs(axis[2])<.95 else (0,1,0)
        u=mul(norm(cross(axis,helper)),width/2); v=mul(norm(cross(axis,u)),depth/2)
        vs=[add(p,add(mul(u,i),mul(v,j))) for p in (a,b) for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        return self.patch(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],color)

    def tube(self,a,b,r0,r1,color,n=8,rng=None,variation=.045):
        axis=norm(sub(b,a)); helper=(0,0,1) if abs(axis[2])<.9 else (0,1,0)
        u=norm(cross(axis,helper)); v=cross(axis,u)
        vs=[]
        for center,r in ((a,r0),(b,r1)):
            for i in range(n):
                vs.append(add(center,add(mul(u,r*cos(2*pi*i/n)),mul(v,r*sin(2*pi*i/n)))))
        if r1<=1e-7:
            # One top vertex, not an n-vertex coincident ring.
            vs=vs[:n]+[b]
            fs=[tuple(reversed(range(n)))]+[(i,(i+1)%n,n) for i in range(n)]
        else:
            fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]
            fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        return self.patch(vs,fs,color,rng,variation)

    def ico(self,center,scale,color,subdivisions=1,rng=None,irregular=.05,variation=.065):
        t=(1+sqrt(5))/2
        vs=[norm(v) for v in [(-1,t,0),(1,t,0),(-1,-t,0),(1,-t,0),
             (0,-1,t),(0,1,t),(0,-1,-t),(0,1,-t),(t,0,-1),(t,0,1),(-t,0,-1),(-t,0,1)]]
        fs=[(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),
            (11,10,2),(10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),
            (4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
        for _ in range(subdivisions):
            cache={}; new=[]
            def mid(a,b):
                key=tuple(sorted((a,b)))
                if key not in cache:
                    cache[key]=len(vs); vs.append(norm(add(vs[a],vs[b])))
                return cache[key]
            for a,b,c in fs:
                ab,bc,ca=mid(a,b),mid(b,c),mid(c,a)
                new.extend([(a,ab,ca),(b,bc,ab),(c,ca,bc),(ab,bc,ca)])
            fs=new
        vs=[add(center,tuple(p[i]*scale[i]*(1+(rng.uniform(-irregular,irregular) if rng else 0)) for i in range(3))) for p in vs]
        return self.patch(vs,fs,color,rng,variation)

    def leaf(self,base,tip,width,color,ridge=.07):
        d=sub(tip,base)
        side=mul(norm(cross(d,(0,0,1))) if abs(d[0])+abs(d[1])>1e-7 else (1,0,0), width/2)
        middle=add(base,mul(d,.47))
        vs=[base,add(middle,side),tip,sub(middle,side),add(middle,(0,0,ridge))]
        return self.patch(vs,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],color)

    def bounds(self):
        return [[min(v[i] for v in self.vertices) for i in range(3)],
                [max(v[i] for v in self.vertices) for i in range(3)]]


BARK=rgb('876038'); WOOD=rgb('bd8b49'); TRIM=rgb('dfa85b'); CREAM=rgb('f3e5ae')
LEAF=rgb('a8bf57'); PINE=rgb('507b40'); GRASS=rgb('8da755'); SAND=rgb('e4cf98')
STONE=rgb('969d86'); PINK=rgb('e6a2b4'); WATER=rgb('4bafb8')


def broadleaf(variant):
    r=random.Random(100+variant)
    m=Mesh(f"CF_Tree_Broadleaf_{variant+1:02d}","Trees",collision="tree")
    h=[5.5,6.1,5.0,6.5][variant]
    main=shade(LEAF,[1.02,.95,1.07,.91][variant])
    m.tube((0,0,0),(.13,-.05,h*.61),.30,.15,BARK,7,r)
    for i in range(5):
        a=2*pi*i/5+.3
        m.tube((.09*cos(a),.09*sin(a),.40),(.87*cos(a),.87*sin(a),.04),.16,.018,shade(BARK,1.13),5,r)
    for i in range(3):
        a=i*2*pi/3+.3
        m.tube((.08,0,h*.34),(.83*cos(a),.83*sin(a),h*.67),.14,.06,BARK,6,r)
    m.ico((.03,.03,h*.73),(1.75,1.65,h*.29),main,1,r,.08)
    for i in range(3):
        a=i*2*pi/3+variant*.65
        m.ico((cos(a)*.99,sin(a)*.93,h*(.65+.03*(i%2))),
              (1.27,1.29,1.28),shade(main,.97+i*.012),1,r,.07)
    return m


def pine(variant):
    r=random.Random(211+variant)
    m=Mesh(f"CF_Tree_Pine_{variant+1:02d}","Trees",collision="tree")
    h=[6.4,7.3,5.4][variant]
    m.tube((0,0,0),(0,0,h*.84),.20,.085,BARK,7,r)
    for layer in range(4):
        bottom=.65+layer*h*.16
        radius=(1.78-layer*.32)*[1,.98,1.08][variant]
        height=h*.40
        n=10; vs=[]
        for i in range(n):
            a=2*pi*i/n + layer*.19
            rr=radius*(1 if i%2==0 else .85)
            vs.append((rr*cos(a),rr*sin(a),bottom+(0 if i%2==0 else .18)))
        for i in range(n):
            a=2*pi*i/n+layer*.19
            vs.append((radius*.42*cos(a),radius*.42*sin(a),bottom+height*.62))
        vs.append((.03,-.025,bottom+height))
        fs=[tuple(reversed(range(n)))]
        for i in range(n):
            j=(i+1)%n
            fs.extend([(i,j,n+j,n+i),(n+i,n+j,2*n)])
        m.patch(vs,fs,shade(PINE,1+layer*.075+variant*.015),r,.035)
    return m


def rock(variant):
    r=random.Random(301+variant)
    m=Mesh(f"CF_Rock_Moss_{variant+1:02d}","Rocks",collision="simple")
    scales=[(.9,.68,.56),(.61,.86,.39),(1.15,.81,.67),(.50,.51,.44)]
    m.ico((0,0,.25),scales[variant],STONE,1,r,.18,.09)
    low=min(v[2] for v in m.vertices)
    m.vertices=[(x,y,z-low-.07) for x,y,z in m.vertices]
    for i,face in enumerate(m.faces):
        a,b,c=(m.vertices[j] for j in face)
        n=norm(cross(sub(b,a),sub(c,a)))
        if n[2]>.25 and r.random()<.73:
            col=shade(rgb('93a852'),r.uniform(.9,1.1)); m.colors[i]=(col,col,col)
    return m


def shrub(variant):
    r=random.Random(411+variant); m=Mesh(f"CF_Shrub_{variant+1:02d}","Understory")
    for i in range(3):
        a=i*2*pi/3
        m.ico((cos(a)*.37,sin(a)*.30,.47),(.62,.55,.54),shade(LEAF,.85+variant*.07),1,r,.07,.06)
    return m


def fern(variant):
    r=random.Random(501+variant); m=Mesh(f"CF_Fern_{variant+1:02d}","Understory",material="foliage")
    col=shade(rgb('b3c773'),1-variant*.065)
    for i in range(7):
        a=2*pi*i/7+r.uniform(-.1,.1); length=r.uniform(.57,.90)
        end=(cos(a)*length,sin(a)*length,.22)
        m.leaf((0,0,.07),end,.075,shade(col,.84),.02)
        for j in range(1,5):
            t=j/5; mid=(end[0]*t,end[1]*t,.08+.31*sin(pi*t))
            for s in (-1,1):
                q=a+s*.80
                tip=add(mid,(cos(q)*.29*(1-t*.55),sin(q)*.29*(1-t*.55),-.07))
                m.leaf(mid,tip,.14*(1-t*.45),shade(col,r.uniform(.95,1.05)),.018)
    return m


def grass(variant):
    r=random.Random(611+variant); m=Mesh(f"CF_GrassTuft_{variant+1:02d}","GroundCover",material="foliage")
    col=shade(rgb('b0bb64'),.88+variant*.06)
    for _ in range(9):
        a=r.uniform(0,2*pi); b=(r.uniform(-.22,.22),r.uniform(-.22,.22),0)
        tip=add(b,(cos(a)*.24,sin(a)*.24,r.uniform(.18,.46)))
        m.leaf(b,tip,r.uniform(.055,.11),shade(col,r.uniform(.95,1.08)),.02)
    return m


def flowers(variant):
    r=random.Random(711+variant); m=Mesh(f"CF_Flowers_{['Daisy','Buttercup','Bluebell'][variant]}","Flowers",material="foliage")
    petals=[rgb('fff3d7'),rgb('f3cb58'),rgb('9ac8e1')][variant]
    for _ in range(6):
        x,y=r.uniform(-.43,.43),r.uniform(-.38,.38); h=r.uniform(.19,.42)
        m.tube((x,y,0),(x,y,h),.013,.009,rgb('6f903d'),5)
        for j in range(6):
            a=j*2*pi/6; tip=(x+.14*cos(a),y+.14*sin(a),h+.015)
            m.leaf((x,y,h),tip,.075,petals,.035)
        m.ico((x,y,h+.037),(.043,.043,.028),rgb('e8b740'),0)
        m.leaf((x,y,h*.45),(x+.12,y+.05,h*.62),.07,shade(GRASS,.9),.013)
    return m


def mushrooms(variant):
    r=random.Random(800+variant); m=Mesh(f"CF_Mushrooms_{variant+1:02d}","Flowers")
    col=[rgb('bd753d'),rgb('cb7860')][variant]
    for x,y,s in [(0,0,1),(.26,.09,.7),(-.19,.22,.52)]:
        m.tube((x,y,0),(x,y,.26*s),.048*s,.033*s,CREAM,7)
        n=9; vs=[(x,y,.40*s)]
        for i in range(n):
            a=2*pi*i/n; vs.append((x+.20*s*cos(a),y+.20*s*sin(a),.24*s))
        vs.append((x,y,.225*s))
        m.patch(vs,[(0,1+i,1+(i+1)%n) for i in range(n)],col,r,.06)
        m.patch(vs,[(n+1,1+(i+1)%n,1+i) for i in range(n)],shade(CREAM,.84))
    return m


def cattails(variant):
    r=random.Random(901+variant); m=Mesh(f"CF_Cattails_{variant+1:02d}","ShorePlants",material="foliage")
    for i in range(6):
        x,y=r.uniform(-.38,.38),r.uniform(-.30,.30); h=r.uniform(.65,1.14)
        m.tube((x,y,-.04),(x+.04,y,h),.016,.012,rgb('708740'),5)
        m.tube((x+.04,y,h-.04),(x+.04,y,h+.29),.045,.039,rgb('70502e'),7)
        for j in range(2):
            a=r.uniform(0,2*pi)
            m.leaf((x,y,0),(x+.33*cos(a),y+.33*sin(a),h*.79),.082,rgb('8b9e4a'),.02)
    return m


def lilypad(variant):
    m=Mesh(f"CF_LilyPad_{['Flower','Leaves'][variant]}","WaterDetails",material="foliage")
    for x,y,s in [(0,0,1)]+([(.58,.21,.68)] if variant else []):
        vs=[(x,y,.025)]
        n=16
        # Leave a genuine wedge open; the centre closes each remaining sector.
        for i in range(n):
            a=.20+i*(2*pi-.48)/(n-1)
            vs.append((x+.45*s*cos(a),y+.39*s*sin(a),.018))
        m.patch(vs,[(0,i,i+1) for i in range(1,n)],rgb('88ad60'))
    if variant==0:
        for layer in range(2):
            for j in range(7):
                a=j*2*pi/7+layer*.4
                tip=(.25*(1-layer*.28)*cos(a),.25*(1-layer*.28)*sin(a),.10+layer*.085)
                m.leaf((0,0,.06),tip,.115,mix(PINK,CREAM,.42+layer*.30),.09)
        m.ico((0,0,.16),(.063,.063,.06),rgb('e7be4d'),0)
    return m


def ripple(variant):
    m=Mesh(f"CF_WaterRipple_{variant+1:02d}","WaterDetails",material="water")
    for j in range(2):
        n=18; start=-.6+j*2.8; end=start+1.1; rr=.7+j*.22
        vs=[]
        for i in range(n):
            a=start+(end-start)*i/(n-1)
            width=.013*sin(pi*i/(n-1))+.001
            vs.extend([((rr-width)*cos(a),(rr-width)*.68*sin(a),.017),((rr+width)*cos(a),(rr+width)*.68*sin(a),.017)])
        m.patch(vs,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(n-1)],rgb('99d2c5'))
    return m


def bridge():
    r=random.Random(1001); m=Mesh("CF_Bridge_Arched","Structures",collision="complex")
    length=5.8
    height=lambda x:.16+.34*(1-(2*x/length)**2)
    for i in range(22):
        x=-length/2+(i+.5)*length/22
        ang=atan2(-.34*8*x/(length*length),1)
        m.box((x,0,height(x)),(length/22-.022,2.26,.14),shade(WOOD,r.uniform(.94,1.08)),(0,-ang,0))
    xs=[-2.82,-1.41,0,1.41,2.82]
    for y in (-1.06,1.06):
        for x in xs:
            m.box((x,y,height(x)+.47),(.14,.14,1.03),TRIM)
            m.box((x,y,height(x)+1.005),(.20,.20,.075),shade(TRIM,1.05))
        for a,b in zip(xs,xs[1:]):
            m.beam((a,y,height(a)+.89),(b,y,height(b)+.89),.14,.15,TRIM)
            m.beam((a,y,height(a)+.40),(b,y,height(b)+.40),.09,.11,WOOD)
            m.beam((a,y*.78,height(a)-.15),(b,y*.78,height(b)-.15),.20,.20,shade(BARK,.94))
    return m


def bench():
    m=Mesh("CF_Bench_Wood","Props",collision="simple")
    for y in (-.25,-.07,.11): m.box((0,y,.48),(1.75,.155,.10),WOOD)
    for x in (-.65,.65):
        for y in (-.19,.24): m.box((x,y,.25),(.12,.12,.5),BARK)
        m.beam((x,.24,.20),(x,.36,1.10),.10,.10,BARK)
    for z in (.78,1.0): m.box((0,.31,z),(1.8,.11,.16),TRIM,(-.12,0,0))
    return m


def dock():
    r=random.Random(1050); m=Mesh("CF_Dock_Wood","Structures",collision="complex")
    for i in range(14):
        x=i*.255; m.box((x,0,0),(.235,1.7,.12),shade(WOOD,r.uniform(.95,1.08)))
    for x in (.0,3.3):
        for y in (-.79,.79):
            m.tube((x,y,-1.2),(x,y,.38),.11,.10,BARK,8)
            m.tube((x,y,.27),(x,y,.38),.123,.123,CREAM,8)
    for y in (-.58,.58): m.box((1.65,y,-.14),(3.7,.12,.17),BARK)
    return m


def fence():
    m=Mesh("CF_Fence_Segment","Props",collision="simple")
    for x in (-1.2,1.2):
        m.box((x,0,.59),(.13,.16,1.18),BARK)
        m.tube((x,0,1.17),(x,0,1.27),.105,0,TRIM,4)
    for z in (.42,.92): m.box((0,0,z),(2.55,.10,.13),WOOD)
    m.beam((-1.15,-.06,.39),(1.15,-.06,.96),.075,.075,shade(WOOD,.9))
    return m


def signpost():
    m=Mesh("CF_Signpost","Props",collision="simple")
    m.box((0,0,.72),(.12,.12,1.44),BARK)
    m.box((.12,0,1.22),(.95,.12,.29),WOOD)
    m.patch([(.595,-.06,1.075),(.78,-.06,1.22),(.595,-.06,1.365)],[(0,1,2)],TRIM)
    # Small leaf emblem, no font or texture dependency.
    m.leaf((-.12,-.073,1.19),(.15,-.073,1.26),.09,CREAM,.008)
    return m


def stump():
    m=Mesh("CF_Stump","Props",collision="simple")
    m.tube((0,0,0),(0,0,.59),.41,.31,BARK,9)
    m.tube((0,0,.59),(0,0,.604),.292,.292,TRIM,9)
    m.tube((0,0,.605),(0,0,.608),.14,.14,shade(TRIM,.83),9)
    for i in range(4):
        a=2*pi*i/4; m.tube((0,0,.2),(.61*cos(a),.61*sin(a),.04),.15,.025,BARK,5)
    return m


def well():
    r=random.Random(1202); m=Mesh("CF_Well_StoneWood","Structures",collision="complex")
    n=12
    for layer in range(3):
        for j in range(n):
            a=2*pi*(j+.5*(layer%2))/n+.018; b=a+2*pi/n-.036
            ri,ro=.58,.87; z=.04+layer*.245
            vs=[(rr*cos(ang),rr*sin(ang),zz) for zz in (z,z+.233) for rr,ang in [(ri,a),(ro,a),(ro,b),(ri,b)]]
            m.patch(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],shade(STONE,r.uniform(.9,1.12)))
    m.tube((0,0,.06),(0,0,.075),.58,.58,rgb('355c59'),16)
    for x in (-1.02,1.02): m.box((x,0,1.23),(.19,.21,2.46),WOOD)
    m.tube((-1.24,0,1.94),(1.26,0,1.94),.105,.105,BARK,10)
    m.box((1.28,0,1.72),(.10,.10,.44),TRIM)
    m.tube((1.23,0,1.51),(1.51,0,1.51),.057,.057,TRIM,8)
    m.tube((0,0,1.95),(0,0,.86),.016,.016,rgb('cbbb88'),6)
    m.tube((0,0,.78),(0,0,1.03),.12,.17,WOOD,9)
    m.tube((0,0,1.018),(0,0,1.05),.176,.176,rgb('6b6252'),9)
    for side in (-1,1):
        m.patch([(side*1.35,-.72,2.35),(side*1.35,.72,2.35),(0,.72,2.85),(0,-.72,2.85)],
                [(0,1,2,3)] if side>0 else [(3,2,1,0)],shade(BARK,1.2))
        m.beam((side*1.36,-.75,2.35),(0,-.75,2.85),.13,.13,TRIM)
    return m


def cottage():
    r=random.Random(1310); m=Mesh("CF_Cottage_RoseRoof","Structures",collision="complex")
    # Footprint: 4.6 x 4.2 m. Front = local -Y, ground pivot at origin.
    m.box((0,0,.20),(4.7,4.3,.40),STONE)
    for x in (-1.78,-.9,0,.9,1.78): m.box((x,-2.18,.20),(.85,.13,.34),shade(STONE,r.uniform(.92,1.08)))
    m.box((0,0,1.72),(4.5,4.05,2.73),CREAM)
    # Gable end wall triangles, front/back.
    for y in (-2.026,2.026):
        tri=[(-2.25,y,3.085),(2.25,y,3.085),(0,y,4.71)]
        m.patch(tri,[(0,1,2)] if y<0 else [(2,1,0)],CREAM)
    for x in (-2.22,2.22):
        for y in (-2.04,2.04): m.box((x,y,1.76),(.20,.20,2.88),TRIM)
    for z in (.46,3.04):
        for y in (-2.055,2.055): m.box((0,y,z),(4.64,.16,.17),TRIM)
        for x in (-2.28,2.28): m.box((x,0,z),(.16,4.21,.17),TRIM)
    # Door, slats, frame and handle.
    for i in range(6): m.box((-.67+(i-2.5)*.185,-2.10,1.42),(.174,.10,1.9),shade(WOOD,r.uniform(.9,1.07)))
    for x in (-1.30,-.04): m.box((x,-2.19,1.43),(.14,.18,2.05),TRIM)
    m.box((-.67,-2.19,2.45),(1.40,.18,.16),TRIM)
    m.box((-.67,-2.20,1.0),(1.10,.09,.10),shade(TRIM,.85))
    m.ico((-.22,-2.27,1.43),(.045,.045,.045),rgb('716b44'),0)
    # Windows assembled in local coordinates; side window rotated as a whole.
    def window(center, angle):
        w=Mesh('_window')
        w.box((0,0,0),(.95,.08,1.0),rgb('82bdb9'))
        for x in (-.55,.55): w.box((x,-.075,0),(.13,.16,1.2),TRIM)
        for z in (-.57,.57): w.box((0,-.075,z),(1.21,.16,.13),TRIM)
        w.box((0,-.092,0),(.075,.14,1.04),WOOD)
        w.box((0,-.10,0),(1.06,.14,.075),WOOD)
        w.box((0,-.11,-.64),(1.31,.32,.12),TRIM)
        m.merge(w,center,(0,0,angle))
    window((1.16,-2.12,1.91),0)
    window((2.31,.45,1.94),pi/2)
    window((-2.31,.45,1.94),-pi/2)
    # Shingle-sized panels, not a single smooth roof plane.
    for side in (-1,1):
        for row in range(4):
            x0=side*(row*2.75/4); x1=side*((row+1)*2.75/4)
            z0=4.9-abs(x0)*.665; z1=4.9-abs(x1)*.665
            for col in range(7):
                y0=-2.55+col*5.1/7; y1=y0+5.1/7-.015
                verts=[(x0,y0,z0+.013*(3-row)),(x1,y0,z1+.013*(3-row)),
                       (x1,y1,z1+.013*(3-row)),(x0,y1,z0+.013*(3-row))]
                m.patch(verts,[(0,1,2,3)] if side>0 else [(3,2,1,0)],shade(PINK,r.uniform(.94,1.055)))
        for y in (-2.59,2.59): m.beam((0,y,4.92),(side*2.82,y,3.035),.18,.18,TRIM)
        m.box((side*2.79,0,3.035),(.16,5.32,.18),TRIM)
    m.beam((0,-2.66,4.94),(0,2.66,4.94),.18,.17,shade(PINK,.94))
    # Entrance steps and tiny peaked porch canopy.
    for j in range(3): m.box((-.67,-3.00+j*.29,.075+j*.09),(1.8,1.03-j*.21,.15+j*.18),shade(STONE,1.03))
    for x in (-1.45,.11): m.box((x,-2.67,1.62),(.12,.12,2.42),WOOD)
    for side in (-1,1):
        x=-.67+side*.97
        verts=[(-.67,-2.08,3.15),(-.67,-2.98,3.15),(x,-2.98,2.64),(x,-2.08,2.64)]
        m.patch(verts,[(0,1,2,3)] if side>0 else [(3,2,1,0)],shade(PINK,.96))
        m.beam((-.67,-3.00,3.17),(x,-3.00,2.65),.13,.13,TRIM)
    # Masonry chimney with a visible dark opening.
    m.box((-1.28,1.17,4.63),(.52,.60,1.55),shade(STONE,1.05))
    m.box((-1.28,1.17,5.44),(.68,.74,.18),STONE)
    m.box((-1.28,1.17,5.54),(.38,.43,.025),rgb('55594a'))
    return m


def noise2(x,y):
    """Smooth deterministic value noise; no external noise package."""
    ix,iy=floor(x),floor(y); tx=smooth(0,1,x-ix); ty=smooth(0,1,y-iy)
    def h(a,b):
        n=(a*374761393+b*668265263+1442695041)&0xffffffff
        n=((n^(n>>13))*1274126177)&0xffffffff
        return ((n^(n>>16))&65535)/65535
    return (h(ix,iy)*(1-tx)+h(ix+1,iy)*tx)*(1-ty)+(h(ix,iy+1)*(1-tx)+h(ix+1,iy+1)*tx)*ty

