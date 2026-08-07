## Done report

T-1180's deflation floor compares a run's `module_join_fraction` against
itself: a module that never got traced (e.g. a subprocess/daemon/CLI-entry
process the fix landed by T-1235 does not reach) still JOINS against
coverage.xml -- it joins at 0% line-rate. The aggregate join fraction alone
cannot tell that apart from a module genuinely covered, so a run that
silently dropped a whole class of process's data could still stamp clean
if enough OTHER modules joined normally. T-0969's diagnosis named this
exact blind spot; this ticket closes it with a second, independent signal
that does not rely on the aggregate ratio at all.

Added `_CANARY_MODULES`/`_canary_deflation` (`src/frob/gates/_coverage.py`):
a small named list of modules known to be exercised by every healthy full
run (currently `src/frob/__main__.py`, invoked by every system test that
spawns the CLI). `_filtered_coverage_or_deflated` now refuses the stamp
(`Err(GateError.CoverageDeflated)`, reusing the existing T-1180 error
value -- same failure class, not a new one to keep in sync) whenever any
present canary reads exactly 0.0%, independent of and in addition to the
existing `_DEFLATION_FLOOR`/`_provenance_drop` checks. Skipped when a
canary is simply absent from a run's `module_line` (a tiny fixture
snapshot that never declared it) -- only a present-but-zero reading trips
it, matching this ticket's acceptance criterion exactly ("named canaries
... nonzero while system tests exist").

Scope note: the ticket's declared scope named `tests/test_coverage.py`,
but that file is unrelated (T-0484's touched-set coverage-target helper
tests) -- every existing `stamp_coverage`/deflation-floor test (T-1180,
T-1363, T-1435) lives in `tests/test_gates.py::TestCoverageLoad` instead.
Added `tests/test_gates.py` to scope via `frob ticket scope --add` (logged
reason: matching existing precedent, not expanding what the ticket does)
rather than fork a duplicate, disconnected test file.

Two new tests added to `TestCoverageLoad`: one builds a coverage.xml where
24 known modules join (well above both `_DEFLATION_MIN_KNOWN_MODULES` and
`_DEFLATION_FLOOR`) but the canary (`src/frob/__main__.py`) reads exactly
0.0%, asserting the stamp is refused with `GateError.CoverageDeflated` and
neither the stamp file nor the lock is written; the other confirms a run
whose snapshot never declares the canary at all stamps normally (the
skip path).

docs/modules/gates.md's `stamp_coverage`-behaviors list gets a new bullet
describing the canary guard alongside its existing T-1180/T-1363 siblings.

### Changed
```
src/frob/gates/_coverage.py | canary-module guard (_CANARY_MODULES, _canary_deflation) wired into _filtered_coverage_or_deflated
tests/test_gates.py         | +2 tests on TestCoverageLoad
docs/modules/gates.md       | +1 bullet describing the T-1236 canary guard
tickets.md                  | T-1236 scope add + evidence + Done report
```

### Evidence
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_zero_canary_module` (pytest node id, verified passing: 33 passed in TestCoverageLoad's full class run)
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_canary_check_skipped_when_module_unknown` (pytest node id, verified passing)

### Captured claims
- tests: 33 passed (full `TestCoverageLoad` class run, `pytest tests/test_gates.py::TestCoverageLoad -q`)
- gates: `frob check --ticket T-1236` across gates-fast/gates-native/gates-security: 0 errors in each of the three invocations (`ty check src/frob/gates/_coverage.py` also clean after fixing a `dict[str, float]`/`Mapping` invariance mismatch `_canary_deflation` introduced)
- `gate:scope-note` disclosure acknowledged: only gate:SCOPE/gate:PREWORK/COV002/TODO001/FMT/AFFECT are ticket-scoped; every other family's 0-errors count above is repo-wide, read directly from its own `gate:<FAMILY>` line, not inferred from the ticket-scoped view alone

### Changed
```
 tickets.md | 18 +++++++++++++++---
 1 file changed, 15 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_zero_canary_module` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_canary_check_skipped_when_module_unknown` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 889 warning(s), 745 waived
- error-findings: none (measured, zero errors)
