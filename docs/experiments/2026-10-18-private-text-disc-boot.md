# 2026-10-18 private European text-disc boot

**Question/hypothesis:** can the original `HELLO SEGA CD` IP reach its entry point and display text under the owner-supplied European BIOSes when a local accepted startup prefix and an original silent CD-DA track are present? **Expected acceptance:** BlastEm breaks at main-CPU `0xff056e`, later reads `D0 = 0x50443030`, and captures `HELLO SEGA CD` from the disc. **Result:** `PASS` in BlastEm 1.0.0 under both EU Model 1 and EU Model 2 BIOS files for the private two-track image. Hardware `NOT RUN`; independent emulator `NOT RUN` by owner decision. This is an emulator-level text-boot result, not a redistributable all-original disc.

## Provenance and private build

**Verified by execution:** host macOS 26.6.2 (25G83), x86_64; tested source revision `281efa854036a951cffcd0e64bc466d7350d3a26`. The later source-only `--silent-audio-track` change at `331d9b4` reproduced byte-identical outputs; the original IP source SHA-256 remained `2fcffefed7425e59bd259f40498ee0244a401a3226fe4d5b6eebd6a9207fae72`. Python 3.14.8 built the images; GNU m68k binutils 2.47.20260726 assembled the 440-byte original IP via `sh scripts/build-smoke.sh`. BlastEm 1.0.0 came from the pinned official macOS x86-64 archive (SHA-256 `2315f5f32b8400b4c56980b87043516ac9ec22aac5fdb9d3bdb97c2b236da221`). The owner-supplied EU Model 1 BIOS SHA-256 was `16735df92fcc1d0fc6a1eced244867e95281c5006340926082b74e363e073dc4`; EU Model 2 SHA-256 was `fe608a2a07676a23ab5fd5eee2f53c9e2526d69a28aa16ccd85c0ec42e6933cb`. Their version labels are not independently authenticated.

**Verified by execution:** the owner explicitly authorized local use of the matched Sonic startup sequence and prohibited putting it in Git. The local source data track at `/private/tmp/pd-ref-converted/reference-mode1-2048.iso` has SHA-256 `2e12056db4533d1c540224f61c2f8484b96e1f6e5950526a7d144e379d7cc5e9`; the owner-supplied CHD has SHA-256 `49d648b78789e40fe6a2e9eaf927d85862cb38b51761eba995e2ed2628056988`. A read of offsets `0x200..0x76d` produced exactly 1,390 private bytes at ignored `build/private/startup-prefix.bin`, SHA-256 `a28af3c9f6121914ca12f4b59cb51fba3d2898a5e2bd05c57e192840e0d8142d`. The original text IP was appended at disc offset `0x76e`, mapping to main-CPU RAM `0xff056e`; the original SP remained at disc `0x1000`. [The prior structural comparison](2026-10-18-shared-boot-prefix.md) found the same prefix bytes in both EU BIOS files. No Sonic audio or game-specific code beyond that startup sequence was copied.

**Verified by execution:** private build commands were `sh scripts/build-smoke.sh`, the extraction below, then `python3 tools/make_smoke_cd.py build/smoke/ip.img build/smoke/sp.img build/private/hello-with-local-prefix.iso build/private/hello-with-silence.cue --region E --startup-prefix build/private/startup-prefix.bin --silent-audio-track build/private/silence-track.bin`.

```sh
python3 - <<'PY'
from pathlib import Path
with Path('/private/tmp/pd-ref-converted/reference-mode1-2048.iso').open('rb') as source:
    source.seek(0x200)
    prefix = source.read(0x56e)
Path('build/private/startup-prefix.bin').write_bytes(prefix)
PY
```

The ISO SHA-256 is `3e4b8c69b5f247890cefe109b0f4466f157f661515328ea9023c095a1b48f557`, CUE SHA-256 `e479150e498f87a517b8877a8a1eb83b09366f35bf43889e0b2b8db1a9d6a1ea`, and generated 150-sector silent 2352-byte CD-DA track SHA-256 `19f0212a2c85ff556ebeb0e7ec8d5ac64299145a606f207ac650c4aab24bf73c`. Static checks verified prefix/IP/SP bytes and the expanded IP/SP header `(0x800,0x800)` / `(0x1000,0x7000)`. The default original-only smoke ISO stayed at SHA-256 `c12d985f15bcc79440ccde1101fd08234aa695f093c0c20faaacfb56b5c3ad4d`. All private images, prefix, generated audio, logs, and screenshots are under ignored `build/`; `git ls-files build` returned no files. No Git push occurred.

