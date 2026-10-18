# Phase 0 toolchain evaluation — 2026-10-16

**2026-10-18 review update:** the owner accepted the [limited Phase 0 review](2026-10-18-phase-0-review.md) for Phase 1 synthetic emulator characterization. The historical NO-GO below applied before a private-disc boot was verified; it remains correct for an original-only distributable disc and for physical-hardware claims. No production renderer has started.

**2026-10-18 update — verified by execution:** a later [private two-track text-disc test](2026-10-18-private-text-disc-boot.md) reached the original IP marker and displayed text in BlastEm under EU Model 1 and Model 2 BIOS files. The owner authorized a local Sonic-derived startup prefix, which remains ignored and outside Git. The original-only image still fails, stock-hardware boot is **unsupported**, and the renderer decision remains NO-GO pending Phase 0 review. The findings below describe the earlier original-only candidate.

**Later 2026-10-18 update — verified by execution:** the [five-second-track test](2026-10-18-eu-us-five-second-text-boot.md) also displayed the text under U.S. Model 1 and Model 2 BIOSes in BlastEm. U.S. NTSC is now the [development baseline](2026-10-18-us-development-baseline.md); physical testing is deferred by owner decision.

**Decision: NO-GO for renderer work.** **Verified by execution:** GNU m68k tools assembled and linked an eight-byte original initial program, and the local image builder emitted a Sega Mega CD image recognized by macOS `file`, p7zip and BlastEm. [The BIOS-backed follow-up](2026-10-16-bios-backed-emulator-check.md) verified EU BIOS UI operation in BlastEm and Genesis Plus GX, but the image did not reach the test marker in the observed runs. **Unsupported:** actual BIOS handoff into the program, stock-hardware boot, and a two-emulator disc-program pass. Those Phase 0 exit criteria remain open.

## Hypothesis and acceptance

**Hypothesis:** GNU m68k ELF binutils can build a deterministic Sega CD initial program on Intel macOS, and a Python standard-library image builder can package it without proprietary content. **Expected evidence:** disassembly, stable SHA-256, independent file identification, and eventual debugger observation of the main CPU executing the IP marker (`D0 = 0x50443030`). **Correction:** the previous sub-CPU marker criterion targeted the wrong processor. **Verified by execution:** a main-CPU breakpoint at the documented IP RAM address did not fire during the updated image's observed BlastEm sequence; see the [follow-up test](2026-10-16-bios-backed-emulator-check.md).

## Host and pinned tools

**Verified by execution:** host macOS 26.6.2 (build 25G83), Darwin 25.6.0, x86_64; Python 3.14.8; GNU assembler/linker 2.47.20260726; m68k-elf-gcc 16.2.0; Homebrew 7.0.9. Source parent revision `ce01008f7eb3fbfc97eaf464e467fc5955f327a9`; the Phase 0 files are included with this report. Compiler was installed and version-checked; the smoke code uses assembler and linker directly, so C compilation is **NOT RUN**. Homebrew formula origin: [GNU binutils](https://formulae.brew.sh/formula/m68k-elf-binutils), [GNU GCC](https://formulae.brew.sh/formula/m68k-elf-gcc).

**Verified by execution:** `brew install m68k-elf-binutils m68k-elf-gcc` installed binutils 2.47 and GCC 16.2.0 from Homebrew bottles. **Documented only:** equivalent Linux execution can use GNU m68k ELF binutils 2.47 and GCC 16.2.0 from a distribution or reviewed upstream build; Linux package naming and binary compatibility were not tested.

## Build and image

**Verified by execution:** from the repository root, run `sh scripts/build-smoke.sh`. This runs `m68k-elf-as -m68000`, `m68k-elf-ld -Ttext=0 -e _start`, and `m68k-elf-objcopy -O binary` for both [IP](../../src/smoke/ip.S) and [SP](../../src/smoke/sp.S), then `python3 tools/make_smoke_cd.py`. Generated files are ignored under `build/smoke/`. [scripts/build-smoke.sh](../../scripts/build-smoke.sh) is the entry point; [tools/make_smoke_cd.py](../../tools/make_smoke_cd.py) emits ISO/CUE using only the Python standard library.

**Verified by execution:** `m68k-elf-objdump -d build/smoke/ip.elf` showed `movel #0x50443030,%d0` at offset 0 and `bras` at offset 6. IP SHA-256: `330afcd923f7f8bcd6ef02a4e942853fb44568379fc4ca4fdefed0708f138d1f`. The initial, IP-only ISO SHA-256 was `f43a87b55a67a7519b68e261413e7438dfb8c0098b4d84ce9785ddcf196be00c`. `file` identified a Sega Mega CD disc image titled `PHASE ZERO SMOKE`, 2048-byte sectors. `7z l` independently parsed an ISO filesystem of 614400 bytes and volume `PHASE0_SMOKE`. The generated ISO is 300 sectors and contains a small ISO 9660 descriptor/root directory; no commercial assets or firmware are embedded. **Verified by execution:** the later original SP stub changed the current ISO SHA-256 to `8baed93a269c2b1c55f6d006da768eb86aba353a8b32e12c37383f34787ec52d`; see the [follow-up test](2026-10-16-bios-backed-emulator-check.md).

**Documented only:** the [Mega CD disc-format specification](https://gist.github.com/akiyan/a90d1e7d41ce89c532f29cafc356ccc2) describes the system ID, disc ID, initial program, system program, and ISO 9660 area. Its US BIOS bulletin describes a region-specific security program. **Hypothesis:** the original-code image is rejected by the EU BIOS because it omits accepted startup/security code; another header or image-format defect remains possible. The image is a **boot candidate**, not a verified bootable disc. The image uses the European region marker. Do not put proprietary security code in this repository.

## Next acceptance test

**Verified by execution:** the owner-supplied EU BIOS has now been used in BlastEm and Genesis Plus GX; see [the follow-up record](2026-10-16-bios-backed-emulator-check.md). The first image declared a 0x7800-byte SP but filled that range with zeroes. The current candidate has an original SP stub and still reaches CD PLAYER. **Expected evidence still missing:** main-CPU IP-entry marker `D0 = 0x50443030`, sub-CPU execution of the SP marker, and a second independent emulator showing the same program behavior. Investigate an independently authored startup sequence; do not copy commercial boot code.
