"""
Run the PyPEEC mesher + solver for one case folder (geometry.yaml + problem.yaml) and
store compact results:
  - terminals.json : V, I, S of every source terminal for every sweep + solver status
  - voxel.mpk      : voxel structure (for the PyPEEC viewer)
  - fields_f30M.npz: voxel current density / potential of the 30 MHz sweeps (plots)

usage: python scripts/run_case.py runs/A_p100_m4 [--fields]
"""

import argparse
import json
import os
import time
import resource

import numpy as np
import scisave
import pypeec

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def cplx(v):
    v = complex(v)
    return [v.real, v.imag]


def main(case, fields, tol_file, fields_all=False, reuse_voxel=False):
    t0 = time.time()
    data_problem = scisave.load_config(os.path.join(case, "problem.yaml"))
    data_tolerance = scisave.load_config(tol_file)

    vfile = os.path.join(case, "voxel.mpk")
    if reuse_voxel and os.path.isfile(vfile) and os.path.getmtime(vfile) > os.path.getmtime(os.path.join(case, "geometry.yaml")):
        # mesher output of an earlier run / xtalk/mesh_check.py (integrity already checked), newer than geometry.yaml
        data_voxel = scisave.load_data(vfile)
    else:
        data_geometry = scisave.load_config(os.path.join(case, "geometry.yaml"))
        data_voxel = pypeec.run_mesher_data(data_geometry=data_geometry)
        scisave.write_data(vfile, data_voxel)
    t1 = time.time()

    data_solution = pypeec.run_solver_data(data_voxel=data_voxel, data_problem=data_problem, data_tolerance=data_tolerance)
    t2 = time.time()

    out = {"status": bool(data_solution["status"]), "t_mesh_s": t1 - t0, "t_solve_s": t2 - t1,
           "maxrss_GB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, "sweeps": {}}
    init = data_solution["data_init"]
    out["n_voxel_c"] = int(len(init["idx_vc"]))
    out["n_face_c"] = int(len(init["idx_fc"]))
    for tag, sw in data_solution["data_sweep"].items():
        out["sweeps"][tag] = {
            "freq": float(sw["freq"]),
            "solution_ok": bool(sw["solution_ok"]),
            "solver_ok": bool(sw["solver_ok"]),
            "condition_ok": bool(sw["condition_ok"]),
            "n_iter": int(sw["solver_status"].get("n_iter", -1)) if isinstance(sw["solver_status"], dict) else -1,
            "sources": {k: {"V": cplx(v["V"]), "I": cplx(v["I"]), "S": cplx(v["S"])} for k, v in sw["source_values"].items()},
            "P_total": float(np.real(sw["integral_total"]["P_total"])) if "P_total" in sw["integral_total"] else None,
            "W_total": float(np.real(sw["integral_total"]["W_total"])) if "W_total" in sw["integral_total"] else None,
        }
    with open(os.path.join(case, "terminals.json"), "w") as fid:
        json.dump(out, fid, indent=1)

    if fields_all:
        save = {"n": np.array(init["n"]), "d": np.array(init["d"]), "c": np.array(init["c"]),
                "idx_vc": np.array(init["idx_vc"])}
        for tag, sw in data_solution["data_sweep"].items():
            save["J_" + tag] = np.array(sw["field_values"]["J_c"]["var"]).astype(np.complex64)
            save["V_" + tag] = np.array(sw["field_values"]["V_c"]["var"]).astype(np.complex64)   # voxel potentials
            save["freq_" + tag] = np.array(sw["freq"])
        np.savez_compressed(os.path.join(case, "fields_all.npz"), **save)

    if fields:
        save = {"n": np.array(init["n"]), "d": np.array(init["d"]), "c": np.array(init["c"]),
                "idx_vc": np.array(init["idx_vc"])}
        for tag, sw in data_solution["data_sweep"].items():
            if abs(sw["freq"] - 30e6) < 1.0:
                save["J_" + tag] = np.array(sw["field_values"]["J_c"]["var"])
                save["V_" + tag] = np.array(sw["field_values"]["V_c"]["var"])
        np.savez_compressed(os.path.join(case, "fields_f30M.npz"), **save)

    print(json.dumps({k: out[k] for k in ["status", "t_mesh_s", "t_solve_s", "maxrss_GB", "n_voxel_c", "n_face_c"]}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--fields", action="store_true")
    ap.add_argument("--fields-all", action="store_true",
                    help="save J and the voxel potential V (complex64) of every sweep to fields_all.npz")
    ap.add_argument("--tol", default=os.path.join(ROOT, "config", "tolerance.yaml"))
    ap.add_argument("--reuse-voxel", action="store_true",
                    help="load <case>/voxel.mpk (if newer than geometry.yaml) instead of re-meshing")
    a = ap.parse_args()
    main(a.case, a.fields, a.tol, a.fields_all, a.reuse_voxel)
