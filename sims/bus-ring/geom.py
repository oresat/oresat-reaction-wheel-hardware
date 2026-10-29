import pickle, math, collections
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
import os
HERE=os.path.dirname(os.path.abspath(__file__))
T=pickle.load(open(os.path.join(HERE,'pcb.pkl'),'rb'))
def find(node,key): return [c for c in node if isinstance(c,list) and c and c[0]==key]
def one(node,key):
    r=find(node,key); return r[0] if r else None
CU=['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']
pours=collections.defaultdict(list)   # (layer,net)->[Polygon]
for z in find(T,'zone'):
    nn=one(z,'net_name') or one(z,'net'); net=nn[1] if nn else '?'
    for fp in find(z,'filled_polygon'):
        lay=one(fp,'layer')[1]
        pts=[(float(p[1]),float(p[2])) for p in one(fp,'pts') if p[0]=='xy']
        if len(pts)>=3:
            pg=Polygon(pts).buffer(0)
            pours[(lay,net)].append(pg)
pours={k:unary_union(v) for k,v in pours.items()}
tracks=[]  # dict(layer,net,line,w)
for s in find(T,'segment'):
    lay=one(s,'layer')[1]; net=one(s,'net')[1]; w=float(one(s,'width')[1])
    st=one(s,'start'); en=one(s,'end')
    a=(float(st[1]),float(st[2])); b=(float(en[1]),float(en[2]))
    if a!=b: tracks.append(dict(layer=lay,net=net,line=LineString([a,b]),w=w))
for s in find(T,'arc'):
    lay=one(s,'layer')[1]; net=one(s,'net')[1]; w=float(one(s,'width')[1])
    st=one(s,'start'); md=one(s,'mid'); en=one(s,'end')
    pts=[(float(st[1]),float(st[2])),(float(md[1]),float(md[2])),(float(en[1]),float(en[2]))]
    tracks.append(dict(layer=lay,net=net,line=LineString(pts),w=w))
vias=[]
for v in find(T,'via'):
    at=one(v,'at'); vias.append(dict(net=one(v,'net')[1],x=float(at[1]),y=float(at[2]),size=float(one(v,'size')[1]),drill=float(one(v,'drill')[1])))
pickle.dump(dict(pours=pours,tracks=tracks,vias=vias),open(os.path.join(HERE,'geom.pkl'),'wb'))
print(len(pours),'pour groups',len(tracks),'tracks',len(vias),'vias')
print('via nets:',collections.Counter(v['net'] for v in vias).most_common(12))
print('track widths L3/L4:',collections.Counter((t['layer'],t['w']) for t in tracks if t['layer'] in('In2.Cu','In3.Cu')).most_common(12))
