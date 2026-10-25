# Phase 1B: Y-sprite source-to-screen lag probe — 2026-10-25

**Hypothesis:** the partial callback-979 `$C` hide on screen 980 may affect a later composed screen because the arcade Y-sprite source and rotation buffer are latched at different times. **Baseline:** the [forward causal-gate report](2026-10-25-forward-road-causal-gate.md) found a left-edge response on three screen-980 rows, a right-edge response on one, and no two-sided causal screen-981 rows from a callback-980 `$C` hide. The exact latch point is unsupported.

## Frozen test

- Use the same owner-local callback-950 state, pulse-112 input, MAME 0.289, and isolated screen-960–990 baseline. No new input schedule or renderer change.
- Replay the **same broad `$C000`–`$C7FF` descriptor hide** at callback **979** and, independently, at callback **980**. Capture composed screens through **982**. Recheck the previously observed screen-980 response as a control.
- For screens **980, 981 and 982**, count baseline sand-boundary rows in Y=153–163 and whether each boundary pixel changes under each hide. Record both sides separately and report every screen, including no-effect outcomes. Keep the same detector; do not select rows from the hidden image or change the road-color definition.
- Require post-write source RAM to match each prepared override, only descriptor hide bytes to change at the callback, and all screens before the callback to remain pixel-identical. Compare the existing screen-980 image hash when replaying callback 979.
- This test maps a source intervention to composed-screen effects. It does **not** score a Sega CD camera packet. A later score requires at least three two-sided causal rows and a separately stated packet rule.

All captures, ROMs, state, screenshots and derived proprietary pixels stay ignored under `build/private`. No physical hardware, second emulator or push is planned. If the two hides do not explain the right edge, document the precise gap and investigate the rotation-buffer or foreground composition path next.
