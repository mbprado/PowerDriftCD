# Phase 1B: machine-readable geometry regression — 2026-10-24

**Question / hypothesis:** can the [calibrated comparison](2026-10-24-phase1b-calibrated-geometry-comparison.md) yield a reproducible regression result without confusing a known baseline miss or adaptation rows with independent validation? **Baseline:** four host-image cases with fit, adaptation and check roles. **Acceptance:** verify current source artifacts and report integrity, detect a deliberately worsened baseline, mark missing or altered evidence INCONCLUSIVE, and keep regression status separate from a road-readiness decision. **Result — verified by execution: PASS** for the checker and its controls. This is a host-geometry regression tool, not hardware acceptance.

## Criteria and results

**Verified by source inspection and execution:** [the criteria file](data/phase1b-road-regression-criteria.json) pins the calibration and case-list hashes, plus each arcade evidence hash. It records the prior per-role metrics as retrospective baselines. Its output-pixel limits are fit and adaptation mean edge ≤1 and width ≤2, and independent check mean edge ≤2 and width ≤2, with at least three rows per role. These limits protect this bounded experiment; they were chosen after the current observations and are **not** a prospective fidelity specification for the game.

**Verified by execution:** `tools/phase1b_geometry_regression.py` recomputes the comparison from current private evidence and original-art previews, requires exact equality with the supplied comparison JSON, then evaluates two separate outcomes. **Regression** asks whether any tracked role became worse than its recorded baseline. **Decision** requires both a fit and an independent `check` role to meet limits. `adaptation` is reported but cannot satisfy the independent-check requirement. A missing file, hash mismatch, changed calibration/case list or stale comparison produces `INCONCLUSIVE`; the tool does not silently substitute a fit row.

| Case | Regression | Fit | Adaptation | Independent check | Decision |
| --- | --- | --- | --- | --- | --- |
| Screen 971 baseline | PASS | PASS | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| Screen 973 baseline | PASS | PASS | INCONCLUSIVE | INCONCLUSIVE | INCONCLUSIVE |
| Screen 975 baseline | PASS | PASS | INCONCLUSIVE | FAIL | FAIL |
| Screen 975 local width bump | PASS | PASS | PASS | INCONCLUSIVE | INCONCLUSIVE |

**Verified by execution:** overall regression is **PASS** because the comparison remains byte-for-byte consistent with the recorded measurements. Overall decision is **FAIL** because baseline screen 975's independent check has mean width error 3.667 output pixels against the retrospective limit of 2. The local width bump's improved Y=157–159 result remains adaptation and cannot turn its decision into PASS. The status is a statement about these host previews under one chosen calibration, not a judgement on Sega CD hardware capability.

## Controls and cost

**Verified by execution:** a private copy of the criteria with screen-971 baseline edge error set to zero made the CLI report regression `FAIL` and exit 1. A missing comparison file made every case and the global regression `INCONCLUSIVE` and exited 2. An altered aggregate metric in a private comparison copy was also `INCONCLUSIVE` because recomputation disagreed with that file. The normal report exited 0. Control outputs remain ignored under `build/private/phase1b-road-regression-controls/`.

**Verified by execution:** five fresh Python-process runs of the normal regression took **0.100344, 0.109779, 0.102769, 0.098596 and 0.101833 host seconds** (median **0.101833**). All wrote identical `build/private/phase1b-road-regression.json` SHA-256 `95598ca430daf74ee394d0f15d434abdd15b870b0480ac6b49d9e3ab2a09418b`. This is offline host processing only; no new emulator operation or original hardware timing was measured.

## Provenance and reproduction

**Verified by execution:** source baseline `1d13c66` on `experiment/perspective-road`, with checker and criteria uncommitted during measurement; macOS Darwin 25.6.0 x86_64; Python 3.14.8; no compiler, MAME, BlastEm or physical Sega CD run. The tracked checker SHA-256 is `c20860b87c18b162b247912970fc5d1abb7b521b782bca2c74a8597c6289327f`; criteria SHA-256 `c20ceb1b185bd1bc102578730224bd143af36359eab734665d218a2274097fec`. The private comparison input SHA-256 is `9df0af32a37cdf22b67531d780b6f24e5d03b5570b4de83bba850f457176eef4`, and its earlier MAME/ROM/state provenance is recorded in the comparison report. The raw five-run timing JSON SHA-256 is `5b29faadb91273228b65054e6f915eda0e5772ebbfbd3801d2d808b2cba51754`.

```sh
python3 tools/phase1b_calibrated_geometry.py build/private docs/experiments/data/phase1b-road-calibration.json docs/experiments/data/phase1b-road-geometry-cases.json
python3 tools/phase1b_geometry_regression.py build/private docs/experiments/data/phase1b-road-regression-criteria.json
python3 -m py_compile tools/phase1b_geometry_regression.py
shasum -a 256 build/private/phase1b-road-regression.json
```

**Limitations — inference from verified execution:** the current independent-check failure is a useful unresolved shape constraint, while the adaptation result cannot establish generalization. The next research experiment should collect another causally verified vertical road span under a different arcade update, then add its host image as a new `check` case. The runner will need its criteria updated deliberately for a new case or calibration. None of these statuses claims a moving curved road will fit stock Sega CD timing or visual limits.

**Subsequent evidence — verified by execution:** the [screen-967 independent span](2026-10-24-screen967-independent-road-span.md) later added two cases and updated the retrospective criteria. The four-case statuses, hashes and timing above belong to the original checker milestone at commit `d028abe`; running the current case and criteria files yields a six-case report with independent decision `FAIL` for both new variants.
