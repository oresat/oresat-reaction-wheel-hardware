import json, math, os, sys, glob
PORTS=['LOC_C_bot','LOC_C_top','LOC_B','BULK_R','BULK_L']
DESC={'LOC_C_bot':'leg C bottom 2.2u x5 (hot loop)','LOC_C_top':'leg C top caps x10','LOC_B':'leg B caps x15 (inter-leg)',
      'BULK_R':'right 47u bulk x4','BULK_L':'left 47u bulk x4 (far)'}
def load(d):
    f=os.path.join(d,'terminals.json')
    if not os.path.isfile(f): return None
    t=json.load(open(f)); out={}
    for tag,s in t['sweeps'].items():
        S=s['sources']; pn=[k for k in S if k.endswith('_p')][0]; nn=pn[:-2]+'_n'
        Z=(complex(*S[pn]['V'])-complex(*S[nn]['V']))/complex(*S[pn]['I'])
        out[s['freq']]=dict(L_pH=Z.imag/(2*math.pi*s['freq'])*1e12,R_mOhm=Z.real*1e3,ok=s['solver_ok'] and s['solution_ok'],n_iter=s['n_iter'])
    out['_meta']=dict(t_solve=t['t_solve_s'],rss=t['maxrss_GB'])
    return out
def table(root):
    print(f"== {root}")
    print(f"  {'port (loop to leg-C short)':38s} {'f':>6s} | {'intended L pH':>13s} {'as-built L pH':>13s} {'ratio':>6s} {'delta pH':>9s} | {'R int/blt mOhm':>15s}")
    res={}
    for p in PORTS:
        a=load(os.path.join(root,'intended_'+p)); b=load(os.path.join(root,'asbuilt_'+p))
        res[p]=(a,b)
        fs=sorted(set(k for k in (a or {}) if k!='_meta')|set(k for k in (b or {}) if k!='_meta'))
        for f in fs:
            la=a[f]['L_pH'] if a and f in a else float('nan'); lb=b[f]['L_pH'] if b and f in b else float('nan')
            ra=a[f]['R_mOhm'] if a and f in a else float('nan'); rb=b[f]['R_mOhm'] if b and f in b else float('nan')
            print(f"  {DESC[p]:38s} {f/1e6:4g}M | {la:13.1f} {lb:13.1f} {lb/la:6.2f} {lb-la:9.1f} | {ra:6.3f} / {rb:6.3f}")
    return res
if __name__=='__main__':
    for r in sys.argv[1:]: table(r)
