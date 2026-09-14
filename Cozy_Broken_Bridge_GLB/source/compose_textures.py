"""Recompose the supplied texture source atlas and derive approximate surface maps.
Run with Python 3.10+, Pillow, NumPy and SciPy. Not a high-poly normal/AO bake.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from scipy.ndimage import gaussian_filter
ROOT=Path(__file__).resolve().parents[1]
TILES={
 'wood_old': [0,0,512,1024], 'wood_clean':[512,0,1024,1024],
 'wood_moss':[1024,0,1536,1024], 'wood_rot':[1536,0,2048,1024],
 'rot_end':[0,1024,512,1536], 'endgrain':[512,1024,1024,1536],
 'moss':[1024,1024,1536,1536], 'cap':[1536,1024,2048,1536],
 'gills':[0,1536,512,2048], 'rope':[512,1536,768,2048],
 'metal':[768,1536,1024,2048], 'leaf':[1024,1536,1536,2048],
 'stone':[1536,1536,2048,2048]}

def compose():
    src=Image.open(ROOT/'texture_sources/Previous_composited_atlas.png').convert('RGB')
    if src.size!=(2048,2048): src=src.resize((2048,2048),Image.Resampling.LANCZOS)
    base=Image.new('RGB',src.size)
    normal=np.full((2048,2048,3),(128,128,255),dtype=np.uint8)
    rough=np.full((2048,2048),220,dtype=np.uint8)
    ao=np.full((2048,2048),255,dtype=np.uint8)
    metal=np.zeros((2048,2048),dtype=np.uint8)
    height=np.zeros((2048,2048),dtype=np.uint8)
    for key,(x0,y0,x1,y1) in TILES.items():
        tile=src.crop((x0,y0,x1,y1))
        # Source regions are kept separate so that a material can be repainted.
        tile.save(ROOT/f'texture_sources/{key}_source.png')
        tile=ImageEnhance.Color(tile).enhance(.87 if key.startswith('wood') else .98)
        tile=ImageEnhance.Brightness(tile).enhance(1.13 if key not in ['moss','leaf','gills'] else 1.04)
        tile=ImageEnhance.Contrast(tile).enhance(.94)
        # Eight pixels of duplicated edge padding in every rectangle.
        w,h=tile.size
        inner=tile.crop((6,6,w-6,h-6)).resize((w-16,h-16),Image.Resampling.LANCZOS)
        arr=np.pad(np.asarray(inner),((8,8),(8,8),(0,0)),mode='edge')
        tile=Image.fromarray(arr)
        base.paste(tile,(x0,y0))
        rgb=arr.astype(np.float32)/255
        lum=rgb@np.array([.2126,.7152,.0722])
        lum=gaussian_filter(lum,1.1)
        dy,dx=np.gradient(lum)
        gain=3.5 if key.startswith('wood') else 2.1
        n=np.stack([-dx*gain,-dy*gain,np.ones_like(lum)],axis=-1)
        n/=np.linalg.norm(n,axis=-1,keepdims=True)
        normal[y0:y1,x0:x1]=np.clip((n*.5+.5)*255,0,255).astype(np.uint8)
        r={'moss':.97,'leaf':.84,'cap':.72,'gills':.88,'rope':.94,'metal':.76,'stone':.9}.get(key,.87)
        green=np.clip((rgb[:,:,1]-rgb[:,:,0])*.6,0,.08)
        rough[y0:y1,x0:x1]=np.clip((r+green+(lum-lum.mean())*.12)*255,0,255).astype(np.uint8)
        valley=np.clip(gaussian_filter(lum,5)-lum,0,.3)
        ao[y0:y1,x0:x1]=np.clip((1-valley*.9)*255,215,255).astype(np.uint8)
        height[y0:y1,x0:x1]=np.clip(lum*255,0,255).astype(np.uint8)
        if key=='metal': metal[y0:y1,x0:x1]=((1-rgb[:,:,0])*.35*255).astype(np.uint8)
    out=ROOT/'textures'; out.mkdir(exist_ok=True)
    base.save(out/'T_BrokenBridge_BaseColor.png')
    Image.fromarray(normal).save(out/'T_BrokenBridge_Normal_GL.png')
    normal_dx=normal.copy(); normal_dx[:,:,1]=255-normal_dx[:,:,1]
    Image.fromarray(normal_dx).save(out/'T_BrokenBridge_Normal_DX.png')
    Image.fromarray(rough).save(out/'T_BrokenBridge_Roughness.png')
    Image.fromarray(ao).save(out/'T_BrokenBridge_AO_Derived.png')
    Image.fromarray(height).save(out/'T_BrokenBridge_Height_Derived.png')
    Image.fromarray(np.stack([ao,rough,metal],axis=-1)).save(out/'T_BrokenBridge_ORM.png')
    meta={'resolution':[2048,2048],'gutter_pixels':8,'uv_pixel_inset':12,
          'tiles_top_left_pixel_coordinates':TILES,
          'source':'Previous conversation composited atlas, supplied as an attachment. Crops are not newly generated separate AI images.',
          'normal':'Approximate luminance-derived tangent-space detail; GL embedded in glb; DX supplied separately.',
          'AO':'Local texture-derived cavity approximation, not geometry-baked ambient occlusion.',
          'ORM':'R=texture-derived AO; G=roughness; B=metallic'}
    (out/'atlas_layout.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Textures recomposited: 2048x2048, 13 source regions.')
if __name__=='__main__': compose()
