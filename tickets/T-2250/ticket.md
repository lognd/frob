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