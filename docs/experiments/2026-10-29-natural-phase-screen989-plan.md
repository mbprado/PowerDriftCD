# Frozen natural-phase road observation plan — 2026-10-29

**Hypothesis:** a naturally varying, independently predicted `$0CEA00` phase can be aligned with a later visible road edge. This is a timing/observability test; no numerical phase-to-pixel transfer function has been established.

**Verified by execution before target images:** using only callback-950 input traces, pulse 220 matched the existing pulse-204 phase sequence through marker 999. Pulse 56 first differs at marker 983 (`$01A6` versus `$01A5`, a one-unit decrease), then differs by one or two phase units at later markers. The pulse-56 20-update predictions are frozen in ignored `build/private/phase1b-natural-phase56-frozen.json`, SHA-256 `8a03f91de7de3c9d0fe6649d5a19e0e6ffb18270847a172805c7c4ad03ff2c20`. The input-only `debug.log` SHA-256 is `70893e32bf54adecdef9908e4a289931c422b284a5ee8b67b4f5601fc1d706ff`. No pulse-56 target-output or screenshot run has been made at this point.

## Fixed check

- **Source prediction:** validate all 20 frozen source/sum/increment/phase/offset rows against a separate pulse-56 output-only MAME run. Exact field equality is required.
- **Timing hypothesis:** use the previously observed callback-961 intervention → first road-edge screen-967 relation as a six-label lead. The first pulse-56 phase divergence at marker 983 therefore nominates composed **screen 989**, with screen 990 as a secondary adjacent-page check. This lead may fail at the later track position.
- **Screen-space rule:** run unmodified pulse-204 and pulse-56 captures from the same callback-950 state through screen 1000. Use the existing `phase1b_mild_steer_width.scan` detector on fixed arcade Y=153–163 inclusive. Record both left and right bounds where available; evaluate the left edge first. Missing detector rows are `INCONCLUSIVE`, not zero-width road.
- **Coordinate calibration:** use the previously tracked [road calibration](data/phase1b-road-calibration.json), SHA-256 `e41b944cab9a2940ec65a0f660e1bcd4db78fa8303ab02b5e67c4d630f79da23`, with its 320×224 arcade screen, Y crop 134–190, and 128×64 output mapping. Do not fit or change calibration after viewing the target images.
- **Provenance:** compare exact screen PNG hashes, captured Y-sprite descriptors and geometry records. A natural pulse difference is not a phase-only intervention; any edge difference needs its own source attribution before being assigned to the predicted phase. No exact pixel position or Sega CD five-word packet is claimed in advance.

**Decision rule:** exact scalar prediction may pass independently of the visual check. A matching screen-edge direction is exploratory. Without an independently fixed phase-to-pixel rule and source attribution, the arcade-to-Sega CD camera handoff remains `INCONCLUSIVE` even if the images differ. A null edge difference at a one-unit phase change does not refute the large controlled lookup intervention.
