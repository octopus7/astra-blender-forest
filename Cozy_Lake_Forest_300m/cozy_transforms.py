"""Dependency-free affine basis conversion, shared by validation and UE import.

The UE importer measures B using three offset calibration cubes imported through
exactly the same FBX settings as the assets. No guessed Euler sign conventions.
For points: p_UE = B p_Blender. For instances: M_UE = B M_Blender B^-1.
B includes the metre-to-centimetre factor; instance scale stays dimensionless.
"""
from math import sqrt, isfinite

IDENTITY3=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]

def transpose(a): return [list(x) for x in zip(*a)]
def mm(a,b): return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def mv(a,v): return [sum(a[i][j]*v[j] for j in range(3)) for i in range(3)]
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def det(a):
    return (a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
           -a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
           +a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]))

def basis_from_probe_centers(centers,expected_units=100.):
    if len(centers)!=3 or any(len(c)!=3 for c in centers): raise ValueError('Three 3D probe centers are required.')
    lengths=[sqrt(dot(c,c)) for c in centers]
    if any(abs(s-expected_units)>.05 for s in lengths):
        raise ValueError(f'FBX unit calibration failed: {lengths}. Expected each 1 m probe at 100 cm. Check FBX unit conversion / pivot settings.')
    axes=[[x/s for x in c] for c,s in zip(centers,lengths)]
    if any(abs(dot(axes[i],axes[j]))>1e-5 for i in range(3) for j in range(i)):
        raise ValueError('Imported calibration axes are not perpendicular.')
    # FBX axis conversions must be a signed permutation, not an arbitrary rotation.
    if any(max(abs(x) for x in a)<.99999 for a in axes):
        raise ValueError('Unexpected non-axis-aligned FBX conversion.')
    return transpose(centers)

def quaternion_from_matrix(m):
    tr=m[0][0]+m[1][1]+m[2][2]
    if tr>0:
        s=sqrt(tr+1.)*2; w=.25*s
        x=(m[2][1]-m[1][2])/s; y=(m[0][2]-m[2][0])/s; z=(m[1][0]-m[0][1])/s
    elif m[0][0]>m[1][1] and m[0][0]>m[2][2]:
        s=sqrt(1+m[0][0]-m[1][1]-m[2][2])*2
        w=(m[2][1]-m[1][2])/s; x=.25*s; y=(m[0][1]+m[1][0])/s; z=(m[0][2]+m[2][0])/s
    elif m[1][1]>m[2][2]:
        s=sqrt(1+m[1][1]-m[0][0]-m[2][2])*2
        w=(m[0][2]-m[2][0])/s; x=(m[0][1]+m[1][0])/s; y=.25*s; z=(m[1][2]+m[2][1])/s
    else:
        s=sqrt(1+m[2][2]-m[0][0]-m[1][1])*2
        w=(m[1][0]-m[0][1])/s; x=(m[0][2]+m[2][0])/s; y=(m[1][2]+m[2][1])/s; z=.25*s
    length=sqrt(x*x+y*y+z*z+w*w)
    return [x/length,y/length,z/length,w/length]

def convert_transform(flat,basis):
    if len(flat)!=16 or any(not isfinite(v) for v in flat): raise ValueError('A finite row-major 4x4 transform is required.')
    if any(abs(flat[12+i]-[0,0,0,1][i])>1e-6 for i in range(4)): raise ValueError('Invalid affine last row.')
    units=sqrt(sum(basis[i][0]**2 for i in range(3)))
    if units<1e-12: raise ValueError('Singular basis.')
    # B is a uniform scale times an orthogonal signed permutation.
    inv=[[basis[j][i]/(units*units) for j in range(3)] for i in range(3)]
    src=[[flat[i*4+j] for j in range(3)] for i in range(3)]
    local=mm(mm(basis,src),inv)
    cols=transpose(local); scale=[sqrt(dot(c,c)) for c in cols]
    if min(scale)<1e-8: raise ValueError('Zero instance scale is not supported.')
    rot=transpose([[v/s for v in col] for col,s in zip(cols,scale)])
    if det(rot)<0: raise ValueError('Negative/mirrored scale is not supported. Mirror the source mesh explicitly.')
    axes=transpose(rot)
    if any(abs(dot(axes[i],axes[j]))>1e-5 for i in range(3) for j in range(i)):
        raise ValueError('Sheared transform: remove non-uniform parent scale / shear before exporting.')
    return {'translation':mv(basis,[flat[3],flat[7],flat[11]]),
            'rotation_xyzw':quaternion_from_matrix(rot),'scale':scale}
