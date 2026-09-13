"""Hand-authored low-poly landmark recipes. Every repeated prop is one shared mesh.
No downloaded assets, font files, Blender operators, or texture dependencies.
"""
from math import sin, cos, pi, sqrt
import random
from cozy_mesh_library import (Mesh, rgb, shade, mix, add, sub, mul, norm, cross,
    transformed, BARK, WOOD, TRIM, CREAM, LEAF, PINE, GRASS, SAND, STONE, PINK,
    broadleaf, cottage, flowers)

TEAL=rgb('78a997'); CORAL=rgb('d98578'); BLUE=rgb('83b6c3'); ROPE=rgb('c9b987')


def gazebo():
    m=Mesh('CF_Gazebo_Sage','Landmarks',collision='complex')
    n=8
    m.tube((0,0,.03),(0,0,.30),2.7,2.7,WOOD,n)
    for i in range(n):
        a=pi/8+2*pi*i/n; b=a+2*pi/n
        x,y=2.4*cos(a),2.4*sin(a)
        m.tube((x,y,.3),(x,y,3.25),.09,.09,TRIM,6)
        if i not in (4,5):
            for h in (.52,1.22):
                m.beam((x,y,h),(2.4*cos(b),2.4*sin(b),h),.09,.11,WOOD)
            for t in (.25,.5,.75):
                xx=x*(1-t)+2.4*cos(b)*t; yy=y*(1-t)+2.4*sin(b)*t
                m.beam((xx,yy,.55),(xx,yy,1.18),.055,.055,TRIM)
        vs=[(3.05*cos(a),3.05*sin(a),3.20),(3.05*cos(b),3.05*sin(b),3.20),
            (1.35*cos(b),1.35*sin(b),4.15),(1.35*cos(a),1.35*sin(a),4.15)]
        m.patch(vs,[(0,1,2,3)],shade(TEAL,1+.04*(i%3)))
        m.patch([(1.35*cos(a),1.35*sin(a),4.15),(1.35*cos(b),1.35*sin(b),4.15),(0,0,4.95)],[(0,1,2)],shade(TEAL,1.08))
        m.beam((3.07*cos(a),3.07*sin(a),3.18),(3.07*cos(b),3.07*sin(b),3.18),.12,.12,CREAM)
    m.tube((0,0,4.90),(0,0,5.24),.08,0,TRIM,6)
    m.box((0,-2.65,.11),(1.7,1.05,.22),WOOD)
    return m


def picnic_table():
    m=Mesh('CF_PicnicTable','Props',collision='simple')
    for y in (-.36,-.12,.12,.36): m.box((0,y,.83),(2.1,.215,.09),WOOD)
    for y in (-.86,.86):
        for dy in (-.1,.1):m.box((0,y+dy,.44),(2.2,.18,.09),TRIM)
    for x in (-.72,.72):
        for s in (-1,1):m.beam((x,s*.93,.03),(x,s*.26,.8),.13,.13,BARK)
        m.beam((x,-1,.36),(x,1,.36),.1,.12,BARK)
    return m


def tent(variant):
    col=[CORAL,TEAL,CREAM][variant]
    m=Mesh(f'CF_Tent_{variant+1:02d}','Camping',material='foliage',collision='complex')
    m.box((0,0,.055),(2.9,3.6,.11),rgb('baa780'))
    # Each face has an intentional normal. Two-sided fabric handles the open doorway.
    m.patch([(-1.5,-1.8,.1),(-1.5,1.8,.1),(0,1.8,2.4),(0,-1.8,2.4)],[(0,3,2,1)],col)
    m.patch([(1.5,-1.8,.1),(1.5,1.8,.1),(0,1.8,2.4),(0,-1.8,2.4)],[(0,1,2,3)],shade(col,.92))
    m.patch([(-1.5,1.8,.1),(1.5,1.8,.1),(0,1.8,2.4)],[(0,2,1)],shade(col,.9))
    for s in (-1,1):
        m.patch([(s*1.5,-1.81,.1),(s*.73,-1.82,.1),(s*.30,-1.81,1.55),(0,-1.81,2.4)],[(0,1,2,3)],shade(CREAM,.98))
        for yy in (-1.8,1.8):
            m.tube((s*1.12,yy,.65),(s*2.1,yy*1.15,.04),.015,.015,ROPE,5)
            m.tube((s*2.1,yy*1.15,0),(s*2.1,yy*1.15,.17),.03,.022,BARK,5)
    m.tube((0,-1.9,.1),(0,-1.9,2.45),.035,.035,BARK,6)
    return m


