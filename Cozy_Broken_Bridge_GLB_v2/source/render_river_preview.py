"""Independent VTK lookdev of delivered GLB plus the SAME river display geometry.
VTK water is an approximation; this is deliberately NOT labeled a Blender render.
"""
from pathlib import Path
import sys,json,math
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
from PIL import Image,ImageDraw,ImageFont
from scene_geometry import make_environment,make_decoration_prototypes,decoration_instances
ROOT=Path(__file__).resolve().parents[1];cfg=json.loads((ROOT/'scene_config.json').read_text())
renwin=vtk.vtkRenderWindow();renwin.SetOffScreenRendering(1);renwin.SetSize(1800,1200);renwin.SetMultiSamples(0)
r=vtk.vtkRenderer();renwin.AddRenderer(r)
imp=vtk.vtkGLTFImporter();imp.SetFileName(str(ROOT/'models/SM_BrokenBridge_v2.glb'));imp.SetRenderWindow(renwin);imp.Update();r=imp.GetRenderer()
r.SetBackground(.51,.62,.60);r.AutomaticLightCreationOff()
for pos,col,power in [((-8,13,6),(1,.85,.65),2.2),((6,10,3),(.72,.90,1),.85),((0,8,-8),(1,.90,.72),1.1)]:
    l=vtk.vtkLight();l.SetLightTypeToSceneLight();l.SetPosition(*pos);l.SetFocalPoint(0,-.4,0);l.SetColor(*col);l.SetIntensity(power);l.SetPositional(False);r.AddLight(l)
H,W=128,256;y=np.linspace(0,1,H)[:,None,None]
env=np.broadcast_to(np.array([.77,.84,.87])[None,None,:]*(.32+.68*np.sin(y*np.pi)),(H,W,3)).copy().astype(np.float32)
data=vtk.vtkImageData();data.SetDimensions(W,H,1);data.GetPointData().SetScalars(numpy_to_vtk(env.reshape(-1,3),deep=True))
tex=vtk.vtkTexture();tex.SetInputData(data);tex.InterpolateOn();tex.MipmapOn();r.UseImageBasedLightingOn();r.SetEnvironmentTexture(tex,False)

def actor(spec):
    v=np.array(spec['vertices']);vf=v[:,[0,2,1]].copy();vf[:,2]*=-1
    points=vtk.vtkPoints();points.SetData(numpy_to_vtk(vf,deep=True));polys=vtk.vtkCellArray()
    for f in spec['faces']:polys.InsertNextCell(len(f));[polys.InsertCellPoint(int(i)) for i in f]
    data=vtk.vtkPolyData();data.SetPoints(points);data.SetPolys(polys)
    if spec['material']=='bank':
        sh=np.array(spec['shore']);a=np.clip((sh-.11)/.10,0,1)[:,None]
        color=np.array([.47,.39,.19])*(1-a)+np.array([.23,.36,.074])*a
        path=np.clip(1-np.abs(v[:,1])/1.6,0,1)[:,None];color=color*(1-path)+np.array([.47,.39,.20])*path
        variation=(.92+.11*np.sin(v[:,0]*5.1+v[:,1]*4.3)+.075*np.sin(v[:,0]*12-v[:,1]*7))[:,None];color=np.clip(color*variation,0,1)
    elif spec['material']=='bed':
        color=np.tile([.24,.31,.19],(len(v),1))*(.85+.25*np.sin(v[:,0]*5+v[:,1]*9)**2)[:,None]
    else:color=None
    if color is not None:
        rgb=numpy_to_vtk((color*255).clip(0,255).astype(np.uint8),deep=True,array_type=vtk.VTK_UNSIGNED_CHAR);rgb.SetName('Color');data.GetPointData().SetScalars(rgb)
    normals=vtk.vtkPolyDataNormals();normals.SetInputData(data);normals.SetFeatureAngle(65);normals.ConsistencyOn();normals.Update()
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort())
    ob=vtk.vtkActor();ob.SetMapper(mapper);prop=ob.GetProperty();prop.SetInterpolationToPBR();prop.SetRoughness(.92)
    if color is None:
        color={'shore_stone':(.33,.39,.22),'lily':(.23,.40,.10),'reed':(.28,.38,.08),'water':(.16,.49,.54)}[spec['material']];prop.SetColor(*color)
    return ob

