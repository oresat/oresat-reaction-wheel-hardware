# 2D quasi-static cross-section solver: Maxwell C matrix (with dielectrics) and TEM L = mu0 eps0 inv(C0).
# Finite-volume on a non-uniform rectilinear grid; conductors are perfect, potential applied at their faces.
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spla
EPS0=8.8541878128e-12; MU0=4e-7*np.pi
STACKS={
 # (name, thickness_mm, kind, eps)   copper layers named by KiCad layer
 'intended':[('F.Cu',.035,'cu',None),('d1',.092,'d',4.1),('In1.Cu',.035,'cu',None),('d2',.100,'d',4.6),('In2.Cu',.035,'cu',None),
             ('d3a',.092,'d',4.1),('d3b',.865,'d',4.6),('d3c',.092,'d',4.1),('In3.Cu',.035,'cu',None),('d4',.100,'d',4.6),
             ('In4.Cu',.035,'cu',None),('d5',.092,'d',4.1),('B.Cu',.035,'cu',None)],
 'asbuilt': [('F.Cu',.035,'cu',None),('d1',.100,'d',4.5),('In1.Cu',.035,'cu',None),('d2',.535,'d',4.5),('In2.Cu',.035,'cu',None),
             ('d3',.100,'d',4.5),('In3.Cu',.035,'cu',None),('d4',.535,'d',4.5),('In4.Cu',.035,'cu',None),('d5',.100,'d',4.5),('B.Cu',.035,'cu',None)],
}
def grid1d(breaks, hmin, hmax, lo, hi, grow=1.25):
    """non-uniform grid: dense (hmin) at breakpoints, growing to hmax between them."""
    br=sorted(set([lo,hi]+[b for b in breaks if lo<b<hi]))
    edges=[lo]
    for a,b in zip(br[:-1],br[1:]):
        L=b-a; seg=[]
        # grow from both ends
        h=hmin; s=[]; x=0
        left=[];right=[]
        xl=0; xr=0; hl=hmin; hr=hmin
        while xl+xr < L-1e-12:
            if xl<=xr:
                hh=min(hl,hmax,L-xl-xr); left.append(hh); xl+=hh; hl*=grow
            else:
                hh=min(hr,hmax,L-xl-xr); right.append(hh); xr+=hh; hr*=grow
        cells=left+right[::-1]
        # merge a tiny trailing cell
        cells=[c for c in cells if c>1e-9]
        x=a
        for c in cells: x+=c; edges.append(x)
        edges[-1]=b
    e=np.array(edges)
    keep=np.concatenate([[True],np.diff(e)>1e-9]); return e[keep]
def build(intervals, stack, a0, a1, board_lo, board_hi, air=3.0, hmin_u=0.005, hmax_u=0.025, hmin_z=0.005, hmax_z=0.02, vacuum=False):
    """intervals: {layer:{net:[(a,b),...]}} along u (mm). Board dielectric exists for u in [board_lo,board_hi]."""
    # z positions (mm), z=0 at bottom of B.Cu, increasing upward (F.Cu on top)
    zs={}; z=0.0; layers=[]
    for name,t,kind,eps in reversed(stack):
        layers.append((name,z,z+t,kind,eps)); z+=t
    ztot=z
    zb=[l[1] for l in layers]+[ztot]
    ub=[board_lo,board_hi]
    for L,d in intervals.items():
        for net,iv in d.items():
            for a,b in iv: ub+= [a,b]
    ue=grid1d(ub,hmin_u,hmax_u,a0,a1)
    ze=grid1d(zb,hmin_z,hmax_z,-air,ztot+air,grow=1.3)
    # far air: let it grow larger
    nu,nz=len(ue)-1,len(ze)-1
    uc=(ue[:-1]+ue[1:])/2; zc=(ze[:-1]+ze[1:])/2; hu=np.diff(ue); hz=np.diff(ze)
    eps=np.ones((nu,nz)); cond=-np.ones((nu,nz),int)
    nets=sorted({n for d in intervals.values() for n in d})
    nid={n:i for i,n in enumerate(nets)}
    inboard=(uc>=board_lo)&(uc<=board_hi)
    for name,z0,z1,kind,e in layers:
        zm=(zc>=z0)&(zc<=z1)
        if kind=='d' and not vacuum:
            eps[np.ix_(inboard,zm)]=e
        if kind=='d' and vacuum: pass
        if kind=='cu':
            # copper cells: within intervals; elsewhere on the copper layer: filled with neighbouring dielectric (use prepreg-ish avg)
            if not vacuum:
                # resin fill between copper on a layer: take eps of adjacent dielectric (avg of above/below)
                idx=[i for i,l in enumerate(layers) if l[0]==name][0]
                es=[layers[j][4] for j in (idx-1,idx+1) if 0<=j<len(layers) and layers[j][3]=='d']
                outer = idx in (0,len(layers)-1)
                if es and not outer: eps[np.ix_(inboard,zm)]=np.mean(es)   # inner layers: resin fill; outer: air
            for net,iv in intervals.get(name,{}).items():
                for a,b in iv:
                    um=(uc>=a)&(uc<=b)
                    cond[np.ix_(um,zm)]=nid[net]
    return dict(ue=ue,ze=ze,uc=uc,zc=zc,hu=hu,hz=hz,eps=eps,cond=cond,nets=nets,layers=layers,ztot=ztot)