def campfire():
    m=Mesh('CF_Campfire_Ring','Camping',collision='simple');r=random.Random(20)
    for i in range(12):
        a=2*pi*i/12
        m.ico((cos(a)*.90,sin(a)*.90,.15),(.26,.22,.2),STONE,0,r,.08)
    for angle in (0,pi/2):
        m.tube((-.65*cos(angle),-.65*sin(angle),.18),(.65*cos(angle),.65*sin(angle),.18),.12,.12,shade(BARK,.7),7)
    for i in range(5):
        a=2*pi*i/5
        m.ico((.25*cos(a),.25*sin(a),.25),(.14,.13,.09),rgb('d57642'),0)
        m.tube((.18*cos(a),.18*sin(a),.27),(.09*cos(a+.5),.09*sin(a+.5),.56+i*.06),.15,0,rgb('edb65a'),5)
    return m


def hammock():
    m=Mesh('CF_Hammock','Camping',material='foliage',collision='simple')
    for x in (-2.1,2.1):
        m.beam((x,0,0),(x*.91,0,1.9),.15,.15,BARK)
        m.beam((x,-.8,.04),(x,.8,.04),.14,.14,WOOD)
    vs=[]
    for i in range(13):
        x=-1.88+i*3.76/12; t=i/12
        z=.78+1.05*(abs(x)/1.88)**2
        width=.08+.65*sin(pi*t)
        vs.extend([(x,-width,z),(x,0,z-.12*sin(pi*t)),(x,width,z)])
    fs=[]
    for i in range(12):
        for j in range(2):fs.append((i*3+j,(i+1)*3+j,(i+1)*3+j+1,i*3+j+1))
    m.patch(vs,fs,CREAM)
    return m


def swing():
    m=Mesh('CF_Swing_Timber','Props',collision='simple')
    for x in (-1.55,1.55):
        for y in (-.85,.85):m.beam((x,y,0),(x,0,3.3),.16,.16,WOOD)
        m.beam((x,-.7,.65),(x,.7,.65),.1,.1,TRIM)
    m.beam((-1.8,0,3.3),(1.8,0,3.3),.22,.22,BARK)
    for x in (-.49,.49):m.tube((x,0,3.25),(x,-.05,.62),.017,.017,ROPE,5)
    m.box((0,-.05,.59),(1.16,.44,.12),TRIM)
    return m


def beehive():
    m=Mesh('CF_Beehive','Garden',collision='simple')
    for x in (-.3,.3):
        for y in (-.25,.25):m.box((x,y,.2),(.085,.085,.4),BARK)
    for i in range(3):
        m.box((0,0,.46+i*.22),(.8,.66,.205),[CREAM,TRIM,CREAM][i])
        m.box((0,-.343,.46+i*.22),(.18,.035,.04),BARK)
    m.box((0,0,1.04),(.99,.83,.14),TEAL)
    m.box((0,-.45,.365),(.47,.31,.05),WOOD)
    return m


def garden_bed(variant):
    m=Mesh(f'CF_GardenBed_{variant+1:02d}','Garden',collision='simple')
    m.box((0,0,.13),(2.05,3.05,.26),rgb('715943'))
    for x in (-1.1,1.1):m.box((x,0,.2),(.15,3.34,.4),WOOD)
    for y in (-1.62,1.62):m.box((0,y,.2),(2.35,.14,.4),WOOD)
    for x in (-.57,0,.57):
        for y in (-1,-.34,.34,1):
            if variant==0:
                m.ico((x,y,.42),(.24,.24,.18),rgb('8aaa55'),0)
                for j in range(5):
                    a=j*2*pi/5;m.leaf((x,y,.42),(x+.34*cos(a),y+.34*sin(a),.45),.28,shade(GRASS,1.14),.08)
            elif variant==1:
                m.ico((x,y,.49),(.24,.26,.24),rgb('db9a48'),1,variation=.04)
                m.tube((x,y,.62),(x+.04,y,.86),.032,.019,BARK,5)
                m.leaf((x,y,.64),(x+.31,y+.06,.72),.18,GRASS)
            else:
                for j in range(5):
                    a=j*2*pi/5;m.leaf((x,y,.29),(x+.17*cos(a),y+.17*sin(a),.79),.085,rgb('86a050'),.02)
    return m


