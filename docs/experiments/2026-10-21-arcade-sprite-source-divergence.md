# Phase 1B: source-sprite divergence behind affine mismatch — 2026-10-21

**Question / hypothesis:** does steering change the image fed into the Y-Board rotation stage, explaining why the captured affine transform alone stops aligning the composed screenshots after callback 965? **Baseline:** [affine road-correspondence test](2026-10-20-arcade-affine-road-correspondence.md). **Acceptance:** compare the mapped Y-sprite, B-sprite and palette RAM at adjacent callbacks; repeat the observations; then change only Y-sprite RAM in a private counterfactual replay while holding steering and rotation parameters fixed. **Result — PASS, verified by execution in MAME:** Y-sprite RAM begins differing at callback 964 and diverges further at 966. Replacing the steered Y-sprite RAM with the centered snapshot after callback 966 restores callback-967 affine pixel agreement from 60.44% to 96.63% (left) and from 57.04% to 94.86% (right). A same-state writeback control changes nothing. This establishes Y-sprite RAM differences as a cause of much of the *emulated* composed-image mismatch at that frame; individual sprite records and arcade camera meanings remain **unsupported**.

## Environment and method

**Verified by execution:** starting Git commit `25e78ef` on `experiment/perspective-road`; final `tools/phase1b_mame_input.lua` SHA-256 `19b725021cbea4d0de446be9f2b37f0a2e7c22202bf9cf91ff0ea35d19079cec`; source comparison tool SHA-256 `3d1a2742c8b86b17ec79a7dec584dec211e1e7ee3421caf66d240e5eb72975cc`. Affine comparison tool from the previous experiment had SHA-256 `04a27f24fad70cec3668630edbdbfc53b9eb5324b3f8252a172b877e4ca3fd29`. Host: macOS 26.6.2 x86_64. Emulator: MAME 0.289 (revision string `unknown`), executable SHA-256 `16f53f49def05df5d3377274ac3e78eea28249c52ae7a1fe80d2b367a78d18b4`; owner-local, ignored 53-file ROM manifest SHA-256 `b8894130f0d4081fb193fe675acd45f7ded2e0f3572a0d23560e9ebb969c6f2f`. No compiler, Sega CD disc image, second emulator or physical hardware was used. Host execution time is not an arcade timing measurement.

