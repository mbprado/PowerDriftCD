# 2026-10-18 EU/US text boot with a five-second audio track

**Question/hypothesis:** does a private disc with one original 375-frame silent CD-DA track and a locally supplied region-compatible startup sequence display the original `HELLO SEGA CD` IP on both European and U.S. Model 1/2 BIOSes in BlastEm? **Expected evidence:** the main-CPU debugger reaches the text IP entry, later shows `D0 = 0x50443030` at the idle loop, and a screenshot visibly contains the text. **Result — verified by execution:** `PASS` on EU Model 1, EU Model 2, U.S. Model 1, and U.S. Model 2 with the passing region image described below. Stock hardware `NOT RUN`; independent emulator `NOT RUN` per owner decision.

## Sources and build

**Documented only:** the [Sega Mega-CD disc specification](https://gist.github.com/akiyan/a90d1e7d41ce89c532f29cafc356ccc2) calls for a CD-ROM track followed by at least one CD-DA track and says an audio tune should exceed four seconds. The [Sega-CD Technical Bulletins](https://segaretro.org/images/2/2e/Sega-CD_Technical_Bulletins.pdf) say each track needs at least 300 frames. [BlastEm developer Michael Pavone's Sega CD notes](https://rhope.retrodev.com/segacd.html) describe the U.S. security check over disc offsets `0x200..0x783`, with execution continuing at main RAM `0xff0584`. Those notes do not establish that every U.S. BIOS contains a usable disc prefix at the same ROM location.

**Verified by execution:** baseline source revision `2b4f46f30d5ab53920620dafc2594eee290591e7`; host macOS 26.6.2 (25G83), x86_64; Python 3.14.8; GNU m68k binutils 2.47.20260726. BlastEm 1.0.0 was the pinned official macOS x86-64 archive, SHA-256 `2315f5f32b8400b4c56980b87043516ac9ec22aac5fdb9d3bdb97c2b236da221`, run from isolated copies in `/private/tmp/`. BIOS SHA-256: EU Model 1 `16735df92fcc1d0fc6a1eced244867e95281c5006340926082b74e363e073dc4`; EU Model 2 `fe608a2a07676a23ab5fd5eee2f53c9e2526d69a28aa16ccd85c0ec42e6933cb`; U.S. Model 1 `807384678ef259494d943eddb6954dfc7069693d0dde0c424e2028488d88e81a`; U.S. Model 2 `b1c2036b79467514eaaa69c76e5ba83801621e821059caa53cb921a0b21e3af4`. Model/version labels come from owner-supplied filenames and are **unsupported** as independent firmware authentication.

**Verified by execution:** `sh scripts/build-smoke.sh` rebuilt the original IP/SP; IP SHA-256 `2fcffefed7425e59bd259f40498ee0244a401a3226fe4d5b6eebd6a9207fae72`, SP SHA-256 `b3384b4c40d4f9b2c7625048d9b478c9c7005a10bebc47123efb3c243500a787`. The builder's optional silent track was increased from 150 to 375 frames (five seconds, 2352 bytes/frame). The default original-only ISO was unchanged, SHA-256 `c12d985f15bcc79440ccde1101fd08234aa695f093c0c20faaacfb56b5c3ad4d`. The resulting silence SHA-256 is `ff793c626048816a52aa19c55232c5226be1f990b3b028ddc435877fc2676547`.

**Verified by execution:** the EU disc used the previously authorized local 1,390-byte prefix, SHA-256 `a28af3c9f6121914ca12f4b59cb51fba3d2898a5e2bd05c57e192840e0d8142d`. For the U.S. experiment, a unique 1,205-byte shared sequence located the candidate block in the owner-supplied U.S. Model 1 BIOS at ROM `0x5744`; the private 1,412-byte slice through the documented `0x783` endpoint has SHA-256 `6ddf49d3e9edffe66b98776507aae447b3b0a90d96d3dae4572618d258d1259d`. These extracted bytes and every derived image remain in ignored `build/private/`, never in tracked source. Build commands from the repository root:

```sh
python3 - <<'PY'
from pathlib import Path
reference = Path('build/private/startup-prefix.bin').read_bytes()
bios = Path('BIOS/Sega CD (U) - Model 1 v1.10 (1992).bin').read_bytes()
anchor = reference[12:1217]
match = bios.find(anchor)
assert match >= 12 and bios.find(anchor, match + 1) < 0
Path('build/private/us-m1-startup-prefix.bin').write_bytes(bios[match - 12:match - 12 + 0x584])
PY
python3 tools/make_smoke_cd.py build/smoke/ip.img build/smoke/sp.img build/private/hello-eu-5s.iso build/private/hello-eu-5s.cue --region E --startup-prefix build/private/startup-prefix.bin --silent-audio-track build/private/silence-eu-5s.bin
python3 tools/make_smoke_cd.py build/smoke/ip.img build/smoke/sp.img build/private/hello-us-m1-5s.iso build/private/hello-us-m1-5s.cue --region U --startup-prefix build/private/us-m1-startup-prefix.bin --silent-audio-track build/private/silence-us-m1-5s.bin
```

**Verified by execution:** EU ISO SHA-256 `3e4b8c69b5f247890cefe109b0f4466f157f661515328ea9023c095a1b48f557`, CUE `76e613b9761ced2645de5c8bd87563427cfec2750f32a9f8cd341742b1f53eab`; U.S. passing ISO `926b00d3525a50b4f5a37c32ec0ae342456a85d2e65748a46d9ca871a21a17f9`, CUE `1c03c038a9abc99eeecb36cf778f72ef6ab91fbe56b995cf7a0a7f5713a59804`. Static assertions verified 375 zero-filled audio frames, exact private-prefix/IP/SP placement, and expanded header IP/SP values `(0x800,0x800)` / `(0x1000,0x7000)`. The original text IP starts at disc `0x76e` / main RAM `0xff056e` in EU and disc `0x784` / main RAM `0xff0584` in U.S.

## BlastEm execution

**Verified by execution:** each row used BlastEm `-r E` or `-r U` and `-d` pointing to its matching private CUE, with the selected local BIOS symlink named `cdbios.bin` in an isolated emulator copy. Main debugger input was `breakpoint 0xff056e` (EU) or `breakpoint 0xff0584` (U.S.), then `frames 600`, `binddown "gamepads.1.start"`, `frames 5`, `bindup "gamepads.1.start"`, `frames 1200`, `print/x pc d0`; after the breakpoint, `frames 120`, `print/x pc d0`, and the `ui.screenshot` binding captured the screen. The frame counts are requested emulated advances, not hardware-speed measurements. No random seed was used. Raw PTY transcripts and screenshots are under ignored `build/evidence/2026-10-18-five-second-regions/`.

| BIOS / private disc | Result | Observed marker and screenshot | Raw log SHA-256 |
| --- | --- | --- | --- |
| EU Model 1 / EU | `PASS` | Entry `ff056e`, idle `ff05ea`, D0 `50443030`; `eu-m1-hello.png` SHA-256 `3c6a3d955b87b643ebdf4a7c8cc06e36f0d1d2e01b5eaa3fb0b85ac0d1b6d192` | `eu-m1.log` `12a84c09619dae3b767fe96bc523af784aee8d53112cbce6d1f90a712de3f67c` |
| EU Model 2 / EU | `PASS` | Same entry, idle, D0, and screenshot hash | `eu-m2.log` `385285bb00aaf8c561a65b58b71c705d3dfe58b10aeec1dc2140e5a284dbd39a` |
| U.S. Model 1 / U.S. Model 1-derived | `PASS` | Entry `ff0584`, idle `ff0600`, D0 `50443030`; `us-m1-hello.png` SHA-256 `364f319d434ae49386e217e6c3492d8c53ff315e8fa40946fbbfbd6e8549f29a` | `us-m1.log` `244a26ffdccfc15895759ee5b3a26a2ddb92082e8203e158a072a4b08420ebab` |
| U.S. Model 2 / U.S. Model 1-derived | `PASS` | Same entry, idle, D0, and screenshot hash | `us-m2-m1-disc.log` `0322fd27f8507985635851ff78423e18b472cf662552b00e5ca92a4849f83bd9` |

**Verified by execution:** two U.S. controls failed. A 1,390-byte U.S. Model 1-derived prefix placed the text at `ff056e`; it returned to CD PLAYER, consistent with the documented `ff0584` handoff. A 1,412-byte slice from the U.S. Model 2 BIOS at ROM `0x6df0` (SHA-256 `472e05cc6a521d52cd14d2518d38f8e51ef107a516c4104d3fc3b0d2ff337aa4`) also returned to CD PLAYER when paired with that same BIOS. Its ISO SHA-256 was `ecfa37e244cd507075448acadcec8bd168b8813edc5cf2e3abdd83f33eeca1f1`, CUE `65d46dd540c161c3b036a8c3d363b91e1ca6b61389b9e38aebd7ef47d4900e7e`. The passing U.S. Model 1-derived disc then booted on that Model 2 BIOS, so the observed failure follows the candidate disc bytes. The exact differing BIOS check and whether a Model 2-derived prefix can be made valid are **unsupported**.

**Limitations:** these are BlastEm-only results, using owner-authorized local proprietary startup bytes. Physical disc lead-in/pregap/lead-out layout and stock-hardware boot are **unsupported**. The original-only redistributable image still returns to CD PLAYER. No Power Drift renderer work should begin until Phase 0 review.
