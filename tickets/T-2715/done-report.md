## Done report

Changed:
src/frob/app/_check_chunking.py::_derive_post_land_sweep_budget_s
src/frob/app/_check_chunking.py::_BUDGET_DERIVE_HEADROOM
src/frob/app/_check_chunking.py::_POST_LAND_SWEEP_BUDGET_FLOOR_S
src/frob/app/ticket_runner/_land_cmd.py::_unscoped_error_findings
src/frob/app/ticket_runner/_land_cmd.py::land_parity_findings
src/frob/app/ticket_runner/_rapid_sweep.py::_matching_error_diagnostics
src/frob/app/ticket_runner/_rapid_sweep.py::_true_finding_count_for_identities
src/frob/app/ticket_runner/_rapid_sweep.py::_identities_still_reproducing

Fix direction chosen: (1) from the ticket's own preference order -- derive
the post-land sweep budget from root's own recorded
`.frob/check-budget-timing.json` stage timing (measured total * 1.5
headroom, floored at 300s, falling back to the old hardcoded 480 only when
a checkout has no/sparse timing data yet) instead of the frozen
`_POST_LAND_SWEEP_BUDGET_S = 480` constant. Chose (1) over (2)/(3) because
(1) removes the recurrence mechanism outright: a hardcoded ceiling
re-derived once per incident (T-2456 raised 300->480, already stale again
by T-2715) has now proven itself a repeating failure class, and a live
derivation ties the ceiling to the same timing file the budget planner
(`_select_budget_chunks`) already reads, so the two can never diverge
again without external interference. (2)'s drift check becomes moot under
(1): there is no longer a static number to drift away from the
measurement. (3) was not pursued -- the ticket's own text flags it as the
weaker option ("buys little there"), and moving the budget check off the
land-adjacent detached-sweep architecture would be a larger, unscoped
change touching `_land_drain`/rapid-sweep scheduling, not a minimal fix
to the shortfall. Also fixed the SAME class of bug, in scope, at
`_rapid_sweep.py`'s `_TRUE_COUNT_BUDGET_S` (300) -- a second hand-synced
hardcoded duplicate of the same constant whose own comment already
admitted the sync-by-hand risk, and which had ALREADY drifted (still 300
while `_land_cmd`'s had moved to 480) before this ticket even started.

T-2713 untouched: `_budget_skipped_groups_from_payload` and every other
`_verify.py` function are outside this change's scope and outside the
touched-file list below; the derived-budget change only affects how large
`budget` is BEFORE a spawn, never how a completed/skipped run is
interpreted afterward.

Evidence:
tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_derives_from_measured_timing_with_headroom
tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_falls_back_to_default_with_no_timing_data
tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_floor_protects_against_sparse_timing_data

Positive controls (both directions):
- test_derives_from_measured_timing_with_headroom reproduces this
  ticket's own live incident numbers (168.49+88.48+135.35+3.69+96.17 =
  492.18s measured total) and asserts the derived budget EXCEEDS that
  total -- the old hardcoded 480 did not.
- test_falls_back_to_default_with_no_timing_data + the floor test cover
  the "still refuses to run wild" direction: no timing data uses the
  caller's `default` verbatim, and sparse timing data is floored rather
  than trusted at face value.
- T-2713's own guarantee (a genuinely unmeasurable run, e.g. a killed
  stage, still refuses to advance) is untouched: no line in
  `_verify.py`'s budget-skip detection changed, and the derived-budget
  change only widens the WINDOW a run gets to complete inside, it cannot
  make a truly incomplete run report as complete.
- Live-backlog validation: ran `frob check --ticket T-2715` (touched-set)
  clean of new findings, ran the full touched test files
  (test_check_budget.py, relevant test_ticket_work_and_land_finish.py
  classes, test_rapid_sweep.py true-count/reproducing classes) -- all
  green. `frob verify now` against the real root backlog is run
  post-land (a real land was in flight in a sibling worktree at
  implementation time -- T-2706 -- so root's own live `frob verify now`
  proof is captured after this lands, not before, per playbook's "no
  concurrent-land root work" rule).

Filed: none

Gates: `frob check --ticket T-2715` clean of new findings (ARCH001 on
`_matching_error_diagnostics`, COV001 on the new function, and PRE001
stale-sweep were all fixed during implementation via a docstring trim,
underscore-prefixing the new helper as private, and `frob ticket sweep`
respectively -- confirmed clean on the re-run).

### Changed
```
 tickets/T-2715/ticket.md | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_derives_from_measured_timing_with_headroom` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_falls_back_to_default_with_no_timing_data` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestDerivePostLandSweepBudget::test_floor_protects_against_sparse_timing_data` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 42 error(s), 1065 warning(s), 681 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
