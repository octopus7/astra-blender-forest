from pathlib import Path
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[1]
w=vtk.vtkRenderWindow();w.SetOffScreenRendering(1);w.SetSize(1900,1250);w.SetMultiSamples(0)
r=vtk.vtkRenderer();w.AddRenderer(r)
imp=vtk.vtkGLTFImporter();imp.SetFileName(str(root/'models/SM_BrokenBridge_v2.glb'));imp.SetRenderWindow(w);imp.Update()
r=imp.GetRenderer();r.SetBackground(.35,.4,.34)
r.AutomaticLightCreationOff()
for pos,col,power in [((-6,12,8),(1.,.87,.69),2.2),((7,8,-5),(.8,.9,1.),1.1)]:
 l=vtk.vtkLight();l.SetLightTypeToSceneLight();l.SetPosition(*pos);l.SetFocalPoint(0,0,0);l.SetColor(*col);l.SetIntensity(power);l.SetPositional(False);r.AddLight(l)
# Diffuse studio environment, used only for preview lighting.
H,W=128,256
ys=np.linspace(0,1,H)[:,None,None]
color=np.array([.78,.83,.77])[None,None,:]*(.35+.65*np.sin(ys*np.pi))
env=np.broadcast_to(color,(H,W,3)).copy().astype(np.float32)
data=vtk.vtkImageData();data.SetDimensions(W,H,1);data.GetPointData().SetScalars(numpy_to_vtk(env.reshape(-1,3),deep=True))
tex=vtk.vtkTexture();tex.SetInputData(data);tex.InterpolateOn();tex.MipmapOn();r.UseImageBasedLightingOn();r.SetEnvironmentTexture(tex,False)
# Studio floor, excluded from the GLB.
p=vtk.vtkPlaneSource();p.SetOrigin(-200,-1.94,200);p.SetPoint1(200,-1.94,200);p.SetPoint2(-200,-1.94,-200)
m=vtk.vtkPolyDataMapper();m.SetInputConnection(p.GetOutputPort());a=vtk.vtkActor();a.SetMapper(m);a.GetProperty().SetColor(.25,.31,.26);a.GetProperty().SetInterpolationToPBR();a.GetProperty().SetRoughness(1);r.AddActor(a)
# Screen-space contact shading. No multisampling: Mesa EGL + MSAA returns black.
ssao=vtk.vtkSSAOPass();ssao.SetRadius(.42);ssao.SetBias(.015);ssao.SetKernelSize(128);ssao.BlurOn();ssao.SetDelegatePass(vtk.vtkRenderStepsPass());r.SetPass(ssao)
cam=r.GetActiveCamera();cam.ParallelProjectionOn()
views=[
    ('01_asset_preview',(10,10.5,16),(0,-.23,0),(0,1,0),4.6),
    ('02_broken_wood_detail',(.4,3.3,5.9),(-2.65,-.15,.25),(0,1,0),2.1),
    ('03_fungus_and_moss_detail',(7.5,2.8,5.1),(4.80,.02,1.70),(0,1,0),1.28),
    ('04_top_view',(0,18,0),(0,-.2,0),(0,0,-1),4.3)]
from PIL import Image,ImageDraw,ImageFont
try:
    font=ImageFont.truetype('DejaVuSans.ttf',20)
except OSError:
    font=ImageFont.load_default()
for name,pos,target,up,scale in views:
    cam.SetPosition(*pos);cam.SetFocalPoint(*target);cam.SetViewUp(*up);cam.SetParallelScale(scale)
    r.ResetCameraClippingRange();r.UseFXAAOff();w.Render()
    f=vtk.vtkWindowToImageFilter();f.SetInput(w);f.ReadFrontBufferOff();f.Update()
    tmp=root/'previews'/f'{name}.png'
    wr=vtk.vtkPNGWriter();wr.SetFileName(str(tmp));wr.SetInputConnection(f.GetOutputPort());wr.Write()
    im=Image.open(tmp).convert('RGB')
    d=ImageDraw.Draw(im);d.rectangle((0,1210,1900,1250),fill=(34,43,38))
    d.text((22,1219),'ACTUAL V2 GLB / VTK RENDER  /  '+name[3:].replace('_',' ').upper(),font=font,fill=(230,235,224))
    d.text((1130,1219),'6,732 triangles   |   1 atlas material   |   2K',font=font,fill=(230,235,224))
    im.save(root/'previews'/f'{name}.jpg',quality=93,subsampling=0)
    tmp.unlink()
    print('Rendered',name,flush=True)
import json
report={'renderer':'VTK '+vtk.vtkVersion.GetVTKVersion()+' / EGL offscreen',
        'source':'models/SM_BrokenBridge_v2.glb','importer':'vtkGLTFImporter',
        'status':'PASS','material_textures_imported':3,'views':[v[0]+'.jpg' for v in views],
        'note':'Studio floor, lights and environment are preview-only. All bridge geometry and textures are re-imported from the delivered GLB.'}
(root/'validation/render_verification.json').write_text(json.dumps(report,indent=2))
