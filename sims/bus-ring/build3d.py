"""Voxel PyPEEC case for the rev8 VBUS/PGND bus: one leg's LMG2100 shorted VIN->PGND, cap banks as ports.
usage: python build3d.py <stack: intended|asbuilt> <out_dir> [--pitch 0.1] [--dz 0.0115] [--freqs 1e7]
One sweep per (port, freq): driven port = stiff 1 mV / 0 V pair, every other terminal = 0 A source (plain copper)."""
import pickle, math, json, os, sys, argparse
import numpy as np, shapely
from shapely.geometry import box, Point
from shapely.ops import unary_union
from shapely import affinity
from scipy import ndimage as ndi
HERE=os.path.dirname(os.path.abspath(__file__))
g=pickle.load(open(os.path.join(HERE,'geom.pkl'),'rb')); T=pickle.load(open(os.path.join(HERE,'pcb.pkl'),'rb'))
CU=['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']
STACK={ # dielectric gaps between consecutive copper layers (top->bottom), mm
 'intended':[0.092,0.100,1.049,0.100,0.092],
 'asbuilt': [0.100,0.535,0.100,0.535,0.100]}
NETS=('VBUS','PGND')
PORTS={  # refdes groups
 'LOC_C_bot':['C74','C75','C76','C77','C95'],
 'LOC_C_top':['C78','C80','C92','C115','C116','C127','C128','C131','C134','C137'],
 'LOC_B':['C58','C59','C60','C61','C94','C62','C64','C91','C112','C113','C122','C123','C130','C133','C136'],
 'BULK_R':['C97','C98','C100','C107'],
 'BULK_L':['C96','C99','C101','C106'],
}
SHORT={'C':'U12','B':'U10','A':'U8'}
def find(node,key): return [c for c in node if isinstance(c,list) and c and c[0]==key]
def one(node,key):
    r=find(node,key); return r[0] if r else None
