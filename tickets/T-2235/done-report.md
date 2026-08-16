## Done report

frob check --budget's per-invocation deferred/BUDGET001 signal only
reflects the tail of THAT call's own resume state, which can already be
a narrow leftover of an earlier, unrelated invocation (measured
incident: a repro against a stale one-group resume state reported zero
deferred and exited clean while four of five stage groups never ran).

Fix: _budget_coverage_report (frob/app/_check_chunking.py) computes
skipped_groups against the FULL available_stages() universe minus what
THIS call actually executed, never against the local deferred list.
_run_budgeted_check now always builds this report and splices it onto
the JSON payload as a top-level "budget" key
(requested_seconds/executed_groups/skipped_groups/complete) via
_report_check_result/_result_as_json_with_fix
(frob/app/check_runner.py), present on every --budget call and absent
on every non-budgeted call (MUST-STILL-PASS acceptance 3 -- unbudgeted
and complete-budget JSON/text/exit codes are unchanged, verified by a
dedicated regression test). _warn_budget_skipped emits an unconditional
WARNING-level stderr line (never gated on --json, never leaks into the
stdout JSON payload -- config.toml's below_warning filter keeps
WARNING+ off stdout) naming every skipped group, satisfying acceptance
5's human-readable requirement. Exit-code semantics are untouched
(still result.total_errors > 0), satisfying acceptance 4.

Repro-first: the failing test was committed alone (6cc8c4f95) and
verified FAILED_AT_PARENT against it before the fix commit
(6bc61b363..5976f1be5) was added on top -- frob ticket evidence
--check-repro --base-ref 6cc8c4f95 confirms FAILED_AT_PARENT.

docs/commands/check.md updated to describe the new "budget" JSON key
and to correct its now-inaccurate "never a silent drop" claim about
BUDGET001 alone.

### Changed
```
 docs/commands/check.md          |  23 ++++++-
 src/frob/app/_check_chunking.py |  79 +++++++++++++++++++++--
 src/frob/app/check_runner.py    |  68 ++++++++++++++++----
 tests/unit/test_check_budget.py | 136 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-2235/ticket.md        |  47 +++++++++++---
 5 files changed, 326 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_budget_key_absent_and_complete_when_everything_ran` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_unbudgeted_json_has_no_budget_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestBudgetCoverageReport::test_skipped_is_universe_minus_executed` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestBudgetCoverageReport::test_empty_skipped_present_not_absent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2235/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2235/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2235, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
