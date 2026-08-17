---
id: T-2235
title: 'frob check --budget silently drops whole gate families and exits normally:
  41 errors became 3 with no skip signal anywhere in the JSON'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/_check_chunking.py
- src/frob/app/check_runner.py
- tests/unit/test_check_budget.py
- docs/commands/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check_budget.py
  reason: T-2235 fix requires new regression tests for the budget-reporting fix; test
    file is the required evidence location for _check_chunking.py/check_runner.py
    changes
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/commands/check.md
  reason: T-2235 documents the new --budget JSON 'budget' key and corrects the now-inaccurate
    'never a silent drop' claim
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_budget_key_absent_and_complete_when_everything_ran
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_unbudgeted_json_has_no_budget_key
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result
- tests/unit/test_check_budget.py::TestBudgetCoverageReport::test_skipped_is_universe_minus_executed
- tests/unit/test_check_budget.py::TestBudgetCoverageReport::test_empty_skipped_present_not_absent
designated_repro_test: tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume
acceptance:
- text: 'A --json --budget run that cannot execute every planned gate emits an explicit
    record of which gates were NOT run, by name (fails today: JSON has only path and
    results)'
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume
  - tests/unit/test_check_budget.py::TestBudgetCoverageReport::test_skipped_is_universe_minus_executed
- text: A run that executed everything reports that positively -- an empty skipped-list
    must be distinguishable from an absent field
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume
  - tests/unit/test_check_budget.py::TestBudgetCoverageReport::test_skipped_is_universe_minus_executed
- text: 'MUST-STILL-PASS: unbudgeted frob check --json and a sufficient budget both
    produce current results unchanged (findings, ordering, exit codes)'
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_budget_key_absent_and_complete_when_everything_ran
  - tests/unit/test_check_budget.py::TestBudgetCoverageReport::test_empty_skipped_present_not_absent
- text: 'Exit-code semantics unchanged: a partial run with no findings must not start
    reporting failure'
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_unbudgeted_json_has_no_budget_key
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result
- text: Stderr/summary states in human-readable form that gates were skipped, without
    requiring JSON parsing
  evidence:
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_runs_selected_chunks_and_reports_result
  - tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_json_reports_universe_skip_despite_narrow_resume
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# `frob check --budget` silently drops whole gate families and exits normally, so a partial run reads as a dramatic improvement

## Measured evidence (2026-08-16)

Two runs of the SAME command, same budget, ~90 minutes apart, on the same repo:

    timeout 540 uv run frob check --json --budget 480

    run 1: exit=1   52 results   41 errors
    run 2: exit=1   15 results    3 errors

Run 2 exited with code 1, NOT 124 -- it was not killed by the shell timeout. It
terminated normally having run 15 of the 52 gates.

What run 2 silently omitted: `gate-summary`, `gate:ARCH`, `gate:COV`, and every
other `gate:*` family. It ran only the standalone tools (`frob-cycle`,
`frob-dup`, `frob-arch`, `claude-config-drift`, and the 11 `frob-exports(...)`
entries).

Consequently the error count fell 41 -> 3, which reads as a 93% improvement.
It is fiction: TICK004 (9 rot findings), COV004 (4), DOC011 (2), DRIFT001 (3),
ARCH001, TEST010 and COV001 were all still present and simply never evaluated.
I came within one sentence of reporting a floor drop that had not happened.

## The output gives a consumer no way to detect this

`--json` emits exactly two top-level keys:

    top-level keys: ['path', 'results']

Every element of `results` carries only `tool`, `exit_code`, `diagnostics`,
`tests`, `summary`. There is no budget record, no skipped/unrun marker, no
expected-total, and no `gate-summary` entry whose ABSENCE is itself the only
available hint. Nothing in stderr says a family was dropped either -- grepping
the stderr for `budget|truncat|exhaust` returns 0 matches, because those words
are never emitted.

So a consumer cannot distinguish "15 gates ran and the repo is clean" from
"15 of 52 ran and 37 were dropped". Both look identical, and the dropped case
looks BETTER because it reports fewer findings.

## Why this matters beyond one measurement

The budgeted path is not a niche flag. It is how the coordinator measures the
error floor and how post-land sweeps assess a tree. A mechanism whose failure
mode is "reports fewer errors, exits normally, says nothing" is the exact shape
that produces a false green -- and this repo has already paid for that shape
twice: T-1928 (FMT gate passing in 0.00s while `frob fmt --check` would rewrite
267 files) and T-1664, which established the governing rule that a check must
report UNRESOLVED rather than silently pass when it cannot analyse. That rule
is enforced for individual semantic checks but NOT for the runner's own
budget-driven gate selection.

## Do NOT fix it this way

- **Do NOT just raise the default budget.** That changes when the silence
  happens, not that it is silent. The defect is the missing signal.
- **Do NOT make `--budget` hard-fail when it cannot run everything.** Budgeted
  quick loops are legitimate and agents depend on them; turning a partial run
  into an error would break `--only` workflows and land-time checks.
- **Do NOT infer completeness by counting results and comparing to a
  hardcoded 52.** That number changes with `--only`, with per-package
  `frob-exports` expansion, and as gates are added. Completeness must be
  reported by the runner, which knows what it planned and what it skipped --
  not reconstructed by the reader.
- **Do NOT fix this only in `scripts/check_summary.py`.** A coordinator script
  papering over it leaves every other consumer (sweeps, land-time checks, other
  agents) still blind. The JSON is the contract; fix it there. Teaching
  check_summary to SURFACE the new field is fine as a follow-on.

## Acceptance criteria

1. (MUST FAIL FIRST) A `--json --budget N` run that cannot execute every
   planned gate emits an explicit record of what was NOT run -- names, not just
   a count. Fails today: the JSON has only `path` and `results`, with no such
   field anywhere. Confirm `--check-repro` reads FAILED_AT_PARENT.
2. A run that DID execute everything reports that fact positively (an empty
   skipped-list is not the same as an absent one, and a consumer must be able
   to tell "nothing skipped" from "this build of frob does not report skips").
3. MUST-STILL-PASS CONTROL: an unbudgeted `frob check --json` and a budget
   large enough to finish must both still produce their current results
   unchanged. A fix that alters findings, ordering, or exit codes on the
   complete path is out of scope and worse than the bug.
4. The exit code semantics do not change: a partial run with no findings must
   not start reporting failure. This is a REPORTING fix.
5. Stderr or the summary states plainly, in human-readable form, that gates
   were skipped -- an operator reading a terminal must see it without parsing
   JSON.

## Scope note

`--budget` is consumed at `src/frob/app/check_runner.py:1028-1029`, which
delegates to `_run_budgeted_check` in `src/frob/app/_check_chunking.py` -- that
is where the plan-vs-executed knowledge lives. Verified by reading the call
site, not inferred from module names. If the skip decision turns out to live
elsewhere, widen scope with a measured reason rather than guessing.

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
