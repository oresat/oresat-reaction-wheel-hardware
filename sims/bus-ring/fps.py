import pickle, collections, json
import os
HERE=os.path.dirname(os.path.abspath(__file__))
T=pickle.load(open(os.path.join(HERE,'pcb.pkl'),'rb'))
def find(node,key): return [c for c in node if isinstance(c,list) and c and c[0]==key]
def one(node,key):
    r=find(node,key); return r[0] if r else None
fps=[]
for f in find(T,'footprint'):
    lay=one(f,'layer')[1]; at=one(f,'at')
    props={p[1]:p[2] for p in find(f,'property')}
    pads=[]
    for p in find(f,'pad'):
        n=one(p,'net'); pads.append((p[1], n[1] if n else ''))
    fps.append(dict(ref=props.get('Reference'),val=props.get('Value'),lay=lay,x=float(at[1]),y=float(at[2]),rot=float(at[3]) if len(at)>3 else 0,fp=f[1],pads=pads))
json.dump(fps,open(os.path.join(HERE,'fps.json'),'w'))
for d in sorted(fps,key=lambda d:d['ref']):
    nets=sorted(set(n for _,n in d['pads']))
    print(f"{d['ref']:6s} {d['val'][:18]:18s} {d['lay']:5s} ({d['x']:.1f},{d['y']:.1f}) {d['fp'].split(':')[-1][:28]:28s} {' | '.join(nets)}")
