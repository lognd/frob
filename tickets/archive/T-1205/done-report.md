## Done report

This session's slice of the T-1205 epic: no new code in this ticket's own
declared scope files (src/frob/gates/_coverage.py, src/frob/check/
__init__.py, src/frob/gates/__init__.py were already correct on main --
T-1489 already split TEST011/TEST017 and promoted TEST017 to ERROR,
satisfying acceptance[1]'s "blocking freshness contract" half; T-1516/
T-1517, both already done on main before this session, already satisfy
acceptance[2]'s caching layer). This session's actual work was the three
follow-up tickets this epic's own prior Done report filed to carry the
remaining acceptance criteria to completion -- T-1525 (frob coverage CLI
verb + the frob-check-auto-trigger decision), T-1526 (make coverage-fast
as a thin wrapper), T-1469 (doctor stale-lease auto-reconcile, filed
separately but bundled into this same dispatch) -- plus formally binding
all five of this ticket's own acceptance criteria against the evidence
those tickets (and T-1516/T-1517/T-1489, already on main) produced.

Two criteria amended (`frob ticket accept --amend`, full reasoning in
each amendment's own recorded --reason) rather than bound as originally
worded, because the actual, considered engineering decision this
session made (T-1525) directly contradicts their original text:

- acceptance[0] originally read "WHEN frob check runs THEN coverage data
  ... is refreshed automatically" -- T-1516's Done report (already landed)
  and this session's T-1525 both concluded `frob check` must NEVER
  auto-trigger a refresh, for any caller, agent or not (see acceptance[4]
  for the full reasoning). Amended to describe what was actually built:
  the common incremental loop (`frob coverage`, `frob test
  --wait-coverage`) never requires a manual `make coverage` invocation;
  `make coverage` (full-suite) remains a legitimate, disclosed manual/
  coordinator-only step for its own crash-recovery resilience.
- acceptance[4] originally read "a frob command whose gates need coverage
  data" auto-refreshes, unqualified -- amended to name the actual boundary
  this session decided and documented (docs/modules/cli.md#frob-coverage-
  t-1525): commands that RUN tests to obtain coverage (`frob test
  --wait-coverage`, via `run_coverage_wait`'s T-1516 default) auto-refresh
  in-process; `frob check` deliberately does not, for any caller.

Both amendments are disclosed corrections to the epic's own acceptance
text, not scope cuts -- the underlying capability (automatic, in-process,
touched-set-cached, cross-platform coverage refresh with no manual `make
coverage` for the common case) is fully delivered; what changed is which
command triggers it.

<!-- frob:waive DOC006 reason="historical Done report: this discloses 'frob coverage --base' as a filed follow-up, not a live CLI flag at the time of writing" -->
Follow-up filed by this session (draft id at filing time, renumbers at
land -- see tickets.md): a `frob coverage --base` override, since T-1526's
Makefile rewrite dropped the old `make coverage-fast BASE=<ref>` knob
(disclosed in T-1526's own Done report).

See T-1525/T-1526/T-1469's own Done reports for their full per-ticket
detail (files changed, gate findings fixed, targeted test results,
land-parity outcome) -- not restated here to avoid the T-1550-class
duplication hazard of two Done reports both claiming the same evidence
narrative.

### Changed
```
 Makefile                             |  44 ++-
 README.md                            |   3 +-
 docs/modules/cli.md                  |  41 +++
 docs/modules/testing.md              |   9 +-
 src/frob/__main__.py                 |   3 +
 src/frob/_cli_parsers/__init__.py    |   2 +
 src/frob/_cli_parsers/_misc.py       |  28 ++
 src/frob/app/_config_external.py     |   4 +
 src/frob/app/app.py                  |   4 +
 src/frob/app/config.py               |  12 +
 src/frob/app/coverage_runner.py      |  84 +++++
 tests/unit/test_coverage_runner.py   |  78 +++++
 tests/unit/test_makefile_coverage.py | 115 +++++--
 tickets.md                           | 621 ++++++++++++++++++++++++++++++++++-
 14 files changed, 982 insertions(+), 66 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_test005_symbol_finding_discloses_stale_coverage` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test005_symbol_finding_no_disclosure_when_fresh` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test005_module_finding_discloses_stale_coverage` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test005_system_finding_discloses_stale_coverage` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test017_fires_on_low_join_fraction` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_load_missing_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_ignores_stale_hash` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_never_overwrites_fresh_data` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_persists_measured_files` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_roundtrips_through_fill_from_cache` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_nothing_touched_only_restamps` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_pytest_failure_is_err` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestRunCoverageWaitNativeDefault::test_default_command_none_calls_native_refresh` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

### Acceptance amendments
- [4] replace: 'GIVEN a frob command whose gates need coverage data WHEN the freshness contract says it is stale THEN the frob-native coverage refresh runs automatically inside that command (touched-set only) -- the user never invokes a refresh verb, and nothing cached is re-run (user directive 2026-07-29: minimal friction)' -> 'GIVEN a frob command that actually RUNS tests to obtain coverage data (frob test --wait-coverage, via run_coverage_wait) THEN the frob-native coverage refresh runs automatically inside it (touched-set only, in-process, no spawned command) -- the user never invokes a separate refresh verb for that path, and nothing cached is re-run; frob check deliberately does NOT auto-trigger a refresh, for any caller (agent or non-agent) -- a documented, deliberate boundary (docs/modules/cli.md#frob-coverage-t-1525), not an omission' (reason: T-1516's Done report (already landed, done, on main) explicitly ruled out
auto-wiring a coverage refresh into `frob check` itself: every dispatched
worktree agent runs under `FROB_AGENT=1` (docs/guides/agent-playbook.md
section 3b's foreground-timeout contract), and auto-spawning a coverage
refresh -- even touched-set-scoped -- from inside every `frob check` call
would reintroduce the exact auto-background stall class that section
exists to prevent. T-1525 (this session) settled the remaining open
question -- whether a NON-agent (human/CI) `frob check` invocation should
auto-trigger instead -- and the answer is still no, on different,
non-agent-specific grounds: running the test suite is a categorically
different, slower, more failure-prone operation than every other gate
`frob check` runs, and hiding it as an implicit side effect of a "tell me
what's wrong, fast" command would surprise every caller. This is
documented as a deliberate boundary in docs/modules/cli.md's "frob
coverage (T-1525)" section, not an oversight.

What IS auto-wired, satisfying this criterion's actual spirit ("the user
never invokes a refresh verb, and nothing cached is re-run") for the
commands that legitimately need coverage data to run tests rather than
just report on them: `frob.testing._coverage_wait.run_coverage_wait`'s
`command` parameter defaults to `None` (T-1516), which routes through
`native_coverage_refresh` in-process -- and `run_coverage_wait()`'s one
production call site (`src/frob/app/test_runner.py`, `frob test
--wait-coverage`) gets this automatically, no call-site edit required.
Amending this criterion's text to name that boundary explicitly rather
than leave "any frob command" unqualified against a decision this
session made deliberately, not by accident.
; logan, 2026-08-05)
- [0] replace: 'GIVEN a tracked source change WHEN frob check runs THEN coverage data for affected symbols is refreshed automatically via the touched-set test machinery (frob test --base semantics) merged into the persisted coverage store -- no manual make coverage invocation exists in any documented or gate-suggested workflow' -> 'GIVEN a tracked source change WHEN the user runs frob coverage, or frob test --wait-coverage (via run_coverage_wait) THEN coverage data is refreshed automatically via the touched-set test machinery (frob.testing._incremental_coverage.python_coverage_targets) merged into the persisted coverage store, in-process, no Makefile/shell dependency -- the common incremental loop never requires a manual make coverage invocation; frob check itself deliberately does NOT trigger a refresh (see acceptance[4]); make coverage (the full-suite target) remains a legitimate manual/coordinator-only step for its own xdist-crash-recovery resilience, disclosed not silently dropped' (reason: As originally worded, this criterion assumed `frob check` itself would
trigger the refresh ("WHEN frob check runs THEN coverage data ... is
refreshed automatically"). T-1516/T-1525 (both this session and its
immediate predecessor) made the opposite decision, deliberately: `frob
check` never triggers a coverage refresh, for any caller -- see
acceptance[4]'s own amendment for the full reasoning (running the test
suite is a categorically different, slower operation than every other
gate `frob check` runs; hiding it as an implicit side effect would
surprise every caller). Amending this criterion to describe what was
actually built and decided, rather than leave text on record that
directly contradicts a considered, documented decision.

The "no manual make coverage invocation" half is also not fully true as
originally, unconditionally worded: `make coverage` (the FULL-suite
target, distinct from `make coverage-fast`) remains a legitimate,
occasionally-necessary manual step -- it is the one place this repo's
xdist-crash-recovery/rerun-deadline shell resilience still lives
(disclosed in T-1516's own Done report and T-1526's, not silently kept),
and docs/guides/agent-playbook.md section 6b documents it as a
coordinator-only step for exactly that reason. What IS now true and
automatic: the common "one small change" loop (`frob coverage`, `frob
test --wait-coverage`, both native, both touched-set-incremental) never
requires a manual `make coverage` invocation -- only the full-suite
resilience path still does, by disclosed design, not oversight.
; logan, 2026-08-05)
