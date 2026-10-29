# Phase 1B: late road-surface Y-sprite source — 2026-10-29

## Question and frozen samples

**Hypothesis:** one reachable page-`$E` Y-sprite descriptor contributes visible road-surface pixels on pulse-56 composed screen 992. **Baseline:** the [render-timing result](2026-10-29-late-road-render-timing.md) fixed callback 991 → MAME native frame 990 → Lua screenshot 992. Before narrowing, the unmodified and broad-hide images were used to select three gray, road-like baseline pixels at `(220,180)`, `(240,180)`, and `(260,180)`. Their baseline RGB values were `(164,164,164)`, `(164,164,164)`, and `(140,140,132)`. **Acceptance:** a single word-0 `$1000` hide must change all three fixed pixels and the native Y bitmap, preserve earlier screens, and repeat in fresh MAME processes. The visual label “road surface” is an image-based interpretation; the causal descriptor attribution is the measured result.

## Result

**Verified by execution — PASS for this screen and schedule:** bounded half-range hides narrowed the common source of all three fixed pixels through `$E000–$E7FF`, `$E400–$E5FF`, `$E500–$E5FF`, `$E580–$E5FF`, `$E5C0–$E5FF`, `$E5C0–$E5DF`, and finally descriptor **`$E5D0`**. Each complementary range left the three pixels unchanged, though several complements changed other pixels. At callback 991, the exact `$E5D0` intervention changed only one byte in 64 KiB source RAM, adding word-0 hide bit `$1000`. Its baseline graphic word was `$3888`, the road-like word seen in earlier independently attributed strips; this supports, but does not alone prove, a continuous game-object identity.

**Verified by execution:** the exact-slot hide changed **4,073 of 262,144 native 16-bit bitmap words** at MAME frame 990 and **3,327 of 71,680 composed RGB pixels** on Lua screenshot 992. The changed screen area was bounded by X=182–319, Y=158–205. The fixed samples changed to `(132,132,123)`, `(132,132,123)`, and `(156,156,156)`. All other composed screens 960–1000 and native frames 988–995 were identical to the same-schedule instrumented baseline. These effects came from the one-byte descriptor hide; no projection, camera, or bitmap data was edited.

| Tested descriptor range | Fixed samples changed? | Screen-992 pixels changed | Native-frame-990 words changed |
|---|---|---:|---:|
| `$E800–$EFFF` | 0/3 | 0 | 0 |
| `$E000–$E3FF` | 0/3 | 6,182 | 6,961 |
| `$E600–$E7FF` | 0/3 | 15,753 | 23,560 |
| `$E400–$E4FF` | 0/3 | 3,495 | 4,351 |
| `$E500–$E57F` | 0/3 | 1,363 | 5,078 |
| `$E580–$E5BF` | 0/3 | 309 | 309 |
| `$E5E0–$E5FF` | 0/3 | 2,914 | 10,522 |
| `$E5C0` | 0/3 | 10,570 | 18,535 |
| **`$E5D0`** | **3/3** | **3,327** | **4,073** |

**Verified by execution:** two further exact-slot trials used fresh MAME processes and separate private directories. All three runs had the same sample vector, affected-pixel/word counts, post-write RAM, native bitmap, and screen-992 checksums. This is repeated source attribution, not independent prediction of the road shape.

**Limitation:** the pulse-204 callback-991 source image has a different graphic word at the same `$E5D0` slot (`$28B9`), observed by source inspection only. The exact-slot intervention was **not run** for that schedule. The address must not be treated as a stable cross-schedule road identity. The previously predicted natural phase still has no validated numerical mapping to this screen's road contour; steering also changes other scene state. The five-word Sega CD camera interface remains unchanged.

## Reproduction and evidence

**Verified by execution:** source revision `e241dd3` on `experiment/perspective-road`; macOS 26.6.2 / Darwin 25.6.0 x86_64; Python 3.14.8; isolated MAME 0.289 source revision `f34f02505e32c1993c6a782b6814232cbfc74e36`, instrumented executable SHA-256 `8e4966a8a42e70cba398a8ec62bf3550bef84938bc17946579a69caac11876ba`. The [capture patch](../../tools/phase1b_mame_render989.patch) is described in the timing report. The owner-private 53-file ROM manifest SHA-256 is `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`; callback-950 state SHA-256 is `700b12cf2a60cdb44448877a07ae24395dc77a35b89d69fb2df6a60d27422b6a`. The [bounded runner and scorer](../../tools/phase1b_late_road_narrow.py) SHA-256 is `3f5f33d2485768087056f40774f6a3cde6a6170a362e18e7c9a84f24fffde91d`.

The runner generates a private 64 KiB source copy from `build/private/phase1b-render989-baseline/source-0991-ysprites.bin`, sets only hide bit `$1000` at 16-byte boundaries in the requested range, and launches the isolated MAME executable from a fresh ignored directory. It sets pulse 56, the same callback-950 state, `PDRIFT_SOURCE_OVERRIDE_FRAME=991`, `PDRIFT_SOURCE_OVERRIDE_RANGE=<range>`, `PDRIFT_YBITMAP_DIR=.`, `PDRIFT_SWAP_DIR=.`, `PDRIFT_CAPTURE_PROFILE=road-edge`, and the tracked `tools/phase1b_mame_input.lua`; the full command, other environment values, and launch options are in the runner. Run each range with `python3 tools/phase1b_late_road_narrow.py run E5D0 0010`, then score with `python3 tools/phase1b_late_road_narrow.py score E5D0 0010`. Add `--repeat 1` and `--repeat 2` for fresh exact-slot replays. All 18 narrowing/repeat trial directories, their raw logs, native bitmaps, source dumps, screenshots and JSON scores are private under ignored `build/private/phase1b-render989-narrow-*`.

The final exact-slot override SHA-256 is `34f9ee278eeed22db22d6b5eee7976f198a800d9204db686cbaf81b26c3a98c1`; native frame-990 SHA-256 is `b86093eebd604e75227bf197e53eda1b184f85c2babed883ba019fd07b0fdd07`; composed screen-992 SHA-256 is `215cf6b6bad6ec6cc0aba4df7a7d87fee396c1c079543cc40e786b4d28864586`. The first private score JSON SHA-256 is `ff2a7a573c7dd30ea6998ce5796cc577e6e7511aa14005f561060546edea25a9`. Commercial ROMs, source RAM, bitmaps, screenshots and saved states remain untracked.

**Next hypothesis:** identify a road-surface contour on both natural schedules using each schedule's own renderer-time descriptor source, then freeze comparable screen-space samples before testing whether the already predicted phase explains any part of their displacement. A single shared slot address is not sufficient because the slots' graphic words differ. MAME is the sole execution instrument here; another arcade emulator, BlastEm and physical hardware were **NOT RUN**. No host wall-clock result is treated as arcade hardware timing.
