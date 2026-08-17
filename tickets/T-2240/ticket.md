---
id: T-2240
title: Wire 'make coverage' full-suite recipe to frob coverage --full, retire text-slicing
  tests
state: done
kind: feature
origin: human
created: '2026-08-16'
priority: high
parent: T-1382
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
evidence_scope:
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_body_is_at_most_two_non_comment_lines
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_calls_frob_coverage_full
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_no_longer_shells_out_to_pytest_or_coverage_directly
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_depends_on_core_not_a_recipe_embedded_make_call
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry
designated_repro_test: null
acceptance:
- text: 'GIVEN the coverage: target in Makefile WHEN read THEN its recipe body is
    a single uv run frob coverage --full line, not the ~40-line inline crash-recovery/rerun/stamp
    shell block'
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_body_is_at_most_two_non_comment_lines
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_calls_frob_coverage_full
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_no_longer_shells_out_to_pytest_or_coverage_directly
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_depends_on_core_not_a_recipe_embedded_make_call
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
  - tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry
- text: GIVEN tests/unit/test_makefile_coverage.py WHEN read THEN it no longer regexes
    Makefile text (_recipe_tail/_MAKEFILE slicing) and instead exercises frob.testing._coverage_refresh's
    --full path directly
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_body_is_at_most_two_non_comment_lines
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_calls_frob_coverage_full
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_no_longer_shells_out_to_pytest_or_coverage_directly
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_depends_on_core_not_a_recipe_embedded_make_call
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
  - tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry
- text: GIVEN the node-down xdist-crash recovery path THEN it still triggers a full
    serial rerun and still refuses to promote partial coverage data on failure (T-1363
    guard), proven by a test, not just inspection
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_body_is_at_most_two_non_comment_lines
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_calls_frob_coverage_full
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_no_longer_shells_out_to_pytest_or_coverage_directly
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_depends_on_core_not_a_recipe_embedded_make_call
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
  - tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Makefile's coverage: target (lines ~315-352) still carries its own ~40-line POSIX shell recipe (timeout, node-down grep, serial rerun, coverage combine, T-1363 promote-guard) even though frob.testing._coverage_refresh.native_coverage_refresh (T-1516/T-1677/T-1672) already reimplements the identical crash-recovery/rerun-deadline logic in pure Python and is reachable via 'uv run frob coverage --full' (frob/_cli_parsers/_misc.py). coverage-fast already made this switch (T-1525); coverage: was explicitly deferred (see Makefile comment near coverage-fast: 'coverage: below is NOT rewritten the same way'). This leaf closes that deferral: point the make target at 'uv run frob coverage --full', verify parity (crash recovery, node-down serial-rerun-with-full-data-recovery, T-1363 never-promote-partial-on-failure, final frob check --stamp-coverage gate), and retire tests/unit/test_makefile_coverage.py's Makefile-text-regex tests (924 lines, _recipe_tail()/_MAKEFILE slicing at lines 16-50+) in favor of tests against the Python implementation directly. First test that must fail today: assert the coverage: recipe body in Makefile is <=2 non-comment lines -- it is currently ~40. MUST-STILL-PASS: make coverage (and its frob coverage --full replacement) must still detect and fail on a genuinely broken test, still refuse to promote partial data on an xdist worker crash, and still run cross-platform (no bash -c, no backslash continuation, no POSIX-only tools) per T-1205 acceptance[3], which _coverage_refresh.py already claims -- verify that claim rather than assume it.

## Done report

Wired Makefile's `coverage:` target to `uv run frob coverage --full`
(src/frob/app/coverage_runner.py -> frob.testing._coverage_refresh.
native_coverage_refresh, T-1516/T-1677/T-1672), retiring the ~40-line
inline shell crash-recovery/rerun/stamp block. `coverage:` now reads:

    coverage: core
    	uv run frob ticket reconcile --apply && uv run frob doctor && uv run frob coverage --full