**Documented only:** [MAME 0.289's Y-Board render path](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaybd.cpp) draws a 512×512 Y-sprite bitmap, sends it through `rotate_draw()`, then composites the B-sprite layer. Its address maps expose Y-sprite RAM to sub-CPU X at `$180000–$18FFFF`, B-sprite RAM to sub-CPU Y at `$188000–$188FFF`, and palette RAM at `$190000–$193FFF`. The captured RAM is the *input state* for that render path, not a direct dump of the finished 512×512 bitmap. MAME's [rotation routine](https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/sega/segaic16.cpp) defines the affine relationship used in the earlier pixel comparison.

**Verified by execution:** `PDRIFT_SOURCE_DIR` adds read-only snapshots at callbacks 960–970 of 65,536 Y-sprite RAM bytes, 4,096 B-sprite RAM bytes and 16,384 palette RAM bytes. The centered steering value remained 128; left/right pulses used 64/192 from callback 960 under the established coin/start/pedal schedule. The runs also retained the previous pre/post rotation-block, screenshot and early RAM captures. Two centered and two left runs matched byte-for-byte across all 33 new RAM files and prior captures; a right run matched its prior uninstrumented screenshots, rotation blocks and early RAM. Three final centered/left/right normal runs using the **final** Lua source reproduced all of those captures exactly. The added memory reads did not change the checked replay outputs.

Run each normal condition from a fresh ignored working directory, omitting `PDRIFT_STEER_PULSE` for center or using `64`/`192` for left/right:

```sh
PDRIFT_RAM_DIR=. PDRIFT_ROTATE_DIR=. PDRIFT_SWAP_DIR=. PDRIFT_SOURCE_DIR=. PDRIFT_SNAPSHOT_DIR=. PDRIFT_RAM_PROFILE=early PDRIFT_STEER_PULSE=64 /usr/local/Cellar/mame/0.289/bin/mame pdrift -rompath /Users/murilo/repos/PowerDriftCD/build/private/phase1b-roms -noreadconfig -video none -sound none -nothrottle -seconds_to_run 18 -autoboot_script /Users/murilo/repos/PowerDriftCD/tools/phase1b_mame_input.lua > phase1b-input.log 2>&1
```

For the **counterfactual only**, set `PDRIFT_SOURCE_OVERRIDE` to the absolute path of the private centered `source-0966-ysprites.bin` file and keep the steered input. The tool snapshots the normal RAM first, then writes exactly 65,536 bytes to sub-CPU X's mapped Y-sprite RAM after callback 966. For the sham control, point the variable to the same left run's own callback-966 file. No override bytes are embedded in tracked source. Private directories are `build/private/phase1b-source-{center1,center2,left1,left2,right1,final-center,final-left,final-right,sham-left,replace-left,replace-left2,replace-right}/`. All raw RAM, screenshots, logs and CSVs remain ignored.

Reproduce the numerical comparisons from the repository root:

```sh
python3 tools/phase1b_source_compare.py build/private/phase1b-source-final-center build/private/phase1b-source-final-left build/private/phase1b-source-final-right --center-repeat build/private/phase1b-source-center1 --left-repeat build/private/phase1b-source-left1 --sham-left build/private/phase1b-source-sham-left --replace-left build/private/phase1b-source-replace-left --replace-right build/private/phase1b-source-replace-right > build/private/phase1b-affine-verify/source-final.csv
python3 tools/phase1b_affine_verify.py build/private/phase1b-source-final-center build/private/phase1b-source-final-left build/private/phase1b-source-final-right > build/private/phase1b-affine-verify/affine-final.csv
```

The private source-difference CSV SHA-256 was `ea2498262bf195f87413e25982d4d0e22f1d16c69261550577279561a6b9e959`, and the unchanged affine baseline CSV SHA-256 was `b77c1ce08ed9bf076149123d30dfa497571e2b498d1be8979bed5ae642b10cf3`. The final normal-run `phase1b-input.log` SHA-256 values were center `61c930894bb0750359202da3d491305f18f553f296aaeb6a3e95eac2cf9603fd`, left `7bd0abd296e145a4a23df8260a51b7d5d1b06177e17ef4ef00a8999c045623c3`, right `0a760a9829fd210fba00ee44126a982750b4562ad54120bb992091860c61a6bc`.

## Observations and intervention

**Verified by execution:** changed-byte counts below compare each 65,536-byte Y-sprite RAM snapshot against centered at the *same callback*. B-sprite and palette counts use their mapped 4,096- and 16,384-byte areas. These are data-byte counts, not pixel or timing measures.

| Callback | Y-sprite left / right | B-sprite left / right | Palette left / right |
| ---: | ---: | ---: | ---: |
| 960–963 | `0 / 0` | `0 / 0` | `0 / 0` |
| 964–965 | `139 / 129` | `0 / 0` | `0 / 0` |
| 966–967 | `537 / 329` | `0 / 0` | `0 / 0` |
| 968 | `699 / 588` | `0 / 0` | `0 / 0` |
| 969 | `699 / 588` | `0 / 3` | `0 / 0` |
| 970 | `619 / 1154` | `0 / 3` | `0 / 0` |

**Verified by execution:** callback-966 Y-sprite RAM is captured after screenshot 966 and before the next frame's render. A same-state left writeback yielded byte-identical screenshots at callbacks 960–970 and the same affine CSV as the normal left run. In the centered-snapshot interventions, the post-write Y-sprite RAM matched the centered snapshot byte-for-byte. The pre-swap affine parameter block after callback 966 and screenshots 965–966 stayed identical to each corresponding normal steered run. Screenshot 967 changed, while screenshot 969 matched the normal steered run again after the game refreshed the sprite RAM. The repeated left intervention matched byte-for-byte across its private captures and screenshots.

| Callback 967 condition | Left predicted exact RGB | Right predicted exact RGB | Left / right RGB mean absolute error |
| --- | ---: | ---: | ---: |
| Normal, or left sham writeback | 60.44% | 57.04% | `26.31 / 28.45` |
| Centered Y-sprite RAM substituted into left | **96.63%** | — | `4.47 / —` |
| Centered Y-sprite RAM substituted into right | — | **94.86%** | `— / 6.62` |

These percentages use the same affine-predicted road-containing rectangle and valid-pixel denominators as the prior report: 28,560 pixels for left and 28,031 for right. The two substitution CSVs had SHA-256 `43c9ab058630092b167cd46686674597db1bf6c5ea4d7ba1d16f54104c393b43` (left) and `3db9e26fb0af9163ccac596ff2ed8073b848627458fa3d9609fcd2d2cdd7399c` (right). Callback-967 substituted screenshot SHA-256 was `a10c70300b7745037cfd02a8c4691fd200105d7ff34da7c10bf5deb954f3f98e` (left) and `700ae576399aac72f664bd1d8ec54bd87a18d65dfeee669f35f05fe394764e4d` (right). The normal counterpart SHA-256 values were `4e6d3113eff7c3a267cb91a98cb33d4a4966bdc0965744f476dfb3a9fcd82072` (left) and `784e742078b8d11be1382304ccfa787c81f0c7a78490eb5d29454c95e92f7c32` (right); see private files for direct verification.

**Interpretation — verified by execution in MAME:** the RAM substitution experiment, sham control and unchanged affine block show that Y-sprite RAM differences cause much of the lost callback-967 composed-image correspondence. The Y-sprite state was already changing at callback 964 but its visible residual was small at 965; the larger callback-966 difference coincided with the large callback-967 residual. **Hypothesis:** steering changes Y-sprite records for road and scenery, adding motion beyond the single whole-screen affine transform. The snapshots do not identify which records are visible, whether the game uses buffers or update delays internally, or whether the remaining 3–5% pixel mismatch comes from B sprites, priority, palette interpretation or other effects. The completed 512×512 source bitmap was not exposed directly through the tested Lua interface.

**Unsupported:** a physical Y-Board timing claim; names or meanings for original track/camera fields; a claim that the Sega CD renderer must reproduce the original sprite hardware; or a complete arcade camera-to-five-word translation. This experiment did not alter the Sega CD renderer or test physical hardware.

**Next bounded experiment — hypothesis:** identify the *specific* changed Y-sprite records that affect the visible road edge and scenery, using the same callback-966 intervention and a small record-level selection rather than substituting all 64 KiB. Separately track one visible road-edge coordinate in the unsteered replay across several frames. These observations can become a candidate real Stage 1 reference sequence without assuming the current five-word Sega CD interface is sufficient.
