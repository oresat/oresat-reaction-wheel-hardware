"""Print each pad's net for the named refs: python refnets.py FB4 C34 R9"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build3d as b3
fp = b3.footprints()
for r in sys.argv[1:]:
    print(r, sorted({(p['num'], p['net']) for p in fp[r]['pads']}))
