# Extract 2D cross-section copper intervals along a cut line, per layer, per net.
import pickle, math, json, sys
from shapely.geometry import LineString, Polygon, box, Point
from shapely.ops import unary_union
from shapely import affinity
g=pickle.load(open('geom.pkl','rb'))
T=pickle.load(open('pcb.pkl','rb'))
CU=['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']
def find(node,key): return [c for c in node if isinstance(c,list) and c and c[0]==key]
def one(node,key):
    r=find(node,key); return r[0] if r else None
# SMD pads on outer layers
pads=[]  # (layer, net, polygon)
for f in find(T,'footprint'):
    at=one(f,'at'); fx,fy=float(at[1]),float(at[2]); fr=float(at[3]) if len(at)>3 else 0
    th=math.radians(fr)
    for p in find(f,'pad'):
        if p[2] not in ('smd',): continue
        n=one(p,'net'); net=n[1] if n else ''
        if not net: continue
        lays=one(p,'layers')[1:]
        pa=one(p,'at'); lx,ly=float(pa[1]),float(pa[2]); pr=float(pa[3]) if len(pa)>3 else 0
        sz=one(p,'size'); w,h=float(sz[1]),float(sz[2])
        x=fx+lx*math.cos(th)+ly*math.sin(th); y=fy-lx*math.sin(th)+ly*math.cos(th)
        poly=box(x-w/2,y-h/2,x+w/2,y+h/2)
        poly=affinity.rotate(poly,-(pr) ,origin=(x,y))   # pad 'at' angle is absolute in kicad files
        for L in lays:
            if L in ('F.Cu','B.Cu'): pads.append((L,net,poly))
def cut(axis,c0,a0,a1):
    """axis='y' : horizontal line y=c0, coordinate along x from a0..a1. axis='x': vertical line x=c0, along y."""
    line=LineString([(a0,c0),(a1,c0)]) if axis=='y' else LineString([(c0,a0),(c0,a1)])
    def coord(pt): return pt[0] if axis=='y' else pt[1]
    out={L:{} for L in CU}
    def add(L,net,geom):
        inter=geom.intersection(line)
        if inter.is_empty: return
        parts=getattr(inter,'geoms',[inter])
        for s in parts:
            if s.length<=0: continue
            cs=[coord(p) for p in s.coords]
            out[L].setdefault(net,[]).append((min(cs),max(cs)))
    for (L,net),geom in g['pours'].items(): add(L,net,geom)
    for t in g['tracks']: add(t['layer'],t['net'],t['line'].buffer(t['w']/2,cap_style=1))
    for L,net,poly in pads: add(L,net,poly)
    # merge intervals per net per layer
    for L in CU:
        for net,iv in out[L].items():
            iv.sort(); m=[]
            for a,b in iv:
                if m and a<=m[-1][1]+1e-6: m[-1]=(m[-1][0],max(m[-1][1],b))
                else: m.append((a,b))
            out[L][net]=m
    vias=[(v['x'] if axis=='y' else v['y'],v['net']) for v in g['vias'] if abs((v['y'] if axis=='y' else v['x'])-c0)<v['size']/2+0.05 and a0<=(v['x'] if axis=='y' else v['y'])<=a1]
    return out,vias
if __name__=='__main__':
    axis,c0,a0,a1=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4])
    out,vias=cut(axis,c0,a0,a1)
    for L in CU:
        print(L)
        for net,iv in sorted(out[L].items(),key=lambda kv:kv[1][0][0]):
            print(f"   {net:22s}", ' '.join(f"[{a:.3f},{b:.3f}]" for a,b in iv))
    print("vias on cut:",vias)