def footprints():
    out={}
    for f in find(T,'footprint'):
        props={p[1]:p[2] for p in find(f,'property')}; ref=props.get('Reference')
        at=one(f,'at'); fx,fy=float(at[1]),float(at[2]); fr=float(at[3]) if len(at)>3 else 0; th=math.radians(fr)
        pads=[]
        for p in find(f,'pad'):
            n=one(p,'net'); net=n[1] if n else ''
            pa=one(p,'at'); lx,ly=float(pa[1]),float(pa[2]); pr=float(pa[3]) if len(pa)>3 else 0
            sz=one(p,'size'); w,h=float(sz[1]),float(sz[2])
            x=fx+lx*math.cos(th)+ly*math.sin(th); y=fy-lx*math.sin(th)+ly*math.cos(th)
            poly=affinity.rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-pr,origin=(x,y))
            dr=one(p,'drill'); drill=float(dr[1]) if dr and len(dr)>1 and not isinstance(dr[1],list) else None
            pads.append(dict(num=p[1],kind=p[2],net=net,layers=one(p,'layers')[1:],poly=poly,x=x,y=y,drill=drill))
        out[ref]=dict(layer=one(f,'layer')[1],x=fx,y=fy,pads=pads)
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('stack'); ap.add_argument('out')
    ap.add_argument('--pitch',type=float,default=0.1); ap.add_argument('--dz',type=float,default=0.0115)
    ap.add_argument('--freqs',default='1e7'); ap.add_argument('--short',default='C')
    ap.add_argument('--crop',default='85.5,89.5,117.5,106.0'); ap.add_argument('--ports',default=','.join(PORTS))
    a=ap.parse_args(); os.makedirs(a.out,exist_ok=True)
    x0,y0,x1,y1=map(float,a.crop.split(',')); p=a.pitch; dz=a.dz
    nx=int(round((x1-x0)/p)); ny=int(round((y1-y0)/p))
    xc=x0+(np.arange(nx)+0.5)*p; yc=y0+(np.arange(ny)+0.5)*p
    XX,YY=np.meshgrid(xc,yc,indexing='ij')
    # z layout (index 0 = bottom). 3 bridge/body voxels below B.Cu, then B.Cu ... F.Cu, then 1 above
    ncu=max(1,int(round(0.035/dz))); gaps=[max(1,int(round(t/dz))) for t in STACK[a.stack]]
    zlay={}; iz=3
    for k,L in enumerate(reversed(CU)):
        zlay[L]=(iz,iz+ncu); iz+=ncu
        if k<5: iz+=gaps[::-1][k]
    nz=iz+1
    fps=footprints()
    port_refs={k:PORTS[k] for k in a.ports.split(',')}
    # per-layer 2D masks
    def raster(geom):
        if geom.is_empty: return np.zeros((nx,ny),bool)
        return shapely.contains_xy(geom,XX,YY)
    vol={}   # label grid: 0 empty, 1 VBUS cu, 2 PGND cu, 3 VBUS via, 4 PGND via, 5 bridge, 10+ terminals
    lab=np.zeros((nx,ny,nz),np.int16)
    crop=box(x0,y0,x1,y1)
    for L in CU:
        for ni,net in enumerate(NETS):
            parts=[]
            if (L,net) in g['pours']: parts.append(g['pours'][(L,net)])
            parts+= [t['line'].buffer(t['w']/2) for t in g['tracks'] if t['layer']==L and t['net']==net]
            for ref,f in fps.items():
                for pd in f['pads']:
                    if pd['net']==net and (L in pd['layers'] or '*.Cu' in pd['layers']):
                        parts.append(pd['poly'] if pd['kind']=='smd' else Point(pd['x'],pd['y']).buffer(0.2))
            geom=unary_union(parts).intersection(crop)
            m=raster(geom); z0,z1=zlay[L]
            sl=lab[:,:,z0:z1]; sl[m]=ni+1
    # vias (solid columns, diameter = drill), plus thru-hole thermal vias of the LMG2100s
    vlist=[(v['x'],v['y'],v['drill'],v['net']) for v in g['vias'] if v['net'] in NETS]
    for ref,f in fps.items():
        for pd in f['pads']:
            if pd['kind']=='thru_hole' and pd['net'] in NETS: vlist.append((pd['x'],pd['y'],pd['drill'] or 0.2,pd['net']))
    zt,zb=zlay['F.Cu'][1],zlay['B.Cu'][0]
    nvia=0
    for vx,vy,dr,net in vlist:
        if not (x0<vx<x1 and y0<vy<y1): continue
        i=int((vx-x0)/p); j=int((vy-y0)/p)
        r=max(dr/2,p*0.75)
        ii=[k for k in range(i-2,i+3) if 0<=k<nx]; jj=[k for k in range(j-2,j+3) if 0<=k<ny]
        cells=[(u,w) for u in ii for w in jj if (xc[u]-vx)**2+(yc[w]-vy)**2<=r*r]
        if not cells: cells=[(i,j)]
        code=3 if net=='VBUS' else 4
        for u,w in cells:
            col=lab[u,w,zb:zt]; col[col==0]=code   # barrel between layers; copper layers keep their label
        nvia+=1
    # leg short: copper block below B.Cu under the shorted LMG2100 spanning PGND pad -> VIN pad
    U=fps[SHORT[a.short]]; vin=[pd for pd in U['pads'] if pd['num']=='7'][0]; pg=[pd for pd in U['pads'] if pd['num']=='6' and pd['kind']=='smd'][0]
    bx0,by0,bx1,by1=unary_union([vin['poly'],pg['poly']]).bounds
    bm=raster(box(bx0,by0,bx1,by1)); zb0=zlay['B.Cu'][0]
    for k in range(zb0-2,zb0):
        sl=lab[:,:,k]; sl[bm]=5
    # terminals: the outer-layer pad voxels of every cap in a port bank
    tdefs={}; code=10
    for pname,refs in port_refs.items():
        for pol,net in (('p','VBUS'),('n','PGND')):
            m=np.zeros((nx,ny),bool); Ls=set()
            for ref in refs:
                f=fps[ref]
                for pd in f['pads']:
                    if pd['net']==net and pd['kind']=='smd': m|=raster(pd['poly']); Ls.add(f['layer'])
            for L in Ls:
                z0,z1=zlay[L]
                for k in range(z0,z1):
                    sl=lab[:,:,k]; sl[m & (sl==(1 if net=='VBUS' else 2))]=code
            tdefs[f"t_{pname}_{pol}"]=code; code+=1
    # keep only the component connected to the bridge (6-connectivity, face neighbours)
    cl,ncl=ndi.label(lab>0)
    keep=np.unique(cl[lab==5]); keep=keep[keep>0]
    removed=int(((lab>0)&~np.isin(cl,keep)).sum())
    lab[~np.isin(cl,keep)]=0
    # sanity: every terminal must survive
    for t,c in tdefs.items():
        n=int((lab==c).sum())
        if n==0: raise SystemExit(f"terminal {t} empty after island removal")
    # VBUS and PGND voxels must never share a face (PEEC would conduct across it); only the bridge joins them
    grp=np.zeros(lab.shape,np.int8)
    grp[np.isin(lab,[1,3]+[c for t,c in tdefs.items() if t.endswith('_p')])]=1
    grp[np.isin(lab,[2,4]+[c for t,c in tdefs.items() if t.endswith('_n')])]=2
    nshort=0
    for axn in range(3):
        q=np.moveaxis(grp,axn,0); nshort+=int((((q[:-1]==1)&(q[1:]==2))|((q[:-1]==2)&(q[1:]==1))).sum())
    if nshort: raise SystemExit(f"{nshort} VBUS/PGND faces touch at pitch {p}: clearances unresolved, use a finer pitch")
    names={1:'cu_VBUS',2:'cu_PGND',3:'via_VBUS',4:'via_PGND',5:'bridge'}; names.update({c:t for t,c in tdefs.items()})
    flat=lab.ravel(order='F')   # pypeec index = ix + nx*iy + nx*ny*iz
    dom={nm:np.flatnonzero(flat==c).tolist() for c,nm in names.items()}
    c_center=[(x0+x1)/2*1e-3,(y0+y1)/2*1e-3,nz*dz/2*1e-3]
    import yaml
    geo={'mesh_type':'voxel','data_voxelize':{'param':{'n':[nx,ny,nz],'d':[p*1e-3,p*1e-3,dz*1e-3],'c':c_center},'domain_index':dom},
         'data_point':{'check_cloud':False,'filter_cloud':False,'pts_cloud':[]},
         'data_resampling':{'use_reduce':False,'use_resample':False,'resampling_factor':[1,1,1]},
         'data_conflict':{'resolve_rules':False,'resolve_random':False,'conflict_rules':[]},
         'data_integrity':{'check_integrity':True,'domain_connected':{'all':{'domain_group':[list(names.values())],'connected':True}},'domain_adjacent':{}}}
    with open(os.path.join(a.out,'geometry.yaml'),'w') as fh: yaml.safe_dump(geo,fh,default_flow_style=None,width=10**9)
    rho=1.72e-8; rho_via=rho*(0.1**2/(0.1**2-0.075**2))   # 25 um plating on a 0.2 mm hole, modelled as a solid column
    cu_list=['cu_VBUS','cu_PGND','bridge']+list(tdefs)
    prob={'material_def':{'copper':{'domain_list':cu_list,'material_type':'electric','orientation_type':'isotropic','var_type':'lumped'},
                          'via':{'domain_list':['via_VBUS','via_PGND'],'material_type':'electric','orientation_type':'isotropic','var_type':'lumped'}},
          'source_def':{t:{'domain_list':[t],'source_type':'voltage','var_type':'lumped'} for t in tdefs},
          'sweep_solver':{}}
    # driven port: voltage sources; other terminals: zero-current sources (plain copper)
    for t in tdefs: prob['source_def'][t]['source_type']='current'
    sweeps={}
    freqs=[float(f) for f in a.freqs.split(',')]
    for pname in port_refs:
        prev=None
        for f in freqs:
            tag=f"f{f/1e6:g}M_{pname}"
            sv={}
            for t in tdefs:
                sv[t]={'I_re':0.0,'I_im':0.0,'Y_re':1e-9,'Y_im':0.0}
            sweeps[tag]=dict(init=prev,param=dict(freq=f,material_val={'copper':{'rho_re':rho,'rho_im':0.0},'via':{'rho_re':rho_via,'rho_im':0.0}},source_val=sv),driven=pname)
            prev=tag
    # pypeec needs one source type per source domain for the whole problem -> make the port terminals voltage sources
    # in every sweep: driven pair stiff (1 mV / 0 V, Z 1e-9), others weak (0 V behind Z = 1e9 -> effectively open)
    for t in tdefs: prob['source_def'][t]['source_type']='voltage'
    for tag,s in sweeps.items():
        sv={}
        for t in tdefs:
            drv=t.startswith(f"t_{s['driven']}_")
            if drv: sv[t]={'V_re':1e-3 if t.endswith('_p') else 0.0,'V_im':0.0,'Z_re':1e-9,'Z_im':0.0}
            else:   sv[t]={'V_re':0.0,'V_im':0.0,'Z_re':1e9,'Z_im':0.0}
        prob['sweep_solver'][tag]={'init':s['init'],'param':dict(s['param'],source_val=sv)}
    with open(os.path.join(a.out,'problem.yaml'),'w') as fh: yaml.safe_dump(prob,fh,default_flow_style=None,width=10**9,sort_keys=False)
    meta=dict(stack=a.stack,pitch=p,dz=dz,n=[nx,ny,nz],n_grid=nx*ny*nz,n_active=int((lab>0).sum()),zlay=zlay,gaps_vox=gaps,
              gaps_mm=[gv*dz for gv in gaps],ncu=ncu,nvia=nvia,removed_island_vox=removed,terminals={t:int((lab==c).sum()) for t,c in tdefs.items()},
              ports=port_refs,short=SHORT[a.short],crop=[x0,y0,x1,y1])
    json.dump(meta,open(os.path.join(a.out,'meta.json'),'w'),indent=1)
    np.savez_compressed(os.path.join(a.out,'labels.npz'),lab=lab)
    print(json.dumps({k:meta[k] for k in ('n','n_grid','n_active','gaps_mm','nvia','removed_island_vox','terminals')}))
if __name__=='__main__': main()
