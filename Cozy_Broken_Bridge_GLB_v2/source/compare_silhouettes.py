import vtk,json
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[1]
import argparse
parser=argparse.ArgumentParser(description='Compare v1 and v2 GLB silhouettes')
parser.add_argument('original_glb',type=Path)
args=parser.parse_args()
views=[('hero',(10,10.5,16),(0,-.23,0),(0,1,0),4.6),('top',(0,18,0),(0,-.2,0),(0,0,-1),4.3),('side',(0,1.9,20),(0,-.2,0),(0,1,0),3.8)]
models=[args.original_glb,root/'models/SM_BrokenBridge_v2.glb']
allmasks=[]
for path in models:
 w=vtk.vtkRenderWindow();w.SetOffScreenRendering(1);w.SetSize(1200,800);w.SetMultiSamples(0)
 r=vtk.vtkRenderer();w.AddRenderer(r);im=vtk.vtkGLTFImporter();im.SetFileName(str(path));im.SetRenderWindow(w);im.Update();r=im.GetRenderer();r.SetBackground(0,0,0);r.AutomaticLightCreationOff()
 actors=r.GetActors();actors.InitTraversal()
 while (actor:=actors.GetNextActor()) is not None:
  prop=actor.GetProperty();prop.RemoveAllTextures();prop.LightingOff();prop.SetColor(1,1,1);prop.SetOpacity(1);prop.SetInterpolationToFlat();prop.BackfaceCullingOff();actor.GetMapper().ScalarVisibilityOff()
 cam=r.GetActiveCamera();cam.ParallelProjectionOn();masks=[]
 for name,pos,target,up,scale in views:
  cam.SetPosition(*pos);cam.SetFocalPoint(*target);cam.SetViewUp(*up);cam.SetParallelScale(scale);r.ResetCameraClippingRange();w.Render()
  f=vtk.vtkWindowToImageFilter();f.SetInput(w);f.ReadFrontBufferOff();f.Update();a=vtk_to_numpy(f.GetOutput().GetPointData().GetScalars()).reshape(800,1200,-1)[::-1]
  masks.append(a.max(axis=-1)>127)
 allmasks.append(masks);w.Finalize()
report={'comparison':'Supplied v1 geometry versus delivered v2, binary silhouettes. Not an AI-reference similarity score.','renderer':'VTK offscreen','resolution':[1200,800],'views':{}}
for (name,*_),a,b in zip(views,*allmasks):
 report['views'][name]={'intersection_over_union':float(np.count_nonzero(a&b)/np.count_nonzero(a|b)),'v1_pixels':int(a.sum()),'v2_pixels':int(b.sum())}
print(json.dumps(report,indent=2));(root/'validation/silhouette_comparison.json').write_text(json.dumps(report,indent=2))
# A transparent description of where the lower-poly silhouette differs.
a,b=allmasks[0][0],allmasks[1][0];out=np.full((800,1200,3),(31,41,39),dtype=np.uint8);out[a&b]=(181,201,170);out[a&~b]=(227,167,102);out[b&~a]=(111,186,214)
im=Image.fromarray(out);d=ImageDraw.Draw(im);font=ImageFont.truetype('DejaVuSans.ttf',17);d.rectangle((0,756,1200,800),fill=(25,34,31));d.text((18,768),'Silhouette: shared / green   v1 only / amber   v2 only / blue',font=font,fill=(239,240,226));im.save(root/'previews/07_silhouette_overlay.png')
