import pickle, math, sys
T=pickle.load(open('pcb.pkl','rb'))
def find(node,key): return [c for c in node if isinstance(c,list) and c and c[0]==key]
def one(node,key):
    r=find(node,key); return r[0] if r else None
want=sys.argv[1:]
for f in find(T,'footprint'):
    props={p[1]:p[2] for p in find(f,'property')}
    if props.get('Reference') not in want: continue
    at=one(f,'at'); fx,fy=float(at[1]),float(at[2]); fr=float(at[3]) if len(at)>3 else 0
    print(props['Reference'],one(f,'layer')[1],fx,fy,'rot',fr)
    th=math.radians(fr)
    for p in find(f,'pad'):
        pa=one(p,'at'); lx,ly=float(pa[1]),float(pa[2])
        x=fx+lx*math.cos(th)+ly*math.sin(th); y=fy-lx*math.sin(th)+ly*math.cos(th)
        sz=one(p,'size'); n=one(p,'net')
        print(f"   pad {p[1]:>3s} {p[2]:4s} ({x:7.2f},{y:7.2f}) {float(sz[1]):.2f}x{float(sz[2]):.2f} {n[1] if n else ''}")