## BlastEm executions and controls

**Verified by execution:** both successful runs used `-r E -d /Users/murilo/repos/PowerDriftCD/build/private/hello-with-silence.cue` from isolated BlastEm copies with the corresponding local BIOS symlink. In the main debugger: `breakpoint 0xff056e; frames 600; binddown "gamepads.1.start"; frames 5; bindup "gamepads.1.start"; frames 1200; print/x pc d0`, followed after the breakpoint by `frames 120; print/x pc d0; bindup "ui.screenshot"; binddown "ui.screenshot"; frames 1`. `frames` values are requested emulator advances, not measured hardware speed; no random seed was used. Both BIOSes hit `FF056E: move.l #$50443030, d0`, then reached the original idle loop at `pc: ff05ea` with `d0: 50443030`. Both captured the visible text. Model 1 raw PTY transcript `build/evidence/2026-10-18-private-boot/pd-private-silence-test.txt` SHA-256 `951bb1080660acbba9fae3e48b1f2ee8abf5c923620e41e7c201138f3f011002`; Model 2 transcript `pd-private-silence-model2.txt` SHA-256 `4ff14fd76ba4be3b136aabc218a56dc3e6b7f26a63661eb547b3306588325e50`. Ignored screenshots `model1-hello.png` and `model2-hello.png` are byte-identical, SHA-256 `3c6a3d955b87b643ebdf4a7c8cc06e36f0d1d2e01b5eaa3fb0b85ac0d1b6d192`.

**Verified by execution:** controls with the same Model 1 BIOS separated the two image changes:

| Startup prefix | Audio track | Observed result |
| --- | --- | --- |
| Absent | Absent | Earlier original-only ISO returned to CD PLAYER; [baseline](2026-10-18-simple-text-boot.md). |
| Present | Absent | Main CPU reached `0xff0000` but did not reach text at `0xff056e`; the observed run later sat at BIOS PC `0x210`. Raw ignored logs `pd-private-prefix-blastem.txt` SHA-256 `bcc6adc6603690a48bc5373ed420cdb56d55bc9eea3ae157c472c83ce81c417a` and `pd-private-prefix-return-trace.txt` SHA-256 `e9cb49121db75e1201be0b01efdbfd629af64b404fe8170eadd1eb9bd09025fd`. |
| Absent | Present | The `no-prefix-with-silence.cue` control did not reach `0xff0000` and displayed CD PLAYER. Raw ignored log `pd-silence-no-prefix-control.txt` SHA-256 `01b79f932d1b259952f0004aa9e2d138b4ff1458bedac623b840f3b32ddc74ba`; screenshot SHA-256 `bea3812933e04130a32f487e3335521d970bdacbc2245d40f217886dc42de67a`. |
| Present | Present | Text IP entry, D0 marker, and screenshot `PASS` with EU Model 1 and Model 2, as above. |

**Verified by execution:** the complete owner reference BIN/CUE, including its audio tracks, reached the Sonic title screen in BlastEm under Model 1 after the same Start sequence and 1,200 requested frames; observed main PC was `ff2404`. Raw ignored log `pd-reference-full-boot.txt` SHA-256 `6db860dd5237be40575b8a01f6d419b33041116856c21578fd1766c24792b670`; ignored reference screenshot SHA-256 `f691a8f3f02c612c46a9eaac2c7ba0074263b1019f8182c614103a4e047101ed`. The earlier data-track-only reference reached `0xff0000` but did not reach title during the observed sequence; raw ignored log `pd-reference-ip-map.txt` SHA-256 `ff207b9ef1ff067f44416163f178718027ebb73b33ef66f7d81af1e61c483995`. The reference screenshot and full commercial BIN/CUE remain local and ignored.

**Inference from the four controlled runs:** in this BlastEm configuration, both the locally supplied accepted startup bytes and a second audio track were needed to reach the original text payload. **Hypothesis:** the BIOS or its CD path requires a compatible disc table of contents before completing startup; the exact branch is **unsupported**. The 150-sector silence worked in BlastEm, but physical-disc validity and stock-hardware boot are **unsupported**. Neither CPU/ASIC cycle timing nor sub-CPU SP execution was measured. The original-only distributable ISO still does not boot; the private local two-track image is the validated Phase 0 text demonstration. No Power Drift renderer work should begin until the Phase 0 results are reviewed.
