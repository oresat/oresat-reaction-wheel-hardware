#!/bin/bash
# One leg-C switching case: board export at R(fr) -> Xyce deck -> Xyce -> frequency-domain post-processing.
# usage: run_tr.sh <stack> <vbias> <i0> <fr> <lpad> <tag> [periods]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/home/solomon/code/odrive/dual-loop-modeling/pcb-inductance/venv/bin/python
XYCE=~/xyce_7_10/xyce_install/serial/bin/Xyce
stack=$1; vb=$2; i0=$3; fr=$4; lpad=$5; tag=$6; per=${7:-2}
mkdir -p "$HERE/xyce/$tag" "$HERE/results"
$PY "$HERE/mk_board_sub.py" "$HERE/mp/$stack" "$HERE/xyce/$tag/board.sub" --fr "$fr" > "$HERE/xyce/$tag/board.log"
$PY "$HERE/mk_tb.py" tran "$stack" "$vb" "$i0" "$HERE/xyce/$tag/tr.cir" --lpad "$lpad" --periods "$per" --sub "$HERE/xyce/$tag/board.sub"
cd "$HERE/xyce/$tag"
$XYCE tr.cir > tr.log 2>&1
grep -E "Number Failed Steps" tr.log | tail -1 || true
$PY "$HERE/post_tran.py" "$HERE/xyce/$tag/tr.cir.csv" "$HERE/mp/$stack" "$stack" "$vb" "$HERE/results/$tag" --fr "$fr" > "$HERE/results/$tag.txt"
echo "done $tag"