def maxwell(G):
    hu,hz,eps,cond=G['hu'],G['hz'],G['eps'],G['cond']
    nu,nz=eps.shape; N=nu*nz
    idx=np.arange(N).reshape(nu,nz)
    free=(cond<0)
    fidx=-np.ones(N,int); fidx[free.ravel()]=np.arange(free.sum())
    nf=free.sum(); nc=len(G['nets'])
    rows=[];cols=[];vals=[]   # free-free
    brow=[];bcon=[];bval=[]   # free-conductor couplings
    qrow=[];qval=[]           # for charge: conductor id, free index, G
    def faces(axis):
        if axis==0:
            d1=hu[:-1,None]/2; d2=hu[1:,None]/2; area=np.broadcast_to(hz[None,:],(nu-1,nz))
            e1=eps[:-1,:]; e2=eps[1:,:]; c1=cond[:-1,:]; c2=cond[1:,:]; i1=idx[:-1,:]; i2=idx[1:,:]
        else:
            d1=hz[None,:-1]/2; d2=hz[None,1:]/2; area=np.broadcast_to(hu[:,None],(nu,nz-1))
            e1=eps[:,:-1]; e2=eps[:,1:]; c1=cond[:,:-1]; c2=cond[:,1:]; i1=idx[:,:-1]; i2=idx[:,1:]
        d1=np.broadcast_to(d1,e1.shape); d2=np.broadcast_to(d2,e1.shape)
        return d1.ravel(),d2.ravel(),area.ravel(),e1.ravel(),e2.ravel(),c1.ravel(),c2.ravel(),i1.ravel(),i2.ravel()
    Gff=[];
    for ax in (0,1):
        d1,d2,area,e1,e2,c1,c2,i1,i2=faces(ax)
        # free-free
        m=(c1<0)&(c2<0)
        g=EPS0*area[m]*1e-3/((d1[m]/e1[m]+d2[m]/e2[m])*1e-3)  # per metre depth: area(mm)->m * 1m depth / dist(m)
        a=fidx[i1[m]]; b=fidx[i2[m]]
        rows+= [a,b,a,b]; cols+=[a,b,b,a]; vals+=[g,g,-g,-g]
        # free(1)-cond(2)
        m=(c1<0)&(c2>=0)
        g=EPS0*area[m]/(d1[m]/e1[m]); a=fidx[i1[m]]
        rows.append(a); cols.append(a); vals.append(g); brow.append(a); bcon.append(c2[m]); bval.append(g)
        m=(c2<0)&(c1>=0)
        g=EPS0*area[m]/(d2[m]/e2[m]); a=fidx[i2[m]]
        rows.append(a); cols.append(a); vals.append(g); brow.append(a); bcon.append(c1[m]); bval.append(g)
        m=(c1>=0)&(c2>=0)&(c1!=c2)
        if m.any(): raise RuntimeError('two different conductors touch')
    A=sp.csc_matrix((np.concatenate(vals),(np.concatenate(rows),np.concatenate(cols))),shape=(nf,nf))
    brow=np.concatenate(brow); bcon=np.concatenate(bcon); bval=np.concatenate(bval)
    B=sp.csc_matrix((bval,(brow,bcon)),shape=(nf,nc))   # coupling free<-conductor
    lu=spla.splu(A)
    V=lu.solve(B.toarray())          # nf x nc : free potentials for each unit conductor excitation
    # charge on conductor j for excitation k: Q_j = sum_faces g (V_j - V_free) = sum g*(delta_jk) - (B^T V)_jk
    gsum=np.bincount(bcon,weights=bval,minlength=nc)
    C=np.diag(gsum)-B.T@V
    return C, V, (fidx,free)
def reduce_ref(C,nets,ref):
    k=[i for i,n in enumerate(nets) if n!=ref]
    return C[np.ix_(k,k)],[nets[i] for i in k]
