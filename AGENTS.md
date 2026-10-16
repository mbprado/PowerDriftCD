# Codex instructions — Power Drift CD

Read `README.md`, `docs/project-rules.md`, and `docs/testing.md` before work.

## Scope / authority
- You may inspect sources, prototype locally, generate source files, run builds and emulators, instrument/test, and report results.
- **Do not push, open PRs, merge, tag, or publish a release without explicit permission for that action.** The initial repository setup is a one-time owner-authorized exception handled by ChatGPT.
- Do not edit upstream emulator repositories in place. Use pinned local clones, isolated patches, or forks.
- Do not download, publish, commit or embed copyrighted Sega CD BIOS, arcade ROMs, or extracted commercial assets.
- No Windows runtime, Wine or Windows-specific dependency unless the owner expressly approves.
- Do not run unknown third-party setup commands without review; document origin and version of tooling.

## Development priorities
1. Original Sega CD / Mega CD hardware compatibility.
2. Correct game and camera behavior matching arcade references.
3. Reproducible frame pacing and performance measurement.
4. Clean, maintainable implementation with measured optimizations.

## Workflow
1. State hypothesis, baseline, test method and expected evidence.
2. Make small, reversible changes; use experiment branches for risky changes.
3. Build and execute relevant tests if tools are available.
4. Record emulator version/commit, host OS/architecture, image checksum, source revision, commands, raw logs and measured results.
5. Cross-check with another emulator where practical; mark hardware tests separately.
6. Explain regressions and limitations, including tests not executed.
7. Never present simulated wall-clock speed as hardware performance, or estimated values as measured values.

## Initial assignment (Phase 0 only)
- Evaluate Sega CD toolchains and debugger coverage on macOS/Linux.
- Test *actual* Sega CD boot, primary/secondary 68000 debug access, Word RAM/ASIC/VDP observability, headless/scriptable runs.
- Candidates: BlastEm, Genesis Plus GX, MAME, ares and ares-for-ai. Verify capabilities; do not assume.
- Produce an original-asset bootable smoke-test image if feasible, and execute it in two independent emulators.
- Write results to `docs/experiments/`; do not start the Power Drift renderer until the results have been reviewed.

## Evidence labels
Every statement about tool availability or functionality must be tagged in prose as one of: **verified by execution**, **documented only**, **hypothesis**, or **unsupported**. Do not fabricate performance numbers.

## Commit expectations
Prefer narrowly scoped commits with the test evidence or rationale alongside the change. Leave uncertain decisions as documented alternatives.
