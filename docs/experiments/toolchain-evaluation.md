# Phase 0 toolchain evaluation — 2026-10-16

**Decision: NO-GO for renderer work.** **Verified by execution:** GNU m68k tools assembled and linked an eight-byte original initial program, and the local image builder emitted a Sega Mega CD image recognized by macOS `file`, p7zip and BlastEm. [The BIOS-backed follow-up](2026-10-16-bios-backed-emulator-check.md) verified EU BIOS UI operation in BlastEm and Genesis Plus GX, but the image did not reach the test marker in the observed runs. **Unsupported:** actual BIOS handoff into the program, stock-hardware boot, and a two-emulator disc-program pass. Those Phase 0 exit criteria remain open.

## Hypothesis and acceptance

**Hypothesis:** GNU m68k ELF binutils can build a deterministic Sega CD initial program on Intel macOS, and a Python standard-library image builder can package it without proprietary content. **Expected evidence:** disassembly, stable SHA-256, independent file identification, and eventual debugger observation of the sub-CPU executing the IP marker (`D0 = 0x50443030`). The last check was attempted in BlastEm and is **FAIL** for the observed image/run: the marker was not reached.

## Host and pinned tools

**Verified by execution:** host macOS 26.6.2 (build 25G83), Darwin 25.6.0, x86_64; Python 3.14.8; GNU assembler/linker 2.47.20260726; m68k-elf-gcc 16.2.0; Homebrew 7.0.9. Source parent revision `ce01008f7eb3fbfc97eaf464e467fc5955f327a9`; the Phase 0 files are included with this report. Compiler was installed and version-checked; the smoke code uses assembler and linker directly, so C compilation is **NOT RUN**. Homebrew formula origin: [GNU binutils](https://formulae.brew.sh/formula/m68k-elf-binutils), [GNU GCC](https://formulae.brew.sh/formula/m68k-elf-gcc).

**Verified by execution:** `brew install m68k-elf-binutils m68k-elf-gcc` installed binutils 2.47 and GCC 16.2.0 from Homebrew bottles. **Documented only:** equivalent Linux execution can use GNU m68k ELF binutils 2.47 and GCC 16.2.0 from a distribution or reviewed upstream build; Linux package naming and binary compatibility were not tested.

## Build and image

**Verified by execution:** from the repository root, run `sh scripts/build-smoke.sh`. This runs `m68k-elf-as -m68000`, `m68k-elf-ld -Ttext=0 -e _start`, `m68k-elf-objcopy -O binary`, and `python3 tools/make_smoke_cd.py`. Generated files are ignored under `build/smoke/`. The source is [src/smoke/ip.S](../../src/smoke/ip.S); [scripts/build-smoke.sh](../../scripts/build-smoke.sh) is the entry point; [tools/make_smoke_cd.py](../../tools/make_smoke_cd.py) emits ISO/CUE using only the Python standard library.

**Verified by execution:** `m68k-elf-objdump -d build/smoke/ip.elf` showed `movel #0x50443030,%d0` at offset 0 and `bras` at offset 6. IP SHA-256: `330afcd923f7f8bcd6ef02a4e942853fb44568379fc4ca4fdefed0708f138d1f`. ISO SHA-256: `f43a87b55a67a7519b68e261413e7438dfb8c0098b4d84ce9785ddcf196be00c`. `file build/smoke/smoke.iso` identified a Sega Mega CD disc image titled `PHASE ZERO SMOKE`, 2048-byte sectors. `7z l build/smoke/smoke.iso` independently parsed an ISO filesystem of 614400 bytes and volume `PHASE0_SMOKE`. The generated ISO is 300 sectors and contains a small ISO 9660 descriptor/root directory; no commercial assets or firmware are embedded.

**Documented only:** the [Mega CD disc-format specification](https://gist.github.com/akiyan/a90d1e7d41ce89c532f29cafc356ccc2) describes the system ID, disc ID, initial program, system program, and ISO 9660 area. Its US BIOS bulletin describes a region-specific security program. **Hypothesis:** the original-code image is rejected by the EU BIOS because it omits accepted startup/security code; another header or image-format defect remains possible. The image is a **boot candidate**, not a verified bootable disc. The image uses the European region marker. Do not put proprietary security code in this repository.

## Next acceptance test

**Verified by execution:** the owner-supplied EU BIOS has now been used in BlastEm and Genesis Plus GX; see [the follow-up record](2026-10-16-bios-backed-emulator-check.md). **Expected evidence still missing:** breakpoint or trace on the sub 68000 at the IP entry, `D0 = 0x50443030`, and a second independent emulator showing the same program behavior. Investigate an independently authored startup sequence or document an unavoidable gate; do not copy commercial boot code.