def crate():
    m=Mesh('CF_AppleCrate','Garden',collision='simple')
    for y in (-.37,.37):
        for z in (.13,.34):m.box((0,y,z),(.96,.07,.17),WOOD)
    for x in (-.46,.46):
        for z in (.13,.34):m.box((x,0,z),(.075,.74,.17),TRIM)
    m.box((0,0,.05),(.9,.7,.1),BARK)
    for x in (-.28,0,.28):
        for y in (-.2,.06,.22):
            m.ico((x,y,.40),(.14,.14,.135),CORAL,0)
            m.tube((x,y,.48),(x+.01,y,.57),.009,.006,BARK,5)
    return m


def barrel():
    m=Mesh('CF_Barrel','Props',collision='simple')
    for z0,z1,r0,r1 in [(0,.16,.29,.36),(.16,.7,.36,.36),(.7,.9,.36,.29)]:
        m.tube((0,0,z0),(0,0,z1),r0,r1,WOOD,10)
    for z in (.14,.69):m.tube((0,0,z),(0,0,z+.07),.369,.369,rgb('626953'),10)
    m.tube((0,0,.904),(0,0,.92),.29,.29,TRIM,10)
    return m


def lantern():
    m=Mesh('CF_LanternPost','Props',collision='simple')
    m.box((0,0,1.23),(.13,.13,2.46),BARK)
    m.beam((0,0,2.45),(.52,0,2.45),.105,.105,WOOD)
    m.tube((.43,0,2.2),(.43,0,2.44),.015,.015,rgb('6d6955'),5)
    m.box((.43,0,1.98),(.24,.24,.36),rgb('f6d994'))
    for x in (.30,.56):
        for y in (-.13,.13):m.box((x,y,1.98),(.025,.025,.4),BARK)
    m.tube((.43,0,2.18),(.43,0,2.33),.21,0,BARK,4)
    m.box((.43,0,1.76),(.31,.31,.055),BARK)
    return m


def festoon():
    m=Mesh('CF_Festoon_8m','Props',collision='none')
    for x in (-4,4):m.tube((x,0,0),(x,0,3.2),.085,.055,WOOD,6)
    last=None
    for i in range(17):
        x=-4+i*.5; p=(x,0,2.5+.7*(x/4)**2)
        if last:m.tube(last,p,.011,.011,BARK,4)
        last=p
        if i%2:
            m.tube(p,(p[0],0,p[2]-.18),.009,.009,BARK,4)
            m.ico((p[0],0,p[2]-.27),(.09,.09,.11),rgb('f7deb0'),0)
    return m


def market_stall(variant):
    m=Mesh(f'CF_MarketStall_{variant+1:02d}','Village',collision='complex')
    m.box((0,0,.58),(2.4,1.4,1.16),WOOD)
    for x in (-1.15,1.15):
        for y in (-.61,.61):m.box((x,y,1.3),(.1,.1,2.6),BARK)
    for i in range(8):
        x=-1.4+(i+.5)*2.8/8
        m.box((x,-.15,2.60),(2.8/8-.009,1.94,.08),CREAM if i%2 else (TEAL if variant else CORAL),(-.1,0,0))
    m.box((0,-.03,1.19),(2.6,1.66,.1),TRIM)
    for x in (-.75,0,.75):
        m.box((x,-.08,1.3),(.6,.7,.14),BARK)
        for y in (-.28,.04,.3):
            m.ico((x,y,1.49),(.19,.13,.11),rgb('dca765') if variant else CORAL,0)
    return m


def variant_cottage(variant):
    m=cottage();m.name=['CF_Cottage_SageRoof','CF_Cottage_HoneyRoof'][variant]
    target=[TEAL,rgb('d3b15f')][variant]
    new=[]
    for cols in m.colors:
        out=[]
        for c in cols:
            if c[0]>c[1]*1.13 and c[2]>c[1]*1.035 and c[0]>.65:
                out.append(shade(target,c[0]/PINK[0]))
            else:out.append(c)
        new.append(tuple(out))
    m.colors=new
    return m


