"""Make a one-sweep smoke-test case from lane0 of a multi-terminal case: python mk_smoke.py <stack_root> <sweep_prefix>"""
import yaml, os, sys
root, pref = sys.argv[1], sys.argv[2]
P = yaml.safe_load(open(os.path.join(root, 'lane0', 'problem.yaml')))
k = [t for t in P['sweep_solver'] if t.startswith(pref)][0]
P['sweep_solver'] = {k: P['sweep_solver'][k]}
d = os.path.join(root, 'smoke'); os.makedirs(d, exist_ok=True)
yaml.safe_dump(P, open(os.path.join(d, 'problem.yaml'), 'w'), default_flow_style=None, width=10 ** 9, sort_keys=False)
if not os.path.exists(os.path.join(d, 'geometry.yaml')):
    os.symlink('../geometry.yaml', os.path.join(d, 'geometry.yaml'))
print(k)
