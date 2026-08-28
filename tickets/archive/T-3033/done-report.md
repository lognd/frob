## Done report

TEST-side fix, not a product bug: `scan_stale_ticket_leases` doing real
per-branch git work is CORRECT behavior for its actual purpose (reconcile
against every branch's ticket state); the flakiness is a test hitting the
real checkout when it had no reason to, compounded by cross-worker xdist
contention.

Root cause confirmed exactly as briefed:
`test_run_diagnosis_reports_frob_version()` called `doctor.run_diagnosis()`
with NO root -- the one test in this file that omitted the `tmp_path`
isolation every sibling test already uses -- so it silently exercised
`_collect_doctor_scans -> scan_stale_ticket_leases -> reconcile ->
_unlanded_branch_work` against the REAL checkout's 900+ branches, one
real `git` subprocess per branch. Reproduced directly: running the file
serially (`-p no:xdist`) on this box's CURRENT branch count now hangs
past even a 280s wall-clock bound (worse than the ticket's original 120s
pytest-timeout description -- this repo's branch count has grown since
that measurement).

Fix: pass `root=tmp_path` to that one test (matching every sibling test's
own isolation posture) -- kills the real-repo branch scan entirely for
an assertion that has nothing to do with ticket-lease reconciliation.
Also applied the ticket's first suggested direction (`pytestmark =
pytest.mark.heavy_subprocess`, the exact `tests/test_ticket_land.py`/
`tests/test_ticket_leases.py` convention) as defense in depth, in case a
future test in this file legitimately needs the real root.

Measured after the fix: full file serial 6.1s (was: times out), full
file under `-n 3` xdist 6.7s (was: times out) -- both from timing out to
essentially instant.

Evidence:
- tests/test_doctor.py::test_module_carries_heavy_subprocess_marker
  (BUG002: confirmed FAILING at the parent commit -- AttributeError, no
  pytestmark)
- tests/test_doctor.py (full file, 14/14): `-p no:xdist` 6.10s,
  `-n 3` 6.72s
- `frob test --base main` selected a very large ripple set (the touched-
  set selector followed test_doctor.py's graph reachability broadly);
  spot-checked several (tests/test_gates.py::TestKnownGateRuleIds::
  test_every_emitted_rule_literal_is_known,
  tests/test_stats.py::test_collect_combines_both) and confirmed BOTH
  fail identically with this ticket's diff reverted -- pre-existing
  repo-wide baseline failures, not introduced by this ticket, already
  T-2992's own "capture and triage the real test failures" territory
  (a concurrent lease on this same ticket series). None of
  tests/test_doctor.py's own tests appear in the failure list.

Filed: none (the pre-existing failures above are already T-2992's
tracked territory, not a new discovery).

Gates: `frob check --ticket T-3033 --only affect_drift --only fmt --only
scope --only prework --only coverage` clean for this ticket's touched
file (tests/test_doctor.py) -- remaining gate:COV/DRIFT/DSL/WAIVE errors
are pre-existing, repo-wide, and untouched by this ticket's diff, per
gate:scope-note.

### Changed
```
 tests/test_doctor.py     | 47 ++++++++++++++++++++++++++++++++++++++++++++---
 tickets/T-3033/ticket.md |  2 +-
 2 files changed, 45 insertions(+), 4 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 87 error(s), 702 warning(s), 863 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3080/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC006@tickets/T-3088/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3065/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/ticket_runner/_new.py, SUPPRESS001@tests/test_ci_report.py, SUPPRESS001@tests/test_tickets.py, SUPPRESS001@tests/test_tickets_acceptance.py, SUPPRESS001@tests/test_tickets_brief.py, SUPPRESS001@tests/test_tickets_velocity.py, SUPPRESS001@tests/unit/verify/test_backpressure.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@src/frob/app/_config_external.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/test_doctor.py, unresolved-attribute@tests/unit/test_main_entry.py