def windmill():
    m=Mesh('CF_Windmill_Hill','Landmarks',collision='complex')
    m.tube((0,0,0),(0,0,.35),2.18,2.18,STONE,10)
    m.tube((0,0,.35),(0,0,7.6),1.92,1.20,CREAM,10)
    m.tube((0,0,7.55),(0,0,9.15),1.85,0,CORAL,10)
    m.box((0,-1.79,1.32),(1.08,.12,2.04),WOOD)
    for z in (3.2,5.3):
        m.box((0,-1.58+(z-3.2)*.1,z),(.65,.13,.87),BLUE)
        m.box((0,-1.66+(z-3.2)*.1,z),(.075,.14,.9),TRIM)
    center=(0,-1.87,6.8)
    m.tube((0,-1.34,6.8),(0,-2.20,6.8),.20,.20,BARK,10)
    for i in range(4):
        a=pi/7+i*pi/2
        def p(rad,side=0):return (sin(a)*rad+cos(a)*side,-2.23,6.8+cos(a)*rad-sin(a)*side)
        m.beam(p(.25),p(4.25),.14,.15,BARK)
        for k in range(6):
            rad=1.45+k*.49
            m.beam(p(rad,.03),p(rad,.78),.08,.1,TRIM)
        m.beam(p(1.4,.77),p(4.10,.77),.065,.09,WOOD)
        m.patch([p(1.48,.09),p(4.04,.09),p(4.04,.68),p(1.48,.68)],[(3,2,1,0)],shade(CREAM,.93))
    m.tube((0,-2.21,6.8),(0,-2.38,6.8),.28,.28,TRIM,10)
    return m


def lookout_deck():
    m=Mesh('CF_LookoutDeck','Landmarks',collision='complex')
    for i in range(22):m.box((-3.15+(i+.5)*6.3/22,0,1.95),(6.3/22-.015,5,.13),WOOD)
    for x in (-2.8,2.8):
        for y in (-2.2,2.2):m.box((x,y,1.02),(.21,.21,2.04),BARK)
    for y in (-2.45,2.45):
        for x in (-3.05,0,3.05):m.box((x,y,2.5),(.13,.13,1.13),TRIM)
        for z in (2.33,2.99):m.box((0,y,z),(6.3,.12,.10),WOOD)
    for x in (-3.08,3.08):
        for z in (2.33,2.99):m.box((x,.7,z),(.12,3.45,.1),WOOD)
    for i in range(11):
        z=(i+1)*1.92/11
        m.box((0,-6.02+i*.33,z/2),(1.7,.36,z),shade(WOOD,1.04))
    for s in (-1,1):
        m.beam((s*.91,-6.1,1.15),(s*.91,-2.56,3.02),.105,.12,TRIM)
        for y,z in [(-6,1.07),(-4.4,1.90),(-2.65,2.85)]:m.box((s*.91,y,z-.45),(.105,.105,.95),BARK)
    return m


def telescope():
    m=Mesh('CF_Telescope','Props',collision='none')
    for i in range(3):
        a=i*2*pi/3;m.beam((.49*cos(a),.49*sin(a),0),(0,0,1.18),.06,.06,WOOD)
    m.tube((0,-.53,1.56),(0,.61,1.16),.13,.10,TEAL,10)
    m.tube((0,-.62,1.59),(0,-.49,1.545),.16,.16,BARK,10)
    m.tube((0,.61,1.16),(0,.79,1.097),.06,.06,BARK,8)
    return m


