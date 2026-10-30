# Phase 1B: same-run cross-CPU list-lock interval

**PASS — verified by execution in MAME 0.289:** three fresh pulse-124 runs independently reproduced the ten-event target interval required by the [prerepetition plan](2026-10-29-same-run-list-lock-plan.md). In each run, main-CPU object `$0C1D00` entered projection with shared count `$0027` and lock clear. Sub-Y then acquired the shared lock, wrote count `$0028`, and released the lock. The main CPU acquired the lock after that, read/copied at `$0028`, and incremented the count to `$0029` before releasing it. There was no count write between main lock acquisition and its copy. This resolves the prior same-run attribution gap for this tested MAME window.

| Fresh private run | Debug log SHA-256 | Control log SHA-256 | Audit |
| --- | --- | --- | --- |
| `build/private/phase1b-projection-lock124-r1/` | `d6ebfba74d063e5e77eba832568d6c53c45aea20ef360e1be0ae2b49ae16ba3b` | `307766d8722d20ec687265779c201e3054400e6d3d80bfb458cbc038bb8aae6c` | PASS |
| `build/private/phase1b-projection-lock124-r2/` | `d6ebfba74d063e5e77eba832568d6c53c45aea20ef360e1be0ae2b49ae16ba3b` | `99b8e1d3bc954303e9d941c0bfa0ec23d00f268b3dc9c13b8311ba9ae069c63f` | PASS |
| `build/private/phase1b-projection-lock124-r3/` | `d6ebfba74d063e5e77eba832568d6c53c45aea20ef360e1be0ae2b49ae16ba3b` | `7a6e8176b1fecfdd14b31f36a0104df05afb28ac849c60794e2e3f36ff388d62` | PASS |

**Verified by execution, event order for marker 961:**

| Ordered event | CPU | Count before/write | Lock before/write |
| --- | --- | --- | --- |
| Target object entry `$033D1E` | Main | `$0027` | clear |
| Lock acquisition | Sub-Y | `$0027` | `00 → 80` |
| Count write (Sub-Y PC `$012B60`) | Sub-Y | `$0027 → $0028` | held (`80`) |
| Lock release | Sub-Y | `$0028` | `80 → 00` |
| TAS before/after `$033E68/$033E70` | Main | `$0028` | `00 → 80` |
| Object copy `$033E8E` | Main | `$0028` | held (`80`) |
| Count increment and release | Main | `$0028 → $0029` | `80 → 00` |

The debugger reports `wpdata` as the value being written and the separately read lock/count fields as the prior memory state at the watchpoint. The auditor checks this old/new relationship, CPU identity, exact ordering and absence of a count write between main acquisition and copy. It is a same-run event audit, not a prediction from earlier Sub-Y state. The source and exact command, build, host, private ROM/state hashes and opt-in capture profile are in the prerepetition plan. Run `python3 tools/phase1b_projection_lock_audit.py build/private/phase1b-projection-lock124-rN` for `N=1,2,3` to reproduce the machine-readable PASS result. Raw logs, ROMs and saved state remain ignored/private.

**Corrected debugger attribution — verified by execution:** the watchpoint action's printed `pc=$033E1E` was the debugger-visible main-CPU PC, although the watchpoint was installed on Sub-Y. A separate Sub-Y-local Lua write tap read `suby.state["CURPC"]=$012B60` for the `$0028` count write; its private control log SHA-256 is `da6ebf7c412ef9caeb31cda9a33230b2116345aef8b427ac9f1e16e915134636`. Private Sub-Y disassembly at `$012B3A–$012B66` (SHA-256 `0461643851ba410a3743239965fb704142fefe8232a7bcfbf941dba70c71d2c0`) independently places TAS, list copy, count increment and lock release there. The prior audit's event order and CPU tags remain valid; its watch-action `pc` must not be read as Sub-Y's PC. The current auditor labels that field `watch_action_visible_pc`.

**Implication — verified by execution for this schedule:** the main CPU copied at slot `$0280` because Sub-Y inserted one record before main acquired the shared lock. The earlier frozen entry-count prediction `$0027` remains correct at entry but cannot by itself predict the later copy slot. **Unsupported:** a rule predicting when Sub-Y wins this lock from prior state, the Sub-Y record's geometry provenance, active-list buffer selection, original-board scheduler timing and a complete arcade-to-Sega CD camera packet. No physical hardware or Sega CD emulator was run; no cycle or host-speed result is claimed. The next bounded experiment should compare windows with and without an intervening Sub-Y write, using earlier Sub-Y control/state and main lock timing to predict the difference.
