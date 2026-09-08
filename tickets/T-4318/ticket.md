---
id: T-4318
title: Deferred post-land sweep is wall-clock-budgeted with nobody waiting, and verify
  status hides the resulting debt
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/rapid_sweep_suite/test_sweep_run.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the detached call site that must pass full=True to _unscoped_error_findings
    (_measure_fresh_and_write_baseline) lives here; _land_cmd.py's full=True mechanism
    already exists but this caller never opts in
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/rapid_sweep_suite/test_sweep_run.py
  reason: T-4318's regression test (test_calls_unscoped_error_findings_with_full_true)
    lives here; adding it to scope so gate:SCOPE/COV can bind this diff to the ticket
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: disclose SCOPE002 acceptance for _land_cmd.py's pre-existing closure, per
    T-4301/T-4289/T-4255/T-4310 precedent
  actor: logan
  at: '2026-09-08'
  old_length: 2780
  new_length: 4372
evidence:
- tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_calls_unscoped_error_findings_with_full_true
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4315 (which is scoped only to src/frob/tickets/_land.py
and cannot house this fix -- the mechanism lives entirely outside that file).

MEASURED: all 5 lands today (T-4197, T-4301, T-4305, T-4306, T-4307) produced
a deferred post-land sweep that reported UNMEASURABLE. Each sweep log
(.frob/rapid-sweep/<ticket>-<sha>.log) shows the same pair of lines: a
"frob check --json --budget" run deferred 3 stage groups (gates-security,
lint, static), then run_deferred_post_land_sweep
(src/frob/app/ticket_runner/_rapid_sweep.py, _measure_fresh_and_write_baseline)
correctly refuses to treat that truncated run as a smaller answer and returns
Err(Unmeasurable) -- that refusal logic is correct and must not change.

ROOT CAUSE: the check invocation this sweep runs is _unscoped_error_findings
(src/frob/app/ticket_runner/_land_cmd.py), whose --budget value comes from
_derive_post_land_sweep_budget_s (src/frob/app/_check_chunking.py) -- a
wall-clock estimate tuned for an INLINE, foreground land someone is waiting
on. The deferred sweep (spawn_deferred_post_land_sweep -> "frob ticket
sweep-async", a DETACHED child with start_new_session=True) reuses the exact
same budget-derivation call with no signal that this invocation is
off-critical-path and nobody is waiting -- so under load it truncates
exactly like an interactive call would, buying zero latency benefit while
losing the entire measurement.

FIX DIRECTION (ticket author's call, not dictated here): give
_unscoped_error_findings / _derive_post_land_sweep_budget_s a way to know
this specific call site is detached (e.g. a detached: bool parameter
threaded from _sweep_async / run_deferred_post_land_sweep) and either omit
--budget entirely on that path, or scale it far above the interactive
estimate (e.g. no ceiling, or a generous multiple of measured full-check
time) since a detached child has no caller-visible deadline to protect.

SECOND DEFECT (also found working T-4315, needs its own scope --
src/frob/app/verify_runner.py and/or src/frob/verify/_watermark.py, wherever
frob verify status's "unverified depth" is computed, plus wherever
rapid-debt.jsonl entries are read back): "frob verify status" reports
"unverified depth (queued land-intents): 0" and "quarantine: clear" even
though .frob/rapid-debt.jsonl has 5 live
skipped: post-land-unscoped-sweep-deferred entries (for the 5 commits
above) that were never cleared or promoted because their sweep never
completed. "frob ticket show" for all 5 tickets prints only [done] with no
unverified/debt marker at all. An UNMEASURABLE sweep currently reaches
nobody outside a log file nobody reads -- this needs its own fix,
independent of the budget fix above, so a commit that stays unverified is
visible wherever a verified result would be.


# frob:waive SCOPE002 reason="src/frob/app/ticket_runner/_land_cmd.py is a large
shared land-command module whose pre-existing frob:doc/frob:tests/private-helper
closure spans dozens of unrelated files (docs/modules/tickets-landing.md,
docs/modules/tickets-verify-sweep.md, docs/modules/tickets-merge-driver.md,
docs/design/registry/EXHAUSTIVENESS-GATE.md, docs/modules/gates.md, plus ~20
test files covering land/merge-driver/verify-sweep/release-bump behavior this
ticket's actual diff never touches). T-4318's real change is two lines: (1)
_measure_fresh_and_write_baseline (src/frob/app/ticket_runner/_rapid_sweep.py,
already in scope) now passes full=True to _unscoped_error_findings instead of
defaulting to a --budget ceiling tuned for an inline foreground land, and (2)
a regression test asserting that. Pulling the whole transitive closure of
_land_cmd.py's pre-existing symbols (unrelated to this fix) into scope would
be scope creep out of proportion to the actual change -- same doc-anchor/
scope-closure tension already documented and accepted by T-4301, T-4289, and
T-4255's identical SCOPE002 waivers on other large shared CLI-runner modules.
Per T-4310's own measured finding, this frob:waive SCOPE002 directive is
DEAD TEXT under the current tickets/T-####/ticket.md-per-file ledger layout
(gate:SCOPE's SCOPE002 violation is hardcoded to file='tickets.md', which the
graph walker never parses in this format, so no WAIVE edge is ever created) --
disclosed here per the same accepted-gap precedent, not as a claim that this
directive mechanically clears the gate finding."