def guardian_oak():
    r=random.Random(430);m=Mesh('CF_GuardianOak','Landmarks',collision='tree')
    m.tube((0,0,0),(.18,0,8.4),1.25,.55,BARK,10,r)
    for i in range(8):
        a=i*2*pi/8
        m.tube((.05,.01,1.3),(3.0*cos(a),3.0*sin(a),.1),.48,.035,shade(BARK,1.08),7,r)
        end=(4.15*cos(a),4.15*sin(a),9.6+.6*(i%2))
        m.tube((.1,0,5.4),end,.4,.12,BARK,7,r)
        m.ico(add(end,(0,0,1)),(3.4,3.15,3.0),shade(LEAF,.99+.027*(i%3)),1,r,.065)
    m.ico((0,0,12.0),(4.8,4.1,3.3),shade(LEAF,1.08),2,r,.045)
    for i in range(9):
        a=i*2*pi/9;rr=3.7
        m.tube((rr*cos(a),rr*sin(a),8.6),(rr*cos(a),rr*sin(a),6.05),.014,.014,ROPE,4)
        m.leaf((rr*cos(a),rr*sin(a),6.3),(rr*cos(a)+.08,rr*sin(a),5.45),.21,[CREAM,PINK,TEAL][i%3],.04)
    return m


def stone_arch():
    m=Mesh('CF_Ruin_StoneArch','Ruins',collision='complex');r=random.Random(560)
    for x in (-1.8,1.8):
        for i in range(4):m.box((x,0,.35+i*.64),(.74,.88,.61),shade(STONE,r.uniform(.86,1.13)))
    # Wedge voussoirs around a true, empty semicircular arch.
    n=9
    for i in range(n):
        a=i*pi/n+.018;b=(i+1)*pi/n-.018
        vs=[(rr*cos(t),yy,2.56+rr*sin(t)) for yy in (-.44,.44) for rr,t in [(1.4,a),(2.15,a),(2.15,b),(1.4,b)]]
        m.patch(vs,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],shade(STONE,r.uniform(.93,1.10)))
    for x in (-1.85,1.80):m.ico((x,0,.25),(.85,.70,.25),rgb('879d60'),0)
    return m


def broken_pillar():
    m=Mesh('CF_Ruin_BrokenPillar','Ruins',collision='simple')
    m.box((0,0,.16),(1.05,1.05,.32),STONE)
    m.tube((0,0,.30),(0,0,2.22),.40,.36,shade(STONE,1.10),8)
    m.ico((0,0,2.18),(.43,.41,.22),STONE,0)
    for i in range(3):
        m.leaf((.12,-.40,.6+i*.38),(.36,-.47,.88+i*.38),.20,GRASS,.03)
    return m


def fox_statue():
    m=Mesh('CF_FoxStatue','Landmarks',collision='simple')
    m.box((0,0,.22),(1.38,1.22,.44),STONE)
    col=rgb('b4b8a1')
    m.ico((0,0,1.08),(.44,.35,.68),col,1)
    m.ico((0,-.13,1.78),(.46,.39,.43),col,1)
    for x in (-.28,.28):
        m.tube((x,-.10,2.02),(x*1.12,-.04,2.60),.23,0,col,4)
        m.ico((x,-.43,1.80),(.043,.025,.041),rgb('596654'),0)
    m.ico((0,-.50,1.60),(.22,.26,.16),shade(col,1.06),0)
    m.ico((0,-.70,1.62),(.08,.06,.05),rgb('596654'),0)
    m.ico((.48,.13,.78),(.31,.33,.63),col,1)
    return m


def book_kiosk():
    m=Mesh('CF_BookKiosk','Village',collision='simple')
    m.box((0,0,.75),(.16,.17,1.5),WOOD)
    m.box((0,.15,1.82),(1.55,.10,1.37),BARK)
    for x in (-.77,.77):m.box((x,-.03,1.84),(.13,.56,1.42),TRIM)
    for z in (1.16,1.61,2.06,2.49):m.box((0,-.03,z),(1.57,.55,.10),WOOD)
    cols=[CORAL,TEAL,CREAM,BLUE,rgb('bba2c7')]
    for j,z in enumerate((1.4,1.85,2.27)):
        for i in range(9):m.box((-.60+i*.146,-.08,z),(.115,.31,.32+(i%3)*.025),cols[(i+j)%5])
    for s in (-1,1):
        m.patch([(0,-.49,2.98),(s*.98,-.49,2.52),(s*.98,.52,2.52),(0,.52,2.98)],[(0,1,2,3)] if s>0 else [(3,2,1,0)],TEAL)
    return m


