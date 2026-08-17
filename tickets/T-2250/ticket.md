---
id: T-2250
title: 'frob check --budget silently ignores --only: ''--only lint --budget 120''
  runs gates-fast and reports lint as skipped'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/_check_chunking.py
- src/frob/app/check_runner.py
- tests/unit/test_check_budget.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check_budget.py
  reason: T-2250 fix requires new regression tests for the --only/--budget combination
    fix; test file is the required evidence location for _check_chunking.py/check_runner.py
    changes
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_scoped_budget_runs_exactly_the_named_group
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_scoped_budget_never_touches_shared_resume_state
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_budget_combo_refuses_a_bare_gate_name
- tests/unit/test_check_budget.py::TestResolveBudgetOnlyScope::test_bare_gate_name_raises_unplannable
designated_repro_test: tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_scoped_budget_runs_exactly_the_named_group
acceptance:
- text: '''--only lint --budget N --json'' executes the lint group or refuses explicitly,
    never a different group (fails today: runs gates-fast, reports lint skipped)'
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_scoped_budget_runs_exactly_the_named_group
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_budget_combo_refuses_a_bare_gate_name
  - tests/unit/test_check_budget.py::TestResolveBudgetOnlyScope::test_bare_gate_name_raises_unplannable
- text: 'MUST-STILL-PASS: --budget without --only, and --only without --budget, both
    behave exactly as today'
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume
- text: The persisted resume file is not narrowed by an --only-scoped run in a way
    a later unrestricted run inherits; state what it contains and why that is safe
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_scoped_budget_never_touches_shared_resume_state
- text: 'T-2235''s budget JSON key stays accurate under the combination: executed_groups
    names what actually ran'
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_only_scoped_budget_runs_exactly_the_named_group
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# `--budget` silently ignores `--only`: `frob check --only lint --budget 120` runs gates-fast and reports lint as skipped

## Measured evidence (2026-08-16, on `e02bf61b20be` -- immediately after T-2235 landed)

With NO pre-existing `.frob/check-budget-state.json` (verified absent first, so
nothing was inherited from an earlier invocation):

    $ frob check --only lint --budget 120 --json
    budget: {'requested_seconds': 120,
             'executed_groups': ['gates-fast'],
             'skipped_groups': ['gates-native', 'gates-security', 'lint', 'static'],
             'complete': False}

I asked for `lint`. It ran `gates-fast` and reported `lint` as one of the
groups that did not run. The `--only` selection was discarded entirely and the
budget path planned over all five stage groups.

The same `--only` works correctly when `--budget` is absent:

    $ frob check --only lint --json
    tools run: ['claude-config-drift', 'ruff-check', 'ruff-format', 'ty']

So `--only` is honoured on the normal path and dropped on the budgeted path.

It also persisted a resume list of the groups it did not run:

    $ cat .frob/check-budget-state.json
    ["gates-native", "gates-security", "lint", "static"]

which the NEXT budgeted invocation inherits -- the mechanism T-2235 just
documented and made visible.

## Why this matters

`--only <group>` is not optional guidance here: T-0627 requires agents to run
`frob check` in `--only <group>` loops, because a bare `frob check` under
FROB_AGENT exits 1 by design. An agent that adds `--budget` to bound the cost
of one of those loops silently gets a DIFFERENT group than it asked for. The
JSON it reads back describes work it never requested, and the group it wanted
is listed as skipped.

This was invisible before T-2235 landed. That fix is what made the discrepancy
observable at all -- the `budget` key and the "did NOT run" warning are
precisely what exposed it.

## Do NOT fix it this way

- **Do NOT make `--only` and `--budget` mutually exclusive.** Bounding the cost
  of a single group is a legitimate and useful request, and refusing the
  combination would push agents back toward unbudgeted full runs -- the thing
  `--budget` exists to avoid.
- **Do NOT have `--budget` narrow the persisted resume file to the `--only`
  selection.** The resume state is shared across invocations; letting a
  `--only` run rewrite it would make the next unrestricted budgeted run inherit
  an artificially narrow plan. That is the exact defect class T-2235 fixed --
  do not reintroduce it from the other direction.
- **Do NOT silently widen `--only` to "all groups, budget-ordered".** That is
  the current behaviour and it is the bug: the flag is accepted and discarded.
  If a combination genuinely cannot be honoured, REFUSE it with a message
  naming why -- never accept a flag and ignore it.

## Acceptance criteria

1. (MUST FAIL FIRST) `frob check --only lint --budget N --json` executes the
   lint group (or refuses explicitly), never a different group. Fails today:
   executes `gates-fast` and reports `lint` skipped. Confirm `--check-repro`
   reads FAILED_AT_PARENT.
2. MUST-STILL-PASS CONTROLS:
   - `--budget N` with NO `--only` behaves exactly as it does today
     (T-2235's coverage reporting, resume-state handling, exit codes unchanged);
   - `--only <group>` with NO `--budget` behaves exactly as today.
   A fix that perturbs either path is worse than the bug.
3. The persisted `.frob/check-budget-state.json` is not narrowed by an
   `--only`-scoped invocation in a way a later unrestricted run would inherit.
   State explicitly what the resume file contains after an `--only` budgeted
   run, and why that is safe.
4. T-2235's `budget` JSON key remains accurate under the combination --
   `executed_groups` must name what actually ran.

## Scope note

`src/frob/app/_check_chunking.py` (owner of `_run_budgeted_check` and the
resume state) and `src/frob/app/check_runner.py` (where `--budget` is consumed,
around line 1028). Both were just touched by T-2235, so its author has the
context.

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
