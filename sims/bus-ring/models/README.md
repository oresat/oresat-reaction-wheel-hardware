# LMG2100R044 SPICE model (unofficial)

TI doesn't publish a model for this part. This one is built from two
EPC2090 FETs, an LMG1205-style driver, and estimated package parasitics,
then calibrated against the LMG2100R044 datasheet (SNOSDF9B).

![validation](validation.png)

## Files

| File | What it is |
|---|---|
| `lmg2100r044.lib` | The model. PSpice syntax; runs in Xyce and ngspice as-is. |
| `lmg2100r044_ltspice.lib` | Same model for LTspice (see note below). Generated, don't edit. |
| `make_ltspice_lib.py` | Regenerates the LTspice copy after you edit the main file. |
| `examples/dpt_hs_{xyce,ngspice,ltspice}.cir` | Double-pulse test, HS hard switching (buck direction), 48 V, ~15 A |
| `examples/dpt_ls_{xyce,ngspice,ltspice}.cir` | Double-pulse test, LS hard switching (boost direction) |
| `examples/buck_{xyce,ngspice}.cir` | 48 V → 12 V, 8 A, 1 MHz buck (TI Table 8-1), reports device dissipation |

```
X1 VIN SW PGND HB HS HI LI VCC AGND LMG2100R044 PARAMS: TJ=25
```

NC pins are left out, and PGND covers pins 6 and 17.

## What's inside

```
VIN -L-R- [HS EPC2090] -LCS- swk -L-R- swb -L-R- SW
                              |          |
                         LGK (Kelvin)   L-R- [LS EPC2090] -LCS- pgk -L-R- PGND
                              |                                   |
 HB -L- hbd [HS driver] hsd --+-L- HS          LGK (Kelvin) ------+
                                                                  |
 VCC -L- vccd [LS driver] vss ------------------------------------+-L- AGND
```

- **FETs.** EPC's EPC2090 model with its equations and parameters unchanged. It was
  rewritten to run outside PSpice: EPC's `G … Q={}` charge sources became an
  E/C/R/F loop, `Temp` became the `TJ` parameter, `if()` became `max()`/`min()`, and
  `log()` became `2.302585093*log10()` (see the Xyce note below). The rewrite
  matches EPC's C–V curves exactly.
