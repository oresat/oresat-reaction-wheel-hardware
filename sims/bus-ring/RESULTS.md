# Rev8 bus ring: results (2026-10-28)

This note gives the VBUS waveform at the L4 feed under the analog sense bundle during leg C switching, and the
pickup on the sense nodes, for the intended and the as-built stackup. All numbers are model results; there is no
bench data yet.

- Work folder: `sims/bus-ring/` (branch `worktree-bus-ring-sim`).
- Figures: `results/fig_edge_8v4_10a.png`, `results/fig_edge_7v6_5a.png`, `results/bus_trap_8v4.png`.
- Waveforms for the explorer: `results/bus_ring_waves.json` (format at the end).

## Summary

- **The aggressor is about the same in both stackups. The coupling into the sense traces is what got worse.**
  - VBUS at the feed rings at the same frequencies in both stackups.
  - Its high-frequency peak is *lower* as built (72 vs 113 mV at 8.4 V / 10 A). The as-built feed is more inductive,
    so it takes a smaller share of the edge current: I_feed/I_dev above 30 MHz is 0.006 vs 0.013.
  - The pickup on VSNS, ISNS and the feed-current EMF is ×6–10 higher as built, which follows the 2D coupling
    (×10 C, ×7–11 M).
- **Three components at the feed** (8.4 V, 10 A, duty 0.5):
  1. **Device-loop ring, 300–340 MHz.** 70–110 mV peak, 1/e in 2–10 ns, gone by about 100 ns. It comes from the
     LMG2100 commutation loop against Coss. The model's package has DC resistance only, so the real ring probably
     decays faster.
  2. **Bus modes at 1.3–1.5 MHz, plus 2–3, 6 and 27 MHz.** About 3.4 mV at 0.1–0.3 µs and 1–1.5 mV at
     0.6–1.2 µs, decaying over about 2 µs. These are the local MLCC banks against the bank-to-bulk and feed copper.
     As built they sit lower (1.3 vs 1.5 MHz) with about 35 % higher device-port impedance peaks.
  3. **96 kHz triangle, 116 mV p-p.** It comes from the bulk C and the 50 mΩ + 100 nH source. It is the same in
     both stackups.
- **After the 69 ns ADC aperture, as built, 8.4 V / 10 A:**

  | pickup | 0–200 ns | 0.2–0.5 µs | 0.5–2 µs |
  |---|---|---|---|
  | feed-current EMF (bound) | 0.45–1.46 mV | 0.35–1.14 mV | 0.12–0.39 mV |
  | VSNS | 0.35 mV | | |
  | ISNS | 0.04–0.12 mV | | |

  On the intended stack every entry is about 6–10× lower.
  - The EMF dominates. It is the slow redistribution of the feed current over about 300 ns after each edge, through
    the feed-to-trace mutual.
  - In ISNS units (INA296A3, 50 V/V × 2 mΩ = 0.1 V/A), 1 mV is 10 mA of phase-current error. It applies only to
    samples within about 0.5 µs of an edge.
- **The 45 MHz / 60 ns ring the explorer animation assumes does not match any of these.** The real picture is a
  300+ MHz burst that the aperture averages away, plus µs-scale MHz modes and the EMF of the feed-current
  redistribution.

## Method

1. **Board.** Multi-terminal PEEC of the VBUS and PGND copper (`build_mp.py`, PyPEEC 5.8, 100 µm × 11.5 µm voxels,
   crop x 85.5–117.5, y 89.5–113 mm). 28 terminals:
   - the three LMG2100 VIN pads and PGND pads;
   - the 8 cap banks;
   - probes P105 and P110 on the feed at x = 115.5 mm, y = 105 / 110 mm (VBUS on L4, PGND on L5);
   - the feed cut at y = 113 mm.

   The admittance matrix is extracted at DC and 10 MHz (`assemble_y.py`). Both matrices are reciprocal to 4e-6, and
   KCL holds to 1e-11 in both stacks.
2. **Bus circuit** (`ac_bus.py`): hub-referenced port impedances Z = R(f) + jωL.
   - L is the 10 MHz value. R(f) is R_dc + (R_10M − R_dc)·√(f / 10 MHz).
   - Caps are Murata SimSurfing ladders at the bus bias (`murata.py`). At 8.4 V they give 0.62 µF (2.2 µF 0402),
     2.10 µF (10 µF 0603) and 17.6 µF (47 µF 1210).
   - The feed continues 10 mm to J1, then C2/C27, then the pack and harness (50 mΩ + 100 nH).
