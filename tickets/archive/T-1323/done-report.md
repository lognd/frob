## Done report

Root cause (acceptance [2]): the confirmed mechanism is candidate 1 from
the ticket body. `_absorb_pre_land_fixes`
(src/frob/app/ticket_runner/_land_cmd.py) calls apply_tier_a_fixes
pre-land, unconditionally, on every land -- including a worktree whose
native extensions (strata_core/frob_core) were stale or missing at that
point. `fix_waive004_stale_waiver`'s self-manufactured run_gates()
verification silently under-reported findings in that state (PERF/REF
reach analysis found nothing to scan against), so every live
frob:waive PERF00x waiver in the tree looked simultaneously stale and
was mass-deleted in one pass -- the 50-file strip that reached main via
the pre-land wip snapshot. Reproduced directly in
tests/test_gates.py::TestWaive004DegradedRunGuard::
test_mass_invalidation_of_one_rule_deletes_nothing (the incident's own
"many waivers of one rule go stale in the same run" shape) and
::test_native001_degraded_run_deletes_nothing (the specific
natives-stale trigger, via run_gates() short-circuiting to a NATIVE001
report).

Changed:
- src/frob/gates/_fix_engine.py::fix_waive004_stale_waiver -- now
  prove-fresh-or-do-nothing: refuses to delete anything when its
  self-manufactured run_gates() looks degraded
  (_degraded_verification_reason: a NATIVE001 finding, or an
  unexpected GateStats.skipped entry) or shows a mass-invalidation
  shape (_mass_invalidation_rule: >=5 waivers of the same rule going
  stale in one run). Either guard aborts the WHOLE batch, never a
  partial subset.
- src/frob/app/ticket_runner/_land_cmd.py::_absorb_pre_land_fixes --
  removed the interim exclude=("WAIVE004",) mitigation now that the
  handler guards itself; WAIVE004 runs unexcluded again. The exclude=
  parameter on apply_tier_a_fixes itself stays (regression-tested).
- src/frob/tickets/_land.py::_check_uncommitted_waive_deletions (new),
  wired into _land_precheck before any git mutation -- refuses land
  when the worktree's UNCOMMITTED state deletes a frob:waive directive
  whose file is neither in the landing ticket's scope nor named in its
  Done report. New LandError.OutOfScopeWaiveDeletion variant
  (src/frob/tickets/_models.py).
- src/frob/tickets/_land_merge.py -- new
  _uncommitted_waive_deletions / _waive_deletion_declared_in_done_report
  / _uncommitted_out_of_scope_waive_deletions helpers backing the above,
  reusing the existing D-12 _deletion_owned deletion-filter precedent
  for the scope half of the check.
- docs/modules/gates.md (Tier-A WAIVE004 handler section) and
  docs/modules/tickets.md (frob ticket land, new step 2.5) document the
  incident and both guards.
- design/frob.strata -- frob sys sync-interface's own generated fix for
  the two new public test classes (SELFAUDIT001/SYS104), same as land's
  own pre-land absorption step would do.

Evidence:
- tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_out_of_scope_undeclared_waive_deletion_refuses_before_merge [accepts 0]
- tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_in_scope_waive_deletion_is_allowed [accepts 0]
- tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_declared_in_done_report_waive_deletion_is_allowed [accepts 0]
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_native001_degraded_run_deletes_nothing [accepts 1, 2]
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_skipped_stage_degraded_run_deletes_nothing [accepts 1]
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_of_one_rule_deletes_nothing [accepts 1, 2]
- tests/test_gates.py::TestWaive004DegradedRunGuard::test_healthy_run_below_threshold_still_deletes [accepts 1]
- tests/test_gates.py::TestFixEngineTierABatch2::test_excluded_handler_is_skipped_and_file_untouched (exclude= regression test)

Filed: none (no out-of-scope work found; the known _land_merge_zones.py
scope-closure warning was already disclosed by the coordinator dispatch).

Gates: full `frob check --ticket T-1323` run (0 errors on ARCH after
splitting fix_waive004_stale_waiver for ARCH001; 0 errors on SELFAUDIT's
SYS104 after `frob sys sync-interface`; 0 errors on AFFECT/SCOPE/COV
after widening scope to src/frob/tickets/_models.py,
docs/modules/tickets.md, and design/frob.strata -- the last is
sync-interface's own generated fix for the two new public test
classes). Every remaining FAIL bucket (OPAQUE, RENDER, the 5 remaining
SELFAUDIT SYS102/103 findings, 1 ARCH001 in src/frob/refactor/_scan.py,
6 unrelated ruff-format files, 1 ty diagnostic in tests/test_fuzz.py)
is pre-existing and does not name any file this ticket touched --
verified by grep against the touched-file list. ruff/ty scoped-clean on
every touched file individually.

### Changed
```
 design/frob.strata                      |   2 +
 docs/modules/gates.md                   |  47 +++++++++
 docs/modules/tickets.md                 |  16 +++
 src/frob/app/ticket_runner/_land_cmd.py |  22 ++--
 src/frob/gates/_fix_engine.py           | 158 +++++++++++++++++++++++++---
 src/frob/tickets/_land.py               |  45 ++++++++
 src/frob/tickets/_land_merge.py         |  88 ++++++++++++++++
 src/frob/tickets/_models.py             |   8 ++
 tests/test_gates.py                     | 181 +++++++++++++++++++++++++++++++-
 tests/test_ticket_land.py               | 149 ++++++++++++++++++++++++++
 tickets.md                              | 145 ++++++++++++++++++++++++-
 11 files changed, 835 insertions(+), 26 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_out_of_scope_undeclared_waive_deletion_refuses_before_merge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_in_scope_waive_deletion_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_declared_in_done_report_waive_deletion_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaive004DegradedRunGuard::test_native001_degraded_run_deletes_nothing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaive004DegradedRunGuard::test_skipped_stage_degraded_run_deletes_nothing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaive004DegradedRunGuard::test_mass_invalidation_of_one_rule_deletes_nothing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWaive004DegradedRunGuard::test_healthy_run_below_threshold_still_deletes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
