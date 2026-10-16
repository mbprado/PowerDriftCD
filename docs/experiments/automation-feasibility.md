# Phase 0 automation feasibility — 2026-10-16

**Verified by execution:** [scripts/capture-emulator.py](../../scripts/capture-emulator.py) runs an emulator under a PTY, bounds host execution time, captures the console transcript in `build/evidence/`, and writes JSON with image/log SHA-256, exit status, timeout and host details. The result intentionally defaults to `INCONCLUSIVE` and `boot_verified: false`; process exit cannot establish Sega CD boot. Cycle and frame counters remain `null`. `wall_seconds` is measured by the host monotonic clock, not by emulated hardware.

**Verified by execution:** the BlastEm 1.0.0 run used:

```sh
python3 scripts/capture-emulator.py \
  --image build/smoke/smoke.iso \
  --out-dir build/evidence/blastem-1.0.0 --timeout 8 \
  --emulator-version 1.0.0 -- \
  /private/tmp/blastem-osx-1.0.0/blastem -r E -d \
  /Users/murilo/repos/PowerDriftCD/build/smoke/smoke.iso
```

**Verified by execution:** the resulting JSON records `timeout: true`, exit `-9`, null frame/cycle counters, and the ISO SHA-256 `f43a87b55a67a7519b68e261413e7438dfb8c0098b4d84ce9785ddcf196be00c`. The raw log SHA-256 is `39edb791f9f14950f026fe0a47d80fb710cc1be4c86cd0e0443b91a06028c394`; its decisive line is the missing `cdbios.bin` error. The GUI remained open after that error until the harness deadline. The timed interval includes startup and shutdown and says nothing about simulated performance.

**Verified by execution:** the [BIOS-backed follow-up](2026-10-16-bios-backed-emulator-check.md) used BlastEm's interactive `frames` command, debugger screenshot binding and a bounded PTY capture. RetroArch 1.22.2 ran Genesis Plus GX with `--max-frames=600 --max-frames-ss`, producing a BIOS-screen PNG and log. This verifies fixed requested frame count and screenshot capture, but not a deterministic input replay, complete headless operation, cycle counters, or disc-program execution.

**Documented only:** [MAME Lua](https://docs.mamedev.org/luascript/ref-debugger.html) can script CPU debugger actions and [video snapshots](https://docs.mamedev.org/luascript/ref-core.html); [ares-for-ai](https://github.com/paulomanrique/ares-for-ai/tree/headless-mcp) exposes frame stepping, CPU registers, breakpoints and traces via JSON-RPC. Both need execution on the smoke image before their evidence can be promoted to verified.

## Proposed deterministic run

1. **Hypothesis:** an independently authored startup path can make the owner-supplied BIOS transfer control to the original-code IP. Use a fixed region, BIOS SHA-256, ISO SHA-256, emulator commit/version and fixed configuration. BIOS content stays in ignored local storage. **Verified by execution:** the current image reaches the BIOS UI but not the IP marker.
2. **Expected acceptance:** capture main-CPU and sub-CPU PC/register state, set a main-CPU breakpoint at IP entry, step the `move.l`, and read `D0 = 0x50443030`; separately prove execution of an original sub-CPU SP. Save raw debugger transcript and screenshot. If a debugger cannot expose the sub CPU, record `INCONCLUSIVE` for that capability.
3. **Graphics counters:** run separate synthetic transactions that change one Word RAM owner flag, one ASIC operation and one VDP transfer. Record register addresses and state before/after. Classify each value as emulated cycles, host wall time, or unknown. A screenshot alone does not prove timing.
4. **Cross-check:** repeat the same image and fixed frame/input count in a second independent emulator. Record both emulator versions/commits and image checksum. If one needs CHD, record the conversion command and CHD checksum. Compare observable state and video, then test stock hardware separately.

**Verified by execution:** basic main/sub breakpoints and VDP register display ran in BlastEm. **Unsupported:** IP-entry breakpoint, Word RAM ownership transaction, ASIC timing, VDP transfer timing and dual-emulator initial-program execution. No frame pacing or hardware performance conclusion follows from this Phase 0 work.
