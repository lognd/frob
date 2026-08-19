## Done report

Investigated all 14 (rule=COV003) findings the coordinator measured;
T-2366's own declared scope covers only T-1205/T-1235/T-1397/T-1526 (the
other 3 ticket ids -- T-1688, T-2344, T-2348 -- are out of scope for this
ticket and were left untouched, per the ticket's own scope field).

Root cause: all 10 stale evidence citations across the 4 tickets named
tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc
or ::TestSubprocessRcIsAbsoluteAndConcurrencyAware -- both classes were
DELETED by T-2240's Makefile-removal work (T-1382 epic), which deleted the
Makefile's own rc-generation mechanism (T-1235's original "Loss A" fix)
without porting it to the native coverage path. Confirmed via
git grep COVERAGE_PROCESS_START src/frob/testing/ -- zero hits before
T-2527. This is the SAME finding T-2256's own done report (2026-08-17)
already reached for these exact 4 tickets; T-2366 independently
re-confirmed it rather than trusting that prior finding on assertion
alone.

Filed T-2527 for the real, live coverage-attribution regression (any
subprocess/pool-worker spawned during a native coverage run measured
nothing) rather than repointing to an unrelated passing test, per this
repo's established no-fabricated-repoint policy. T-2527 landed
(a9dd9c55682b295a6f0b2f70ea43578594c92cac), re-adding the mechanism with
new tests carrying T-1235's original claims, and MEASURING the gap
directly: a real subprocess test showed src/frob/doctor.py at 0% covered
before the fix, 57% after, on the identical subprocess call.

With T-2527 landed, this ticket repointed 8 of the 10 orphaned citations
to the new tests (each verified to carry the SAME underlying claim as the
deleted node -- absolute rc paths, concurrency+sigterm, [paths] remap,
never-points-at-pyproject.toml, shared-not-duplicated across full/
incremental branches, and pyproject.toml's own concurrency/sigterm
settings). The remaining 2 (T-1397's file-target-caching claim, T-1526's
recipe-step-ordering claim) are genuinely about retired Makefile mechanics
with no honest native equivalent -- documented explicitly in their
archived ticket bodies as PERMANENTLY UNRESOLVABLE rather than repointed
to a convenient-but-unrelated passing test. These 2 will continue to fail
COV003 by design; this is the correct, honest end state per this ticket's
own instructions, not an incomplete fix.

Side finding: `frob ticket body <id> --append` has no --archived support
and silently resurrected a full duplicate active-tree copy of an archived
ticket instead of editing it in place or refusing -- filed as T-2548
(out of scope), recovered by hand.

### Evidence
tests/test_coverage.py::TestSubprocessCoverageRc (5 of its methods) and
TestPyprojectDeclaresCoverageConcurrency::test_pyproject_declares_concurrency_and_sigterm
-- the new tests T-1205/T-1235/T-1397/T-1526's repointed citations now
name.

### Changed
```
 tests/test_coverage.py           |  85 ++++++++++++++++++++++++++
 tickets/T-2366/ticket.md         |  29 ++++++++-
 tickets/T-2548/ticket.md         |  50 +++++++++++++++
 tickets/archive/T-1205/ticket.md |  21 ++++++-
 tickets/archive/T-1235/ticket.md |  51 +++++++++++++---
 tickets/archive/T-1397/ticket.md |  46 +++++++++++++-
 tickets/archive/T-1526/ticket.md | 127 +++++++++------------------------------
 7 files changed, 297 insertions(+), 112 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_uses_absolute_source_and_data_file` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_declares_multiprocessing_and_sigterm` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_remaps_paths_back_to_source` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_never_points_at_pyproject_toml` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_incremental_run_shares_the_same_rc_as_full_run` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPyprojectDeclaresCoverageConcurrency::test_pyproject_declares_concurrency_and_sigterm` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2366/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
