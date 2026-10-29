# Rev8 wrong stackup: what else it touches (review, 2026-10-28)

A general look at what the as-built stackup (KiCad default, 0.1 / 0.535 / 0.1 / 0.535 / 0.1 mm) changes beyond the
two findings already worked out:

- the analog bundle now references the L4 VBUS feed (`power-stage-rev8/docs/stackup-sim/HANDOFF.md`);
- the bus ring and sense pickup (`sims/bus-ring/RESULTS.md`).

Everything here uses the current board file (rev 8.1.1). It is identical to the built revisions except in the
regulator corner. All numbers are model results; there is no bench data.

Confidence tags:

- **computed:** from board geometry with a solver or a plate model;
- **estimated:** a hand calculation on top of computed numbers, good to about ×3;
- **judgment:** reasoning without a number that settles it.

## Bottom line

- **Nothing new is on the scale of the two known problems.** Those are the bundle pickup (×6–10) and the VBUS
  distribution inductance (×1.8–2.3). Every other cross-net overlap, crosstalk path, loop and thermal path checked
  here is either unchanged, slightly better, or (in flight firmware) worse by an amount far below 1 ADC LSB. One ADC
  LSB is 0.73 mV, or about 7 mA of phase current.
- **PGND over GND (Solomon's question): it doesn't matter.** Total PGND/GND plate capacitance goes from 9 to 18 pF.
  The new part sits around J1 and in a strip beside NT1. PGND and GND are already tied at NT1 and inside each
  LMG2100, so a few pF between them carries at most nA at bus-mode frequencies and about 1 mA at the 330 MHz device
  ring. Details are in the next section.
- **The largest new effect is small:** for 5–8 mm per net near the MCU, the analog bundle sits over **digital GND**
  (L4) instead of AGND (L2). That is 0.4–0.6 pF per net to GND, and the estimated pickup is ≤0.2 mV, asynchronous to
  the PWM.
- **No conclusion of the prior study is contradicted.** Three refinements:
  - gate drive "no change" is confirmed, net by net;
  - the INA296 REF1 pins are fed from +VREF along the same bundle, which partly cancels the feed-current EMF, so
    the EMF numbers in RESULTS.md are a true upper bound (realistically about 0.5–0.7× of it for content below
    1–2 MHz);
  - the Kelvin pairs are not entirely "over PGND" as built: 20% of phase A's pair runs over the SW-node keep-outs.
    This is harmless.

## Your question: PGND and GND facing each other

Yes, there are such places. In most of them L3 GND sits over L4 PGND, 0.1 mm apart. Plate capacitance (no fringing)
by region (`fig_gnd_overlap.png`):

| region | intended | as built |
|---|---|---|
| around J1 (x ≈ 104–111, y ≈ 113–125) | 4.2 pF (L1-L2 3.5, L3-L4 0.7) | **11.1 pF** (L3-L4 7.5 over 19 mm², L1-L2 3.6) |
| strip beside NT1 (x ≈ 111–113.5, y ≈ 101–113) | 0.4 pF | **3.9 pF** (L3-L4, 10 mm²) |
| band south edge and left strip (y ≈ 99; x ≈ 89–90) | 4.3 pF (mostly L4 GND over L5 PGND) | 3.2 pF (L3 PGND over L4 GND 1.8) |
| **total** | **9.0 pF** | **18.4 pF** |

It doesn't matter, for four reasons:

1. **A capacitor only does something if there is a voltage across it.** PGND and GND are tied at DC at NT1. They are
   tied again inside every LMG2100: the part's AGND pin is on your GND net, and the datasheet says AGND is
   "internally connected to low-side GaN FET source".
   - At the J1 patch, the PGND-to-GND voltage is the PGND drop between J1 and NT1 (about 17 mm). That is about 1 mV
     during the µs-scale feed-current redistribution, and at most about 50 mV at the 330 MHz device ring. The ring
     is only 72 mV VBUS-to-PGND at the feed as built.
   - Through 11 pF this is tens of nA and at most about 1 mA, which returns to NT1 through the GND planes and leaves
     well under 1 mV behind.
   - The NT1 strip sits next to the tie itself, so it sees almost no voltage.
2. **The tie wins below about 1–2 GHz.** 18 pF has an impedance equal to that of a sub-nH net tie only at
   1–2 GHz. Below that, NT1 is the connection and the overlap does nothing.
3. **The intended stack already had 9 pF of this**: L1-L2 at J1, and L4 GND over L5 PGND along the band edge. As
   built, the total roughly doubles, from small to small.
4. **AGND is not involved.** AGND–PGND facing is ≤0.1 pF in both stacks, and AGND–GND drops from 5.4 to 4.0 pF.
   AGND is the net the ADC references.

The same J1 area also has **L3 GND over the L4 VBUS feed**: VBUS/GND goes from 6.4 to 20.7 pF. The argument is the
same, and stronger, because U4's input caps (C4, C5 and C86, about 6 µF effective) already connect VBUS to GND
3 mm from NT1. The overlap injects about 2 mA at 330 MHz and less than 1 µA at 96 kHz–1.3 MHz.

**What would make a PGND/GND overlap matter:** PGND copper that carries hot-loop di/dt, sitting over GND far from
NT1, under something sensitive. Nothing like that exists here: under the legs, L3/L4 are VBUS band and PGND.
**Check:** none needed.

## Ranked list

The ranking is impact × likelihood. Items 1–7 are effects that exist, from largest to smallest. Items 8–18 were
checked and do not matter. The prior study's two findings are still #1 and #2 overall; this list ranks only what is
beyond them.

| # | item | intended → as built | impact × likelihood | conf | settle with |
|---|---|---|---|---|---|
| 1 | analog bundle over digital GND near U3 | 0.05 → 0.4–0.6 pF per net to GND | low × medium | computed / judgment | ADC noise floor with the bridge off, regulators on |
| 2 | DAC_1–3 under VSNS/ISNS near U3 | 2 → 22 fF per crossing | none in flight; low in debug | computed | confirm the test build keeps the DACs static |
| 3 | VBUS facing GND (J1, NT1 strip) | 6.4 → 20.7 pF | negligible | computed / estimated | none needed |
| 4 | PGND facing GND (J1, NT1 strip) | 9.0 → 18.4 pF | negligible | computed / estimated | none needed |
| 5 | Kelvin pairs over the SW keep-outs | CM 15 → 25 fF; DM M 0.1–0.24 → ≈0 pH/mm | neutral to better | computed | the prior CMP4 sweep |
| 6 | SW-node capacitance through the keep-outs | +0.4–0.5 pF per phase | negligible | computed | none needed |
| 7 | VBUS/PGND plate capacitance lost | 222 → 103 pF | negligible | computed | VBUS ring at C97/C98 (prior open item) |
| 8 | gate drive, SPI, trace/debug, +3V3 on L4 | identical GND exposure | no change (prior confirmed) | computed | none needed |
| 9 | edge crosstalk inside the bundle | 32.5 → 33.6 fF/mm | no change | computed | none needed |
| 10 | U4/U14 switching loops | same layers, same C | no change | computed / judgment | the item 1 measurement covers it |
| 11 | MCU power distribution | same | no change | judgment | none needed |
| 12 | LMG2100 thermal path | through-board vias 13.7–16.2 → 13.2–15.6 K/W | wash (prior confirmed) | estimated | thermocouple on U12 at a fixed load, if a reference board exists |
| 13 | MA732 stray field from the band | 0.11 → 0.28 µT/A | negligible | estimated | angle offset vs bus current at a locked rotor |
| 14 | plane-cavity resonances | 1.5–2.5 GHz both | no | computed | none needed |
| 15 | controlled impedance | Z0 50.9 → 49.8 Ω | no | computed | none needed |
| 16 | capacitor ripple-current sharing at 96 kHz | set by C, not L | no change | estimated | none needed |
| 17 | +3V3A pickup into the INA supplies | ≤0.5 mV at 330 MHz on the supply | negligible | estimated | none needed |
| 18 | right bulk-cap vias beside the bundle | 0.8–2.7 mm away | no new term | judgment | the CMP4 sweep (it measures the total pickup) |

### 1. Analog bundle over digital GND near the MCU (low × medium)

- **Mechanism.** On its horizontal run into U3 (y ≈ 113–114.5, x ≈ 104–113), the bundle was over the L2 AGND
  channel. As built, the closest copper is the **L4 GND pour** (`fig_bundle_mcu.png`). The regulator corner (U4,
  U14 and their inductors) is 3–6 mm away, and AGND joins GND only at NT3.
  - GND noise relative to AGND therefore couples into the traces.
  - The coupling is about C_GND/C_node at high frequency for VSNS, and ωC·Z_out for ISNS.
- **Numbers.**
  - Length over L4 GND, as built: +3V3A 6.8 mm, +VREF 7.9, ISNS 4.9–5.4, VSNS 4.8–7.2.
  - 2D cut at x = 108: each 0.1 mm trace has 74 fF/mm to GND as built. Intended, it had 76 fF/mm to AGND and
    8–9 fF/mm to GND from the side. Per net, that is about 0.05 → 0.4–0.6 pF to GND.
  - VSNS (13.4 pF node): about 3–4% of the GND–AGND noise above about 6 MHz.
  - ISNS (20–100 Ω): at most about 1% even at 30 MHz.
  - With a few mV of GND noise from the regulators (2.5 and 4 MHz) in that area, VSNS sees ≤0.1–0.2 mV and ISNS
    ≤0.03 mV.
  - The noise is asynchronous to the PWM, so it averages out instead of becoming a systematic error. VSNS is used
    only during coast.
  - L2 copper above (GND around the regulators, the AGND channel over the bundle) and L4/L5 GND below also shield
    the bundle from the regulators' own loops (on L1) and inductors (on L6).
- **Confidence.** The capacitance is computed. The GND noise level is judgment.
- **Check.**
  1. Bridge disabled (HI = LI = 0), regulators running.
  2. Log the ISNS/VSNS ADC samples at the normal trigger.
  3. If the rms is ≤1 LSB with no 2.5/4 MHz alias lines, close the item.

### 2. DAC crossings near U3 (none in flight; low in debug)

- **Mechanism.** DAC_1–3 on L4 run under VSNS/ISNS for 0.5–0.6 mm each, now 0.1 mm away instead of 1.05 mm.
- **Numbers.**
  - Plate capacitance (computed): PHB_VSNS–DAC_3 2.2 → 22.9 fF, PHA_VSNS–DAC_1 2.2 → 22.4 fF, PHB_ISNS–DAC_2
    2.1 → 21.7 fF. The other crossings are 5–12 fF.
  - With fringing, about 35–45 fF.
  - A 3 V DAC step would put about 8–10 mV on VSNS (τ ≈ 27 ns) and about 10 µV on ISNS.
  - The firmware (`control_ll.c`) has the per-loop DAC dumps commented out. `app_main.c` sets the DACs to 0, and
    only the open-loop test controller writes DAC1, so the DACs are static in flight.
- **Check.** Make sure the build used to characterize these boards does not stream to the DACs. If it must, update
  the DAC right after the ADC read in the ISR, as the commented code does.

### 3–4. VBUS and PGND facing GND (negligible)

See the previous section.

### 5. Kelvin SNS± pairs over the SW-node keep-outs (neutral to better)

- **Mechanism.**
  - L4 and L5 are cut out under the L6 /PHx_SW pours, as the LMG2100 datasheet asks.
  - Phase A's pair crosses the B and C keep-outs, and phase B's crosses C's (`fig_kelvin.png`).
  - As built, over the keep-out the pair sees the other phase's SW pour at 0.8 mm. Intended, it was 1.3 mm, with L2
    PGND 0.1 mm above.
  - Over solid L4, PGND is now 0.1 mm directly under the pair.
- **Numbers (computed).**
  - CM capacitance to the other phases' SW pours: 15 → 25 fF per trace (A↔B_SW), 12 → 20 (A↔C_SW), 14 → 22.5
    (B↔C_SW). SNS+ and SNS− match to <0.1 fF, and the pair is pinned by a 2 mΩ shunt.
  - DM mutual from a neighbouring SW pour, along the keep-out edges (2D cuts at y = 86.5 and 89.5): intended
    −0.12 to +0.24 pH/mm, **as built <0.001 pH/mm**, because L4 PGND under the pair shields it.
  - Phase C's pair beside its own SW pour: 0.59 → 0.64 pH/mm.
  - The crossings themselves are near-perpendicular, so the DM flux cancels.
- **Check.** None beyond the prior CMP4 sweep.

### 6. SW-node capacitance (negligible)

- /PHx_SW sees L3 PGND through the L4/L5 keep-outs: 0.6–0.7 → 1.0–1.15 pF per phase.
- /Phase x/SW sees the L3 VBUS band: 0.17–0.22 → 0.28–0.35 pF.
- That is +0.5 pF against C_OSS of 364 pF per FET (at 50 V; more at 8 V).

### 7. VBUS/PGND plate capacitance lost (negligible)

- 222 → 103 pF, mostly the band (L2-L3 and L4-L5 now 0.535 mm). At 330 MHz, |Z| goes from 2.2 to 4.7 Ω, against
  about 0.2 Ω for the hot-loop MLCC path.
- Note: the bus-ring PEEC is inductive only, so neither stack had this capacitance. That omission slightly
  overstates the intended stack's 330 MHz feed ring relative to as built. It changes nothing downstream, because
  the 69 ns aperture averages the ring.

### 8–18. Checked, does not matter

- **8. Gate drive, SPI, trace/debug, +3V3 on L4** (`refaudit.txt`). Every L4 digital net has exactly the same
  length over GND as built (L3) as intended (L5). For example, PHC_HI is 28.6 mm both ways and SPI_SCK 28.4 mm.
  - No HI/LI, SPI or TRACECLK copper faces any non-GND net above 2 fF.
  - Z0 of a 0.1 mm L4 trace: 50.9 → 49.8 Ω.
  - The gate loop itself is inside the LMG2100, and the VCC/boot caps are on L6 over L5 (unchanged).
  - The encoder SPI (SPI3 at prescaler 16, so SCK around 10 MHz; 30 mm on L4) faces only GND and has no overlap
    with any analog trace, so its timing relative to the ADC samples does not matter for this question.
- **9. Edge crosstalk inside the bundle.** Neighbour coupling is 32.5 fF/mm intended and 33.6 fF/mm as built, at both
  y = 105 (over the feed) and x = 108 (over GND). Wherever L4 is solid, the nearest plane is still 0.1 mm away. The
  bundle is over L4 voids for only 1–4 mm per net.
- **10. U4/U14.**
  - The hot loops are on L1 over L2 GND (0.092 → 0.1 mm).
  - The inductors are on L6 over L5 GND.
  - The SW and FB nodes face only GND, with the same capacitance in both stacks (U14-SW 0.59 pF, U4-SW 0.52 pF, FB
    0.16–0.31 pF).
  - The boards actually built have the pre-swap modules here, with the SW nodes inside the module. That corner was
    not analysed.
- **11. MCU power distribution.**
  - +3V3 on L4 has GND 0.1 mm away in both stacks.
  - The decoupling loops are through-board via pairs whose length doesn't change.
- **12. Thermal.**
  - Per LMG2100 (46 mm² including a 1 mm margin): 22–26 vias, of which 13–14 VBUS, 3–8 PGND and 2–3 GND.
  - Through-board conduction: vias 13.7–16.2 K/W intended, 13.2–15.6 as built. The dielectric alone is 100–105 K/W.
  - L6→L5 dielectric: 6.7 → 7.3 K/W, in parallel with the vias and the L6 copper. R_θJB is 6.2 K/W.
  - Heat from VBUS copper to PGND crosses 0.535 instead of 0.1 mm in the band, but it also leaves through the L1/L6
    VBUS pours, which are unchanged. The effect is ≪1 K at a few tenths of a watt per device.
- **13. MA732.**
  - The band's stray field at the die is 0.11 → 0.28 µT per amp of band current (the return planes are farther).
  - At 5 A that is about 1.4 µT, or about 0.002° against a roughly 50 mT magnet.
  - The phase-current fields on L6 dominate and are unchanged.
- **14. Plane-cavity modes.**
  - TM10 is at 2.5 GHz for the band (29 mm) and 1.5–2.1 GHz for board-size cavities. These frequencies depend on
    size and εr, not thickness.
  - Edge content stops at about 350 MHz.
- **15. Controlled impedance.** No net needs it. CAN and UART are on outer layers (unchanged). The L4 trace port is
  short and still about 50 Ω.
- **16. Ripple-current sharing.**
  - At 96 kHz, ωL of the bus paths is about 1 mΩ, against 1/ωC ≈ 24 mΩ for the bulk bank. The split is set by
    capacitance, so the bulk and MLCC ripple currents are unchanged.
  - The ×2 L only moves the 1.3 MHz mode (already covered).
- **17. +3V3A into the INA supplies.**
  - R31 and FB8 are 0 Ω, so the +3V3A trace's VBUS pickup (3.9 pF, prior study) reaches +3V3A_SWFILT.
  - 100 nF + 4.7 µF sit at each INA. That leaves ≤0.5 mV at 330 MHz on the supply, before PSRR, and less than 1 µV
    at the bus modes.
- **18. Right bulk-cap vias** (C97, C98, C100, C107) are 0.8–2.7 mm from the bundle (`fig_bulk_vias.png`). A
  vertical current beside a long straight trace/return loop links flux in opposite senses on its two sides. No term
  appears beyond the 2D feed M the prior study used.

## Refinements to the prior study (none changes its conclusions)

- **INA REF1 rides the same bundle (estimated).**
  - REF1 of U9, U11 and U13 comes from +VREF through R19, R30 and R41 (0 Ω), with 100 nF at each INA.
  - +VREF runs 43.5 mm in the bundle, alongside ISNS (M = 5.2 pH/mm as built, against 2.5–6.9 for ISNS).
  - The feed-current EMF in the +VREF/AGND loop therefore moves REF1 at the INA. The INA output shifts by half of
    that (V_out = G·V_sense + (REF1+REF2)/2), in the sense that **cancels part** of the ISNS-trace EMF.
  - The +VREF loop is about 15 nH against 3 × 100 nF. It resonates at about 2.4 MHz with Q ≈ 0.9, so REF1 follows the
    EMF (κ ≈ 1) up to about 2 MHz. κ is 0.24 at 5 MHz and 0.06 at 10 MHz.
  - Including the INA's roughly 1 MHz REF path, the EMF error is about **0.5–0.7× the RESULTS.md bound** for the
    µs-scale redistribution and the 1–2 MHz ring, and about 1× above 5 MHz.
  - The stackup ratio (×6–10) is unchanged.
- **Kelvin pairs** "over PGND in both stackups": as built, 4.9 of 25 mm of phase A's pair and about 3 of 17 mm of
  phase B's run over the L4/L5 keep-outs. Harmless; see item 5.
- **Bus-ring PEEC without GND.**
  - As built, L3 GND lies 0.1 mm over the feed for y ≈ 113–125, below the probes, as a floating eddy-current sheet.
    The only DC tie, NT1, is at the other end.
  - U4's input caps form a VBUS→GND→NT1→PGND decoupling path 3 mm from NT1.
  - Both effects slightly lower the feed L beyond the probes. Neither changes the probe-region results.
- **Gate drive "no change" and thermal/mechanical "wash"** are confirmed with numbers (items 8 and 12).

## Context: what an edge already does to ISNS (not a stackup effect)

- Each phase output has a 3.3 nF + 12 Ω snubber to PGND (C31/C32/C34 with R7–R9) after the ferrite. The
  shunt (R17, R28, R39) sits upstream of it, so every edge pushes about 3.3 nF × 8.4 V ≈ 28 nC through the shunt.
- Through the INA296A3 (×50, roughly 1 MHz, first-order assumption), that reads as roughly 0.2 A peak of real
  current that is not motor current, still roughly 10–15 mA at 0.5 µs.
- The as-built EMF pickup in the same windows is 3.5–11 mA (0.2–0.5 µs) and 1–4 mA (0.5–2 µs).
- So when an edge lands within about 0.5 µs of a sample, the reading is already disturbed in **both** stackups. The
  stackup adds a smaller, but systematic, layer on top.
- Judgment: the INA's real step response is not first-order. The prior's CMP4 sweep would show both effects.

## Unknowns that could move these numbers

- **The real fab stackup** (εr, dielectric thicknesses), from the stackup report or a microsection. All ratios
  assume the KiCad default with εr 4.5.
- **Inner copper weight.** KiCad's default is 35 µm. If the fab used 18 µm inner layers, the band's DC resistance
  doubles, which is still only mW.
- **Which commit was built.** The regulator corner differs before the swap (modules). Nothing else here depends on
  it: the J1 and NT1 overlaps, the bundle and the Kelvin routing are identical from RC2 on (HANDOFF.md).

## Method and files

All scripts read the pickles in `../bus-ring/` (`pcb.pkl`, `geom.pkl`) and write only into this folder. Run them with
the pcb-inductance venv python.

| file | what |
|---|---|
| `raster.py` | rasterizes every copper layer to a net-id grid at 25 µm: pours, tracks, pads, via rings. Writes `raster.npz` (gitignored) |
| `overlap.py` → `overlap_table.txt`, `overlap_pairs.json` | column model: at each pixel, consecutive copper across voids gives a plate capacitor; C for both stacks per net pair and layer pair, no fringing |
| `query.py` | filters `overlap_pairs.json`, e.g. `query.py --sig 2` or `query.py "PGND" 5` |
| `refaudit.py` → `refaudit.txt` | what every L3/L4 signal faces at 0.1 mm, intended vs as built (raster version of the prior `under.py`) |
| `kelvin2d.py` → `kelvin2d_y*.json` | 2D quasi-static cut (prior `fd2d.py`): Kelvin DM/CM coupling to the SW pours |
| `bundle2d.py` → `bundle2d_*.json` | 2D cut: per-mm capacitance of each analog trace to everything, both stacks |
| `misc.py` | thermal vias, L4 Z0, MA732 stray field, cavity modes, plate-C impedance |
| `fig_gnd_overlap.png` (`.py`) | where PGND/GND and VBUS/GND face each other, both stacks |
| `fig_bundle_mcu.png` (`.py`) | bundle near U3 over L2 (intended) vs L4 (as built), with the regulator parts |
| `fig_kelvin.png` (`.py`) | Kelvin pairs over the L4/L5 keep-outs and the L6 SW pours |
| `fig_bulk_vias.png` (`.py`) | right-edge bundle against the bulk-cap pads and vias |
| `survey.py`, `parts.py` | net/layer inventory, part positions |

Limits:

- The plate model has no fringing. It underestimates trace coupling by about 1.5–2×, and the 2D cuts cover that
  where it matters.
- 2D cuts assume infinite parallel runs and perfect conductors (the TEM limit).
- Noise levels on GND are judgment, not simulation.
