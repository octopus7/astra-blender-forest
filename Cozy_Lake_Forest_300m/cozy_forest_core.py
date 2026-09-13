"""Cozy Lake Forest 300 m -- deterministic shared geometry and authored world layout.
Units are metres. This module runs in plain Python, without bpy or other packages.
The 300 x 300 terrain is not a scaled-up 64 m scene: paths, water and POIs are new.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from math import sin,cos,sqrt,atan2,pi,floor,isfinite
from functools import lru_cache
import random,json,hashlib
from cozy_mesh_library import (Mesh,clamp,smooth,rgb,shade,mix,add,sub,mul,dot,cross,norm,
    transformed,noise2,GRASS,SAND,WATER,broadleaf,pine,rock,shrub,fern,grass,flowers,
    mushrooms,cattails,lilypad,ripple,bench,fence,signpost,stump,bridge,dock,cottage,well)
from cozy_landmarks import all_new_assets

VERSION='2.0.0'
DEFAULTS={
    'seed':42,'map_size_m':300.0,'terrain_resolution':480,'terrain_tiles_per_axis':6,
    'tree_count':3800,'ground_detail_count':10000,'shore_rock_count':600,
    'meadow_flower_count':900,'shore_plant_count':360,'lily_count':250,
    'path_width_m':2.8,'tree_min_spacing_m':3.15,
    'include_cabin':True,'include_well':True,'include_bridge':True,'include_dock':True,
    'include_landmarks':True,'include_micro_props':True,
    'render_resolution_x':1800,'render_resolution_y':1300,'render_samples':48,
    'render_preview_on_build':False,'save_blend_on_build':False,
    'viewport_material_preview':False,'output_directory':'./output',
}

# name, English title, Korean title, x, y, clearing radius, levelled ground height
POI_SPECS=[
 ('village','Lakeside Village','호숫가 작은 마을',64,37,17,2.15),
 ('meadow','Wildflower Garden','꽃바람 정원',-79,28,21,1.85),
 ('camp','Lantern Camp','랜턴 캠핑장',-58,-43,15,2.05),
 ('orchard','Honey Orchard','꿀벌 과수원',78,-94,22,2.4),
 ('lookout','Windmill Lookout','풍차 전망 언덕',99,98,15,7.1),
 ('guardian','Wishing Grove','소원 나무 숲',-98,95,15,3.7),
 ('ruins','Mossy Sanctuary','이끼 낀 작은 유적',-103,-101,15,2.65),
 ('fishing','Quiet Fishing Pond','조용한 낚시 연못',98,-61,9,.9),
 ('reading','Forest Library','숲속 책 쉼터',3,103,11,2.8),
 ('mushroom','Mushroom Tea Garden','버섯 티 가든',33,-105,13,2.05),
 ('arrival','Welcome Clearing','숲 입구 쉼터',54,-133,10,1.7),
 ('boathouse','Lakeside Picnic','물가 피크닉터',29,-16,8,1.05),
]


def validate_config(config=None):
    c=dict(DEFAULTS)
    if config:
        extra=set(config)-set(c)
        if extra:raise ValueError('Unknown configuration keys: '+', '.join(sorted(extra)))
        c.update(config)
    if not isinstance(c['map_size_m'],(float,int)) or not 240<=c['map_size_m']<=480:
        raise ValueError('map_size_m must be 240..480 metres; the authored default is 300.')
    n=c['terrain_resolution'];nt=c['terrain_tiles_per_axis']
    if type(n) is not int or type(nt) is not int or not 1<=nt<=12 or not 60<=n<=900 or n%nt:
        raise ValueError('terrain_resolution must be 60..900, divisible by terrain_tiles_per_axis (1..12).')
    for key,limit in [('tree_count',14000),('ground_detail_count',40000),('shore_rock_count',2000),
                      ('meadow_flower_count',5000),('shore_plant_count',2000),('lily_count',2000)]:
        if type(c[key]) is not int or not 0<=c[key]<=limit:raise ValueError(f'{key}: integer 0..{limit}.')
    for key,lo,hi in [('path_width_m',1.8,6),('tree_min_spacing_m',2.8,8)]:
        if not isinstance(c[key],(int,float)) or not lo<=c[key]<=hi:raise ValueError(f'{key}: {lo}..{hi}.')
    if type(c['seed']) is not int:raise ValueError('seed must be an integer.')
    for key in ('include_cabin','include_well','include_bridge','include_dock','include_landmarks',
                'include_micro_props','render_preview_on_build','save_blend_on_build','viewport_material_preview'):
        if type(c[key]) is not bool:raise ValueError(key+' must be true/false.')
    if c['render_resolution_x']<64 or c['render_resolution_y']<64 or c['render_samples']<1:
        raise ValueError('Invalid render settings.')
    return c


def sample_curve(points,subdivisions=6):
    """Clamped Catmull-Rom polyline; geometry is painted into terrain, not floating decals."""
    out=[]
    for i in range(len(points)-1):
        p0=points[max(0,i-1)];p1=points[i];p2=points[i+1];p3=points[min(len(points)-1,i+2)]
        for j in range(subdivisions):
            t=j/subdivisions;t2=t*t;t3=t2*t
            out.append(tuple(.5*((2*p1[k])+(-p0[k]+p2[k])*t+(2*p0[k]-5*p1[k]+4*p2[k]-p3[k])*t2+
                            (-p0[k]+3*p1[k]-3*p2[k]+p3[k])*t3) for k in (0,1)))
    return out+[tuple(points[-1])]


class Layout:
    def __init__(self,cfg):
        self.config=cfg;self.half=cfg['map_size_m']/2;self.k=cfg['map_size_m']/300
        k=self.k
        self.lakes=[{'name':'main_lake','center':(5*k,20*k),'rx':43*k,'ry':33*k},
                    {'name':'mirror_pond','center':(-55*k,89*k),'rx':13*k,'ry':10*k},
                    {'name':'fishing_pond','center':(96*k,-42*k),'rx':17*k,'ry':12*k}]
        self.pois=[{'id':a,'title':b,'title_ko':c,'x':x*k,'y':y*k,'radius':rad*k,'height':z,
                    'enabled':cfg['include_landmarks'] or (a=='village' and cfg['include_cabin'])}
                   for a,b,c,x,y,rad,z in POI_SPECS]
        self.poi={p['id']:p for p in self.pois}
        self.bridge_ys=[-34*k,-80*k,-129*k]
        self.blockers=[]
        def sc(points):return [(x*k,y*k) for x,y in points]
        def rs(y):return self.stream_x(y*k)/k
        self.routes=[]
        def route(name,pts,curved=True):
            self.routes.append({'id':name,'points':sample_curve(sc(pts),5) if curved else sc(pts)})
        # Continuous outer walking route, with a flat crossing at the southern bridge.
        route('outer_walk',[(54,-143),(54,-133),(69,-120),(78,-94),(103,-78),(98,-61),
             (119,-24),(115,4),(86,20),(64,37),(80,64),(99,98),(57,120),(7,123),
             (-40,123),(-77,119),(-98,95),(-115,64),(-92,44),(-79,28),(-87,-5),
             (-68,-23),(-58,-43),(-79,-65),(-103,-101),(-71,-121),(rs(-129)-13,-129)])
        route('outer_bridge',[(rs(-129)-13,-129),(rs(-129)+13,-129)],False)
        route('outer_return',[(rs(-129)+13,-129),(28,-134),(54,-133)])
        # Lakeside loop leaves enough bank for foliage and benches.
        ring=[]
        for i in range(81):
            a=2*pi*i/80;x,y=self.shore_point(a,6.6*k,0);ring.append((x,y))
        self.routes.append({'id':'lake_loop','points':ring})
        route('camp_to_lake',[(-58,-43),(-38,-37),(rs(-34)-12,-34)])
        route('middle_bridge',[(rs(-34)-12,-34),(rs(-34)+12,-34)],False)
        route('middle_to_lake',[(rs(-34)+12,-34),(29,-28),(29,-16),(38,-7)])
        route('garden_link',[(-79,28),(-60,38),(-49,34),(-44,22)])
        route('north_library',[(3,123),(3,103),(12,84),(4,67),(6,59)])
        route('village_link',[(64,37),(54,28),(51,23)])
        route('orchard_mushroom',[(78,-94),(58,-94),(33,-105),(23,-93),(rs(-80)+12,-80)])
        route('lower_bridge',[(rs(-80)+12,-80),(rs(-80)-12,-80)],False)
        route('camp_lower',[(rs(-80)-12,-80),(-35,-73),(-52,-63),(-58,-43)])
        route('mirror_pond_walk',[(-98,95),(-80,89),(-73,76),(-60,72),(-42,74),(-25,92),(3,103)])
        self._segments=defaultdict(list);bin_size=16*k
        self.bin_size=bin_size
        for r in self.routes:
            for a,b in zip(r['points'],r['points'][1:]):
                dx=b[0]-a[0];dy=b[1]-a[1];ll=dx*dx+dy*dy
                if ll<1e-12:continue
                seg=(a[0],a[1],dx,dy,1/ll)
                reach=7
                for ix in range(floor((min(a[0],b[0])-reach)/bin_size),floor((max(a[0],b[0])+reach)/bin_size)+1):
                    for iy in range(floor((min(a[1],b[1])-reach)/bin_size),floor((max(a[1],b[1])+reach)/bin_size)+1):
                        self._segments[(ix,iy)].append(seg)
        self._sample_cache={}

    def boundary(self,a):return 1+.038*sin(3*a+.4)+.022*sin(5*a-.9)+.016*cos(7*a)

    def shore_point(self,a,offset=0,lake_index=0):
        p=self.lakes[lake_index];r=self.boundary(a)
        return (p['center'][0]+(p['rx']*r+offset)*cos(a),p['center'][1]+(p['ry']*r+offset)*sin(a))

    def stream_x(self,y):
        yy=y/self.k
        return self.k*(-3+10*sin((yy+40)*.035)+2*sin(yy*.073))

    def stream_half(self,y):return (2.20+.30*sin(y/self.k*.043)+.19*cos(y/self.k*.081))*self.k

    def water_distance(self,x,y):
        best=1e9
        for p in self.lakes:
            xx=(x-p['center'][0])/p['rx'];yy=(y-p['center'][1])/p['ry']
            a=atan2(yy,xx)
            best=min(best,(sqrt(xx*xx+yy*yy)-self.boundary(a))*min(p['rx'],p['ry']))
        stream=max(abs(x-self.stream_x(y))-self.stream_half(y),y+5*self.k)
        return min(best,stream)

    def path_distance(self,x,y):
        best=1e6
        for a,b,dx,dy,inv in self._segments.get((floor(x/self.bin_size),floor(y/self.bin_size)),()):
            t=clamp(((x-a)*dx+(y-b)*dy)*inv)
            d=(x-a-t*dx)**2+(y-b-t*dy)**2
            if d<best:best=d
        return sqrt(best)

    def path_half_width(self,x,y):return self.config['path_width_m']*.5+.12*sin(x*.18+y*.12)

    def raw_height(self,x,y,d=None):
        d=self.water_distance(x,y) if d is None else d
        if d<0:return max(-2.4,d*.70)
        xx=x/self.k;yy=y/self.k
        h=.78+1.45*noise2(xx*.020+31,yy*.020-4)+.25*sin(xx*.031)*cos(yy*.043)
        # Broad, gently sloped hills, not scaled-up mountain geometry.
        h+=5.7*max(0,1-((xx-99)**2+(yy-98)**2)/54**2)**2
        h+=2.7*max(0,1-((xx+113)**2+(yy-110)**2)/49**2)**2
        return h*smooth(0,4.8*self.k,d)

    def height(self,x,y,d=None):
        d=self.water_distance(x,y) if d is None else d
        h=self.raw_height(x,y,d)
        if d<0:return h
        for p in self.pois:
            if not p['enabled']:continue
            dx=x-p['x'];dy=y-p['y'];r=p['radius']
            if abs(dx)>r+5*self.k or abs(dy)>r+5*self.k:continue
            dist=sqrt(dx*dx+dy*dy)
            f=(1-smooth(r*.78,r+5*self.k,dist))*smooth(.4,4.2*self.k,d)
            h=h*(1-f)+p['height']*f
        return h

    def ground_color(self,x,y,d=None,pd=None):
        d=self.water_distance(x,y) if d is None else d
        pd=self.path_distance(x,y) if pd is None else pd
        n=noise2(x*.21+7,y*.21);fine=noise2(x*1.7,y*1.7)
        col=mix(rgb('8fa951'),rgb('adbb69'),clamp(.1+n*.82))
        col=shade(col,.945+fine*.10)
        p=self.poi['meadow'];dist=sqrt((x-p['x'])**2+(y-p['y'])**2)
        if p['enabled'] and dist<p['radius']:col=mix(col,rgb('a9bd76'),.34)
        width=self.path_half_width(x,y)
        path=1-smooth(width-.2,width+.42,pd)
        shore=1-smooth(.55,1.48*self.k,d)
        col=mix(col,shade(SAND,.965+.05*n),max(path,shore))
        for key in ('village','arrival','ruins'):
            p=self.poi[key]
            rr={'village':6,'arrival':4,'ruins':4}[key]*self.k
            ds=sqrt((x-p['x'])**2+(y-p['y'])**2)
            if p['enabled'] and ds<rr+.6:
                col=mix(col,shade(SAND,.97),1-smooth(rr-.4,rr+.6,ds))
        if d<-.10:col=mix(rgb('b9c69d'),rgb('5b8977'),smooth(.1,2.2,-d))
        return col

    def reserved(self,x,y,margin=0):
        for p in self.pois:
            if p['enabled'] and (x-p['x'])**2+(y-p['y'])**2<(p['radius']+margin)**2:return True
        for yy in self.bridge_ys:
            if abs(y-yy)<2.4+margin and abs(x-self.stream_x(yy))<5.5+margin:return True
        for xx,yy,rr in self.blockers:
            if (x-xx)**2+(y-yy)**2<(rr+margin)**2:return True
        return False

    def blocked(self,x,y,margin=0):
        return any((x-xx)**2+(y-yy)**2<(rr+margin)**2 for xx,yy,rr in self.blockers)

    def zone(self,x,y):
        best=min(self.pois,key=lambda p:(x-p['x'])**2+(y-p['y'])**2)
        return best['id']

    def terrain_sample(self,x,y):
        d=self.water_distance(x,y);p=self.path_distance(x,y)
        return self.height(x,y,d),self.ground_color(x,y,d,p),d


@dataclass
class World:
    config:dict
    assets:dict=field(default_factory=dict)
    instances:list=field(default_factory=list)
    notes:list=field(default_factory=list)
    points_of_interest:list=field(default_factory=list)
    routes:list=field(default_factory=list)

    def register(self,mesh):
        if mesh.name in self.assets:raise ValueError('Duplicate asset_id: '+mesh.name)
        self.assets[mesh.name]=mesh;return mesh.name

    def cell(self,x,y):
        half=self.config['map_size_m']/2;nt=self.config['terrain_tiles_per_axis'];size=2*half/nt
        ix=int(clamp(floor((x+half)/size),0,nt-1));iy=int(clamp(floor((y+half)/size),0,nt-1))
        return f'C{ix:02d}_{iy:02d}'

    def place(self,asset,location=(0,0,0),rotation=(0,0,0),scale=(1,1,1),label=None,zone='forest',source='authored'):
        if isinstance(scale,(float,int)):scale=(scale,scale,scale)
        if asset not in self.assets:raise KeyError(asset)
        record={'name':label or f'{asset}__{len(self.instances):06d}','asset_id':asset,
                'location':tuple(location),'rotation_euler_xyz':tuple(rotation),'scale':tuple(scale),
                'cell_id':self.cell(location[0],location[1]),'zone':zone,'source':source}
        self.instances.append(record)
        return record

    def stats(self):
        counts=Counter(i['asset_id'] for i in self.instances)
        cat=Counter(self.assets[i['asset_id']].category for i in self.instances)
        return {'version':VERSION,'map_size_m':self.config['map_size_m'],
            'area_m2':self.config['map_size_m']**2,'cell_size_m':self.config['map_size_m']/self.config['terrain_tiles_per_axis'],
            'cells':self.config['terrain_tiles_per_axis']**2,
            'unique_assets':len(self.assets),'placed_instances':len(self.instances),
            'unique_triangles':sum(len(m.faces) for m in self.assets.values()),
            'placed_triangles':sum(len(self.assets[k].faces)*n for k,n in counts.items()),
            'forest_trees':sum(1 for i in self.instances if i['source']=='forest_tree'),
            'trees':sum(cat[x] for x in ('Trees','Orchard','BlossomTrees')),
            'trees_including_guardian':sum(cat[x] for x in ('Trees','Orchard','BlossomTrees'))+counts.get('CF_GuardianOak',0),
            'landmark_zones':len([p for p in self.points_of_interest if p['enabled']]),
            'categories':dict(cat),'instance_counts':dict(sorted(counts.items())),
            'cell_instance_counts':dict(sorted(Counter(i['cell_id'] for i in self.instances).items())),
            'zone_instance_counts':dict(sorted(Counter(i['zone'] for i in self.instances).items()))}


def build_terrain(w,L):
    """Terrain and clipped water per spatial cell, without seams or overlapping water."""
    cfg=w.config;n=cfg['terrain_resolution'];nt=cfg['terrain_tiles_per_axis'];tn=n//nt
    half=cfg['map_size_m']/2;step=2*half/n
    # Global shared samples ensure identical heights/colours at tile boundaries.
    grid=[];cols=[];ds=[]
    for j in range(n+1):
        y=-half+j*step
        for i in range(n+1):
            x=-half+i*step;z,c,d=L.terrain_sample(x,y)
            grid.append((x,y,z));cols.append(c);ds.append(d)
    for ty in range(nt):
        for tx in range(nt):
            origin=(-half+tx*tn*step,-half+ty*tn*step,0)
            m=Mesh(f'CF_Terrain_{tx:02d}_{ty:02d}','Terrain',collision='complex',smooth_shading=True)
            vs=[];vc=[]
            for j in range(tn+1):
                for i in range(tn+1):
                    gi=(ty*tn+j)*(n+1)+tx*tn+i
                    vs.append(sub(grid[gi],origin));vc.append(cols[gi])
            fs=[]
            for j in range(tn):
                for i in range(tn):
                    a=j*(tn+1)+i;b=a+1;d=a+tn+1;c=d+1
                    fs.extend([(a,b,c),(a,c,d)] if ((tx*tn+i)+(ty*tn+j))%2==0 else [(a,b,d),(b,c,d)])
            m.patch(vs,fs,GRASS,corner_colors=vc);w.register(m);w.place(m.name,origin,zone='terrain',source='terrain')
            water=Mesh(f'CF_Water_{tx:02d}_{ty:02d}','Water',material='water',smooth_shading=True)
            def clip(indices):
                pts=[(grid[k][0],grid[k][1],ds[k]) for k in indices];out=[]
                for a,b in zip(pts,pts[1:]+pts[:1]):
                    ina=a[2]<=0;inb=b[2]<=0
                    if ina:out.append(a)
                    if ina!=inb:
                        t=a[2]/(a[2]-b[2]);out.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),0))
                for j in range(1,len(out)-1):
                    pts3=[out[0],out[j],out[j+1]]
                    verts=[(p[0]-origin[0],p[1]-origin[1],.004) for p in pts3]
                    a,b,c=verts;area=cross(sub(b,a),sub(c,a))
                    if dot(area,area)<1e-14:continue
                    colors=[mix(rgb('9bcebb'),rgb('4eafb9'),smooth(.08,4.0,-L.water_distance(p[0],p[1]))) for p in pts3]
                    water.patch(verts,[(0,1,2)],WATER,corner_colors=colors)
            for j in range(tn):
                for i in range(tn):
                    gj=ty*tn+j;gi=tx*tn+i;a=gj*(n+1)+gi;b=a+1;d=a+n+1;c=d+1
                    tris=[(a,b,c),(a,c,d)] if (gi+gj)%2==0 else [(a,b,d),(b,c,d)]
                    for tri in tris:
                        if min(ds[t] for t in tri)<=0:clip(tri)
            if water.faces:w.register(water);w.place(water.name,origin,zone='water',source='water')


def build_landmarks(w,L,r):
    cfg=w.config;k=L.k
    def ground(asset,x,y,scale=1,yaw=0,dz=0,label=None,zone=None,block=0,normalized=True):
        if normalized:x*=k;y*=k
        rec=w.place(asset,(x,y,L.height(x,y)+dz),(0,0,yaw),scale,label,zone or L.zone(x,y),'authored')
        if block:L.blockers.append((x,y,block))
        return rec
    def local(zone,asset,dx=0,dy=0,scale=1,yaw=0,dz=0,block=0):
        p=L.poi[zone]
        return ground(asset,p['x']/k+dx,p['y']/k+dy,scale,yaw,dz,zone=zone,block=block)
    if cfg['include_cabin']:
        local('village','CF_Cottage_RoseRoof',-8,6,1.12,-.12,block=4.4)
        local('village','CF_Cottage_SageRoof',3,9,1.06,.06,block=4.2)
        local('village','CF_Cottage_HoneyRoof',11,2,1.08,-pi/2,block=4.3)
    if cfg['include_well']:local('village','CF_Well_StoneWood',0,0,1.15,block=1.7)
    if cfg['include_bridge']:
        for j,y in enumerate(L.bridge_ys):
            x=L.stream_x(y);sx=max(1.7,(L.stream_half(y)*2+5)/5.8)
            half_length=2.9*sx
            z=max(L.height(x-half_length,y),L.height(x+half_length,y))-.17
            w.place('CF_Bridge_Arched',(x,y,z),(0,0,0),(sx,1.45,1),f'CF_Bridge_{j+1:02d}',zone='river')
            L.blockers.append((x,y,half_length))
    if cfg['include_dock']:
        for j,(idx,angle) in enumerate([(0,-.88),(0,.09),(1,-.70),(2,-pi/2)]):
            x,y=L.shore_point(angle,.65*k,idx)
            # Long axis points from dry bank towards the lake centre.
            p=L.lakes[idx]['center'];yaw=atan2(p[1]-y,p[0]-x)
            w.place('CF_Dock_Wood',(x,y,.69),(0,0,yaw),(1.8,1.35,1),f'CF_Dock_{j+1:02d}',zone='lakeshore')
            L.blockers.append((x,y,3.4))
            if cfg['include_landmarks']:
                bx=x+cos(yaw)*4.2-sin(yaw)*2.2;by=y+sin(yaw)*4.2+cos(yaw)*2.2
                w.place('CF_Rowboat',(bx,by,.05),(0,0,yaw+.12),1,zone='lakeshore')
    if not cfg['include_landmarks']:return
    local('village','CF_MarketStall_01',-7,-5,1,.12,block=2.0)
    local('village','CF_MarketStall_02',1,-7,1,-.12,block=2.0)
    local('village','CF_BookKiosk',8,-3,1,-.5)
    for dx,dy in [(-8,-11),(8,-10)]:local('village','CF_PicnicTable',dx,dy,1,.15,block=1.5)
    for dy in (-5,3):local('village','CF_Festoon_8m',-4,dy,1,.1)
    local('meadow','CF_Gazebo_Sage',0,0,1.1,0,block=3.7)
    local('meadow','CF_Swing_Timber',10,6,1,-.4,block=2.3)
    for dx,dy in [(-9,8),(-12,7),(-15,7)]:local('meadow','CF_Beehive',dx,dy,1.1,-.3,block=.8)
    for dx,dy in [(-10,-7),(10,-9)]:local('meadow','CF_Bench_Wood',dx,dy,1,pi if dy>0 else 0,block=1.0)
    # Camp: entrances face the central hearth, with tables and hanging lamps.
    local('camp','CF_Campfire_Ring',0,0,1.25,block=1.5)
    for i,a in enumerate((.35,2.35,4.4)):
        dx=8.4*cos(a);dy=8.4*sin(a);yaw=a-pi/2
        local('camp',f'CF_Tent_{i+1:02d}',dx,dy,1.07,yaw,block=3.0)
    for a in (1.1,3.2,5.15):
        local('camp','CF_Bench_Wood',3.7*cos(a),3.7*sin(a),1,a-pi/2,block=1.1)
    local('camp','CF_Hammock',-9,3,1,.4,block=2.5)
    local('camp','CF_PicnicTable',6,-4,1,-.2,block=1.8)
    local('camp','CF_Festoon_8m',-.5,10,1,.1)
    # Orderly orchard with 30 deliberately shared trees, garden rows and beehives.
    for iy in range(5):
        for ix in range(6):
            dx=-15+ix*5.1; dy=-2+iy*4.5; p=L.poi['orchard']
            if L.path_distance(p['x']+dx*k,p['y']+dy*k)<3.0: continue
            local('orchard','CF_Tree_Apple',dx,dy,r.uniform(.81,1.04),r.uniform(0,2*pi),block=1.7)
    for iy in range(2):
        for ix in range(5):local('orchard',f'CF_GardenBed_{(ix+iy)%3+1:02d}',-10+ix*4.4,-12+iy*4.7,1,block=1.9)
    for dx in (-16,-13,-10):local('orchard','CF_Beehive',dx,-17,1.15,.25,block=.8)
    local('orchard','CF_MarketStall_01',12,-13,1.1,-.2,block=2.4)
    for dx,dy in [(10,-16),(13,-17),(15,-16)]:local('orchard','CF_AppleCrate',dx,dy,1.1,.1)
    # Windmill summit. Deck is lower to the south so stairs enter the trail.
    local('lookout','CF_Windmill_Hill',4,4,1.15,.10,block=5.3)
    local('lookout','CF_LookoutDeck',-5,-5,1,-.18,block=6.5)
    local('lookout','CF_Telescope',-5,-5,1,-.65,dz=2.035,block=0)
    local('lookout','CF_Bench_Wood',10,-6,1,.9,block=1)
    local('guardian','CF_GuardianOak',0,1,1,0,block=6.4)
    local('guardian','CF_Swing_Timber',-8,-3,1.1,.35,block=2.4)
    local('guardian','CF_FoxStatue',6,-5,1.15,.3,block=1)
    local('guardian','CF_Bench_Wood',-3,-8,1,0,block=1)
    # Sympathetic small-scale ruins, not a large castle.
    for dx,dy,yaw in [(-4,2,.3),(3,5,-.7)]:local('ruins','CF_Ruin_StoneArch',dx,dy,1.15,yaw,block=3.3)
    for dx,dy in [(-8,-2),(8,-2),(-3,-7),(5,10)]:local('ruins','CF_Ruin_BrokenPillar',dx,dy,r.uniform(.8,1.2),r.random(),block=1)
    local('ruins','CF_FoxStatue',0,0,1.35,0,block=1.3)
    local('ruins','CF_Bench_Wood',6,-7,1,-.5)
    local('fishing','CF_Bench_Wood',4,-1,1,pi,block=1)
    local('fishing','CF_PicnicTable',-3,-2,1,.1,block=1.5)
    local('reading','CF_Gazebo_Sage',0,0,.95,0,block=3.1)
    local('reading','CF_BookKiosk',5,-3,1.12,-.4,block=1.1)
    for dx,dy in [(-5,-3),(3,5)]:local('reading','CF_Bench_Wood',dx,dy,1,0,block=1)
    for i,(dx,dy,sc) in enumerate([(-5,3,1.45),(4,4,1.16),(7,-3,.95),(-6,-5,.75)]):
        local('mushroom','CF_GiantMushroom',dx,dy,sc,r.random(),block=2.0*sc)
    local('mushroom','CF_PicnicTable',0,0,1,.2,block=1.7)
    local('mushroom','CF_Stump',4,-2,1.2)
    local('arrival','CF_WelcomeGate',0,-4,1.15,0,block=3.6)
    local('arrival','CF_Signpost',-4,1,1.25,.3)
    local('arrival','CF_Bench_Wood',6,2,1,-.4)
    local('boathouse','CF_PicnicTable',0,-2,1,.3,block=1.7)
    local('boathouse','CF_Bench_Wood',-3,2,1,pi,block=1)
    # Repeated cherry blossom trees frame several clearings instead of filling a grid.
    for zone,n,rr in [('meadow',9,17),('reading',7,9.5),('village',6,16),('mushroom',5,11)]:
        p=L.poi[zone]
        for i in range(n):
            a=(i+.4)*2*pi/n;x=p['x']+rr*k*cos(a);y=p['y']+rr*k*sin(a)
            if L.water_distance(x,y)<3 or L.path_distance(x,y)<3 or L.blocked(x,y,2):continue
            ground('CF_Tree_Blossom',x,y,r.uniform(.80,1.13),r.uniform(0,2*pi),zone=zone,block=2,normalized=False)
    # A few shore ducks; static posed props, not AI or animated characters.
    for idx,n in [(0,9),(1,5),(2,5)]:
        for j in range(n):
            a=r.uniform(0,2*pi);x,y=L.shore_point(a,-r.uniform(3,6),idx)
            if L.water_distance(x,y)<-.5:
                w.place('CF_Duck_Sitting',(x,y,.018),(0,0,r.uniform(0,2*pi)),r.uniform(.9,1.12),zone='water')
    if not cfg['include_micro_props']:return
    for key in ('village','camp','orchard','reading','arrival','mushroom'):
        for dx,dy in [(-6,-5),(6,5)]:local(key,'CF_LanternPost',dx,dy,1,.3)
    for key in ('village','orchard','camp'):
        for dx,dy in [(5,7),(6,8)]:local(key,'CF_Barrel',dx,dy,1,.1)
    for key in ('meadow','reading','guardian'):
        for dx,dy in [(6,7),(-7,-6)]:local(key,'CF_Birdhouse',dx,dy,1,.2)
    for key in ('village','orchard'):
        p=L.poi[key]
        # Fence runs use an exact 2.4 m pitch so shared segment endpoints join.
        for y in (-19,19):
            for i in range(12):
                x=p['x']+(-13.2+2.4*i)*k;yy=p['y']+y*k
                if L.path_distance(x,yy)>2.5 and L.water_distance(x,yy)>2:
                    ground('CF_Fence_Segment',x,yy,k,0,zone=key,normalized=False)
    for route in L.routes:
        if len(route['points'])<8:continue
        pts=route['points']
        for i in range(2,len(pts)-2,18):
            x,y=pts[i];px,py=pts[i+1];dx,dy=px-x,py-y;length=sqrt(dx*dx+dy*dy)
            if length<.01:continue
            x+=-dy/length*2.5;y+=dx/length*2.5
            if L.water_distance(x,y)>2 and not L.blocked(x,y,.8):
                ground('CF_LanternPost',x,y,.92,atan2(dy,dx),normalized=False)
    for key in ('meadow','camp','orchard','guardian','ruins','reading','fishing'):
        p=L.poi[key];local(key,'CF_Signpost',0,-p['radius']/k+1,1.15,.35)


class SpatialHash:
    def __init__(self,cell):self.cell=cell;self.data=defaultdict(list)
    def key(self,x,y):return floor(x/self.cell),floor(y/self.cell)
    def add(self,x,y,r=0):self.data[self.key(x,y)].append((x,y,r))
    def clear(self,x,y,d):
        ix,iy=self.key(x,y);n=int(d/self.cell)+1
        for a in range(ix-n,ix+n+1):
            for b in range(iy-n,iy+n+1):
                for xx,yy,rr in self.data.get((a,b),()):
                    if (x-xx)**2+(y-yy)**2<max(d,rr)**2:return False
        return True


def scatter_forest(w,L,r):
    cfg=w.config;bound=L.half-4.8;spacing=cfg['tree_min_spacing_m'];grid=SpatialHash(spacing)
    count=0;attempts=0;max_attempts=max(500,cfg['tree_count']*70)
    while count<cfg['tree_count'] and attempts<max_attempts:
        attempts+=1;x=r.uniform(-bound,bound);y=r.uniform(-bound,bound)
        d=L.water_distance(x,y)
        if d<3.5 or L.path_distance(x,y)<L.path_half_width(x,y)+2.0 or L.reserved(x,y,1.9):continue
        # Uneven grove density and distinct broadleaf / northern pine pockets.
        density=noise2(x*.029+41,y*.029-18)
        if r.random()>.40+density*.66:continue
        if not grid.clear(x,y,spacing):continue
        p=noise2(x*.018-21,y*.022+60)
        q=r.random()
        if q<.18+(y/L.half+1)*.09 and p>.30:asset=f'CF_Tree_Pine_{r.randint(1,3):02d}';sc=r.uniform(.88,1.38)
        elif d<10 and q<.76:asset='CF_Tree_Willow';sc=r.uniform(.88,1.18)
        elif p<.32 and q<.65:asset='CF_Tree_Birch';sc=r.uniform(.94,1.34)
        else:asset=f'CF_Tree_Broadleaf_{r.randint(1,4):02d}';sc=r.uniform(.94,1.38)
        # Rooted at terrain height; no geometry is copied by placement records.
        w.place(asset,(x,y,L.height(x,y)),(0,0,r.uniform(0,2*pi)),(sc*r.uniform(.95,1.05),sc*r.uniform(.95,1.05),sc),
                zone=L.zone(x,y),source='forest_tree')
        grid.add(x,y);count+=1
    if count<cfg['tree_count']:w.notes.append(f'Tree target {cfg["tree_count"]} could not fit without overlap; placed {count}. Reduce spacing or target count.')
    return grid


def scatter_details(w,L,r):
    cfg=w.config;half=L.half-1.5
    def ground(asset,x,y,sc=1,zone=None,source='detail'):
        w.place(asset,(x,y,L.height(x,y)-.01),(0,0,r.uniform(0,2*pi)),sc,zone=zone or L.zone(x,y),source=source)
    trees=[i for i in w.instances if i['source']=='forest_tree']
    small_grid=SpatialHash(.60)
    count=0;attempts=0
    while count<cfg['ground_detail_count'] and attempts<max(1000,cfg['ground_detail_count']*18):
        attempts+=1
        if trees and r.random()<.56:
            inst=r.choice(trees);a=r.uniform(0,2*pi);rad=r.uniform(1.4,4.4)
            x=inst['location'][0]+rad*cos(a);y=inst['location'][1]+rad*sin(a)
        else:x=r.uniform(-half,half);y=r.uniform(-half,half)
        if abs(x)>half or abs(y)>half or L.water_distance(x,y)<1.30 or L.path_distance(x,y)<L.path_half_width(x,y)+.35:continue
        if L.reserved(x,y,.3) or not small_grid.clear(x,y,.48):continue
        q=r.random()
        if q<.16:asset=f'CF_Shrub_{r.randint(1,3):02d}';sc=r.uniform(.65,1.3)
        elif q<.36:asset=f'CF_Fern_{r.randint(1,2):02d}';sc=r.uniform(.85,1.6)
        elif q<.63:asset=f'CF_GrassTuft_{r.randint(1,3):02d}';sc=r.uniform(.95,1.9)
        elif q<.82:asset=r.choice(['CF_Flowers_Daisy','CF_Flowers_Buttercup','CF_Flowers_Bluebell','CF_Flowers_Lavender']);sc=r.uniform(.85,1.55)
        elif q<.89:asset=f'CF_Mushrooms_{r.randint(1,2):02d}';sc=r.uniform(.9,1.65)
        elif q<.985:asset=f'CF_Rock_Moss_{r.randint(1,4):02d}';sc=r.uniform(.7,1.8)
        else:asset='CF_Stump';sc=r.uniform(.9,1.3)
        ground(asset,x,y,sc);small_grid.add(x,y);count+=1
    # Large flower islands rather than thousands of uniformly isolated single flowers.
    if cfg['include_landmarks']:
        p=L.poi['meadow'];placed=0
        flower_grid=SpatialHash(.52)
        for attempt in range(cfg['meadow_flower_count']*25):
            if placed>=cfg['meadow_flower_count']:break
            a=r.uniform(0,2*pi);rr=sqrt(r.random())*p['radius']
            x=p['x']+rr*cos(a);y=p['y']+rr*sin(a)
            if L.path_distance(x,y)<1.9 or L.blocked(x,y,.38) or not flower_grid.clear(x,y,.46):continue
            patch=noise2(x*.08+55,y*.08)
            asset='CF_Flowers_Lavender' if patch<.40 else 'CF_Flowers_Daisy' if patch<.60 else 'CF_Flowers_Buttercup' if patch<.76 else 'CF_Flowers_Sunflower'
            ground(asset,x,y,r.uniform(.85,1.35),'meadow','meadow_flower');flower_grid.add(x,y);placed+=1
        for key in ('camp','reading','guardian','ruins','mushroom','arrival','village'):
            p=L.poi[key]
            for j in range(70):
                a=r.uniform(0,2*pi);rr=r.uniform(p['radius']*.50,p['radius']*.98)
                x=p['x']+rr*cos(a);y=p['y']+rr*sin(a)
                if L.blocked(x,y,.5) or L.water_distance(x,y)<1.1 or L.path_distance(x,y)<1.9:continue
                asset=r.choice(['CF_Fern_01','CF_Flowers_Daisy','CF_Flowers_Lavender','CF_Mushrooms_02'])
                if key=='ruins':asset=r.choice(['CF_Rock_Moss_03','CF_Fern_02','CF_Shrub_01'])
                ground(asset,x,y,r.uniform(.8,1.5),key,'landmark_detail')
    # Shore rocks: interrupted and varied, not a continuous wall around the lake.
    placed=0
    for j in range(cfg['shore_rock_count']*9):
        if placed>=cfg['shore_rock_count']:break
        if r.random()<.73:
            idx=r.choices((0,1,2),weights=(.62,.18,.20))[0]
            a=r.uniform(0,2*pi);x,y=L.shore_point(a,r.uniform(.25,2.1),idx)
        else:
            y=r.uniform(-L.half+3,-16*L.k);side=r.choice((-1,1));x=L.stream_x(y)+side*(L.stream_half(y)+r.uniform(.4,1.7))
        if L.blocked(x,y,1.4) or L.path_distance(x,y)<1.85:continue
        if not small_grid.clear(x,y,.92):continue
        ground(f'CF_Rock_Moss_{r.randint(1,4):02d}',x,y,r.uniform(.85,1.7),source='shore_rock');small_grid.add(x,y);placed+=1
    placed=0
    for j in range(cfg['lily_count']*5):
        if placed>=cfg['lily_count']:break
        idx=r.choices((0,1,2),weights=(.64,.16,.20))[0];a=r.uniform(0,2*pi)
        x,y=L.shore_point(a,-r.uniform(.8,4.5)*L.k,idx)
        if L.water_distance(x,y)>-.3 or L.blocked(x,y,2.8):continue
        w.place('CF_LilyPad_Flower' if r.random()<.64 else 'CF_LilyPad_Leaves',(x,y,.025),(0,0,r.uniform(0,2*pi)),r.uniform(.8,1.35),zone='water',source='lily');placed+=1
    placed=0
    for j in range(cfg['shore_plant_count']*6):
        if placed>=cfg['shore_plant_count']:break
        if r.random()<.71:
            idx=r.choices((0,1,2),weights=(.6,.2,.2))[0];a=r.uniform(0,2*pi)
            x,y=L.shore_point(a,r.uniform(-.38,.35),idx)
        else:
            y=r.uniform(-L.half+2,-15*L.k);x=L.stream_x(y)+r.choice((-1,1))*(L.stream_half(y)-.16)
        if L.blocked(x,y,2.0):continue
        w.place(f'CF_Cattails_{r.randint(1,3):02d}',(x,y,max(.004,L.height(x,y))-.05),(0,0,r.uniform(0,2*pi)),r.uniform(.9,1.4),zone='lakeshore',source='shore_plant');placed+=1
    for _ in range(100):
        idx=r.choices((0,1,2),weights=(.7,.15,.15))[0];p=L.lakes[idx]
        x=p['center'][0]+r.uniform(-.8,.8)*p['rx'];y=p['center'][1]+r.uniform(-.8,.8)*p['ry']
        if L.water_distance(x,y)<-3:w.place('CF_WaterRipple_01',(x,y,.02),(0,0,r.uniform(0,2*pi)),r.uniform(1.5,3.2),zone='water',source='ripple')


def build_world(config=None):
    cfg=validate_config(config);w=World(cfg);L=Layout(cfg);r=random.Random(cfg['seed'])
    makers=[*[broadleaf(i) for i in range(4)],*[pine(i) for i in range(3)],*[rock(i) for i in range(4)],
       *[shrub(i) for i in range(3)],*[fern(i) for i in range(2)],*[grass(i) for i in range(3)],
       *[flowers(i) for i in range(3)],*[mushrooms(i) for i in range(2)],*[cattails(i) for i in range(3)],
       *[lilypad(i) for i in range(2)],ripple(0),bench(),fence(),signpost(),stump(),*all_new_assets()]
    if cfg['include_cabin']:makers.append(cottage())
    if cfg['include_well']:makers.append(well())
    if cfg['include_bridge']:makers.append(bridge())
    if cfg['include_dock']:makers.append(dock())
    for mesh in makers:w.register(mesh)
    build_terrain(w,L)
    build_landmarks(w,L,r)
    scatter_forest(w,L,r)
    scatter_details(w,L,r)
    used={i['asset_id'] for i in w.instances};w.assets={k:v for k,v in w.assets.items() if k in used}
    w.points_of_interest=[dict(p,z=L.height(p['x'],p['y'])) for p in L.pois]
    w.routes=L.routes
    w.notes.extend([
        'Every repeated prop uses one shared source mesh. Terrain/water cells are unique where their shape differs.',
        'All water is a static visual surface at z=0 m. Windmill, ducks and campfire are static props, not animations.',
        '50 m default cells are grouping/export units, not automatic World Partition or sublevel streaming.',
        'No production LODs or gameplay collision are generated. See README_KO.md before first-person gameplay.'
    ])
    return w


def validate_world(w):
    errors=[]
    for key,m in w.assets.items():
        if not m.vertices or not m.faces:errors.append(key+': empty mesh')
        if len(m.colors)!=len(m.faces):errors.append(key+': colour/face mismatch')
        for i,tri in enumerate(m.faces):
            if len(tri)!=3 or any(j<0 or j>=len(m.vertices) for j in tri):errors.append(key+': invalid indices');break
            a,b,c=(m.vertices[j] for j in tri);area=cross(sub(b,a),sub(c,a))
            if dot(area,area)<1e-19:errors.append(f'{key}: degenerate triangle {i}')
        for v in m.vertices:
            if any(not isfinite(x) for x in v):errors.append(key+': non-finite vertex');break
        for corners in m.colors:
            if len(corners)!=3 or any(len(c)!=4 or any(not 0<=x<=1 for x in c) for c in corners):errors.append(key+': invalid colour');break
    seen=set();half=w.config['map_size_m']/2
    for inst in w.instances:
        if inst['asset_id'] not in w.assets:errors.append('Missing asset '+inst['asset_id'])
        if inst['name'] in seen:errors.append('Duplicate instance name '+inst['name'])
        seen.add(inst['name'])
        if any(not isfinite(v) for vals in [inst['scale'],inst['location'],inst['rotation_euler_xyz']] for v in vals):errors.append('Invalid transform '+inst['name'])
        if min(inst['scale'])<=0:errors.append('Non-positive scale '+inst['name'])
        if max(abs(inst['location'][0]),abs(inst['location'][1]))>half+.01:errors.append('Pivot outside map '+inst['name'])
        if inst['cell_id']!=w.cell(*inst['location'][:2]):errors.append('Wrong cell '+inst['name'])
    return errors


def geometry_digest(w):
    h=hashlib.sha256()
    for key in sorted(w.assets):
        m=w.assets[key];h.update(json.dumps([key,m.vertices,m.faces,m.colors],separators=(',',':')).encode())
    h.update(json.dumps(w.instances,sort_keys=True,separators=(',',':')).encode())
    return h.hexdigest()


def matrix_for(location,rotation,scale):
    cols=[transformed(tuple(1 if j==i else 0 for j in range(3)),(0,0,0),rotation,scale) for i in range(3)]
    return sum([[cols[j][i] for j in range(3)]+[location[i]] for i in range(3)]+[[0,0,0,1]],[])
