## Done report

frob check --only <group> --budget N discarded --only entirely: the
early-exit dispatch in check_runner.run checked check_budget before
ever looking at check_only, so a scoped request fell straight into
_run_budgeted_check's unrestricted self-selection over the full
5-group available_stages() universe -- it could run a different group
than requested and report the requested one as "skipped" (measured:
--only lint --budget 120 ran gates-fast, reported lint skipped).

Fix, in _check_chunking.py only (check_runner.py's dispatch order was
untouched -- the combination is resolved entirely inside
_run_budgeted_check, matching the "do not make them mutually
exclusive" constraint):

- _resolve_budget_only_scope validates cfg.check_only against
  available_stages(); a recognized stage-group alias becomes the exact
  candidate list _run_budgeted_check plans over (never widened to
  every group); a bare gate/tool name (not itself a whole alias, e.g.
  "ruff") raises _BudgetOnlyUnplannable, and the caller REFUSES loudly
  (exit 1, a "config" ToolResult naming the offending value and the
  recognized aliases) rather than silently discarding --only or
  silently expanding it.
- _resolve_budget_remaining returns (remaining, scoped); scoped=True
  means an --only-scoped call, which never reads OR writes
  .frob/check-budget-state.json in either direction -- the shared
  resume file stays exactly what an unrestricted run left it, so a
  scoped call can never narrow what a later unrestricted --budget call
  inherits (the T-2235 defect class, closed from the other direction).
- The T-2235 "budget" JSON key's reporting universe is the caller's
  own --only selection for a scoped run, never the full universe, so
  it never claims a group the caller did not ask for was "skipped".

MUST-STILL-PASS verified directly: --budget alone still plans/persists
over the full 5-group universe exactly as before (test_only_scoped_
budget_never_touches_shared_resume_state's own second half exercises
an unrestricted call after a scoped one and asserts it is unaffected);
--only alone (no --budget) is untouched code path, unchanged.

Repro-first: the failing test was committed alone (887c3e870) and
verified FAILED_AT_PARENT against it before the fix commit (f9f79f482)
was added on top -- frob ticket evidence --check-repro --base-ref
887c3e870 confirms FAILED_AT_PARENT.

Manually reproduced the exact measured incident end to end pre- and
post-fix: `frob check --only lint --budget 120 --json` now runs
exactly lint (budget.executed_groups=["lint"], skipped_groups=[],
complete=true) and leaves no .frob/check-budget-state.json behind; a
following unrestricted `frob check --budget 120 --json` still plans
over the full universe and persists resume state exactly as T-2235
established.

### Changed
```
 src/frob/app/_check_chunking.py | 298 ++++++++++++++++++++++++++++++++--------
 tests/unit/test_check_budget.py | 159 +++++++++++++++++++++
 tickets/T-2250/ticket.md        |  35 ++++-
 3 files changed, 429 insertions(+), 63 deletions(-)
```

### Evidence
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_scoped_budget_runs_exactly_the_named_group` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_scoped_budget_never_touches_shared_resume_state` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_budget_combo_refuses_a_bare_gate_name` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_budget.py::TestResolveBudgetOnlyScope::test_bare_gate_name_raises_unplannable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2250/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2250/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2250, RENDER001@src/frob/scaffold/_skills_sync.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