Verified this is wiring, not new logic, by reading
`native_coverage_refresh`/`_pytest_outcome`/`_run_full_suite` directly:
wall-clock + no-progress watchdog (`_spawn_with_watchdog`), xdist
worker-crash ("node down") signature detection with a one-shot serial
`-p no:xdist` retry that recovers full coverage data
(`_retry_after_worker_crash`), T-1676's "keep the data, mark degraded"
posture for an ordinary red suite, and a T-1363-equivalent guard (a
watchdog-aborted run never reaches `coverage xml`/`stamp_coverage` --
`_write_abort_provenance`'s branch in `native_coverage_refresh`) all
already exist and are reachable via `--full`. This is proven by test,
not just inspection: `tests/test_coverage.py::TestNativeCoverageRefresh
::test_full_run_produces_coverage_xml_after_worker_crash_recovery` and
`TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_
one_serial_retry` (both pre-existing, both re-verified passing here) --
NO DUPLICATION: this ticket does not re-implement those checks against
a second, Makefile-text-derived copy.

`core` is a real Makefile prerequisite (not a recipe-embedded `$(MAKE)`
line -- keeps T-2098's `make -n` dry-run-executes-$(MAKE)-lines fix
intact); `reconcile`/`doctor` stay as one `&&`-chained recipe line
(no `$(MAKE)` token on it, so `make -n coverage` still only prints it)
to preserve T-1469's stale-ticket-lease self-heal ahead of the run.

Retired `tests/unit/test_makefile_coverage.py`'s Makefile-text-regex
tests (`_recipe_tail`/`_MAKEFILE` slicing of the deleted shell block,
924 lines down to 195): kept the two checks that were never about the
deleted shell fragment (`TestPreviouslyZeroModulesNowAttributeInTheCo
mmittedLock`, reads the committed coverage lock directly;
`TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor`, fixed its regex
for the new `coverage: core` target line), and added a new
`TestCoverageRecipeDelegatesToFrobCoverageFull` class asserting the
recipe body is <=2 non-comment lines, calls `uv run frob coverage
--full`, no longer shells to pytest/coverage directly, and depends on
`core` as a prerequisite rather than a recipe-embedded `$(MAKE)` call.

Disclosed parity gap (pre-existing, not introduced by this leaf):
neither `frob coverage --full` nor `coverage-fast:` (already migrated
under T-1525) generates `.frob/coverage-subprocess.rc`/sets
`COVERAGE_PROCESS_START` the way the old ~40-line recipe did, so a test
that spawns `frob` (or anything else) as a real subprocess is not
separately coverage-instrumented under the new path. `coverage-fast`
already accepted this gap at T-1525; this leaf inherits it rather than
newly creating it, and does not attempt to fix it (that would be
src/frob/testing/_coverage_refresh.py work, a different ticket).
Removed the now-dead `COVERAGE_RERUN_DEADLINE`/`COVERAGE_WORKERS`/
`COVERAGE_XDIST_DEADLINE`/`COVERAGE_STACKDUMP_ENV` Makefile variables
and the `.frob/coverage-subprocess.rc` file-target rule that only the
deleted recipe read, replacing them with a short pointer comment (the
surrounding incident-history prose for T-1180/T-1235/T-1335/T-1353/
T-1433 is left in place as institutional memory, now explicitly marked
as documenting the retired shell logic).

MUST-STILL-PASS verified via `make -n <target>` for every OTHER target
(all/check/test/test-fast/test-unit/test-integration/test-system/
format/lint/lint-fix/typecheck/coverage-fast/sync-skills/playbook/
deploy-audit/pool-warm/pool-lease/pool-status/upload): all print their
expected commands, all unaffected by this change.

Filed T-2252 during T-2244 (this same worktree, series-first
ticket) capturing real src/frob gaps found while premise-checking that
sibling leaf (frob quality check's ruff-check/ruff-format bundling,
frob quality test's lack of directory-scoped selection, no ruff-autofix
write mode) -- unrelated to this ticket's own scope but filed in this
same worktree session, noted here for the coordinator's awareness.

### Changed
```
 tickets/T-1382/ticket.md           | 71 ++++++++++++++++++++++++++--
 tickets/T-2240/ticket.md           | 43 +++++++++++++++--
 tickets/T-2244/ticket.md           |  5 +-
 tickets/T-2251/ticket.md | 72 ++++++++++++++++++++++++++++
 tickets/T-2252/ticket.md | 96 ++++++++++++++++++++++++++++++++++++++
 5 files changed, 279 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_body_is_at_most_two_non_comment_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_calls_frob_coverage_full` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_no_longer_shells_out_to_pytest_or_coverage_directly` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_depends_on_core_not_a_recipe_embedded_make_call` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t1382-makefile/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t1382-makefile/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, TICK006@tickets.md