3. **Device edge** (`mk_tb.py`, `run_tr.sh`).
   - Xyce runs the LMG2100R044 model (`models/`) on leg C's pads, with the leg's real gate-drive parts:
     2.7 Ω VCC and bootstrap resistors, 100 nF bootstrap, 22 Ω / 47 pF on the inputs.
   - Dead time is 10.4 ns. PWM is 96 kHz, centre-aligned, duty 0.5.
   - The load is 100 µH to duty·Vbus. Two periods are simulated; the last one is used. The integrator is BDF2.
   - The board is the exported bus subcircuit (`mk_board_sub.py`). It matches the Python model to 1e-4 at AC.
4. **Probes** (`post_tran.py`).
   - The device current from Xyce goes through an FFT to 1 GHz, then through the frequency-domain transfers with the
     full R(f): to P105/P110, and to the feed current.
   - Check against Xyce's own device-port voltage and feed current above 1 MHz: 2.4–7 % and 1.5–1.6 % rms.
5. **Pickup** (`pickup.py`). Coupling numbers are from the 2D study (`power-stage-rev8/docs/stackup-sim/HANDOFF.md`).
   - **VSNS:** 2.03 kΩ source with 13.4 pF on the node. C_c to VBUS is 1.88 pF as built, 0.188 pF intended.
   - **ISNS:** the INA296 output drives the ADC pin directly. Its output impedance above the loop bandwidth is
     bracketed at 20–100 Ω (assumption), with 10 pF on the node.
   - **Feed-current EMF in the trace loop:** M·dI_feed/dt. M is 2.5–6.9 pH/mm as built (0.2–0.9 intended) over
     23–27 mm of trace on the feed.
   - **ADC:** the 69 ns aperture is applied as a moving average.

## Board loop inductance, multi-port, 10 MHz (loop from a bank to leg C, device shorted at its pads)

| bank | intended | as built | ratio | single-port study ratio |
|---|---|---|---|---|
| C_bot (5 × 2.2 µF, hot loop) | 61.6 pH | 65.3 pH | ×1.06 | ×1.22 |
| C_top (through-board) | 82.4 | 89.6 | ×1.09 | ×1.20 |
| B_bot (leg to leg) | 205 | 417 | ×2.04 | ×2.07 (leg B) |
| BULK_R | 226 | 402 | ×1.77 | ×1.77 |
| BULK_L | 534 | 1234 | ×2.31 | ×2.27 |

The device pads are equipotential terminals here, which is a lower bound. The single-port study used a copper slab
across the pads, which adds about 40–80 pH. The near-bank loops therefore read lower, 62–90 pH vs 105–173 pH. The
far loops and every ratio agree.

## Leg C switching (VBUS = mean of P105/P110 unless noted; R at 300 MHz in Xyce)

| quantity | intended 8.4 V 10 A | as built 8.4 V 10 A | intended 7.6 V 5 A | as built 7.6 V 5 A |
|---|---|---|---|---|
| SW 10–90 %, on / off (ns) | 1.16 / 1.16 | 1.12 / 1.17 | 1.04 / 2.12 | 1.02 / 2.12 |
| device current peak at turn-on (A) | 19.6 | 19.6 | 14.0 | 14.0 |
| device-loop ring at the probes | 336–340 MHz | 333–337 MHz | 332–333 MHz | 329 MHz |
| VBUS > 30 MHz, peak within 300 ns, on / off edge (mV) | 113 / 98 | 72 / 60 | 92 / 35 | 58 / 22 |
| same, P105 alone (mV) | 144 / 113 | 97 / 74 | 121 / 41 | 81 / 27 |
| bus modes (1–30 MHz), dominant f | 1.44–1.50 MHz | 1.30–1.35 MHz | 1.40 MHz | 1.19–1.20 MHz |
| bus modes, peak at 0.1–0.3 / 0.6–1.2 µs (mV) | 3.3 / 1.3–1.4 | 3.4 / 0.9 | 1.5 / 0.7 | 1.6 / 0.4 |
| device-port \|Z\| peaks | 1.47 MHz 3.4 mΩ, 2.86 MHz 2.0, 5.88 MHz 4.5 | 1.27 MHz 4.6 mΩ, 2.34 MHz 4.4, 5.71 MHz 5.8 | | |
| 96 kHz ripple at the feed, p-p (mV) | 116 | 116 | 53 | 53 |
| VSNS node, raw peak (mV) | 1.65 | 10.5 | 1.31 | 8.3 |
| VSNS after 69 ns aperture, 0–200 ns (mV) | 0.04 | 0.35 | 0.02 | 0.16 |
| ISNS at 20–100 Ω, after aperture, 0–200 ns (mV) | 0.006–0.020 | 0.04–0.12 | 0.005–0.015 | 0.03–0.09 |
| feed→trace EMF, raw peak (mV) | 1.1–5.9 | 6.3–20 | 0.9–4.6 | 5.0–16 |
| EMF after aperture, 0–0.2 / 0.2–0.5 / 0.5–2 µs (mV) | 0.05–0.25 / 0.03–0.14 / 0.01–0.04 | 0.45–1.46 / 0.35–1.14 / 0.12–0.39 | 0.02–0.12 | 0.21–0.70 |

