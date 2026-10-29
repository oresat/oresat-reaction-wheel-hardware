# Rev8 bus ring study: STATUS

Goal: the real VBUS waveform at the feed under the analog sense bundle during PWM switching, intended vs as-built
stackup. Replaces the assumed ring in the explorer's ADC animation and the lumped bus-impedance estimate.

Work folder: `sims/bus-ring/` in worktree `bus-ring-sim` (branch `worktree-bus-ring-sim`). Prior study files:
`power-stage-rev8/docs/stackup-sim/` in the main checkout (HANDOFF.md).

## Plan
1. Multi-terminal PEEC of VBUS/PGND (28 terminals) for both stacks: `build_mp.py` -> `mp/<stack>/`. DONE.
   Terminals: 3 leg devices (VIN pad, PGND pads), 6 local banks, 2 bulk banks, probes P105 / P110 on the L4 feed
   (V on L4, G on L5), feed cut at y = 113 toward J1.
2. Y-matrix at DC + 10 MHz on tinyhorse. DONE 2026-10-29 01:11Z (both stacks, about 2 h per lane); instance stopped.
3. `assemble_y.py`: reciprocity 4e-6, KCL 1e-11 both stacks; far-loop ratios match the single-port study. DONE.
4. `ac_bus.py` with Murata ladders (`murata.py`). DONE. `test_trap.py` PASS.
5. LMG2100R044 (`models/`) in Xyce with the exported bus (`mk_board_sub.py`, `mk_tb.py`, `run_tr.sh`), device
   current -> frequency-domain transfers (`post_tran.py`). DONE: 4 cases x 2 stacks + 1 R sensitivity.
6. Pickup (`pickup.py`), tables (`summarize.py`), figures (`fig_edge.py`), explorer export (`export_wave.py`). DONE.
   Results: `RESULTS.md`.

## Inputs (Solomon, 2026-10-28)
- LMG2100R044 model: /tmp/spice/lmg2100r044.lib (copied to `models/`). The `lmg-spice` session owns it.
- Operating point: 8.4 V / 10 A worst case, 7.6 V / 5 A nominal.
- Pack + harness: 50 mOhm + 100 nH.
- Murata models: `murata_dl/` (download_murata_mlcc, 25 degC, 7.6 and 8.4 V). The 0402 2.2u uses the KE13 model.

## Xyce notes
- Integrator: BDF2 (`method=gear maxord=2`). Trap diverges on the stiff Murata ladders; higher-order Gear stalls in
  the LMG input Schmitt triggers. `nonlin-tran maxstep=100` for the LI edge breakpoint.
- Start with both FETs off and hand the load current to the bridge after LS turn-on (OP fails otherwise).
- Open terminals (probes, legs A/B) are left out of the Xyce board subckt: exact in Z form, and inductor-only nodes
  ring under trap.
- Xyce cannot read I(L) of K-coupled inductors in B sources: 0 V sense sources in each branch.

## Known approximations
- Only VBUS and PGND copper; GND/AGND and the U4 input caps (VBUS-GND) are not in the model.
- Probe G terminal is PGND on L5, not AGND: the sense traces reference AGND, which ties to GND/PGND elsewhere.
- Feed beyond y = 113 to J1 is a lumped L (2D per-mm x ~10 mm).
- R(f) interpolated as sqrt(f) between DC and 10 MHz; L fixed at the 10 MHz value.