for spec in make_environment(cfg):
    if spec['material']!='water':r.AddActor(actor(spec))
# Smooth textured water surface for VTK; Blender instead uses a closed volume.
x=cfg['river_half_width_m'];y=cfg['river_length_m']/2;level=cfg['water_level_m']
spec={'name':'water','material':'water','vertices':[(-x,-y,level),(x,-y,level),(x,y,level),(-x,y,level)],'faces':[(0,1,2),(0,2,3)]}
water=actor(spec);prop=water.GetProperty();prop.SetRoughness(.16);prop.SetMetallic(.08);prop.SetOpacity(.75)
# Procedural wave normal texture, only for matching a calm-water impression in VTK.
N=1024;yy,xx=np.mgrid[0:N,0:N]/N
h=.4*np.sin((yy*16+.3*np.sin(xx*12))*math.tau)+.21*np.sin((yy*31+xx*4)*math.tau)+.13*np.sin((yy*53-xx*8)*math.tau)
dy,dx=np.gradient(h);n=np.stack([-dx*1.5,dy*1.5,np.ones_like(dx)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
imdata=vtk.vtkImageData();imdata.SetDimensions(N,N,1);imdata.GetPointData().SetScalars(numpy_to_vtk(((n*.5+.5)*255).astype(np.uint8).reshape(-1,3),deep=True))
nt=vtk.vtkTexture();nt.SetInputData(imdata);nt.InterpolateOn();nt.MipmapOn()
poly=water.GetMapper().GetInput();uv=numpy_to_vtk(np.array([(0,0),(1,0),(1,1),(0,1)],np.float32),deep=True);uv.SetName('UV');poly.GetPointData().SetTCoords(uv)
tangents=vtk.vtkPolyDataTangents();tangents.SetInputData(poly);tangents.Update();water.GetMapper().SetInputConnection(tangents.GetOutputPort());prop.SetNormalTexture(nt)
r.AddActor(water)
protos={d['name']:d for d in make_decoration_prototypes()}
for name,pos,rot,scale in decoration_instances(cfg):
    ob=actor(protos[name]);ob.SetPosition(pos[0],pos[2],-pos[1]);ob.SetScale(scale[0],scale[2],scale[1]);ob.RotateY(math.degrees(rot[2]));r.AddActor(ob)
ssao=vtk.vtkSSAOPass();ssao.SetRadius(.32);ssao.SetBias(.018);ssao.SetKernelSize(96);ssao.BlurOn();ssao.SetDelegatePass(vtk.vtkRenderStepsPass());r.SetPass(ssao)
cam=r.GetActiveCamera();cam.ParallelProjectionOn();cam.SetPosition(10,11,16);cam.SetFocalPoint(0,-.2,0);cam.SetViewUp(0,1,0);cam.SetParallelScale(6.0)
r.ResetCameraClippingRange();renwin.Render()
f=vtk.vtkWindowToImageFilter();f.SetInput(renwin);f.ReadFrontBufferOff();f.Update();wr=vtk.vtkPNGWriter();p=ROOT/'previews/05_river_layout_vtk.png';wr.SetFileName(str(p));wr.SetInputConnection(f.GetOutputPort());wr.Write()
im=Image.open(p).convert('RGB');d=ImageDraw.Draw(im);font=ImageFont.load_default(size=18);d.rectangle((0,1150,1800,1200),fill=(25,40,37));d.text((20,1164),'V2 GLB + RIVER LAYOUT  |  VTK preview; Blender water shader is configured by the script.',font=font,fill=(226,236,226));im.save(ROOT/'previews/05_river_layout_vtk.jpg',quality=92,subsampling=0);p.unlink();print('River preview rendered.')
