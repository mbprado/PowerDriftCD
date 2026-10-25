# Phase 1B: frozen forward-only screen-977 road test plan — 2026-10-25

**Hypothesis:** carrying forward the most recent earlier packet, selected by nearest previously captured `road_depth`, predicts the next composed road-region span within mean absolute edge and width errors of 2 output pixels each. **Baseline:** the [nearest-depth diagnostic](2026-10-25-nearest-depth-camera-packet.md) had one exploratory offline success and four leave-one-out failures. This plan is frozen **before** capturing or inspecting screen 977.

## Frozen inputs and decision

- Target: pulse-112 composed arcade screen **977**, from the owner-local callback-950 state. Intervene on source Y-sprite RAM at callback **976**. Keep earlier screens 960–976 pixel-identical to the unmodified baseline.
- Candidate packet: **`[38,0,0,4,31]`**, the existing screen-975 original-art inverse-fit packet. It is the latest packet among the already measured screens 969/971/973/975; the captured `road_depth` sequence is monotonic through 975. Use it without looking at screen-977 edges or trying another packet. If a later `road_depth` value is absent or reverses the ordering, report the state-cue condition as failed rather than choosing by target geometry.
- Original host art: widths **52/54/58** centered at source X=139; no local width bump. Five-word interface and `wide_geometry_lines` unchanged.
- Calibration: tracked `docs/experiments/data/phase1b-road-calibration.json`, arcade Y crop 134–190 into output rows 0–63, horizontal output sample `(10x+3)/4`. This is an explicit comparison convention, not a recovered arcade camera transform.
- Eligible arcade rows: screen Y **153–163**, with detected left and right sand boundaries that **both change** under a source hide at callback 976. Evaluate **every** eligible row; no row is chosen after seeing its error. At least **three** eligible rows are needed for a decision. If fewer exist or no causal source is isolated, mark `INCONCLUSIVE` and keep any noncausal comparison separate.
- `PASS` for this bounded host geometry test requires both mean absolute edge error ≤**2** and mean absolute inclusive-width error ≤**2** output pixels over all eligible rows. `FAIL` means an eligible causal span exists and either limit is exceeded. These are retrospective host geometry thresholds, not arcade-fidelity or hardware acceptance.

## Capture and attribution method

**Planned / hypothesis:** run a new isolated MAME 0.289 baseline through screen 977, with the existing fixed pedal and pulse-112 steering schedule. Compare screens 960–976 to the saved baseline pixel-for-pixel. Inspect the callback-976 Y-sprite linked-list page; use a broad page hide, then narrow only enough to establish that both measured edges are caused by the hidden source. Verify the post-write source RAM and all earlier screens. Re-run the accepted intervention independently if practical. Keep state, ROMs, screenshots, source RAM, logs and derived proprietary pixels under ignored `build/private`.

**Restrictions:** no Sega CD renderer or art change, no use of screen-977 edges to choose the packet, no physical hardware, no push. The result will state exactly which MAME and host software ran. A failure of this simple forward rule will not by itself prove the five-word interface insufficient.
