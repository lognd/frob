---
id: T-1526
title: 'coverage: make make coverage/coverage-fast a thin wrapper over native_coverage_refresh'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: rewriting coverage-fast into a thin wrapper obsoletes tests/unit/test_makefile_coverage.py's
    own recipe-content assertions about the old inline xargs/rc logic; must update
    them in the same change, and testing.md documents the make-target contract
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/testing.md
  reason: rewriting coverage-fast into a thin wrapper obsoletes tests/unit/test_makefile_coverage.py's
    own recipe-content assertions about the old inline xargs/rc logic; must update
    them in the same change, and testing.md documents the make-target contract
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_coverage.py::TestSubprocessCoverageRc::test_incremental_run_shares_the_same_rc_as_full_run
- tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_still_rebuilds_natives_first
  new_node: tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives
  reason: 'T-2743 sweep: T-2240 deleted the Makefile test class this cited; the
    successor asserts the identical claim (coverage-fast''s incremental branch
    restores/verifies natives before pytest runs) against the native coverage-fast
    entrypoint directly.'
  actor: logan
  at: '2026-08-20'
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: the coverage-xml step always passes -i/--ignore-errors. Successor exercises
    native_coverage_refresh''s own ''coverage xml -i'' call directly (coverage-fast
    now delegates entirely to native_coverage_refresh per this same ticket''s own
    T-1526 rewrite, so there is no separate Makefile-side xml invocation left to test).'
  actor: logan
  at: '2026-08-17'
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
  new_node: tests/test_coverage.py::TestSubprocessCoverageRc::test_incremental_run_shares_the_same_rc_as_full_run
  reason: T-2240 deleted the Makefile test class this cited; T-2527 re-added the underlying
    shared-rc-generation behavior natively and this new test proves the same shared-not-duplicated
    claim.
  actor: logan
  at: '2026-08-18'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1205 acceptance[3] asks for make coverage to become a thin optional wrapper around the frob-native orchestration. T-1516 added native_coverage_refresh and rewired run_coverage_wait's default onto it, but the Makefile coverage/coverage-fast targets themselves were left untouched (they still run the full ~300-line shell recipe independently). Rewrite them to delegate their common-path work to native_coverage_refresh, keeping only the xdist-crash-recovery/rerun-deadline shell logic (or whatever that becomes once T-1524 lands) as the part that stays Makefile-side, or is itself ported.

T-2366/T-2527 note (2026-08-18): this ticket's second evidence citation,
tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_still_rebuilds_natives_first,
is DELIBERATELY LEFT UNREPOINTED and will continue to fail COV003. Its
claim was about Makefile RECIPE ORDERING -- `coverage-fast:`'s own
`$(MAKE) core && uv run frob doctor` step running BEFORE
.frob/coverage-subprocess.rc generation, within one Makefile target body.
T-2527 (which re-added the underlying subprocess-coverage measurement
natively, since T-2240 dropped it entirely without porting it) writes
the rc inside native_coverage_refresh itself; natives-rebuild is an
entirely separate mechanism (T-1213's auto-rebuild in run_gates) that
native_coverage_refresh does not own or sequence against -- there is no
natural equivalent to "this recipe step runs before that one" inside a
single Python function with no such ordering claim to make. This
specific claim (about a retired Makefile recipe's own step order) has
no honest native equivalent; the underlying coverage-measurement
behavior itself is now proven by tests/test_coverage.py::
TestSubprocessCoverageRc (T-2527). Repointing this citation to an
unrelated passing test would misrepresent what this ticket actually
proved, so it is recorded here as permanently unresolvable instead.
