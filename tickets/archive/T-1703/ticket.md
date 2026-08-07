---
id: T-1703
title: 'Post-land sweep reports CLEAN on a dirty tree: budget-truncated frob check
  parsed as measured-zero, and ty/dup errors never parsed at all'
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets.md
- src/frob/app/check_runner.py
- tests/unit/test_check_budget.py
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'root cause of a leaked-stdout-under---json defect discovered while fixing
    _unscoped_error_findings: --handle_early_exit_modes (--budget/--only list/--land-parity)
    runs BEFORE run()''s own quiet_stdout_logs(--json) wrap, so --budget --json''s
    own INFO log lines print into the same stdout stream as the JSON payload, corrupting
    it -- the exact T-0806 class of bug already fixed one guard later for _refuse_ticket_lease_mismatch/_handle_stamp_modes
    but missed for _handle_early_exit_modes; this directly breaks T-1703''s own --budget
    --json fix in production, not a tangential finding'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_check_budget.py
  reason: 'root cause of a leaked-stdout-under---json defect discovered while fixing
    _unscoped_error_findings: --handle_early_exit_modes (--budget/--only list/--land-parity)
    runs BEFORE run()''s own quiet_stdout_logs(--json) wrap, so --budget --json''s
    own INFO log lines print into the same stdout stream as the JSON payload, corrupting
    it -- the exact T-0806 class of bug already fixed one guard later for _refuse_ticket_lease_mismatch/_handle_stamp_modes
    but missed for _handle_early_exit_modes; this directly breaks T-1703''s own --budget
    --json fix in production, not a tangential finding'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: in-scope functions _check_gates_summary_fn/_check_gate_findings_fn/_shared_check_spawn_fn
    now spawn --json unconditionally (the T-1703 fix); this test file's fake-stdout
    fixtures simulate the OLD plain-text shape and must be updated to JSON to keep
    testing real production behavior, not a shape frob check no longer emits from
    these call sites
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_ty_and_gate_error_both_appear_in_parsed_set
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_budget_truncated_run_yields_none_not_a_partial_set
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_check_gates_summary_fn_returns_none_on_budget_truncated_run
- tests/unit/test_check_budget.py::TestRunBudgetedCheck::test_budget_json_stdout_is_pure_parsable_json
designated_repro_test: null
threat: null
component: null
---
The post-land sweep can report CLEAN on a tree that has errors. Observed
live 2026-08-06: `.frob/rapid-sweep/T-1542-c581c297e28f.log` recorded

    rapid sweep: recorded rolling baseline of 0 error(s)
    rapid sweep: T-1542 deferred unscoped sweep CLEAN

at a commit where a plain `frob check` reported five errors, two of them
TICK006 regressions that land had just introduced.

THIS IS NOT A RAPID-PROFILE BUG. `_unscoped_error_findings` is shared:
T-1456's synchronous, revert-on-red `standard` post-land sweep and
T-1514's pre-commit sweep call the identical function with the identical
budget. Every post-land sweep this repo has ever run has had this hole.
T-1684 only made it visible by logging the count.

ROOT CAUSE. The sweep spawns `frob check --budget 300`. `--budget` runs
as many STAGE GROUPS as fit the time budget and defers the rest. Gates
that never ran emit no error lines, and the parser cannot distinguish
"this gate ran and found nothing" from "this gate never ran". A partial
run is therefore parsed as a measured-empty set.

It is also time-dependent, which makes it worse than merely incomplete:
two `--budget 300` runs on the same tree minutes apart produced different
stage groups, so the sweep's "error identity set" is not a function of
tree state at all. The rolling baseline diff is comparing sets drawn from
different gate populations, which can manufacture BOTH false greens and
false regressions.

This directly violates the invariant the whole verification design rests
on: CANNOT VERIFY IS NEVER VERIFIED. The parser already honours that
invariant for one failure mode (no gate-summary line at all returns
`None`, explicitly "unmeasured, not necessarily zero"). It simply does
not know that a budget-truncated run is the same kind of event.

FIX.

1. STOP PARSING RENDERED CONSOLE OUTPUT. `frob check --json` already
   exists. Consume it. A regex over human-facing prose is a lexical
   scraper standing in for a structured result: it silently drops every
   diagnostic whose renderer does not match its assumed
   `[tag] file:line CODE` shape -- `[ty]` lines carry `file:line:col` and
   never match, and `[frob-dup]` lines lead with prose. Those two classes
   are invisible to every sweep today, independently of the budget bug.
   Verify this: a `ty` error and a `frob-dup` finding must both appear in
   the parsed set after the fix.
2. THE RESULT MUST CARRY WHICH STAGES RAN. If any stage group was
   deferred, skipped, or timed out, the sweep result is `None`
   (unmeasured) -- never a set. Partial coverage is not a smaller answer,
   it is a different question.
3. GIVE THE SWEEP AN UNBOUNDED-OR-EXPLICIT BUDGET. The deferred sweep
   runs detached and nothing waits on it, so the budget that existed to
   protect a synchronous land no longer buys anything under `rapid`. If a
   budget is kept for the synchronous profiles, exceeding it must return
   `None`, not a partial set.
4. Re-baseline `.frob/rapid-sweep-baseline.json` after the fix: the
   stored 0-finding baseline is a false record, and diffing against it
   would report every real pre-existing error as a new regression on the
   next land.

REGRESSION COVERAGE. Assert the actual invariant, not the plumbing: a
check whose output reflects a truncated/partial run must yield `None`
from `_unscoped_error_findings`, and a tree with a known `ty` error and a
known gate error must yield BOTH in the parsed set. A test that only
feeds a well-formed complete `## Errors` section proves nothing about
the failure mode that caused this ticket.

This is the highest-integrity item in the queue. Until it is fixed, no
sweep result -- in any profile -- is trustworthy evidence of anything,
and the T-1686 verification-watermark epic would be building a watermark
on top of a measurement that can silently read zero.