- **Driver.** Behavioural:
  - TTL Schmitt inputs referenced to AGND, 200 kΩ pulldowns
  - VCC and HB UVLO with hysteresis and a 100 ns deglitch
  - 8-stage RC delay line plus an asymmetric pulse filter
  - level-1 MOSFET output stages (1.2 A / 2.1 Ω pull-up, 5 A / 0.6 Ω pull-down, from the LMG1205)
  - bootstrap diode with a 5 V clamp that opens a series switch about 270 ns
    after HB-HS goes over 5 V (that's how the LMG1205 datasheet describes its clamp)
  - 400 pF of on-die rail bypass on each driver supply
- **Package.** Everything below is an estimate; TI doesn't publish these values.

## Package / driver parameters (all overridable via `PARAMS:`)

| Param | Default | Basis |
|---|---|---|
| `LVIN`, `LSWH`, `LSWL`, `LPGND`, 2×`LCS` | 50, 40, 40, 50, 10+10 pH | Internal power loop ≈ **0.2 nH**. In the flip-chip routable leadframe the SW route runs about 2 mm over the PGND pad, roughly 0.1 mm apart and 2.3 mm wide. μ0·h·l/w gives ~0.13 nH, plus bumps and vias. Cross-check: TI's EVM rings at 285–380 MHz against ~0.4 nF of Coss, which implies 0.45–0.8 nH total including the board. |
| `LSWP` | 50 pH | The SW pad sits under the LS drain. It's in series with your inductor, so it barely matters. |
| `RVIN`…`RPGND`, `RSWP` | 0.6 / 0.5 mΩ per path | Datasheet Rds(on) at the pins (4.4 / 4.3 mΩ) minus EPC2090 die (3.8 mΩ). Copper tempco is applied with `TJ`. |
| `LCS` | 10 pH | Common-source inductance. Both drivers have Kelvin returns, so only the die and bumps are shared. |
| `LG`, `LGK` | 0.4 nH, 0.2 nH | Driver→gate trace and Kelvin return. Weak sensitivity: cutting both 4× raised turn-on slew 3% at RBST = 2.7 Ω (14% at 0 Ω) and moved the peak by <1 V. |
| `LHBP`, `LHSP`, `LVCCP`, `LAGNDP` | 0.3 nH each | QFN pin plus internal route to the driver die. |
| `CHBI`, `CVCCI` | 400 pF | On-die rail bypass, **calibrated to Fig 5-7**. At 1 nF, RBST stops mattering; at 200 pF, RBST matters too much. |
| `COUT` | 50 pF | Driver output capacitance. Without it, the gate trace rings at GHz. |
| `CWELL` | 30 pF | Datasheet value (HS well to PGND). |
| `IPU/RPU`, `IPD/RPD` | 1.2 A / 2.1 Ω, 5 A / 0.6 Ω | LMG1205 output stage. |
| `TCLAMP`, `TUVLO` | 270 ns, 100 ns | Clamp delay is from the LMG1205 datasheet; the UVLO deglitch is assumed. |
| `TDH`, `TDL`, `TPWR`, `TPWF` | 22.5, 22.5, 9, 4.7 ns | Calibrated for 35 / 33 ns delays. Set `TDH ≠ TDL` to model tMON/tMOFF mismatch. |
| `TJ` | 25 °C | Static junction temperature for both FETs and the package copper. |

## How it compares to the datasheet

| Quantity | Model | Datasheet |
|---|---|---|
| Rds(on) HS / LS at 16 A, 25 °C | 4.39 / 4.29 mΩ | 4.4 / 4.3 typ |
| Rds(on) at 125 / 150 °C (normalized) | 1.54× / 1.77× | ~1.57× / 1.8× (Fig 5-6) |
| Ciss / Coss / Crss at 50 V | 1019 / 354 / 2.9 pF | 1046 / 364 / 2.9 typ |
| Qoss, HS + LS + well, 0→50 V | 56 nC | 55 typ |
| Prop delay on / off (HI or LI → SW 10%) | 35.0 / 32.9 ns | 35 / 33 typ |
| Min input pulse | 12 ns swallowed, 15 ns passes | tPW 10 ns typ |
| HS turn-on slew vs RBST (0 / 1.2 / 1.8 / 2.7 / 4.7 / 10 Ω), boot cap | 25.8 / 16.4 / 14.2 / 12.4 / 10.5 / 6.0 V/ns | – / 18.8 / 17.3 / 14.8 / 10.6 / 5.4 (Fig 5-7) |
| HS turn-on, RBST 2.7 Ω, HB-HS held at 5 V externally | 15.2 V/ns | 14.74 (Fig 8-5) |
| HS turn-on peak, RBST 2.7 Ω | 51.1 V | ~51.5 V (Fig 8-3) |
| HS turn-off at 18 A | 21 V/ns, −4.0 V undershoot | 25.5 V/ns, ~−5 V (Fig 8-4, current not stated) |
| LS turn-on, RVCC 2.7 Ω, 15 A | 14.7 V/ns | 18.1 (Fig 8-6, current not stated) |
| HB-HS in a running buck | 4.93–5.09 V | clamp 4.65–5.2 |
| 3rd-quadrant drop at 0.5 A | 1.9 V | 1.5 typ (this one comes from EPC's model) |
| Dissipation, 48→12 V, 8 A, 1 MHz | 2.2 W | ~3 W from TI's eq. 5 (which TI calls conservative) |

Xyce, ngspice and LTspice agree within about 0.5% on the example benches (HS turn-on
12.35 / 12.42 / 12.37 V/ns, peak 51.1 / 51.2 / 51.1 V). In Xyce I re-ran the
Rds(on), third-quadrant drop, capacitances, delays, minimum pulse, both double-pulse
tests and the buck; they match ngspice to the precision shown.

## Things to know before you use it

- **Ringing damping is your board's job.** The package model only has DC copper
  resistance. On its own, the loop rings for 30+ cycles, whereas TI's scope shots
  decay in about 3. The examples put a 3 Ω resistor across the 0.3 nH PCB loop
  inductor (`RPCB`), a crude skin-effect loss tuned to match Fig 8-3. Swap in your
  own layout numbers, and remove `RPCB` to see the worst case.
- **Xyce: `log()` is base 10.** PSpice, LTspice and ngspice all use natural log, and
  vendor GaN models lean on `log(1+exp(…))` everywhere. This library avoids `log()`
  (it uses `2.302585093*log10()`), so it's correct either way. **Unmodified EPC
  models, including the EPC2016C inside TI's `lmg5200.lib`, are wrong in plain
  Xyce.** EPC2016C Rds(on) comes out at 17.8 mΩ instead of 12.6 mΩ, and its
  capacitances are off too. Run those with `Xyce -hspice-ext math …`, which makes
  `log()` natural and doesn't change this model's results. The Xyce examples use
  default settings (no options needed), and the operating point converges directly.
- **LTspice: use `lmg2100r044_ltspice.lib`.** LTspice silently adds 1 mΩ in series
  with every inductor, plus extra damping. With ~4 package inductors per path, that
  adds ~4 mΩ to Rds(on) (8.2 mΩ instead of 4.4). Also give your own bench inductors
  `Rser=0`.
- **ngspice:** the examples set `option method=gear`. Trapezoidal passed everything
  I threw at it in the end, but gear is the more forgiving choice. The operating
  point always goes through gmin stepping (that's the EPC FET model); this is
  automatic and fast.
- **PSpice:** the syntax is kept PSpice-compatible. I couldn't run PSpice here, so
  this path is untested.
- **Don't drive SW with an ideal current source at t=0.** With everything off, no
  simulator's DC solve can reach the OP. Xyce fails outright (gmin and source
  stepping don't help). ngspice silently falls back to a transient-op that leaves
  large caps half-charged; on my test bench that gave a 42 V peak instead of 51 V.
  LTspice's pseudo-transient picks an arbitrary bootstrap state. Drop-in fix: replace
  `I1 sw 0 15` with a big inductor that a current source pre-charges and then hands
  off:
  ```
  LBIG sw 0 100u
  IPRE 0 sw PWL(0 15 2n 15 3n 0)
  ```
  At DC the inductor is a short carrying 15 A, so the OP is trivial. That bench then
  matches across Xyce and ngspice (12.43 V/ns, 51.04 V). The buck example uses the
  same trick.
- **The bootstrap starts empty if SW starts high.** Precharge it, e.g.
  `.ic v(hb)=<V_SW+4.6>`. With RVCC in place, charging an empty CBST through the VCC
  pin drags VCC into UVLO, which is real behaviour.
- **HS and AGND are internally tied to SW and the LS source (Kelvin).** Don't short
  HS to SW externally unless your board does: it puts the Kelvin path in parallel
  with the power path, and the gate drive gets hammered. The same goes for tying
  AGND straight to PGND, which TI also warns against.

## Known limitations

- The package parasitics are educated guesses; treat the power-loop L as ±50%.
  The on-die bypass and gate-loop values were tuned to TI's slew-rate curve, not
  measured.
- The driver is the LMG1205 transplanted. The real LMG2100 driver may differ, and
  the 270 ns clamp delay in particular comes from the LMG1205 datasheet.
- At RBST ≈ 0 the model may be too aggressive: 25.8 V/ns and a ~61 V peak at 48 V,
  with or without the damped board. TI doesn't publish that corner; part of it is
  the internal HB rail ringing, which depends on the guessed `CHBI` / `LHBP` / `LHSP`.
- Not modelled: Coss hysteresis loss, level-shifter dv/dt immunity, and thermal
  dynamics (`TJ` is static).