Sensitivity cases at 8.4 V / 10 A:
- **Pad +60 pH** (the slab-equivalent): the device ring moves to 301–308 MHz. The VBUS peak changes by −8 to −25 %.
  The bus modes and the pickup after the aperture are unchanged.
- **Phase current −10 A** (HS turn-off becomes the hard edge): SW peaks at 13.9 V. VBUS and pickup are within
  ±10 % of the +10 A case.
- **Copper R taken at 10 MHz instead of 300 MHz** in Xyce: no visible change (as built).

## Mechanisms

- **Device-loop ring.** Each edge rings the LMG2100 commutation loop: package ≈ 0.2 nH plus the board pad-to-bank
  path, against the EPC2090 Coss at 8 V.
  - The device-port voltage rings ±1 V.
  - The VBUS planes carry a fraction to the feed, set by the quasi-static voltage division of the plane pair.
  - The intended stack has tight VBUS/PGND plane pairs (L3/L2 and L4/L5 at 0.1 mm), which spread the ring further.
    That is why it reads 1.5× higher at the probes.
  - The 69 ns aperture averages ≈ 23 cycles. The ring still matters for anything wideband, such as comparators and
    the INA input.
- **Bus modes.** The local banks ring against the bank-to-bulk L.
  - The as-built bus is more inductive (×1.8–2.3 per path), so the modes move down and the device sees about 35 %
    more impedance at the peaks.
  - The feed voltage is set by the current divider, so its amplitude at the probes is about the same in both
    stackups.
- **Feed-current redistribution.** After each edge the feed current changes by about 1.5 A (10 A step) over
  200–400 ns, then rings at 1–2 MHz. dI/dt × M is the largest pickup term after the aperture.
  - The intended feed carries more of the HF current, but its M is 7–11× lower.

## Approximations

- Only VBUS and PGND copper; GND/AGND and the U4 input caps (VBUS–GND) are not in the model. The probe reference
  is PGND on L5; the sense traces reference AGND.
- The device pads are equipotential terminals, which is a lower bound on the board loop. The pad +60 pH case
  brackets this.
- The feed beyond y = 113 mm is a lumped 220 pH (as built) / 165 pH (intended). The pack and harness are
  50 mΩ + 100 nH.
- R(f) is extrapolated as √f above 10 MHz. The PEEC is quasi-static, so transfers above ≈ 1 GHz are not meaningful.
  Spectra are cut at 1 GHz.
- The LMG2100R044 model is unofficial: EPC2090 dies with an LMG1205-style driver, and a package L of ±50 %.
- **ISNS:** the INA296 output impedance above its loop bandwidth is a bracket, not data.
- **EMF:** the full EMF is a bound. How much reaches the ADC depends on where the trace/AGND loop closes.
- Only one leg switches, with the other legs open. In a real PWM period the three legs' edges are staggered, and each
  adds its own burst.
- The 2.2 µF 0402 uses the Murata model of GRT155C81C225KE13. The BOM part (ME13) has no SimSurfing model; the KE13
  has the same size, dielectric and rating, with K tolerance instead of M.

## `results/bus_ring_waves.json`

- `cases.<label>`: one PWM period, `t` in ns from the period start. LS is on at the start; HS is on, centred in the
  period, for duty 0.5.
- `edges_ns`: the HI command edges [HS on, HS off]. SW moves about 39 ns (on) and 31 ns (off) after the command.
- Series:

  | key | quantity | unit |
  |---|---|---|
  | `vbus` | VBUS AC at the feed (mean of P105/P110) | mV |
  | `ifeed` | feed current AC | A |
  | `idev` | device current | A |
  | `sw` | SW node | V |
  | `vsns` | VSNS node pickup | mV |
  | `isns_z20`, `isns_z100` | ISNS node pickup at 20 / 100 Ω INA output impedance | mV |
  | `emf_lo`, `emf_hi` | feed→trace EMF at the low / high M | mV |

- The time step is 0.32 ns within 300 ns of each edge and 5 ns elsewhere.
- `metrics` and `pickup` hold the scalar numbers above.
