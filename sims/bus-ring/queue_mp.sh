#!/bin/bash
# sequential PyPEEC queue for the rev8 bus-ring multi-terminal extraction; skips cases that already have terminals.json
cd ~/rw8-busring
source ~/dual-workdir/pcb-inductance/venv/bin/activate
export LD_LIBRARY_PATH=$VIRTUAL_ENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export OMP_NUM_THREADS=10 MKL_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10
for c in "$@"; do
  [ -f "$c/terminals.json" ] && { echo "skip $c" >> queue.log; continue; }
  echo "$(date -Is) start $c" >> queue.log
  python run_case.py "$c" --tol tol10.yaml > "$c/run.log" 2>&1
  echo "$(date -Is) end $c exit $?" >> queue.log
done
echo "$(date -Is) lane done" >> queue.log