def giant_mushroom():
    m=Mesh('CF_GiantMushroom','Landmarks',collision='simple');r=random.Random(36)
    m.tube((0,0,0),(.16,.05,2.26),.30,.24,CREAM,9)
    n=14;vs=[(.16,.05,3.22)]
    for rad,z in ((.9,2.89),(1.48,2.25),(1.36,2.15)):
        for i in range(n):
            a=i*2*pi/n;vs.append((.16+rad*cos(a),.05+rad*sin(a),z))
    fs=[(0,1+i,1+(i+1)%n) for i in range(n)]
    for row in range(2):
        for i in range(n):a=1+row*n+i;b=1+row*n+(i+1)%n;fs.append((a,a+n,b+n,b))
    fs.append(tuple(reversed(range(1+2*n,1+3*n))))
    m.patch(vs,fs,CORAL,r,.04)
    for i in range(10):
        a=i*2*pi/10;rr=.7 if i%2 else 1.14
        z=3.22-(rr/1.48)**1.6*.96
        m.ico((.16+rr*cos(a),.05+rr*sin(a),z+.03),(.17,.16,.08),CREAM,0)
    return m


def boat():
    m=Mesh('CF_Rowboat','WaterDetails',collision='complex')
    n=10
    # Hollow low-poly hull: outer top/bottom and inset inner gunwale.
    ring=[(1.75*cos(2*pi*i/n),.62*sin(2*pi*i/n)) for i in range(n)]
    vs=[]
    for sx,sy,z in ((.83,.58,-.16),(1,1,.41),(.89,.80,.36),(.71,.35,-.02)):
        vs.extend((x*sx,y*sy,z) for x,y in ring)
    for row in range(3):
        m.patch(vs,[(row*n+i,row*n+(i+1)%n,(row+1)*n+(i+1)%n,(row+1)*n+i) for i in range(n)],shade(WOOD,1+.05*row))
    m.patch(vs,[tuple(range(3*n,4*n))],shade(WOOD,.85))
    for x in (-.68,.48):m.box((x,0,.24),(.29,.85,.075),TRIM)
    for s in (-1,1):
        a=(-.2,s*.52,.34);b=(.88,s*1.33,.17)
        m.tube(a,b,.026,.026,BARK,6)
        m.beam(b,(1.36,s*1.67,.10),.12,.045,TRIM)
    return m


def entrance_gate():
    m=Mesh('CF_WelcomeGate','Landmarks',collision='simple')
    for x in (-2.8,2.8):
        m.box((x,0,1.95),(.29,.32,3.9),WOOD)
        m.tube((x,0,3.87),(x,0,4.25),.34,0,TEAL,4)
        m.beam((x,0,2.8),(x*.62,0,3.77),.15,.15,TRIM)
    m.box((0,0,3.75),(6.2,.22,.36),BARK)
    m.box((0,-.05,3.46),(2.4,.19,.54),TRIM)
    # Leaf emblem made in the XZ plane rather than using an external font.
    m.patch([(-.38,-.155,3.42),(0,-.155,3.27),(.38,-.155,3.53),(0,-.155,3.63)],[(0,1,2,3)],CREAM)
    return m


