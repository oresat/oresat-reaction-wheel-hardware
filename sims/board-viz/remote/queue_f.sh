#!/bin/bash
# PyPEEC field reruns for board-viz (fields_all.npz: J_c and V_c of every sweep). One lane per invocation.
cd ~/rw8-fields
source ~/dual-workdir/pcb-inductance/venv/bin/activate
export LD_LIBRARY_PATH=$VIRTUAL_ENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export OMP_NUM_THREADS=10 MKL_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10
for c in "$@"; do
  [ -f "$c/fields_all.npz" ] && { echo "skip $c" >> queue.log; continue; }
  echo "$(date -Is) start $c" >> queue.log
  python run_case.py "$c" --tol tol10.yaml --fields-all --reuse-voxel > "$c/run.log" 2>&1
  echo "$(date -Is) end $c exit $?" >> queue.log
done
echo "$(date -Is) lane done" >> queue.log
