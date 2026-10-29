#!/bin/bash
# Build ~/rw8-fields from the finished ~/rw8-busring cases (problem, geometry, voxel mesh) and start 3 lanes.
set -e
mkdir -p ~/rw8-fields
cp -p ~/rw8-busring/run_case.py ~/rw8-busring/tol10.yaml ~/rw8-fields/
for s in intended asbuilt; do
  for l in 0 1 2; do
    d=~/rw8-fields/mp/$s/lane$l; mkdir -p $d
    cp -pL ~/rw8-busring/mp/$s/lane$l/geometry.yaml $d/
    cp -p ~/rw8-busring/mp/$s/lane$l/problem.yaml $d/
    [ -f ~/rw8-busring/mp/$s/lane$l/voxel.mpk ] && cp -p ~/rw8-busring/mp/$s/lane$l/voxel.mpk $d/
  done
done
ls -la ~/rw8-fields/mp/*/lane*/ | head -40
for l in 0 1 2; do
  screen -dmS f$l bash ~/rw8-fields/queue_f.sh mp/intended/lane$l mp/asbuilt/lane$l
done
sleep 2; screen -ls