def apple_tree():
    m=broadleaf(0);m.name='CF_Tree_Apple';m.category='Orchard'
    m.vertices=[(x*.84,y*.84,z*.84) for x,y,z in m.vertices]
    for i in range(18):
        a=i*2*pi/9;rr=1.48+(i%3)*.12; z=2.64+(i//9)*.95
        p=(rr*cos(a),rr*sin(a),z)
        m.ico(p,(.145,.145,.145),CORAL,0)
        m.leaf(add(p,(0,0,.13)),add(p,(.20,.02,.19)),.10,GRASS,.025)
    return m


def blossom_tree():
    m=broadleaf(2);m.name='CF_Tree_Blossom';m.category='BlossomTrees'
    for i,cols in enumerate(m.colors):
        c=cols[0]
        if c[1]>c[0]*.96 and c[1]>c[2]*1.2:
            m.colors[i]=tuple(shade(PINK,.94+c[1]*.12) for _ in range(3))
    return m


def birch_tree():
    m=Mesh('CF_Tree_Birch','Trees',collision='tree');r=random.Random(178)
    m.tube((0,0,0),(.14,0,6.4),.17,.075,CREAM,7)
    for j in range(9):m.tube((.14*j/10,0,.45+j*.56),(.14*j/10,0,.51+j*.56),.174-j*.008,.174-j*.008,rgb('776b51'),7)
    for i in range(4):
        a=2*pi*i/4
        m.tube((.06,0,3.2),(.65*cos(a),.65*sin(a),5.8),.075,.026,CREAM,6)
        m.ico((.60*cos(a),.60*sin(a),5.5+.30*(i%2)),(1.14,1.04,1.8),shade(LEAF,1.04),1,r,.05)
    return m


def willow_tree():
    m=Mesh('CF_Tree_Willow','Trees',collision='tree');r=random.Random(64)
    m.tube((0,0,0),(.10,0,4.2),.26,.12,BARK,8)
    m.ico((0,0,4.4),(2.2,1.9,1.38),rgb('96b477'),1,r,.04)
    for i in range(10):
        a=i*2*pi/10
        m.ico((1.55*cos(a),1.5*sin(a),3.2),(.65,.59,1.7),shade(rgb('9bb879'),1+.045*(i%3)),1,r,.05)
    return m


def flower_patch(variant):
    if variant==0:
        m=flowers(2);m.name='CF_Flowers_Lavender'
        # More upright silhouette and lavender colour.
        m.vertices=[(x,y,z*1.6) for x,y,z in m.vertices]
        for i,cols in enumerate(m.colors):
            c=cols[0]
            if c[2]>c[0]*1.1:m.colors[i]=(rgb('b0a0c7'),)*3
        return m
    m=Mesh('CF_Flowers_Sunflower','Flowers',material='foliage')
    for i in range(5):
        a=i*2*pi/5;x=.5*cos(a);y=.5*sin(a);z=.68+.07*(i%2)
        m.tube((x,y,0),(x,y,z),.017,.013,GRASS,5)
        for j in range(9):
            b=j*2*pi/9;m.leaf((x,y,z),(x+.22*cos(b),y+.22*sin(b),z+.02),.10,rgb('f0ce68'),.05)
        m.ico((x,y,z+.025),(.11,.11,.04),BARK,0)
        m.leaf((x,y,.25),(x+.31,y+.04,.41),.14,GRASS,.025)
    return m


def birdhouse():
    m=Mesh('CF_Birdhouse','Props',collision='none')
    m.tube((0,0,0),(0,0,2.1),.055,.04,BARK,6)
    m.box((0,0,2.13),(.49,.40,.59),CREAM)
    m.tube((0,-.21,2.15),(0,-.22,2.15),.077,.077,BARK,9)
    for s in (-1,1):
        m.patch([(0,-.30,2.68),(s*.36,-.30,2.40),(s*.36,.3,2.4),(0,.3,2.68)],[(0,1,2,3)] if s>0 else [(3,2,1,0)],CORAL)
    m.tube((0,-.19,1.97),(0,-.41,1.97),.022,.022,WOOD,6)
    return m


def duck():
    m=Mesh('CF_Duck_Sitting','WaterDetails')
    m.ico((0,0,.22),(.33,.23,.23),CREAM,1)
    m.ico((.23,0,.47),(.17,.16,.18),CREAM,1)
    m.box((.42,0,.45),(.19,.15,.065),rgb('d5a140'))
    for y in (-.144,.144):m.ico((.30,y,.50),(.025,.019,.025),rgb('4e5442'),0)
    m.tube((-.25,0,.26),(-.48,0,.33),.10,0,CREAM,5)
    return m


def all_new_assets():
    return [gazebo(),picnic_table(),*[tent(i) for i in range(3)],campfire(),hammock(),swing(),beehive(),
        *[garden_bed(i) for i in range(3)],crate(),barrel(),lantern(),festoon(),*[market_stall(i) for i in range(2)],
        *[variant_cottage(i) for i in range(2)],windmill(),lookout_deck(),telescope(),guardian_oak(),stone_arch(),
        broken_pillar(),fox_statue(),book_kiosk(),giant_mushroom(),boat(),entrance_gate(),apple_tree(),blossom_tree(),
        birch_tree(),willow_tree(),*[flower_patch(i) for i in range(2)],birdhouse(),duck()]
